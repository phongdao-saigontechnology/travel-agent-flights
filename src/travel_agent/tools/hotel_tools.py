"""Hotel-related tools for the travel agent."""

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from travel_agent.clients.amadeus_client import AmadeusClientError, get_amadeus_client


class HotelSearchInput(BaseModel):
    """Input schema for hotel search."""

    city_code: str = Field(
        description="City IATA code (e.g., 'PAR' for Paris, 'NYC' for New York)"
    )
    check_in_date: str = Field(description="Check-in date in YYYY-MM-DD format")
    check_out_date: str = Field(description="Check-out date in YYYY-MM-DD format")
    adults: int = Field(default=1, ge=1, description="Number of adult guests")
    rooms: int = Field(default=1, ge=1, description="Number of rooms needed")


@tool(args_schema=HotelSearchInput)
def search_hotels(
    city_code: str,
    check_in_date: str,
    check_out_date: str,
    adults: int = 1,
    rooms: int = 1,
) -> str:
    """Search for available hotels in a city.

    Use this tool when the user wants to find hotel accommodations.
    Returns a list of hotels with prices, ratings, and room information.

    Use the search_airports tool first to find the city code if the user
    provides a city name instead of an IATA code.
    """
    try:
        client = get_amadeus_client()
        results = client.search_hotels_by_city(
            city_code=city_code,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            adults=adults,
            room_quantity=rooms,
        )

        if not results:
            return f"No hotels found in {city_code} for the specified dates."

        formatted = []
        for i, hotel_data in enumerate(results[:5], 1):
            hotel = hotel_data.get("hotel", {})
            offers = hotel_data.get("offers", [])

            if not offers:
                continue

            offer = offers[0]
            price = offer.get("price", {})
            room = offer.get("room", {})
            room_desc = room.get("description", {}).get("text", "Standard Room")

            # Get rating info
            rating = hotel.get("rating", "N/A")
            rating_str = f"{rating} stars" if rating != "N/A" else "Unrated"

            hotel_info = [
                f"Option {i} (Hotel ID: {hotel.get('hotelId', 'N/A')}):",
                f"  Name: {hotel.get('name', 'N/A')}",
                f"  Rating: {rating_str}",
                f"  Address: {hotel.get('address', {}).get('lines', ['N/A'])[0]}",
                f"  Room Type: {room_desc[:50]}...",
                f"  Price: {price.get('total', 'N/A')} {price.get('currency', 'USD')} total",
            ]

            # Add amenities if available
            amenities = hotel.get("amenities", [])
            if amenities:
                amenities_str = ", ".join(amenities[:5])
                hotel_info.append(f"  Amenities: {amenities_str}")

            formatted.append("\n".join(hotel_info))

        if not formatted:
            return f"No hotel offers available in {city_code} for the specified dates."

        return (
            f"Available hotels in {city_code}:\n"
            f"Check-in: {check_in_date}, Check-out: {check_out_date}\n\n"
            + "\n\n".join(formatted)
        )

    except AmadeusClientError as e:
        return f"Error searching hotels: {e.message}"


@tool
def get_hotel_details(hotel_id: str, offer_id: str) -> str:
    """Get detailed information about a specific hotel offer.

    Use this when the user wants more information about a particular hotel
    before making a booking decision.

    Args:
        hotel_id: The hotel ID from search results
        offer_id: The specific offer ID
    """
    try:
        client = get_amadeus_client()
        details = client.get_hotel_offer_details(offer_id)

        if not details:
            return f"Could not retrieve details for hotel {hotel_id}."

        hotel = details.get("hotel", {})
        offer = details.get("offers", [{}])[0] if details.get("offers") else {}

        room = offer.get("room", {})
        price = offer.get("price", {})
        policies = offer.get("policies", {})

        info = [
            f"Hotel: {hotel.get('name', 'N/A')}",
            f"Rating: {hotel.get('rating', 'N/A')} stars",
            "",
            "Room Details:",
            f"  Type: {room.get('type', 'N/A')}",
            f"  Description: {room.get('description', {}).get('text', 'N/A')}",
            f"  Beds: {room.get('typeEstimated', {}).get('beds', 'N/A')}",
            "",
            "Price:",
            f"  Total: {price.get('total', 'N/A')} {price.get('currency', 'USD')}",
            f"  Base: {price.get('base', 'N/A')} {price.get('currency', 'USD')}",
            "",
            "Policies:",
            f"  Cancellation: {policies.get('cancellation', {}).get('description', {}).get('text', 'See hotel policy')}",
            f"  Payment: {policies.get('paymentType', 'N/A')}",
        ]

        return "\n".join(info)

    except AmadeusClientError as e:
        return f"Error getting hotel details: {e.message}"


@tool
def add_hotel_to_cart(
    hotel_id: str,
    hotel_name: str,
    check_in: str,
    check_out: str,
    price: float,
    currency: str,
) -> str:
    """Add a selected hotel to the booking cart.

    Use this when the user confirms they want to book a specific hotel.

    Args:
        hotel_id: The hotel ID
        hotel_name: Name of the hotel
        check_in: Check-in date
        check_out: Check-out date
        price: Total price
        currency: Currency code
    """
    return (
        f"Added to cart: {hotel_name}\n"
        f"Check-in: {check_in}\n"
        f"Check-out: {check_out}\n"
        f"Price: {price} {currency}\n\n"
        f"To complete the hotel booking, I'll need:\n"
        f"- Guest name(s)\n"
        f"- Contact email\n"
        f"- Contact phone\n"
        f"- Payment information (credit card)\n\n"
        f"Please provide the guest details."
    )
