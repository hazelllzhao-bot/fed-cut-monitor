from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Fed Cut Monitor", layout="wide")

st.title("Fed Cut Monitor")
st.caption("MVP：先监控美债 2Y / 10Y / 10s2s，后续再接入 Fed 降息预期、估值代理和 regime 判断")

# 读取数据
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

# 时间窗口
window_map = {
    "30天": 30,
    "90天": 90,
    "1年": 365,
    "全部": None,
}

selected_window = st.radio(
    "查看区间",
    options=list(window_map.keys()),
    horizontal=True,
)

window_days = window_map[selected_window]

if window_days is None:
    view_df = df.copy()
else:
    cutoff = df["date"].max() - pd.Timedelta(days=window_days)
    view_df = df[df["date"] >= cutoff].copy()

# 顶部信息
st.info(f"当前数据来源：{data_source}")
st.caption(f"最新数据日期：{latest['date'].strftime('%Y-%m-%d')}")

# 状态判断
if latest["curve_10s2s"] > 0:
    curve_state = "正常陡峭 / 正斜率"
elif latest["curve_10s2s"] < 0:
    curve_state = "倒挂"
else:
    curve_state = "近乎走平"

if delta_curve_bp is not None:
    if delta_curve_bp > 0:
        curve_move = "今天相对上一条：走陡"
    elif delta_curve_bp < 0:
        curve_move = "今天相对上一条：走平 / 倒挂加深"
    else:
        curve_move = "今天相对上一条：基本不变"
else:
    curve_move = "数据不足，暂无变化判断"

# 顶部指标
col1, col2, col3, col4 = st.columns(4)

if has_prev:
    col1.metric("UST 2Y", f"{latest['ust2']:.2f}%", f"{delta_2y_bp:.1f} bp")
    col2.metric("UST 10Y", f"{latest['ust10']:.2f}%", f"{delta_10y_bp:.1f} bp")
    col3.metric("10s2s", f"{latest['curve_10s2s']:.2f}%", f"{delta_curve_bp:.1f} bp")
else:
    col1.metric("UST 2Y", f"{latest['ust2']:.2f}%")
    col2.metric("UST 10Y", f"{latest['ust10']:.2f}%")
    col3.metric("10s2s", f"{latest['curve_10s2s']:.2f}%")

col4.metric("曲线状态", curve_state)

st.caption(curve_move)

# 图1：2Y / 10Y
st.subheader("美债收益率（2Y / 10Y）")
fig_rates = px.line(
    view_df,
    x="date",
    y=["ust2", "ust10"],
    labels={
        "value": "收益率 (%)",
        "date": "日期",
        "variable": "指标",
    },
)

fig_rates.for_each_trace(
    lambda t: t.update(
        name={
            "ust2": "UST 2Y",
            "ust10": "UST 10Y",
        }.get(t.name, t.name)
    )
)

fig_rates.update_layout(legend_title_text="指标")
st.plotly_chart(fig_rates, use_container_width=True)

# 图2：10s2s 单独看，更清楚
st.subheader("期限利差（10s2s）")
fig_curve = px.line(
    view_df,
    x="date",
    y="curve_10s2s",
    labels={
        "curve_10s2s": "10s2s (%)",
        "date": "日期",
    },
)
st.plotly_chart(fig_curve, use_container_width=True)

# 预留：后面接入更多字段后自动显示
if "cuts_12m_bp" in df.columns:
    st.subheader("降息预期（预留）")
    fig_cuts = px.line(
        view_df,
        x="date",
        y="cuts_12m_bp",
        labels={
            "cuts_12m_bp": "未来12个月累计降息(bp)",
            "date": "日期",
        },
    )
    st.plotly_chart(fig_cuts, use_container_width=True)

if "spy_pe_fy1" in df.columns and "qqq_pe_trailing" in df.columns:
    st.subheader("估值代理（预留）")
    fig_val = px.line(
        view_df,
        x="date",
        y=["spy_pe_fy1", "qqq_pe_trailing"],
        labels={
            "value": "估值水平",
            "date": "日期",
            "variable": "指标",
        },
    )

    fig_val.for_each_trace(
        lambda t: t.update(
            name={
                "spy_pe_fy1": "SPY PE FY1",
                "qqq_pe_trailing": "QQQ Trailing PE",
            }.get(t.name, t.name)
        )
    )

    fig_val.update_layout(legend_title_text="指标")
    st.plotly_chart(fig_val, use_container_width=True)

# 自动解读
st.subheader("自动解读")

if has_prev:
    direction_2y = "上行" if delta_2y_bp > 0 else "下行或持平"
    direction_10y = "上行" if delta_10y_bp > 0 else "下行或持平"
    direction_curve = "走陡" if delta_curve_bp > 0 else "走平或倒挂加深"

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

st.write(f"当前曲线形态可粗略理解为：**{curve_state}**。")
st.caption("下一步会接入 Fed 降息预期、SPY/QQQ 估值代理、regime 标签和更完整的自动解读。")

# 原始数据区
st.subheader("最近10行原始数据")
st.dataframe(df.tail(10), use_container_width=True)
