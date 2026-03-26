import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="宏观市场监控面板",
    layout="wide",
)

st.title("宏观市场监控面板")
st.caption("主题：美联储降息预期、纳指/标普500估值代理、2Y/10Y美债收益率及曲线联动监控")

REQUIRED_BASE_COLS = ["date", "ust2", "ust10", "curve_10s2s"]

OPTIONAL_NUMERIC_COLS = [
    "fed_funds",
    "fed_cuts_proxy_bp",
    "sp500_index",
    "nasdaq100_index",
    "spy_valuation_proxy_pct",
    "qqq_valuation_proxy_pct",
]

OPTIONAL_TEXT_DEFAULTS = {
    "fed_cut_expectation_label": "unknown",
    "spy_valuation_label": "unknown",
    "qqq_valuation_label": "unknown",
    "regime_label": "neutral",
}


@st.cache_data(ttl=3600)
def load_data():
    candidates = [
        ("market_data.csv", "真实数据：FRED"),
        ("sample.csv", "示例数据：sample.csv"),
    ]

    for file_name, source_label in candidates:
        if not os.path.exists(file_name):
            continue

        try:
            df = pd.read_csv(file_name)

            if "date" not in df.columns:
                continue

            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"]).copy()

            for col in REQUIRED_BASE_COLS[1:]:
                if col not in df.columns:
                    df[col] = pd.NA

            for col in OPTIONAL_NUMERIC_COLS:
                if col not in df.columns:
                    df[col] = pd.NA

            for col, default_value in OPTIONAL_TEXT_DEFAULTS.items():
                if col not in df.columns:
                    df[col] = default_value
                df[col] = df[col].fillna(default_value).astype(str)

            numeric_cols = REQUIRED_BASE_COLS[1:] + OPTIONAL_NUMERIC_COLS
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            df = (
                df.sort_values("date")
                .drop_duplicates(subset=["date"])
                .reset_index(drop=True)
            )

            if df[["ust2", "ust10", "curve_10s2s"]].dropna(how="all").empty:
                continue

            return df, source_label

        except Exception:
            continue

    return None, "无可用数据"


def bp_delta_from_pct_series(series: pd.Series) -> pd.Series:
    return series.diff() * 100


def format_pct(value):
    if pd.isna(value):
        return "N/A"
    return f"{value:.2f}%"


def format_bp_from_pct(value):
    if pd.isna(value):
        return "N/A"
    return f"{value * 100:.1f} bp"


def format_bp_value(value):
    if pd.isna(value):
        return "N/A"
    return f"{value:.1f} bp"


def format_delta_bp_from_pct(current, previous):
    if pd.isna(current) or pd.isna(previous):
        return "N/A"
    return f"{(current - previous) * 100:+.1f} bp"


def format_delta_bp(current, previous):
    if pd.isna(current) or pd.isna(previous):
        return "N/A"
    return f"{(current - previous):+.1f} bp"


def format_delta_pct(current, previous):
    if pd.isna(current) or pd.isna(previous):
        return "N/A"
    return f"{(current - previous):+.2f} pct"


def format_number(value):
    if pd.isna(value):
        return "N/A"
    return f"{value:,.1f}"


def classify_curve_state(x):
    if pd.isna(x):
        return "未知"
    return "倒挂" if x < 0 else "正常"


def classify_daily_shape(ust2_chg_bp, curve_chg_bp):
    if pd.isna(ust2_chg_bp) or pd.isna(curve_chg_bp):
        return "Neutral"

    if curve_chg_bp > 0 and ust2_chg_bp < 0:
        return "Bull Steepening"
    elif curve_chg_bp > 0 and ust2_chg_bp > 0:
        return "Bear Steepening"
    elif curve_chg_bp < 0 and ust2_chg_bp < 0:
        return "Bull Flattening"
    elif curve_chg_bp < 0 and ust2_chg_bp > 0:
        return "Bear Flattening"
    else:
        return "Neutral"


def pretty_cut_label(label):
    mapping = {
        "strong_easing_priced": "强烈计价降息",
        "mild_easing_priced": "温和计价降息",
        "neutral": "中性",
        "higher_for_longer": "更久维持高利率",
        "unknown": "未知",
    }
    return mapping.get(str(label), str(label))


def pretty_valuation_label(label):
    mapping = {
        "rich_vs_trend": "高于趋势偏热",
        "cheap_vs_trend": "低于趋势偏冷",
        "neutral": "中性",
        "unknown": "未知",
    }
    return mapping.get(str(label), str(label))


def pretty_regime_label(label):
    mapping = {
        "good_cuts": "good_cuts（偏积极降息交易）",
        "bad_cuts": "bad_cuts（偏衰退式降息交易）",
        "neutral": "neutral（中性）",
        "unknown": "未知",
    }
    return mapping.get(str(label), str(label))


def get_freshness_message(latest_date):
    today = pd.Timestamp.today().normalize()
    latest_day = pd.to_datetime(latest_date).normalize()
    days_old = (today - latest_day).days

    if days_old <= 3:
        return "success", f"数据新鲜度正常：距离最新数据日 {days_old} 天"
    elif days_old <= 7:
        return "warning", f"数据略有滞后：距离最新数据日 {days_old} 天"
    else:
        return "error", f"数据可能过旧：距离最新数据日 {days_old} 天"


def build_interpretation(latest_row):
    parts = []

    ust2 = latest_row.get("ust2")
    ust10 = latest_row.get("ust10")
    curve = latest_row.get("curve_10s2s")
    curve_state = latest_row.get("curve_state")
    daily_shape = latest_row.get("daily_shape")
    fed_proxy = latest_row.get("fed_cuts_proxy_bp")
    fed_label = pretty_cut_label(latest_row.get("fed_cut_expectation_label", "unknown"))
    spy_proxy = latest_row.get("spy_valuation_proxy_pct")
    qqq_proxy = latest_row.get("qqq_valuation_proxy_pct")
    spy_label = pretty_valuation_label(latest_row.get("spy_valuation_label", "unknown"))
    qqq_label = pretty_valuation_label(latest_row.get("qqq_valuation_label", "unknown"))
    regime_label = pretty_regime_label(latest_row.get("regime_label", "neutral"))

    if not pd.isna(ust2) and not pd.isna(ust10):
        parts.append(f"当前 2Y 为 {ust2:.2f}%，10Y 为 {ust10:.2f}%。")

    if not pd.isna(curve):
        parts.append(f"10s2s 为 {curve * 100:.1f} bp，当前曲线状态为“{curve_state}”。")

    if not pd.isna(fed_proxy):
        parts.append(f"降息预期代理为 {fed_proxy:.1f} bp，对应标签为“{fed_label}”。")

    if not pd.isna(spy_proxy) and not pd.isna(qqq_proxy):
        parts.append(
            f"当前 SPY 估值代理为 {spy_proxy:.2f}%，标签为“{spy_label}”；"
            f"QQQ 估值代理为 {qqq_proxy:.2f}%，标签为“{qqq_label}”。"
        )

    parts.append(f"当前 regime 标签为“{regime_label}”。")
    parts.append(f"最近一个交易日的日度形态判断为“{daily_shape}”。")

    raw_regime = str(latest_row.get("regime_label", "neutral"))

    if raw_regime == "good_cuts":
        parts.append("当前更接近“好降息”交易：市场在计价降息，但风险资产位置与曲线状态尚未明显恶化。")
    elif raw_regime == "bad_cuts":
        parts.append("当前更接近“坏降息”交易：市场在明显计价降息，同时风险资产或曲线状态偏弱，更像衰退式宽松预期。")
    else:
        parts.append("当前更接近中性阶段，说明降息交易与风险偏好信号还没有形成特别明确的单边组合。")

    return " ".join(parts)


def build_signal_dashboard(latest_row):
    raw_regime = str(latest_row.get("regime_label", "neutral"))
    raw_cut = str(latest_row.get("fed_cut_expectation_label", "unknown"))
    raw_spy = str(latest_row.get("spy_valuation_label", "unknown"))
    raw_qqq = str(latest_row.get("qqq_valuation_label", "unknown"))
    curve_state = str(latest_row.get("curve_state", "未知"))
    daily_shape = str(latest_row.get("daily_shape", "Neutral"))

    if raw_regime == "good_cuts":
        headline = "当前主结论：更接近“好降息”交易，风险偏好仍有支撑。"
        tone = "success"
        stance = "当前偏向：在降息预期存在的情况下，市场暂未明显切入衰退恐慌模式。"
    elif raw_regime == "bad_cuts":
        headline = "当前主结论：更接近“坏降息”交易，要更关注增长/衰退担忧。"
        tone = "error"
        stance = "当前偏向：市场在计价降息，但这种降息更像是对基本面走弱的反应。"
    else:
        headline = "当前主结论：处于中性过渡区，信号还没有形成明确单边组合。"
        tone = "info"
        stance = "当前偏向：先观察利率、曲线和风险资产代理是否继续朝同一方向强化。"

    rate_signal = f"利率信号：{pretty_cut_label(raw_cut)}；曲线状态：{curve_state}；最新日度形态：{daily_shape}。"
    risk_signal = (
        f"风险资产信号：SPY 为 {pretty_valuation_label(raw_spy)}，"
        f"QQQ 为 {pretty_valuation_label(raw_qqq)}。"
    )

    watch_items = []

    if raw_cut == "strong_easing_priced":
        watch_items.append("盯住：市场是否继续强化降息交易，避免把“降息预期升温”直接等同于利好风险资产。")
    elif raw_cut == "higher_for_longer":
        watch_items.append("盯住：短端利率是否继续维持高位，这通常不利于高久期成长风格继续扩张估值。")
    else:
        watch_items.append("盯住：降息预期是否从中性进一步走向明确方向。")

    if curve_state == "倒挂":
        watch_items.append("盯住：10s2s 是否继续修复；若长期倒挂，通常说明增长预期仍有压力。")
    else:
        watch_items.append("盯住：曲线转正后是“健康修复”还是“衰退式陡峭化”。")

    if raw_qqq == "rich_vs_trend":
        watch_items.append("盯住：QQQ 位置已偏热，后续更需要盈利或流动性继续配合。")
    elif raw_qqq == "cheap_vs_trend":
        watch_items.append("盯住：QQQ 位置偏冷，需观察是超跌机会还是基本面走弱前兆。")
    else:
        watch_items.append("盯住：QQQ 位置暂时中性，等待是否出现趋势性偏离。")

    return {
        "headline": headline,
        "tone": tone,
        "stance": stance,
        "rate_signal": rate_signal,
        "risk_signal": risk_signal,
        "watch_items": watch_items,
    }


def build_fomc_event_view(df_input: pd.DataFrame) -> pd.DataFrame:
    fomc_dates = [
        "2024-01-31",
        "2024-03-20",
        "2024-05-01",
        "2024-06-12",
        "2024-07-31",
        "2024-09-18",
        "2024-11-07",
        "2024-12-18",
        "2025-01-29",
        "2025-03-19",
        "2025-05-07",
        "2025-06-18",
        "2025-07-30",
        "2025-09-17",
        "2025-10-29",
        "2025-12-10",
        "2026-01-28",
        "2026-03-18",
    ]

    event_rows = []

    for event_date_str in fomc_dates:
        event_date = pd.to_datetime(event_date_str)
        eligible = df_input[df_input["date"] <= event_date].copy()

        if eligible.empty:
            continue

        row = eligible.iloc[-1]

        event_rows.append(
            {
                "fomc_date": event_date,
                "market_date_used": row["date"],
                "ust2": row["ust2"],
                "ust10": row["ust10"],
                "curve_10s2s": row["curve_10s2s"],
                "fed_cuts_proxy_bp": row["fed_cuts_proxy_bp"],
                "qqq_valuation_proxy_pct": row["qqq_valuation_proxy_pct"],
                "regime_label": row["regime_label"],
                "fed_cut_expectation_label": row["fed_cut_expectation_label"],
            }
        )

    if not event_rows:
        return pd.DataFrame()

    event_df = pd.DataFrame(event_rows).sort_values("fomc_date", ascending=False).reset_index(drop=True)
    return event_df


df, data_source = load_data()

if df is None or df.empty:
    st.error("没有读到可用数据。请先确认仓库里存在 market_data.csv，且文件中包含 date / ust2 / ust10 / curve_10s2s。")
    st.stop()

df = df.copy()

df["curve_state"] = df["curve_10s2s"].apply(classify_curve_state)
df["ust2_chg_bp"] = bp_delta_from_pct_series(df["ust2"])
df["ust10_chg_bp"] = bp_delta_from_pct_series(df["ust10"])
df["curve_10s2s_chg_bp"] = bp_delta_from_pct_series(df["curve_10s2s"])
df["fed_funds_chg_bp"] = bp_delta_from_pct_series(df["fed_funds"])
df["fed_cuts_proxy_chg_bp"] = df["fed_cuts_proxy_bp"].diff()
df["sp500_index_chg"] = df["sp500_index"].diff()
df["nasdaq100_index_chg"] = df["nasdaq100_index"].diff()
df["spy_valuation_proxy_chg"] = df["spy_valuation_proxy_pct"].diff()
df["qqq_valuation_proxy_chg"] = df["qqq_valuation_proxy_pct"].diff()

df["daily_shape"] = df.apply(
    lambda row: classify_daily_shape(row["ust2_chg_bp"], row["curve_10s2s_chg_bp"]),
    axis=1,
)

latest_row = df.iloc[-1]
previous_row = df.iloc[-2] if len(df) >= 2 else df.iloc[-1]
latest_date = latest_row["date"]

st.markdown(f"**当前数据来源：{data_source}**")
st.markdown(f"**最新数据日期：{latest_date.strftime('%Y-%m-%d')}**")

freshness_level, freshness_message = get_freshness_message(latest_date)
if freshness_level == "success":
    st.success(freshness_message)
elif freshness_level == "warning":
    st.warning(freshness_message)
else:
    st.error(freshness_message)

top1, top2, top3, top4, top5 = st.columns(5)

top1.metric(
    "UST 2Y",
    format_pct(latest_row["ust2"]),
    format_delta_bp_from_pct(latest_row["ust2"], previous_row["ust2"]),
)

top2.metric(
    "UST 10Y",
    format_pct(latest_row["ust10"]),
    format_delta_bp_from_pct(latest_row["ust10"], previous_row["ust10"]),
)

top3.metric(
    "10s2s",
    format_bp_from_pct(latest_row["curve_10s2s"]),
    format_delta_bp_from_pct(latest_row["curve_10s2s"], previous_row["curve_10s2s"]),
)

top4.metric(
    "降息预期代理",
    format_bp_value(latest_row["fed_cuts_proxy_bp"]),
    format_delta_bp(latest_row["fed_cuts_proxy_bp"], previous_row["fed_cuts_proxy_bp"]),
)

top5.metric(
    "当前 Regime",
    pretty_regime_label(latest_row["regime_label"]),
    "",
)

st.subheader("时间窗口")
window = st.radio(
    "选择查看区间",
    options=["30天", "90天", "1年", "全部"],
    horizontal=True,
)

filtered_df = df.copy()
max_date = df["date"].max()

if window == "30天":
    filtered_df = df[df["date"] >= (max_date - pd.Timedelta(days=30))]
elif window == "90天":
    filtered_df = df[df["date"] >= (max_date - pd.Timedelta(days=90))]
elif window == "1年":
    filtered_df = df[df["date"] >= (max_date - pd.Timedelta(days=365))]

if filtered_df.empty:
    filtered_df = df.copy()

tab1, tab2, tab3, tab4, tab5 = st.tabs(["总览", "利率监控", "风险资产代理", "事件日视图", "数据表"])

with tab1:
    signal_board = build_signal_dashboard(latest_row)

    st.subheader("一句话结论")
    if signal_board["tone"] == "success":
        st.success(signal_board["headline"])
    elif signal_board["tone"] == "error":
        st.error(signal_board["headline"])
    else:
        st.info(signal_board["headline"])

    s1, s2, s3 = st.columns(3)
    s1.metric("当前 Regime", pretty_regime_label(latest_row["regime_label"]), "")
    s2.metric("降息标签", pretty_cut_label(latest_row["fed_cut_expectation_label"]), "")
    s3.metric("QQQ位置标签", pretty_valuation_label(latest_row["qqq_valuation_label"]), "")

    st.subheader("关键信号拆解")
    st.write(signal_board["stance"])
    st.write(signal_board["rate_signal"])
    st.write(signal_board["risk_signal"])

    st.subheader("接下来重点盯什么")
    for item in signal_board["watch_items"]:
        st.markdown(f"- {item}")

    st.subheader("自动解读（完整版）")
    st.info(build_interpretation(latest_row))

    st.subheader("Fed 降息预期代理（MVP）")
    fc1, fc2, fc3 = st.columns(3)

    fc1.metric(
        "联邦基金有效利率",
        format_pct(latest_row["fed_funds"]),
        format_delta_bp_from_pct(latest_row["fed_funds"], previous_row["fed_funds"]),
    )

    fc2.metric(
        "降息预期代理",
        format_bp_value(latest_row["fed_cuts_proxy_bp"]),
        format_delta_bp(latest_row["fed_cuts_proxy_bp"], previous_row["fed_cuts_proxy_bp"]),
    )

    fc3.metric(
        "预期标签",
        pretty_cut_label(latest_row["fed_cut_expectation_label"]),
        "",
    )

    st.caption("说明：当前 MVP 代理定义为（联邦基金有效利率 - 2Y美债收益率）×100，数值越高，通常表示市场越在提前计价未来降息。")

    st.subheader("Regime 标签（MVP）")
    rg1, rg2, rg3 = st.columns(3)

    rg1.metric(
        "当前 Regime",
        pretty_regime_label(latest_row["regime_label"]),
        "",
    )

    rg2.metric(
        "降息标签",
        pretty_cut_label(latest_row["fed_cut_expectation_label"]),
        "",
    )

    rg3.metric(
        "QQQ位置标签",
        pretty_valuation_label(latest_row["qqq_valuation_label"]),
        "",
    )

    st.caption("说明：当前 regime 还是规则版 MVP，用于先跑通自动打标签链路，后面还会继续优化判断逻辑。")

    st.subheader("关键图表总览")
    ov1, ov2 = st.columns(2)

    with ov1:
        fig_curve = go.Figure()
        fig_curve.add_trace(
            go.Scatter(
                x=filtered_df["date"],
                y=filtered_df["curve_10s2s"] * 100,
                mode="lines",
                name="10s2s (bp)",
            )
        )
        fig_curve.add_hline(y=0, line_dash="dash")
        fig_curve.update_layout(
            height=360,
            xaxis_title="日期",
            yaxis_title="bp",
            margin=dict(l=20, r=20, t=30, b=20),
            showlegend=False,
            title="期限利差（10s2s）",
        )
        st.plotly_chart(fig_curve, use_container_width=True)

    with ov2:
        fig_proxy = go.Figure()
        fig_proxy.add_trace(
            go.Scatter(
                x=filtered_df["date"],
                y=filtered_df["fed_cuts_proxy_bp"],
                mode="lines",
                name="Fed Cuts Proxy (bp)",
            )
        )
        fig_proxy.add_hline(y=0, line_dash="dash")
        fig_proxy.update_layout(
            height=360,
            xaxis_title="日期",
            yaxis_title="bp",
            margin=dict(l=20, r=20, t=30, b=20),
            showlegend=False,
            title="降息预期代理",
        )
        st.plotly_chart(fig_proxy, use_container_width=True)

with tab2:
    st.subheader("利率监控")

    rate1, rate2, rate3, rate4 = st.columns(4)

    rate1.metric(
        "UST 2Y",
        format_pct(latest_row["ust2"]),
        format_delta_bp_from_pct(latest_row["ust2"], previous_row["ust2"]),
    )

    rate2.metric(
        "UST 10Y",
        format_pct(latest_row["ust10"]),
        format_delta_bp_from_pct(latest_row["ust10"], previous_row["ust10"]),
    )

    rate3.metric(
        "10s2s",
        format_bp_from_pct(latest_row["curve_10s2s"]),
        format_delta_bp_from_pct(latest_row["curve_10s2s"], previous_row["curve_10s2s"]),
    )

    rate4.metric(
        "曲线状态",
        latest_row["curve_state"],
        latest_row["daily_shape"],
    )

    fig_yields = go.Figure()
    fig_yields.add_trace(
        go.Scatter(
            x=filtered_df["date"],
            y=filtered_df["ust2"],
            mode="lines",
            name="UST 2Y",
        )
    )
    fig_yields.add_trace(
        go.Scatter(
            x=filtered_df["date"],
            y=filtered_df["ust10"],
            mode="lines",
            name="UST 10Y",
        )
    )
    fig_yields.update_layout(
        height=420,
        xaxis_title="日期",
        yaxis_title="收益率 (%)",
        margin=dict(l=20, r=20, t=30, b=20),
        title="美债收益率（2Y / 10Y）",
    )
    st.plotly_chart(fig_yields, use_container_width=True)

    fig_curve2 = go.Figure()
    fig_curve2.add_trace(
        go.Scatter(
            x=filtered_df["date"],
            y=filtered_df["curve_10s2s"] * 100,
            mode="lines",
            name="10s2s (bp)",
        )
    )
    fig_curve2.add_hline(y=0, line_dash="dash")
    fig_curve2.update_layout(
        height=380,
        xaxis_title="日期",
        yaxis_title="bp",
        margin=dict(l=20, r=20, t=30, b=20),
        showlegend=False,
        title="期限利差（10s2s）",
    )
    st.plotly_chart(fig_curve2, use_container_width=True)

with tab3:
    st.subheader("风险资产代理")

    vc1, vc2, vc3, vc4 = st.columns(4)

    vc1.metric(
        "标普500指数代理",
        format_number(latest_row["sp500_index"]),
        format_number(latest_row["sp500_index_chg"]) if pd.notna(latest_row["sp500_index_chg"]) else "N/A",
    )

    vc2.metric(
        "SPY估值代理",
        format_pct(latest_row["spy_valuation_proxy_pct"]),
        format_delta_pct(latest_row["spy_valuation_proxy_pct"], previous_row["spy_valuation_proxy_pct"]),
    )

    vc3.metric(
        "纳指100指数代理",
        format_number(latest_row["nasdaq100_index"]),
        format_number(latest_row["nasdaq100_index_chg"]) if pd.notna(latest_row["nasdaq100_index_chg"]) else "N/A",
    )

    vc4.metric(
        "QQQ估值代理",
        format_pct(latest_row["qqq_valuation_proxy_pct"]),
        format_delta_pct(latest_row["qqq_valuation_proxy_pct"], previous_row["qqq_valuation_proxy_pct"]),
    )

    vl1, vl2 = st.columns(2)
    with vl1:
        st.markdown(f"**SPY 估值标签：** {pretty_valuation_label(latest_row['spy_valuation_label'])}")
    with vl2:
        st.markdown(f"**QQQ 估值标签：** {pretty_valuation_label(latest_row['qqq_valuation_label'])}")

    st.caption("说明：当前 MVP 代理定义为“指数点位相对 200 日均线的偏离度”。这是热度/位置代理，不是真实 PE。")

    ra1, ra2 = st.columns(2)

    with ra1:
        fig_index = go.Figure()
        fig_index.add_trace(
            go.Scatter(
                x=filtered_df["date"],
                y=filtered_df["sp500_index"],
                mode="lines",
                name="SP500",
            )
        )
        fig_index.add_trace(
            go.Scatter(
                x=filtered_df["date"],
                y=filtered_df["nasdaq100_index"],
                mode="lines",
                name="NASDAQ100",
            )
        )
        fig_index.update_layout(
            height=380,
            xaxis_title="日期",
            yaxis_title="指数点位",
            margin=dict(l=20, r=20, t=30, b=20),
            title="标普500 / 纳指100 指数代理",
        )
        st.plotly_chart(fig_index, use_container_width=True)

    with ra2:
        fig_val = go.Figure()
        fig_val.add_trace(
            go.Scatter(
                x=filtered_df["date"],
                y=filtered_df["spy_valuation_proxy_pct"],
                mode="lines",
                name="SPY Proxy (%)",
            )
        )
        fig_val.add_trace(
            go.Scatter(
                x=filtered_df["date"],
                y=filtered_df["qqq_valuation_proxy_pct"],
                mode="lines",
                name="QQQ Proxy (%)",
            )
        )
        fig_val.add_hline(y=0, line_dash="dash")
        fig_val.update_layout(
            height=380,
            xaxis_title="日期",
            yaxis_title="相对200日均线偏离 (%)",
            margin=dict(l=20, r=20, t=30, b=20),
            title="SPY / QQQ 估值代理",
        )
        st.plotly_chart(fig_val, use_container_width=True)

with tab4:
    st.subheader("事件日视图（FOMC MVP）")
    st.caption("说明：先用内置 FOMC 日期做 MVP，市场数据取该事件日当日或该日前最近一个可用交易日。")

    event_df = build_fomc_event_view(df)

    if event_df.empty:
        st.warning("当前没有可显示的 FOMC 事件数据。")
    else:
        show_event_df = event_df.copy()
        show_event_df["fomc_date"] = show_event_df["fomc_date"].dt.strftime("%Y-%m-%d")
        show_event_df["market_date_used"] = show_event_df["market_date_used"].dt.strftime("%Y-%m-%d")
        show_event_df["ust2"] = show_event_df["ust2"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
        show_event_df["ust10"] = show_event_df["ust10"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
        show_event_df["curve_10s2s"] = show_event_df["curve_10s2s"].map(lambda x: f"{x * 100:.1f} bp" if pd.notna(x) else "N/A")
        show_event_df["fed_cuts_proxy_bp"] = show_event_df["fed_cuts_proxy_bp"].map(lambda x: f"{x:.1f} bp" if pd.notna(x) else "N/A")
        show_event_df["qqq_valuation_proxy_pct"] = show_event_df["qqq_valuation_proxy_pct"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
        show_event_df["regime_label"] = show_event_df["regime_label"].map(pretty_regime_label)
        show_event_df["fed_cut_expectation_label"] = show_event_df["fed_cut_expectation_label"].map(pretty_cut_label)

        show_event_df = show_event_df.rename(
            columns={
                "fomc_date": "FOMC日期",
                "market_date_used": "使用的市场数据日期",
                "ust2": "UST 2Y",
                "ust10": "UST 10Y",
                "curve_10s2s": "10s2s",
                "fed_cuts_proxy_bp": "降息预期代理",
                "qqq_valuation_proxy_pct": "QQQ估值代理",
                "regime_label": "Regime",
                "fed_cut_expectation_label": "降息标签",
            }
        )

        st.dataframe(show_event_df, use_container_width=True)

with tab5:
    st.subheader("最近5日变化监控")

    monitor_cols = [
        "date",
        "ust2",
        "ust2_chg_bp",
        "ust10",
        "ust10_chg_bp",
        "curve_10s2s",
        "curve_10s2s_chg_bp",
        "daily_shape",
        "fed_cuts_proxy_bp",
        "fed_cut_expectation_label",
        "spy_valuation_proxy_pct",
        "spy_valuation_label",
        "qqq_valuation_proxy_pct",
        "qqq_valuation_label",
        "regime_label",
    ]

    monitor_df = df[monitor_cols].tail(5).copy()
    monitor_df = monitor_df.sort_values("date", ascending=False).reset_index(drop=True)

    monitor_df["date"] = monitor_df["date"].dt.strftime("%Y-%m-%d")
    monitor_df["ust2"] = monitor_df["ust2"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
    monitor_df["ust10"] = monitor_df["ust10"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
    monitor_df["curve_10s2s"] = monitor_df["curve_10s2s"].map(lambda x: f"{x * 100:.1f} bp" if pd.notna(x) else "N/A")
    monitor_df["ust2_chg_bp"] = monitor_df["ust2_chg_bp"].map(lambda x: f"{x:+.1f} bp" if pd.notna(x) else "N/A")
    monitor_df["ust10_chg_bp"] = monitor_df["ust10_chg_bp"].map(lambda x: f"{x:+.1f} bp" if pd.notna(x) else "N/A")
    monitor_df["curve_10s2s_chg_bp"] = monitor_df["curve_10s2s_chg_bp"].map(lambda x: f"{x:+.1f} bp" if pd.notna(x) else "N/A")
    monitor_df["fed_cuts_proxy_bp"] = monitor_df["fed_cuts_proxy_bp"].map(lambda x: f"{x:.1f} bp" if pd.notna(x) else "N/A")
    monitor_df["fed_cut_expectation_label"] = monitor_df["fed_cut_expectation_label"].map(pretty_cut_label)
    monitor_df["spy_valuation_proxy_pct"] = monitor_df["spy_valuation_proxy_pct"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
    monitor_df["qqq_valuation_proxy_pct"] = monitor_df["qqq_valuation_proxy_pct"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
    monitor_df["spy_valuation_label"] = monitor_df["spy_valuation_label"].map(pretty_valuation_label)
    monitor_df["qqq_valuation_label"] = monitor_df["qqq_valuation_label"].map(pretty_valuation_label)
    monitor_df["regime_label"] = monitor_df["regime_label"].map(pretty_regime_label)

    monitor_df = monitor_df.rename(
        columns={
            "date": "日期",
            "ust2": "UST 2Y",
            "ust2_chg_bp": "2Y变化",
            "ust10": "UST 10Y",
            "ust10_chg_bp": "10Y变化",
            "curve_10s2s": "10s2s",
            "curve_10s2s_chg_bp": "10s2s变化",
            "daily_shape": "日度形态",
            "fed_cuts_proxy_bp": "降息预期代理",
            "fed_cut_expectation_label": "降息标签",
            "spy_valuation_proxy_pct": "SPY估值代理",
            "spy_valuation_label": "SPY标签",
            "qqq_valuation_proxy_pct": "QQQ估值代理",
            "qqq_valuation_label": "QQQ标签",
            "regime_label": "Regime",
        }
    )

    st.dataframe(monitor_df, use_container_width=True)

    st.subheader("最近10行原始数据表")

    raw_df = df.tail(10).copy()
    raw_df = raw_df.sort_values("date", ascending=False).reset_index(drop=True)
    raw_df["date"] = raw_df["date"].dt.strftime("%Y-%m-%d")

    st.dataframe(raw_df, use_container_width=True)
