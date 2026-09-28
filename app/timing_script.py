import httpx
import subprocess
import asyncio

ORIGIN = {"lat": 22.3375, "lng" : 114.2626}
SERVER_URL = "http://127.0.0.1:8000/plan_route"

def make_test_calls():
    """
    This function makes about 15 test calls to the server. It starts the next one when the previous one has finished or timed out. It reads the prompts from example_prompts.txt
    """
    ## lets first start the server 
    with open("app/example_prompts.txt", "r") as f:
        lines = f.readlines()
        prompts = [line.strip() for line in lines]
        # now for each prompt
        with httpx.Client(timeout=120.0) as client:
            for i, prompt in enumerate(prompts):
                try:
                    response = client.post(url=SERVER_URL, json={"user_input":prompt, "origin":ORIGIN} )
                    print(f"[{i + 1}/ {len(prompts)}] {response.status_code} : {prompt}")
                except httpx.TimeoutException:
                    print(f"[{i + 1} / {len(prompts)}] timeouts. Prompt: {prompt}")
                except httpx.ConnectError: 
                    print("Server not running. Please run server first")
                    return
                except Exception as e:
                    print(f"An error occurred: {e}. Prompt {i + 1}: {prompt}")

if __name__ == "__main__":
    make_test_calls()


        
