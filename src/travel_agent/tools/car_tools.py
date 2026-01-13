"""Car rental and transfer tools for the travel agent."""

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from travel_agent.clients.amadeus_client import AmadeusClientError, get_amadeus_client


class TransferSearchInput(BaseModel):
    """Input schema for transfer search."""

    airport_code: str = Field(description="Airport IATA code (e.g., 'JFK', 'CDG')")
    destination_address: str = Field(
        description="Full destination address (e.g., '123 Main St, Paris')"
    )
    transfer_datetime: str = Field(
        description="Transfer date and time in ISO format (e.g., '2024-06-15T14:00:00')"
    )
    passengers: int = Field(default=1, ge=1, le=50, description="Number of passengers")


@tool(args_schema=TransferSearchInput)
def search_transfers(
    airport_code: str,
    destination_address: str,
    transfer_datetime: str,
    passengers: int = 1,
) -> str:
    """Search for airport transfer services.

    Use this tool when the user needs transportation from an airport to
    a specific address (hotel, business, etc.). Returns available transfer
    options with vehicle types and prices.

    The transfer_datetime should include both date and time in ISO format.
    """
    try:
        client = get_amadeus_client()
        results = client.search_transfers(
            start_location_code=airport_code,
            end_address_line=destination_address,
            transfer_date=transfer_datetime,
            passengers=passengers,
        )

        if not results:
            return (
                f"No transfers available from {airport_code} to {destination_address} "
                f"on {transfer_datetime}."
            )

        formatted = []
        for i, transfer in enumerate(results[:5], 1):
            vehicle = transfer.get("vehicle", {})
            quote = transfer.get("quotation", {})

            transfer_info = [
                f"Option {i} (ID: {transfer.get('id', 'N/A')}):",
                f"  Vehicle: {vehicle.get('description', 'N/A')}",
                f"  Category: {vehicle.get('category', 'N/A')}",
                f"  Max Passengers: {vehicle.get('seats', 'N/A')}",
                f"  Baggage: {vehicle.get('baggages', 'N/A')} bags",
                f"  Price: {quote.get('monetaryAmount', 'N/A')} {quote.get('currencyCode', 'USD')}",
            ]

            # Add service provider info if available
            provider = transfer.get("serviceProvider", {})
            if provider:
                transfer_info.append(f"  Provider: {provider.get('name', 'N/A')}")

            formatted.append("\n".join(transfer_info))

        return (
            f"Available transfers from {airport_code}:\n"
            f"To: {destination_address}\n"
            f"Date/Time: {transfer_datetime}\n"
            f"Passengers: {passengers}\n\n"
            + "\n\n".join(formatted)
        )

    except AmadeusClientError as e:
        return f"Error searching transfers: {e.message}"


class CarRentalSearchInput(BaseModel):
    """Input schema for car rental search."""

    pickup_location: str = Field(
        description="Pickup location IATA code (airport) or city code"
    )
    pickup_date: str = Field(description="Pickup date in YYYY-MM-DD format")
    dropoff_date: str = Field(description="Drop-off date in YYYY-MM-DD format")
    pickup_time: str = Field(
        default="10:00", description="Pickup time in HH:MM format"
    )
    dropoff_time: str = Field(
        default="10:00", description="Drop-off time in HH:MM format"
    )


@tool(args_schema=CarRentalSearchInput)
def search_car_rentals(
    pickup_location: str,
    pickup_date: str,
    dropoff_date: str,
    pickup_time: str = "10:00",
    dropoff_time: str = "10:00",
) -> str:
    """Search for car rental options.

    Use this tool when the user wants to rent a car. Note that Amadeus
    car rental APIs may have limited availability in the self-service tier.

    Returns available car rental options with vehicle types and prices.
    """
    # Note: The Amadeus self-service API has limited car rental support
    # This is a placeholder that provides helpful guidance

    return (
        f"Car Rental Search:\n"
        f"  Pickup: {pickup_location} on {pickup_date} at {pickup_time}\n"
        f"  Drop-off: {dropoff_date} at {dropoff_time}\n\n"
        f"Note: Direct car rental search through Amadeus requires an Enterprise subscription.\n\n"
        f"Recommended alternatives:\n"
        f"1. Search for airport transfers using the search_transfers tool\n"
        f"2. Popular car rental providers at {pickup_location}:\n"
        f"   - Hertz (hertz.com)\n"
        f"   - Avis (avis.com)\n"
        f"   - Enterprise (enterprise.com)\n"
        f"   - Budget (budget.com)\n"
        f"   - Sixt (sixt.com)\n\n"
        f"Would you like me to search for airport transfers instead?"
    )


@tool
def add_transfer_to_cart(
    transfer_id: str,
    vehicle_description: str,
    from_location: str,
    to_location: str,
    datetime: str,
    price: float,
    currency: str,
) -> str:
    """Add a selected transfer to the booking cart.

    Args:
        transfer_id: The transfer offer ID
        vehicle_description: Description of the vehicle
        from_location: Pickup location
        to_location: Destination address
        datetime: Transfer date and time
        price: Total price
        currency: Currency code
    """
    return (
        f"Added to cart: Airport Transfer\n"
        f"Vehicle: {vehicle_description}\n"
        f"From: {from_location}\n"
        f"To: {to_location}\n"
        f"Date/Time: {datetime}\n"
        f"Price: {price} {currency}\n\n"
        f"To complete the booking, I'll need:\n"
        f"- Lead passenger name\n"
        f"- Contact phone (for driver coordination)\n"
        f"- Flight number (optional, for tracking)\n\n"
        f"Please provide the required information."
    )
