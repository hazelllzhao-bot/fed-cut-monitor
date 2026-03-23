from pathlib import Path
import pandas as pd
from pandas_datareader import data as web

# 取最近两年数据
end = pd.Timestamp.today().normalize()
start = end - pd.Timedelta(days=365 * 2)

series = ["DGS2", "DGS10", "T10Y2Y"]

df = web.DataReader(series, "fred", start, end)
df = df.reset_index()

# 把第一列统一改成 date
first_col = df.columns[0]
df = df.rename(columns={first_col: "date"})

# 改成更容易读的列名
df = df.rename(columns={
    "DGS2": "ust2",
    "DGS10": "ust10",
    "T10Y2Y": "curve_10s2s"
})

# 丢掉全空行
df = df.dropna(how="all")

# 保存到仓库根目录
df.to_csv("market_data.csv", index=False)

print("已生成 market_data.csv")
print(df.tail())