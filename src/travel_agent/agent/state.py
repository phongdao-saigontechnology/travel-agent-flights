"""State schema for the Travel Agent."""

from typing import Annotated, Any

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class TravelSearchContext(TypedDict, total=False):
    """Context for the current travel search."""

    # Flight context
    origin: str
    destination: str
    departure_date: str
    return_date: str | None
    adults: int
    children: int
    travel_class: str | None

    # Hotel context
    hotel_city: str
    check_in_date: str
    check_out_date: str
    hotel_guests: int
    room_quantity: int

    # Car/Transfer context
    pickup_location: str
    dropoff_location: str
    pickup_date: str
    dropoff_date: str


class BookingItem(TypedDict):
    """A single booking item (flight, hotel, or car)."""

    type: str  # "flight", "hotel", "car", "transfer"
    offer_id: str
    offer_data: dict[str, Any]
    price: float
    currency: str
    description: str
    confirmed: bool


class TravelerInfo(TypedDict, total=False):
    """Traveler information for booking."""

    id: str
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str  # "MALE" or "FEMALE"
    email: str
    phone: str
    document_type: str  # "PASSPORT", "ID_CARD"
    document_number: str
    document_expiry: str
    document_issuance_country: str
    nationality: str


class TravelAgentState(TypedDict):
    """Main state schema for the Travel Agent.

    This state persists across the conversation and tracks:
    - Conversation messages
    - Current search context
    - Search results cache
    - Selected items pending booking
    - Traveler information
    - Booking confirmation status
    """

    # Core messages - uses add_messages reducer to append
    messages: Annotated[list[AnyMessage], add_messages]

    # Search context - current travel search parameters
    search_context: TravelSearchContext

    # Search results cache - avoid re-fetching
    flight_offers: list[dict[str, Any]]
    hotel_offers: list[dict[str, Any]]
    car_offers: list[dict[str, Any]]
    transfer_offers: list[dict[str, Any]]

    # Shopping cart - items selected for booking
    cart: list[BookingItem]

    # Traveler details collected
    travelers: list[TravelerInfo]

    # Contact information
    contact_email: str
    contact_phone: str

    # Booking workflow state
    pending_booking: BookingItem | None  # Item awaiting confirmation
    booking_confirmed: bool  # Human approval received
    completed_bookings: list[dict]  # Successful booking references

    # Error tracking
    last_error: str | None


def create_initial_state() -> TravelAgentState:
    """Create a fresh initial state for a new conversation."""
    return TravelAgentState(
        messages=[],
        search_context={},
        flight_offers=[],
        hotel_offers=[],
        car_offers=[],
        transfer_offers=[],
        cart=[],
        travelers=[],
        contact_email="",
        contact_phone="",
        pending_booking=None,
        booking_confirmed=False,
        completed_bookings=[],
        last_error=None,
    )
