from datetime import datetime, timedelta, timezone
import json
import pandas as pd
from pandas_datareader import data as web

end = datetime.today()
start = end - timedelta(days=365 * 2)

series_map = {
    "DGS2": "ust2",
    "DGS10": "ust10",
    "T10Y2Y": "curve_10s2s",
    "DFF": "fed_funds",
    "SP500": "sp500_index",
    "NASDAQ100": "nasdaq100_index",
}

frames = []

for fred_code, new_name in series_map.items():
    s = web.DataReader(fred_code, "fred", start, end)
    s = s.rename(columns={fred_code: new_name})
    frames.append(s)

df = pd.concat(frames, axis=1).reset_index()
df = df.rename(columns={"DATE": "date", "DATE ": "date"})

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = (
    df.dropna(subset=["date"])
    .sort_values("date")
    .drop_duplicates(subset=["date"])
    .reset_index(drop=True)
)

value_cols = [
    "ust2",
    "ust10",
    "curve_10s2s",
    "fed_funds",
    "sp500_index",
    "nasdaq100_index",
]

for col in value_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df[value_cols] = df[value_cols].ffill()
df = df.dropna(subset=value_cols).reset_index(drop=True)

# 1) Fed 降息预期代理（MVP）
df["fed_cuts_proxy_bp"] = ((df["fed_funds"] - df["ust2"]) * 100).round(1)

def label_cut_expectation(x):
    if pd.isna(x):
        return "unknown"
    if x >= 50:
        return "strong_easing_priced"
    elif x >= 15:
        return "mild_easing_priced"
    elif x > -15:
        return "neutral"
    else:
        return "higher_for_longer"

df["fed_cut_expectation_label"] = df["fed_cuts_proxy_bp"].apply(label_cut_expectation)

# 2) SPY / QQQ 估值代理（MVP）
df["sp500_200dma"] = df["sp500_index"].rolling(window=200, min_periods=60).mean()
df["nasdaq100_200dma"] = df["nasdaq100_index"].rolling(window=200, min_periods=60).mean()

df["spy_valuation_proxy_pct"] = (
    (df["sp500_index"] / df["sp500_200dma"] - 1) * 100
).round(2)

df["qqq_valuation_proxy_pct"] = (
    (df["nasdaq100_index"] / df["nasdaq100_200dma"] - 1) * 100
).round(2)

def label_valuation_proxy(x):
    if pd.isna(x):
        return "unknown"
    if x >= 10:
        return "rich_vs_trend"
    elif x <= -10:
        return "cheap_vs_trend"
    else:
        return "neutral"

df["spy_valuation_label"] = df["spy_valuation_proxy_pct"].apply(label_valuation_proxy)
df["qqq_valuation_label"] = df["qqq_valuation_proxy_pct"].apply(label_valuation_proxy)

# 3) regime 标签（MVP）
def classify_regime(row):
    fed_proxy = row.get("fed_cuts_proxy_bp")
    curve = row.get("curve_10s2s")
    qqq_proxy = row.get("qqq_valuation_proxy_pct")

    if pd.isna(fed_proxy) or pd.isna(curve) or pd.isna(qqq_proxy):
        return "neutral"

    if fed_proxy >= 50 and (curve < 0 or qqq_proxy <= -5):
        return "bad_cuts"

    if fed_proxy >= 15 and curve >= -0.25 and qqq_proxy > -5:
        return "good_cuts"

    return "neutral"

df["regime_label"] = df.apply(classify_regime, axis=1)

df = df[
    [
        "date",
        "ust2",
        "ust10",
        "curve_10s2s",
        "fed_funds",
        "fed_cuts_proxy_bp",
        "fed_cut_expectation_label",
        "sp500_index",
        "nasdaq100_index",
        "spy_valuation_proxy_pct",
        "qqq_valuation_proxy_pct",
        "spy_valuation_label",
        "qqq_valuation_label",
        "regime_label",
    ]
]

df.to_csv("market_data.csv", index=False)

latest_date = df["date"].max()
latest_date_str = latest_date.strftime("%Y-%m-%d") if pd.notna(latest_date) else None

status = {
    "last_successful_update_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "data_start_date": df["date"].min().strftime("%Y-%m-%d") if not df.empty else None,
    "data_end_date": latest_date_str,
    "row_count": int(len(df)),
    "column_count": int(len(df.columns)),
    "data_source": "FRED",
    "series_codes": list(series_map.keys()),
}

with open("update_status.json", "w", encoding="utf-8") as f:
    json.dump(status, f, ensure_ascii=False, indent=2)

print("market_data.csv updated successfully")
print("update_status.json updated successfully")
print(df.tail())
print(status)
