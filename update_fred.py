from datetime import datetime, timedelta
import pandas as pd
from pandas_datareader import data as web

end = datetime.today()
start = end - timedelta(days=365 * 2)

series_map = {
    "DGS2": "ust2",
    "DGS10": "ust10",
    "T10Y2Y": "curve_10s2s",
}

frames = []

for fred_code, new_name in series_map.items():
    s = web.DataReader(fred_code, "fred", start, end)
    s = s.rename(columns={fred_code: new_name})
    frames.append(s)

df = pd.concat(frames, axis=1).reset_index()
df = df.rename(columns={"DATE": "date", "DATE ": "date"})

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date"]).sort_values("date").drop_duplicates(subset=["date"]).reset_index(drop=True)

value_cols = ["ust2", "ust10", "curve_10s2s"]

for col in value_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df[value_cols] = df[value_cols].ffill()
df = df.dropna(subset=value_cols).reset_index(drop=True)

df = df[["date", "ust2", "ust10", "curve_10s2s"]]

df.to_csv("market_data.csv", index=False)

print("market_data.csv updated successfully")
print(df.tail())
