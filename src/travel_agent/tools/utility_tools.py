"""Utility tools for the travel agent."""

from datetime import datetime

from langchain_core.tools import tool

from travel_agent.clients.amadeus_client import AmadeusClientError, get_amadeus_client


@tool
def search_airports(keyword: str) -> str:
    """Search for airports and cities by keyword.

    Use this tool when the user provides a city name or partial airport code
    and you need to find the correct IATA code for flight or hotel searches.

    Args:
        keyword: Search term - can be city name, airport name, or partial code
    """
    try:
        client = get_amadeus_client()
        results = client.search_airports(keyword)

        if not results:
            return f"No airports or cities found matching '{keyword}'. Try a different search term."

        formatted = []
        for loc in results[:10]:
            loc_type = loc.get("subType", "UNKNOWN")
            address = loc.get("address", {})
            city = address.get("cityName", "")
            country = address.get("countryName", "")

            location_str = f"{city}, {country}" if city and country else city or country or "N/A"

            formatted.append(
                f"  {loc['iataCode']}: {loc.get('name', 'N/A')} "
                f"({loc_type}) - {location_str}"
            )

        return f"Locations matching '{keyword}':\n" + "\n".join(formatted)

    except AmadeusClientError as e:
        return f"Error searching locations: {e.message}"


@tool
def get_current_date() -> str:
    """Get the current date.

    Use this tool when you need to know today's date for calculating
    travel dates or validating user input.
    """
    today = datetime.now()
    return (
        f"Today's date: {today.strftime('%Y-%m-%d')}\n"
        f"Day of week: {today.strftime('%A')}\n"
        f"Time (local): {today.strftime('%H:%M')}"
    )


@tool
def get_airline_info(airline_code: str) -> str:
    """Get information about an airline from its IATA code.

    Use this tool to look up the full name of an airline when you have
    the two-letter IATA code (e.g., 'AA' for American Airlines).

    Args:
        airline_code: Two-letter IATA airline code
    """
    try:
        client = get_amadeus_client()
        name = client.get_airline_name(airline_code)
        return f"Airline {airline_code}: {name}"
    except AmadeusClientError as e:
        return f"Could not look up airline {airline_code}: {e.message}"


@tool
def calculate_trip_duration(departure_date: str, return_date: str) -> str:
    """Calculate the duration of a trip in days.

    Args:
        departure_date: Trip start date in YYYY-MM-DD format
        return_date: Trip end date in YYYY-MM-DD format
    """
    try:
        dep = datetime.strptime(departure_date, "%Y-%m-%d")
        ret = datetime.strptime(return_date, "%Y-%m-%d")

        if ret < dep:
            return "Error: Return date cannot be before departure date."

        duration = (ret - dep).days

        if duration == 0:
            return "Same-day trip (day trip)"
        elif duration == 1:
            return "1-night trip"
        else:
            return f"{duration}-night trip ({duration + 1} days total)"

    except ValueError:
        return "Error: Invalid date format. Please use YYYY-MM-DD."


@tool
def format_booking_summary(
    booking_type: str,
    description: str,
    price: float,
    currency: str,
    travelers: int = 1,
) -> str:
    """Format a booking summary for the user.

    Args:
        booking_type: Type of booking (flight, hotel, transfer)
        description: Brief description of the booking
        price: Total price
        currency: Currency code
        travelers: Number of travelers
    """
    price_per_person = price / travelers if travelers > 0 else price

    summary = [
        "=" * 50,
        f"BOOKING SUMMARY - {booking_type.upper()}",
        "=" * 50,
        "",
        description,
        "",
        f"Total Price: {price:.2f} {currency}",
    ]

    if travelers > 1:
        summary.append(f"Price per person: {price_per_person:.2f} {currency}")

    summary.extend(
        [
            "",
            "=" * 50,
        ]
    )

    return "\n".join(summary)
