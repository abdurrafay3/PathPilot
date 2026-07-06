from openai import OpenAI
from app.schemas.agent_state import IntentOutput
from agents import Agent, Runner, function_tool
from app.schemas.agent_state import Coordinates
from app.agents.geocoder import get_region_context
import logging

logger = logging.getLogger(__name__)

async def normalize_intent(user_input: str, current_location : Coordinates | None = None, region_context : dict | None = None) -> IntentOutput:
    """
    Normalize the user's input to extract structured information such as origin, destination, travel mode, required stops, etc.

    Args:
        user_input (str): The raw input from the user.
        current_location (Coordinates): The current location of the user.
        region_context (dict): The region context based on the current location.

    Returns:
        IntentNormalizerAgentOutput: A structured representation of the user's intent.
    """

    logger.info(f"\033[92mNormalizing intent for user input\033[0m")

    user_location = "Unknown location"
    if region_context and region_context.get("results"):
        user_location = region_context["results"][0]["formatted_address"]
    system_prompt = """
You are an intent normalizer agent for a route planning app.

Extract the user's route intent into the provided structured output schema.

Rules:
- Correct obvious typos.
- Always set origin.value to the user's current location if no explicit origin is mentioned. Otherwise, set origin.value to the explicitly mentioned origin.
- If the user mentions a specific location as the origin, set origin.location_type to "explicit_location", origin.value to the mentioned location, and origin.confidence to 1.0.
- The destination should be specified as much as possible. If the user mentions only a district or area name, try to infer the specific location based on the current location of the user. For example, if the user is in the US and says "take me to central", you can infer that they mean "Central Park, New York, NY" if they are in New York City. 
- Extract origin if mentioned.
- Extract destination if mentioned.
- Extract travel mode if mentioned.
- Extract required stops, such as hospital, restaurant, ATM, pharmacy, gas station, etc.
- If the user says "on the way", set the stop position to "along_route".
- If the user says "must", "need", or "make sure", treat it as a hard constraint.
- If the user says "preferably" or "if possible", treat it as a soft constraint.
- If a required stop is mentioned and no detour limit is given, use 12 minutes.
- If the user says they do not want to walk too much, set max_walking_minutes to 10.
- If travel mode is missing, use "auto".
- If optimization goal is missing, use "fastest_valid_route".
- Add assumptions for defaults and typo corrections.
"""


    user_prompt = f"{user_input}\n\nLatitude: {current_location.lat}, Longitude: {current_location.lng}\nuser address: {user_location}\n\nPlease extract the intent into the provided structured output schema."

    intent_normalizer = Agent(name="intent_normalizer", instructions=system_prompt, model="gpt-4o-mini", output_type=IntentOutput)
    intent_normalizer_runner = await Runner.run(starting_agent=intent_normalizer, input=user_prompt)
    result = intent_normalizer_runner.final_output

    logger.info(f"\033[31mIntent normalization completed!\033[0m")
    return result