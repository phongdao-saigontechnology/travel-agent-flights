"""API request/response models."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    thread_id: str | None = Field(
        default=None,
        description="Thread ID for conversation continuity. If None, creates a new thread.",
    )
    message: str = Field(
        ...,
        min_length=1,
        description="User message to send to the agent",
    )


class ToolCall(BaseModel):
    """Represents a tool call made by the agent."""

    name: str
    arguments: dict[str, Any]


class BookingConfirmation(BaseModel):
    """Pending booking that requires confirmation."""

    booking_type: str = Field(description="Type: flight, hotel, or transfer")
    offer_id: str = Field(description="ID of the offer to be booked")
    description: str = Field(description="Human-readable booking description")
    price: float = Field(description="Total price")
    currency: str = Field(description="Currency code")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional booking details",
    )


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    thread_id: str = Field(description="Thread ID for this conversation")
    response: str = Field(description="Agent's response message")
    tool_calls: list[ToolCall] = Field(
        default_factory=list,
        description="Tools called during this turn",
    )
    pending_confirmation: BookingConfirmation | None = Field(
        default=None,
        description="Booking awaiting user confirmation, if any",
    )


class StreamEvent(BaseModel):
    """Event model for streaming responses."""

    event: str = Field(description="Event type: token, tool_call, done, error")
    data: str | dict[str, Any] = Field(description="Event data")


class ConfirmationDecision(BaseModel):
    """User decision for a pending booking confirmation."""

    action: Literal["approve", "reject", "edit"] = Field(
        description="Decision: approve, reject, or edit the booking"
    )
    edits: dict[str, Any] | None = Field(
        default=None,
        description="Modified values if action is 'edit'",
    )
    reason: str | None = Field(
        default=None,
        description="Optional reason for rejection",
    )


class ConfirmationResponse(BaseModel):
    """Response after processing a booking confirmation."""

    success: bool = Field(description="Whether the confirmation was processed")
    message: str = Field(description="Result message")
    booking_reference: str | None = Field(
        default=None,
        description="Booking reference number if confirmed",
    )


class ThreadState(BaseModel):
    """Current state of a conversation thread."""

    thread_id: str
    message_count: int
    has_pending_booking: bool
    cart_items: int
    last_updated: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(default="healthy")
    version: str
    amadeus_configured: bool
    openai_configured: bool


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(description="Error type")
    message: str = Field(description="Error message")
    details: dict[str, Any] | None = Field(
        default=None,
        description="Additional error details",
    )
