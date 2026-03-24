from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Fed Cut Monitor", layout="wide")

st.title("Fed Cut Monitor")
st.caption("第二版：先接入真实的美债利率数据")

# 优先读真实数据；如果还没有，就退回 sample.csv
if Path("market_data.csv").exists():
    df = pd.read_csv("market_data.csv")
    data_source = "真实数据：FRED"
else:
    df = pd.read_csv("sample.csv")
    data_source = "演示数据：sample.csv"

df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date")

latest = df.iloc[-1]

st.info(f"当前数据来源：{data_source}")
st.caption(f"最新数据日期：{latest['date'].strftime('%Y-%m-%d')}")

col1, col2, col3 = st.columns(3)
col1.metric("UST 2Y", f"{latest['ust2']:.2f}%")
col2.metric("UST 10Y", f"{latest['ust10']:.2f}%")
col3.metric("10s2s", f"{latest['curve_10s2s']:.2f}%")

st.subheader("美债利率主图")
fig1 = px.line(
    df,
    x="date",
    y=["ust2", "ust10", "curve_10s2s"],
    labels={
        "value": "收益率 / 利差 (%)",
        "date": "日期",
        "variable": "指标"
    }
)

fig1.for_each_trace(
    lambda t: t.update(
        name={
            "ust2": "UST 2Y",
            "ust10": "UST 10Y",
            "curve_10s2s": "10s2s"
        }.get(t.name, t.name)
    )
)

st.plotly_chart(fig1, use_container_width=True)

# 如果是假数据，才显示 cuts 和 valuation 图
if "cuts_12m_bp" in df.columns:
    st.subheader("政策预期")
    fig2 = px.line(df, x="date", y="cuts_12m_bp")
    st.plotly_chart(fig2, use_container_width=True)

if "spy_pe_fy1" in df.columns and "qqq_pe_trailing" in df.columns:
    st.subheader("估值代理")
    fig3 = px.line(df, x="date", y=["spy_pe_fy1", "qqq_pe_trailing"])
    st.plotly_chart(fig3, use_container_width=True)

st.subheader("自动解读")
st.write(
    f"最新数据显示，2Y 为 {latest['ust2']:.2f}%，"
    f"10Y 为 {latest['ust10']:.2f}%，"
    f"10s2s 为 {latest['curve_10s2s']:.2f}%。"
)

st.caption("下一步会接入 Fed 宽松预期和估值代理。")
st.subheader("最近10行原始数据")
st.dataframe(df.tail(10), use_container_width=True)
