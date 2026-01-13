"""Chat API routes."""

import asyncio
import json
import uuid
from typing import AsyncGenerator

import structlog
from fastapi import APIRouter, HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from sse_starlette.sse import EventSourceResponse

from travel_agent.agent.graph import create_llm, create_travel_agent
from travel_agent.config import get_settings
from travel_agent.models.api import (
    ChatRequest,
    ChatResponse,
    ConfirmationDecision,
    ConfirmationResponse,
    FollowUpChats,
    ThreadState,
    ToolCall,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/chat", tags=["chat"])

# Store for active agents (in production, use Redis or similar)
_agents: dict = {}

# Prompt for generating follow-up suggestions
SUGGESTIONS_PROMPT = """Based on this travel assistant conversation, generate exactly 3 brief \
follow-up chats the user might want to ask next.

The chats should be:
- Relevant to the conversation context
- Actionable and specific
- Short (under 10 words each)

User asked: {user_message}

Assistant responded: {assistant_response}"""


async def generate_suggestions(user_message: str, assistant_response: str) -> list[str]:
    """Generate follow-up suggestions using the LLM with structured output.

    Args:
        user_message: The user's original message
        assistant_response: The assistant's response

    Returns:
        List of 3 suggested follow-up questions
    """
    try:
        settings = get_settings()
        llm = create_llm(settings)

        # Use structured output - LLM returns validated Pydantic object
        structured_llm = llm.with_structured_output(FollowUpChats)

        prompt = SUGGESTIONS_PROMPT.format(
            user_message=user_message[:200],  # Truncate for efficiency
            assistant_response=assistant_response[:500],
        )

        result = await asyncio.to_thread(
            structured_llm.invoke,
            [HumanMessage(content=prompt)]
        )

        # Result is already a FollowUpSuggestions object - no parsing needed
        return result.chats[:3]

    except Exception as e:
        logger.warning("suggestions_generation_failed", error=str(e))

    # Fallback suggestions
    return [
        "Tell me more about the options",
        "What are the prices?",
        "Can you help me book this?"
    ]


def get_or_create_agent(thread_id: str):
    """Get existing agent or create new one for the thread."""
    if thread_id not in _agents:
        _agents[thread_id] = create_travel_agent()
    return _agents[thread_id]


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a message to the travel agent and get a response.

    If thread_id is not provided, a new conversation thread is created.
    The agent processes the message and returns its response along with
    any tool calls made during processing.
    """
    # Generate thread_id if not provided
    thread_id = request.thread_id or str(uuid.uuid4())

    logger.info("chat_request", thread_id=thread_id, message=request.message[:50])

    try:
        agent = get_or_create_agent(thread_id)
        config = {"configurable": {"thread_id": thread_id}}

        # Invoke the agent
        result = await asyncio.to_thread(
            agent.invoke,
            {"messages": [HumanMessage(content=request.message)]},
            config=config,
        )

        # Extract the response
        messages = result.get("messages", [])
        if not messages:
            raise HTTPException(status_code=500, detail="No response from agent")

        # Get the last AI message
        last_message = messages[-1]
        response_text = ""
        tool_calls_list = []

        if isinstance(last_message, AIMessage):
            response_text = last_message.content or ""

            # Extract tool calls if any
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                for tc in last_message.tool_calls:
                    tool_calls_list.append(
                        ToolCall(
                            name=tc.get("name", ""),
                            arguments=tc.get("args", {}),
                        )
                    )

        return ChatResponse(
            thread_id=thread_id,
            response=response_text,
            tool_calls=tool_calls_list,
            pending_confirmation=None,  # TODO: Implement HITL detection
        )

    except Exception as e:
        logger.exception("chat_error", thread_id=thread_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> EventSourceResponse:
    """Stream the agent's response using Server-Sent Events.

    This endpoint streams tokens as they are generated, providing
    real-time feedback to the user.
    """
    thread_id = request.thread_id or str(uuid.uuid4())

    logger.info("chat_stream_request", thread_id=thread_id)

    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            agent = get_or_create_agent(thread_id)
            config = {"configurable": {"thread_id": thread_id}}

            # Collect full response for suggestions
            full_response = ""

            # Stream events from the agent
            for event in agent.stream(
                {"messages": [HumanMessage(content=request.message)]},
                config=config,
                stream_mode="messages",
            ):
                # event is a tuple of (message, metadata)
                if isinstance(event, tuple) and len(event) >= 1:
                    message = event[0]
                    if isinstance(message, AIMessage):
                        if message.content:
                            full_response += message.content
                            yield {
                                "event": "token",
                                "data": json.dumps({"content": message.content}),
                            }

            # Generate follow-up suggestions
            if full_response:
                suggestions = await generate_suggestions(
                    request.message, full_response
                )
                yield {
                    "event": "suggestions",
                    "data": json.dumps({"suggestions": suggestions}),
                }

            # Send completion event
            yield {
                "event": "done",
                "data": json.dumps({"thread_id": thread_id}),
            }

        except Exception as e:
            logger.exception("stream_error", thread_id=thread_id)
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }

    return EventSourceResponse(event_generator())


@router.post("/{thread_id}/confirm", response_model=ConfirmationResponse)
async def confirm_booking(
    thread_id: str,
    decision: ConfirmationDecision,
) -> ConfirmationResponse:
    """Approve, reject, or edit a pending booking.

    This endpoint is used for human-in-the-loop confirmation of bookings.
    When a booking requires confirmation, the agent will return a
    pending_confirmation in the response.
    """
    logger.info(
        "booking_confirmation",
        thread_id=thread_id,
        action=decision.action,
    )

    if thread_id not in _agents:
        raise HTTPException(status_code=404, detail="Thread not found")

    try:
        if decision.action == "approve":
            return ConfirmationResponse(
                success=True,
                message="Booking confirmed successfully.",
                booking_reference=f"BK-{uuid.uuid4().hex[:8].upper()}",
            )
        elif decision.action == "reject":
            return ConfirmationResponse(
                success=True,
                message=f"Booking cancelled. {decision.reason or ''}".strip(),
                booking_reference=None,
            )
        else:  # edit
            return ConfirmationResponse(
                success=True,
                message="Booking details updated. Please confirm again.",
                booking_reference=None,
            )

    except Exception as e:
        logger.exception("confirmation_error", thread_id=thread_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{thread_id}/state", response_model=ThreadState)
async def get_thread_state(thread_id: str) -> ThreadState:
    """Get the current state of a conversation thread."""
    if thread_id not in _agents:
        raise HTTPException(status_code=404, detail="Thread not found")

    try:
        agent = _agents[thread_id]
        config = {"configurable": {"thread_id": thread_id}}

        # Get the current state
        state = agent.get_state(config)
        messages = state.values.get("messages", [])

        from datetime import datetime

        return ThreadState(
            thread_id=thread_id,
            message_count=len(messages),
            has_pending_booking=False,  # TODO: Check actual state
            cart_items=0,  # TODO: Check actual cart
            last_updated=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.exception("get_state_error", thread_id=thread_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{thread_id}")
async def delete_thread(thread_id: str) -> dict:
    """Delete a conversation thread and its history."""
    if thread_id not in _agents:
        raise HTTPException(status_code=404, detail="Thread not found")

    del _agents[thread_id]
    logger.info("thread_deleted", thread_id=thread_id)

    return {"message": f"Thread {thread_id} deleted successfully"}
