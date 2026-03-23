import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Fed Cut Monitor", layout="wide")

st.title("Fed Cut Monitor")
st.caption("第一版演示页面")

df = pd.read_csv("data/sample.csv")
df["date"] = pd.to_datetime(df["date"])

latest = df.iloc[-1]

col1, col2, col3, col4 = st.columns(4)
col1.metric("12M Cuts Priced (bp)", f"{latest['cuts_12m_bp']:.0f}")
col2.metric("UST 2Y", f"{latest['ust2']:.2f}%")
col3.metric("UST 10Y", f"{latest['ust10']:.2f}%")
col4.metric("10s2s", f"{latest['curve_10s2s']:.2f}%")

st.subheader("政策预期")
fig1 = px.line(df, x="date", y="cuts_12m_bp")
st.plotly_chart(fig1, use_container_width=True)

st.subheader("利率")
fig2 = px.line(df, x="date", y=["ust2", "ust10", "curve_10s2s"])
st.plotly_chart(fig2, use_container_width=True)

st.subheader("估值代理")
fig3 = px.line(df, x="date", y=["spy_pe_fy1", "qqq_pe_trailing"])
st.plotly_chart(fig3, use_container_width=True)

st.subheader("自动解读")
st.write(
    f"最新数据显示，市场计入未来12个月降息约 {latest['cuts_12m_bp']:.0f}bp，"
    f"2Y 回落至 {latest['ust2']:.2f}%，10Y 为 {latest['ust10']:.2f}%，"
    f"当前曲线为 {latest['curve_10s2s']:.2f}%。"
)
