import os 
import csv
import time 
from contextlib import contextmanager
import httpx, asyncio
TIMING_FILE = "timing.csv"
def record_timing(function: str, call : str, kind: str, timeSeconds : float, status : str = "ok") -> None:
    """
    This function records how long `function` takes to run. It then appends a row to the table.
    Args:
        function : The function in this app that was run
        call : Which API function was called
        kind : the company behind the API function
        timeSeconds : the time it took to run this call
        status : "ok", an HTTP status code, "timeout", or the exception name
    Returns:
        None
    """
    if os.getenv("RECORD_TIMINGS") != "1":
        return
    new_file = not os.path.exists(TIMING_FILE)
    with open(TIMING_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["Function", "Call", "Kind", "Time Taken", "Status"])
        writer.writerow([function, call, kind, round(timeSeconds, 3), status])


@contextmanager
def timed(function: str, call : str, kind: str):
    result = {"status" : "ok"}
    t0 = time.perf_counter()
    try:
        yield result 
    except httpx.TimeoutException:
        result["status"] = "timeout"
        raise
    except Exception as e:
        result["status"] = type(e).__name__
        raise
    except asyncio.CancelledError:
        result["status"] = "cancelled"
        raise
    finally:
        record_timing(function, call, kind, time.perf_counter() - t0, result["status"])




