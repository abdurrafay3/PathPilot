from pydantic import BaseModel, Field

class RouteModifiers(BaseModel):
    avoidTolls: bool = Field(default=False, description="Indicates whether to avoid toll roads in the route.")
    avoidHighways : bool = Field(default=False, description="Indicates whether to avoid highways in the route.")
    avoidFerries : bool = Field(default=False, description="Indicates whether to avoid ferries in the route.")


