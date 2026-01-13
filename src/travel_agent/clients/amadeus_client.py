"""Amadeus API client wrapper with error handling and retry logic."""

from typing import Any

import structlog
from amadeus import Client, ResponseError
from tenacity import retry, stop_after_attempt, wait_exponential

from travel_agent.config import get_settings

logger = structlog.get_logger()


class AmadeusClientError(Exception):
    """Custom exception for Amadeus API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        details: dict | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AmadeusClientWrapper:
    """Wrapper around the Amadeus SDK with error handling, retries, and logging."""

    def __init__(self):
        settings = get_settings()
        self._client = Client(
            client_id=settings.amadeus_client_id.get_secret_value(),
            client_secret=settings.amadeus_client_secret.get_secret_value(),
            hostname=settings.amadeus_hostname,
        )
        self._logger = logger.bind(component="amadeus_client")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def _execute_request(self, method: callable, **kwargs) -> Any:
        """Execute an Amadeus API request with retry logic."""
        try:
            response = method(**kwargs)
            return response.data
        except ResponseError as e:
            self._logger.error(
                "amadeus_api_error",
                status_code=getattr(e.response, "status_code", None),
                error=str(e),
            )
            raise AmadeusClientError(
                message=str(e),
                status_code=getattr(e.response, "status_code", None),
                details={"raw_response": getattr(e.response, "body", None)},
            ) from e

    # ========== Flight APIs ==========

    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        adults: int = 1,
        return_date: str | None = None,
        travel_class: str | None = None,
        non_stop: bool = False,
        max_results: int = 10,
    ) -> list[dict]:
        """Search for flight offers.

        Args:
            origin: Origin airport IATA code (e.g., 'JFK')
            destination: Destination airport IATA code (e.g., 'LAX')
            departure_date: Departure date in YYYY-MM-DD format
            adults: Number of adult passengers (1-9)
            return_date: Return date for round-trip (optional)
            travel_class: ECONOMY, PREMIUM_ECONOMY, BUSINESS, or FIRST
            non_stop: If True, only return non-stop flights
            max_results: Maximum number of results to return

        Returns:
            List of flight offer dictionaries
        """
        params = {
            "originLocationCode": origin.upper(),
            "destinationLocationCode": destination.upper(),
            "departureDate": departure_date,
            "adults": adults,
            "max": max_results,
        }
        if return_date:
            params["returnDate"] = return_date
        if travel_class:
            params["travelClass"] = travel_class.upper()
        if non_stop:
            params["nonStop"] = "true"

        self._logger.info("search_flights", **params)
        return self._execute_request(
            self._client.shopping.flight_offers_search.get,
            **params,
        )

    def get_flight_price(self, flight_offer: dict) -> dict:
        """Confirm pricing for a specific flight offer.

        Args:
            flight_offer: The flight offer dictionary from search results

        Returns:
            Pricing confirmation response
        """
        self._logger.info("get_flight_price", offer_id=flight_offer.get("id"))
        return self._execute_request(
            self._client.shopping.flight_offers.pricing.post,
            flights=[flight_offer],
        )

    def create_flight_order(
        self,
        flight_offer: dict,
        travelers: list[dict],
        contact: dict,
    ) -> dict:
        """Create a flight booking order.

        Args:
            flight_offer: The priced flight offer
            travelers: List of traveler information dictionaries
            contact: Contact information dictionary

        Returns:
            Booking confirmation response
        """
        self._logger.info("create_flight_order", offer_id=flight_offer.get("id"))
        return self._execute_request(
            self._client.booking.flight_orders.post,
            flights=[flight_offer],
            travelers=travelers,
            contacts=[contact],
        )

    def get_seat_maps(self, flight_offer: dict) -> list[dict]:
        """Get seat maps for a flight offer.

        Args:
            flight_offer: The flight offer dictionary

        Returns:
            List of seat map dictionaries
        """
        return self._execute_request(
            self._client.shopping.seatmaps.post,
            flights=[flight_offer],
        )

    # ========== Hotel APIs ==========

    def search_hotels_by_city(
        self,
        city_code: str,
        check_in_date: str,
        check_out_date: str,
        adults: int = 1,
        room_quantity: int = 1,
        radius: int = 5,
        radius_unit: str = "KM",
    ) -> list[dict]:
        """Search for hotels in a city.

        Args:
            city_code: City IATA code (e.g., 'PAR' for Paris)
            check_in_date: Check-in date in YYYY-MM-DD format
            check_out_date: Check-out date in YYYY-MM-DD format
            adults: Number of adult guests
            room_quantity: Number of rooms
            radius: Search radius
            radius_unit: 'KM' or 'MILE'

        Returns:
            List of hotel offer dictionaries
        """
        self._logger.info(
            "search_hotels_by_city",
            city_code=city_code,
            check_in=check_in_date,
            check_out=check_out_date,
        )

        # First get hotel list in the city
        try:
            hotels = self._execute_request(
                self._client.reference_data.locations.hotels.by_city.get,
                cityCode=city_code.upper(),
                radius=radius,
                radiusUnit=radius_unit,
            )
        except AmadeusClientError:
            return []

        if not hotels:
            return []

        # Get hotel offers for first 20 hotels
        hotel_ids = [h["hotelId"] for h in hotels[:20]]

        try:
            return self._execute_request(
                self._client.shopping.hotel_offers_search.get,
                hotelIds=hotel_ids,
                checkInDate=check_in_date,
                checkOutDate=check_out_date,
                adults=adults,
                roomQuantity=room_quantity,
            )
        except AmadeusClientError:
            return []

    def get_hotel_offer_details(self, offer_id: str) -> dict:
        """Get detailed information about a specific hotel offer.

        Args:
            offer_id: The hotel offer ID

        Returns:
            Hotel offer details dictionary
        """
        return self._execute_request(
            self._client.shopping.hotel_offer_search.get,
            offerId=offer_id,
        )

    def book_hotel(
        self,
        offer_id: str,
        guests: list[dict],
        payment: dict,
    ) -> dict:
        """Book a hotel room.

        Args:
            offer_id: The hotel offer ID
            guests: List of guest information dictionaries
            payment: Payment information dictionary

        Returns:
            Booking confirmation response
        """
        return self._execute_request(
            self._client.booking.hotel_bookings.post,
            offerId=offer_id,
            guests=guests,
            payments=[payment],
        )

    # ========== Transfer/Car APIs ==========

    def search_transfers(
        self,
        start_location_code: str,
        end_address_line: str,
        transfer_date: str,
        passengers: int = 1,
        transfer_type: str = "PRIVATE",
    ) -> list[dict]:
        """Search for airport transfers.

        Args:
            start_location_code: Airport IATA code
            end_address_line: Destination address
            transfer_date: Transfer date-time in ISO format
            passengers: Number of passengers
            transfer_type: 'PRIVATE' or 'SHARED'

        Returns:
            List of transfer offer dictionaries
        """
        self._logger.info(
            "search_transfers",
            start=start_location_code,
            end=end_address_line,
            date=transfer_date,
        )
        try:
            return self._execute_request(
                self._client.shopping.transfer_offers.post,
                startLocationCode=start_location_code,
                endAddressLine=end_address_line,
                transferType=transfer_type,
                startDateTime=transfer_date,
                passengers=passengers,
            )
        except AmadeusClientError:
            return []

    # ========== Reference Data APIs ==========

    def search_airports(self, keyword: str) -> list[dict]:
        """Search for airports/cities by keyword.

        Args:
            keyword: Search term (city name, airport code, etc.)

        Returns:
            List of location dictionaries
        """
        self._logger.info("search_airports", keyword=keyword)
        try:
            return self._execute_request(
                self._client.reference_data.locations.get,
                keyword=keyword,
                subType="AIRPORT,CITY",
            )
        except AmadeusClientError:
            return []

    def get_airline_name(self, airline_code: str) -> str:
        """Get airline name from IATA code.

        Args:
            airline_code: IATA airline code (e.g., 'AA')

        Returns:
            Airline business name or the code if not found
        """
        try:
            result = self._execute_request(
                self._client.reference_data.airlines.get,
                airlineCodes=airline_code,
            )
            return result[0]["businessName"] if result else airline_code
        except AmadeusClientError:
            return airline_code


# Lazy-loaded singleton instance
_amadeus_client: AmadeusClientWrapper | None = None


def get_amadeus_client() -> AmadeusClientWrapper:
    """Get the Amadeus client singleton instance."""
    global _amadeus_client
    if _amadeus_client is None:
        _amadeus_client = AmadeusClientWrapper()
    return _amadeus_client


# For backward compatibility
amadeus_client = property(lambda self: get_amadeus_client())
