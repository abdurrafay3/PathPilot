import random
from locust import FastHttpUser, task, between
from pathlib import Path

PROMPTS = [line.strip() for line in (Path(__file__).parent / "example_prompts.txt").read_text().splitlines() if line.strip()]

class RoutePlannerUser(FastHttpUser):
    wait_time = between(1, 5)
    @task
    def plan_route_task(self):
        prompt = random.choice(PROMPTS)
        with self.client.post("/plan_route", json={"user_input": prompt , "origin": {"lat": 22.3375, "lng" : 114.2626}}, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}")
            elif not (response.json() or {}).get("accepted_routes"):
                response.failure("200 but no accepted routes")
            else:
                response.success()
