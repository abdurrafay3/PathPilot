from pydantic import BaseModel, Field
from typing import Literal

from app.schemas.agent_state import CandidateRoute

class RoutePlannerOutput(BaseModel):
    status: str
    candidate_routes: list[CandidateRoute] = []
    final_answer: str