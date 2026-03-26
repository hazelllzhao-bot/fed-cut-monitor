from datetime import datetime, timedelta
import pandas as pd
from pandas_datareader import data as web

end = datetime.today()
start = end - timedelta(days=365 * 2)

series_map = {
    "DGS2": "ust2",
    "DGS10": "ust10",
    "T10Y2Y": "curve_10s2s",
    "DFF": "fed_funds",
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

value_cols = ["ust2", "ust10", "curve_10s2s", "fed_funds"]

for col in value_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df[value_cols] = df[value_cols].ffill()
df = df.dropna(subset=value_cols).reset_index(drop=True)

# ---------------------------
# 降息预期代理（MVP）
# 解释：
# fed_cuts_proxy_bp = (当前联邦基金有效利率 - 2Y美债收益率) * 100
# 若该值为正，通常表示市场在计价未来一段时间的降息
# 若该值为负，通常表示市场仍在计价 higher for longer / 甚至加息风险
# ---------------------------
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

df = df[
    [
        "date",
        "ust2",
        "ust10",
        "curve_10s2s",
        "fed_funds",
        "fed_cuts_proxy_bp",
        "fed_cut_expectation_label",
    ]
]

df.to_csv("market_data.csv", index=False)

print("market_data.csv updated successfully")
print(df.tail())
