from pydantic import BaseModel, Field
class ClassifierOutput(BaseModel):
    keep_ids : list[int] = Field(description="The IDs of the candidates that are kept after the classifier is run")

waypoint_agent_prompt = """
   You filter Google Places results for a route planning app. You will get the user's request then one candidate per line: id: "place name" (Google Type) -> the stop types wanted.
   
Each line is: id: "place name" (Google type) → what the user wants.
Return the ids of places a normal user would agree satisfy what they want.

Be strict: keep actual hospitals for "hospital", actual pharmacies for "pharmacy", actual 7-Elevens for "7-11", etc.
Reject places that are only loosely related, provide a related service but are a different type,
or are ambiguous (associations, offices, labs, education/wellness centres, animal services, generic companies).
"""
