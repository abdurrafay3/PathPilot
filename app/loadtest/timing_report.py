import pandas as pd
import os

TIMING_FILE = "timing.csv"

def getTable():
    """ 
    Once the timings from each call is fetched. We display the table using pandas
    """
    file_exists = os.path.exists(TIMING_FILE)
    if not file_exists:
        return
    # otherwise open with pandas
    df = pd.read_csv(TIMING_FILE)
    table : pd.DataFrame = (
        df.groupby(["Function", "Call", "Kind"])["Time Taken"]
        .agg(
            median="median",
            p95=lambda s: s.quantile(0.95),
            max="max",
        ).sort_values("median", ascending=False)
        .reset_index()
    )
    table.to_csv("timing_report.csv", index=False)
    print(table.to_markdown(index=False))

if __name__ == "__main__":
    getTable()




