"""Flight-related tools for the travel agent."""

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from travel_agent.clients.amadeus_client import AmadeusClientError, get_amadeus_client


class FlightSearchInput(BaseModel):
    """Input schema for flight search."""

    origin: str = Field(description="Origin airport IATA code (e.g., 'JFK', 'LAX')")
    destination: str = Field(description="Destination airport IATA code")
    departure_date: str = Field(description="Departure date in YYYY-MM-DD format")
    return_date: str | None = Field(
        default=None, description="Return date for round trip (YYYY-MM-DD)"
    )
    adults: int = Field(default=1, ge=1, le=9, description="Number of adult passengers")
    travel_class: str | None = Field(
        default=None,
        description="Travel class: ECONOMY, PREMIUM_ECONOMY, BUSINESS, or FIRST",
    )
    non_stop: bool = Field(default=False, description="Only return non-stop flights")


@tool(args_schema=FlightSearchInput)
def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None = None,
    adults: int = 1,
    travel_class: str | None = None,
    non_stop: bool = False,
) -> str:
    """Search for available flights between two airports.

    Use this tool when the user wants to find flights. Returns a list of
    flight options with prices, airlines, departure/arrival times, and duration.

    Always confirm the origin, destination, dates, and number of passengers
    before searching. Use the search_airports tool first if the user provides
    city names instead of airport codes.
    """
    try:
        client = get_amadeus_client()
        results = client.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            adults=adults,
            travel_class=travel_class,
            non_stop=non_stop,
            max_results=5,
        )

        if not results:
            return f"No flights found from {origin} to {destination} on {departure_date}."

        # Format results for readability
        formatted = []
        for i, offer in enumerate(results, 1):
            price = offer["price"]
            itineraries = offer.get("itineraries", [])

            if not itineraries:
                continue

            # Format outbound flight
            outbound = itineraries[0]
            segments = outbound.get("segments", [])
            if not segments:
                continue

            first_seg = segments[0]
            last_seg = segments[-1]

            stops = len(segments) - 1
            stop_text = "Direct" if stops == 0 else f"{stops} stop(s)"

            # Get carrier info
            carrier = first_seg.get("carrierCode", "N/A")
            flight_number = first_seg.get("number", "")

            flight_info = [
                f"Option {i} (ID: {offer['id']}):",
                f"  Flight: {carrier} {flight_number}",
                f"  Route: {first_seg['departure']['iataCode']} -> {last_seg['arrival']['iataCode']}",
                f"  Departure: {first_seg['departure']['at']}",
                f"  Arrival: {last_seg['arrival']['at']}",
                f"  Duration: {outbound.get('duration', 'N/A')}",
                f"  {stop_text}",
                f"  Price: {price['total']} {price['currency']}",
            ]

            # Add return flight info if round-trip
            if len(itineraries) > 1:
                return_flight = itineraries[1]
                ret_segments = return_flight.get("segments", [])
                if ret_segments:
                    ret_first = ret_segments[0]
                    ret_last = ret_segments[-1]
                    ret_stops = len(ret_segments) - 1
                    ret_stop_text = "Direct" if ret_stops == 0 else f"{ret_stops} stop(s)"
                    flight_info.extend(
                        [
                            f"  Return:",
                            f"    Departure: {ret_first['departure']['at']}",
                            f"    Arrival: {ret_last['arrival']['at']}",
                            f"    {ret_stop_text}",
                        ]
                    )

            formatted.append("\n".join(flight_info))

        return "Available flights:\n\n" + "\n\n".join(formatted)

    except AmadeusClientError as e:
        return f"Error searching flights: {e.message}"


@tool
def get_flight_price_confirmation(offer_id: str, offer_data: str) -> str:
    """Get confirmed pricing for a selected flight offer.

    Use this after the user selects a flight option to confirm the current
    price before proceeding to booking.

    Args:
        offer_id: The flight offer ID from search results
        offer_data: JSON string of the flight offer data
    """
    import json

    try:
        offer = json.loads(offer_data)
    except json.JSONDecodeError:
        return "Invalid offer data format. Please search for flights again."

    try:
        client = get_amadeus_client()
        pricing = client.get_flight_price(offer)

        if not pricing:
            return f"Could not confirm pricing for flight {offer_id}. The offer may have expired."

        flight_offers = pricing.get("flightOffers", [])
        if not flight_offers:
            return "No pricing information available."

        price_info = flight_offers[0].get("price", {})

        return (
            f"Confirmed price for flight {offer_id}:\n"
            f"  Base fare: {price_info.get('base', 'N/A')} {price_info.get('currency', 'USD')}\n"
            f"  Total (including taxes): {price_info['total']} {price_info.get('currency', 'USD')}\n"
            f"\nWould you like to proceed with booking this flight?"
        )

    except AmadeusClientError as e:
        return f"Error confirming price: {e.message}. The offer may have expired."


@tool
def add_flight_to_cart(offer_id: str, description: str, price: float, currency: str) -> str:
    """Add a selected flight to the booking cart.

    Use this when the user confirms they want to book a specific flight.
    The flight will be added to their cart for checkout.

    Args:
        offer_id: The flight offer ID
        description: Brief description of the flight (route, date)
        price: Total price of the flight
        currency: Currency code (e.g., 'USD', 'EUR')
    """
    return (
        f"Added to cart: {description}\n"
        f"Price: {price} {currency}\n\n"
        f"To complete booking, I'll need traveler details:\n"
        f"- Full name (as on passport)\n"
        f"- Date of birth\n"
        f"- Gender\n"
        f"- Passport number and expiry date\n"
        f"- Nationality\n"
        f"- Contact email and phone number\n\n"
        f"Please provide information for each traveler."
    )


@tool
def confirm_flight_booking(
    offer_id: str,
    traveler_first_name: str,
    traveler_last_name: str,
    traveler_dob: str,
    traveler_gender: str,
    traveler_email: str,
    traveler_phone: str,
    passport_number: str,
    passport_expiry: str,
    nationality: str,
) -> str:
    """Execute the flight booking after collecting all traveler information.

    This tool will finalize the booking. Only use after:
    1. User has selected a specific flight
    2. All traveler information has been collected
    3. User has confirmed they want to proceed

    Args:
        offer_id: The flight offer ID to book
        traveler_first_name: Traveler's first name (as on passport)
        traveler_last_name: Traveler's last name (as on passport)
        traveler_dob: Date of birth (YYYY-MM-DD)
        traveler_gender: MALE or FEMALE
        traveler_email: Contact email address
        traveler_phone: Contact phone number
        passport_number: Passport document number
        passport_expiry: Passport expiry date (YYYY-MM-DD)
        nationality: Two-letter country code (e.g., 'US', 'GB')
    """
    # Note: In a real implementation, this would call the Amadeus booking API
    # For now, we return a simulated confirmation
    # The actual booking would require human-in-the-loop approval

    booking_summary = f"""
BOOKING CONFIRMATION PENDING

Flight: {offer_id}

Traveler Information:
  Name: {traveler_first_name} {traveler_last_name}
  Date of Birth: {traveler_dob}
  Gender: {traveler_gender}
  Passport: {passport_number} (expires: {passport_expiry})
  Nationality: {nationality}

Contact:
  Email: {traveler_email}
  Phone: {traveler_phone}

Please review the above information carefully.
Reply with 'CONFIRM' to complete the booking or 'CANCEL' to abort.
"""
    return booking_summary
