from agents import function_tool, RunContextWrapper
from app.schemas.agent_state import Coordinates, RoutePlannerContext
import httpx
from app.config import settings
from app.schemas.agent_state import IntentOutput, GeocoderAgentOutput
import logging
import asyncio, json, os
from app.timing import timed
from app.mock.helper import record_fixture, fake_latency, MOCK, load_fixture

logger = logging.getLogger(__name__)

GOOGLE_GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"


MOCK = os.getenv("MOCK_EXTERNAL") == "1"


class GeocodingError(Exception):
    """Google couldn't resolve an address (e.g. ZERO_RESULTS)."""


async def get_region_context(coordinates: Coordinates) -> dict:
    """
    Returns the region context based on the provided coordinates.
    """
    logger.info(
        f"\033[94mFetching region context for coordinates: {coordinates}\033[0m"
    )
    if MOCK:
        data = load_fixture("geocode_region")
        await fake_latency(0.3365, 0.5774)
    else:
        async with httpx.AsyncClient() as client:
            params = {
                "latlng": f"{coordinates.lat},{coordinates.lng}",
                "key": settings.GOOGLE_MAPS_API_KEY,
            }
            with timed("geocoder.get_region_context", "geocode_reverse", "google") as t:
                response = await client.get(GOOGLE_GEOCODING_URL, params=params)
                t["status"] = response.status_code
            response.raise_for_status()

            data = response.json()
            record_fixture("geocode_region", data)

    if data["status"] != "OK":
        raise ValueError(f"Error from Google Geocoding API: {data['status']}")
    return data


GOOGLE_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"


async def search_place_by_text(
    query: str, near: Coordinates | None
) -> Coordinates | None:
    body = {"textQuery": query, "maxResultCount": 1}
    if near:
        body["locationBias"] = {
            "circle": {
                "center": {"latitude": near.lat, "longitude": near.lng},
                "radius": 50000.0,
            }
        }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "places.location",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        with timed(
            "geocoder.search_place_by_text", "places_text_search", "google"
        ) as t:
            response = await client.post(
                GOOGLE_TEXT_SEARCH_URL, headers=headers, json=body
            )
            t["status"] = response.status_code
    response.raise_for_status()
    places = response.json().get("places", [])
    if not places:
        return None
    loc = places[0]["location"]
    return Coordinates(lat=loc["latitude"], lng=loc["longitude"])


async def get_coordinates_from_address(address: str, near : Coordinates | None) -> Coordinates:
    """
    Returns the coordinates (latitude and longitude) for a given address using the Google Geocoding API.
    """
    params = {"address": address, "region": "hk", "key": settings.GOOGLE_MAPS_API_KEY}

    logger.info(f"\033[94mFetching coordinates for address: {address}\033[0m")
    if MOCK:
        data = load_fixture("geocode_forward")
        await fake_latency(0.348, 0.505)
    else:
        async with httpx.AsyncClient() as client:
            with timed(
                "geocoder.get_coordinates_from_address", "geocode_forward", "google"
            ) as t:
                response = await client.get(GOOGLE_GEOCODING_URL, params=params)
                t["status"] = response.status_code
            response.raise_for_status()
            data = response.json()
    record_fixture("geocode_forward", data)

    if data["status"] != "OK" or not data.get("results"):
        logger.error(f"Error from Google Geocoding API: {data['status']}")
        # we fall back on Google Places Text Search if geocoding did not find anything
        fallback = await search_place_by_text(address, near)
        return fallback
    location = data["results"][0]["geometry"]["location"]
    return Coordinates(lat=location["lat"], lng=location["lng"])


@function_tool
async def produce_origin_destination_tool(
    ctx: RunContextWrapper[RoutePlannerContext],
) -> GeocoderAgentOutput:
    """
    Extracts the origin and destination coordinates from the intent normalizer output.
    """
    intent_normalizer_output = ctx.context.intent_output
    result = await produce_origin_destination(intent_normalizer_output)
    ctx.context.geocoder_output = result
    return result


async def produce_origin_destination(
    intent_normalizer_output: IntentOutput,
) -> GeocoderAgentOutput:
    """
    Extracts the origin and destination coordinates from the intent normalizer output.

    Args:
        intent_normalizer_output (IntentOutput): The output from the intent normalizer agent.

    Returns:
        GeocoderAgentOutput: A dict containing the origin and destination coordinates, if available.
    """
    # we assume that the intent normalizer output already contains valid formatted addresses
    logger.info(
        f"\033[94mProducing origin and destination from intent normalizer output\033[0m"
    )
    origin_coordinates = None
    if intent_normalizer_output.origin.coordinates:
        origin_coordinates = intent_normalizer_output.origin.coordinates
    else:
        origin_coordinates = (
            await get_coordinates_from_address(formatted_address_origin, origin_coordinates)
            if formatted_address_origin
            else None
        )
    
    formatted_address_destination = intent_normalizer_output.destination.value
    formatted_address_origin = intent_normalizer_output.origin.value
    # get the coordinates for the destination by using the geocoding API
    destination_coordinates = None
    if intent_normalizer_output.destination.coordinates:
        destination_coordinates = intent_normalizer_output.destination.coordinates
    else:
        destination_coordinates = (
            await get_coordinates_from_address(formatted_address_destination, origin_coordinates)
            if formatted_address_destination
            else None
        )
    
    return GeocoderAgentOutput(
        origin={
            "formatted_address": formatted_address_origin,
            "coordinates": origin_coordinates if origin_coordinates else None,
            "confidence": 1.0 if formatted_address_origin else None,
        },
        destination={
            "formatted_address": formatted_address_destination,
            "coordinates": destination_coordinates if destination_coordinates else None,
            "confidence": 1.0 if formatted_address_destination else None,
        },
    )
