"""LangGraph agent definition for the travel agent."""

from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from travel_agent.agent.prompts import SYSTEM_PROMPT
from travel_agent.config import get_settings
from travel_agent.tools.car_tools import add_transfer_to_cart, search_car_rentals, search_transfers
from travel_agent.tools.flight_tools import (
    add_flight_to_cart,
    confirm_flight_booking,
    get_flight_price_confirmation,
    search_flights,
)
from travel_agent.tools.hotel_tools import add_hotel_to_cart, get_hotel_details, search_hotels
from travel_agent.tools.utility_tools import (
    calculate_trip_duration,
    format_booking_summary,
    get_airline_info,
    get_current_date,
    search_airports,
)

# Collect all tools
ALL_TOOLS = [
    # Flight tools
    search_flights,
    get_flight_price_confirmation,
    add_flight_to_cart,
    confirm_flight_booking,
    # Hotel tools
    search_hotels,
    get_hotel_details,
    add_hotel_to_cart,
    # Car/Transfer tools
    search_transfers,
    search_car_rentals,
    add_transfer_to_cart,
    # Utility tools
    search_airports,
    get_current_date,
    get_airline_info,
    calculate_trip_duration,
    format_booking_summary,
]


def create_llm(settings):
    """Create the appropriate LLM based on provider configuration.

    Args:
        settings: Application settings with provider configuration.

    Returns:
        Configured ChatOpenAI or AzureChatOpenAI instance.
    """
    if settings.llm_provider == "azure_openai":
        return AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            azure_deployment=settings.azure_openai_deployment_name,
            api_key=settings.azure_openai_api_key.get_secret_value(),
            api_version=settings.azure_openai_api_version,
            reasoning_effort=settings.reasoning_effort,
        )
    return ChatOpenAI(
        model=settings.model_name,
        reasoning_effort=settings.reasoning_effort,
        api_key=settings.openai_api_key.get_secret_value(),
    )


def create_travel_agent(checkpointer=None):
    """Create the travel agent graph.

    Args:
        checkpointer: Optional checkpointer for state persistence.
                     Defaults to MemorySaver for development.

    Returns:
        Compiled LangGraph agent
    """
    # Initialize the LLM with tools
    settings = get_settings()
    model = create_llm(settings)
    model_with_tools = model.bind_tools(ALL_TOOLS)

    # Define the agent node
    def agent_node(state: MessagesState):
        """Call the model to generate a response."""
        # Add system prompt as the first message if not present
        messages = state["messages"]

        # Check if system message exists
        has_system = any(
            getattr(msg, "type", None) == "system"
            or (hasattr(msg, "content") and msg.content == SYSTEM_PROMPT)
            for msg in messages
        )

        if not has_system:
            from langchain_core.messages import SystemMessage

            messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)

        response = model_with_tools.invoke(messages)
        return {"messages": [response]}

    # Create the tool node
    tool_node = ToolNode(ALL_TOOLS)

    # Build the graph
    graph = StateGraph(MessagesState)

    # Add nodes
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    # Add edges
    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        tools_condition,
        {
            "tools": "tools",
            END: END,
        },
    )
    graph.add_edge("tools", "agent")

    # Use provided checkpointer or default to MemorySaver
    if checkpointer is None:
        checkpointer = MemorySaver()

    # Compile and return
    return graph.compile(checkpointer=checkpointer)


# Create a default agent instance
def get_default_agent():
    """Get the default travel agent instance with memory checkpointer."""
    return create_travel_agent()
