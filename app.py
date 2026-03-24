from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Fed Cut Monitor", layout="wide")

st.title("Fed Cut Monitor")
st.caption("MVP：先监控美债2Y / 10Y / 10s2s，后续再接入 Fed 降息预期、估值代理和 regime 判断")

# 优先读取真实数据；如果没有，就退回 sample.csv
if Path("market_data.csv").exists():
    df = pd.read_csv("market_data.csv")
    data_source = "真实数据：FRED"
else:
    df = pd.read_csv("sample.csv")
    data_source = "演示数据：sample.csv"

# 基础清洗
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)

latest = df.iloc[-1]

# 处理“上一条数据”，避免数据太少时报错
has_prev = len(df) >= 2
if has_prev:
    prev = df.iloc[-2]
    delta_2y_bp = (latest["ust2"] - prev["ust2"]) * 100
    delta_10y_bp = (latest["ust10"] - prev["ust10"]) * 100
    delta_curve_bp = (latest["curve_10s2s"] - prev["curve_10s2s"]) * 100
else:
    delta_2y_bp = None
    delta_10y_bp = None
    delta_curve_bp = None

# 顶部信息
st.info(f"当前数据来源：{data_source}")
st.caption(f"最新数据日期：{latest['date'].strftime('%Y-%m-%d')}")

# 顶部指标
col1, col2, col3 = st.columns(3)

if has_prev:
    col1.metric("UST 2Y", f"{latest['ust2']:.2f}%", f"{delta_2y_bp:.1f} bp")
    col2.metric("UST 10Y", f"{latest['ust10']:.2f}%", f"{delta_10y_bp:.1f} bp")
    col3.metric("10s2s", f"{latest['curve_10s2s']:.2f}%", f"{delta_curve_bp:.1f} bp")
else:
    col1.metric("UST 2Y", f"{latest['ust2']:.2f}%")
    col2.metric("UST 10Y", f"{latest['ust10']:.2f}%")
    col3.metric("10s2s", f"{latest['curve_10s2s']:.2f}%")

# 主图
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

fig1.update_layout(legend_title_text="指标")
st.plotly_chart(fig1, use_container_width=True)

# 后续扩展字段：如果数据里已经有，就自动显示
if "cuts_12m_bp" in df.columns:
    st.subheader("降息预期（预留）")
    fig2 = px.line(
        df,
        x="date",
        y="cuts_12m_bp",
        labels={"cuts_12m_bp": "未来12个月累计降息(bp)", "date": "日期"}
    )
    st.plotly_chart(fig2, use_container_width=True)

if "spy_pe_fy1" in df.columns and "qqq_pe_trailing" in df.columns:
    st.subheader("估值代理（预留）")
    fig3 = px.line(
        df,
        x="date",
        y=["spy_pe_fy1", "qqq_pe_trailing"],
        labels={
            "value": "估值水平",
            "date": "日期",
            "variable": "指标"
        }
    )

    fig3.for_each_trace(
        lambda t: t.update(
            name={
                "spy_pe_fy1": "SPY PE FY1",
                "qqq_pe_trailing": "QQQ Trailing PE"
            }.get(t.name, t.name)
        )
    )

    fig3.update_layout(legend_title_text="指标")
    st.plotly_chart(fig3, use_container_width=True)

# 自动解读
st.subheader("自动解读")

curve_text = "陡峭化" if latest["curve_10s2s"] > 0 else "倒挂/偏平"
direction_2y = "上行" if (delta_2y_bp is not None and delta_2y_bp > 0) else "下行或持平"
direction_10y = "上行" if (delta_10y_bp is not None and delta_10y_bp > 0) else "下行或持平"
direction_curve = "走陡" if (delta_curve_bp is not None and delta_curve_bp > 0) else "走平或倒挂加深"

if has_prev:
    st.write(
        f"最新数据显示，UST 2Y 为 {latest['ust2']:.2f}%（较上一条 {delta_2y_bp:.1f} bp，{direction_2y}），"
        f"UST 10Y 为 {latest['ust10']:.2f}%（较上一条 {delta_10y_bp:.1f} bp，{direction_10y}），"
        f"10s2s 为 {latest['curve_10s2s']:.2f}%（较上一条 {delta_curve_bp:.1f} bp，{direction_curve}）。"
    )
else:
    st.write(
        f"最新数据显示，UST 2Y 为 {latest['ust2']:.2f}%，"
        f"UST 10Y 为 {latest['ust10']:.2f}%，"
        f"10s2s 为 {latest['curve_10s2s']:.2f}%。"
    )

st.write(f"当前曲线形态可粗略理解为：**{curve_text}**。")

st.caption("下一步会接入 Fed 降息预期、SPY/QQQ 估值代理、regime 标签和更完整的自动解读。")

# 调试/核对区
st.subheader("最近10行原始数据")
st.dataframe(df.tail(10), use_container_width=True)
