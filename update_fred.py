from datetime import datetime, timedelta
import pandas as pd
from pandas_datareader import data as web

# 取最近两年的数据
end = datetime.today()
start = end - timedelta(days=365 * 2)

series_map = {
    "DGS2": "ust2",
    "DGS10": "ust10",
    "T10Y2Y": "curve_10s2s",
}

all_data = []

for fred_code, new_name in series_map.items():
    s = web.DataReader(fred_code, "fred", start, end)
    s = s.rename(columns={fred_code: new_name})
    all_data.append(s)

df = pd.concat(all_data, axis=1).reset_index()
df = df.rename(columns={"DATE": "date"})

# 日期处理
df["date"] = pd.to_datetime(df["date"])

# 按日期排序
df = df.sort_values("date").reset_index(drop=True)

# 用前值填充，避免某些交易日单列缺失
df[["ust2", "ust10", "curve_10s2s"]] = df[["ust2", "ust10", "curve_10s2s"]].ffill()

# 删除仍然缺失的行（通常是最前面少数行）
df = df.dropna(subset=["ust2", "ust10", "curve_10s2s"]).reset_index(drop=True)

# 只保留需要的列顺序
df = df[["date", "ust2", "ust10", "curve_10s2s"]]

# 输出到仓库根目录
df.to_csv("market_data.csv", index=False)

print("market_data.csv updated successfully")
print(df.tail())
