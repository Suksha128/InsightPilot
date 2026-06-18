import streamlit as st
import time
from core import (
    get_vanna_instance,
    detect_ambiguity,
    validate_sql,
    check_cache,
    save_cache,
    log_query,
    log_feedback,
    save_insight,
    get_saved_insights,
    generate_insights_and_followups,
)

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="InsightPilot X",
    page_icon="📊",
)

# ─── CSS — clean enterprise dark, no glow/bloom effects ──────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

*, html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    box-sizing: border-box;
}

/* ── Canvas ── */
.stApp {
    background-color: #0f1117;
    color: #d1d5db;
}
#MainMenu, footer, header { visibility: hidden; }
.block-container {
    padding: 1.5rem 2.5rem 3rem 2.5rem;
    max-width: 100%;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #161b22 !important;
    border-right: 1px solid #21262d !important;
}
[data-testid="stSidebar"] * { color: #c9d1d9 !important; }
[data-testid="stSidebar"] .stTextInput input {
    background: #0d1117 !important;
    border: 1px solid #30363d !important;
    border-radius: 6px !important;
    color: #c9d1d9 !important;
    font-size: 0.82rem !important;
}
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: #0d1117 !important;
    border: 1px solid #30363d !important;
    border-radius: 6px !important;
    color: #c9d1d9 !important;
}

/* ── Sidebar brand ── */
.sb-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 1rem 0 0.5rem 0;
    border-bottom: 1px solid #21262d;
    margin-bottom: 1rem;
}
.sb-brand-name {
    font-size: 1rem;
    font-weight: 700;
    color: #f0f6fc !important;
    letter-spacing: -0.3px;
}
.sb-brand-tag {
    font-size: 0.65rem;
    color: #8b949e !important;
    font-weight: 400;
    letter-spacing: 0.3px;
}
.sb-section {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #484f58 !important;
    font-weight: 600;
    margin: 1rem 0 0.4rem 0;
}
.sb-divider {
    height: 1px;
    background: #21262d;
    margin: 0.8rem 0;
}

/* Schema table pills */
.tbl-pills { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 0.3rem; }
.tbl-pill {
    background: #21262d;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.68rem;
    color: #8b949e !important;
    font-family: 'SFMono-Regular', monospace;
}

/* Saved insight cards */
.si-card {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 0.6rem 0.8rem;
    margin-bottom: 0.5rem;
}
.si-card-title {
    font-size: 0.75rem;
    font-weight: 600;
    color: #58a6ff !important;
    margin-bottom: 3px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.si-card-text {
    font-size: 0.68rem;
    color: #6e7681 !important;
    line-height: 1.5;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

/* ── Top nav bar ── */
.topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 0 1.4rem 0;
    border-bottom: 1px solid #21262d;
    margin-bottom: 1.5rem;
}
.topbar-left { display: flex; align-items: center; gap: 12px; }
.topbar-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #f0f6fc;
    letter-spacing: -0.3px;
}
.topbar-sub {
    font-size: 0.72rem;
    color: #484f58;
    font-weight: 400;
}
.topbar-badge {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 4px;
    padding: 3px 10px;
    font-size: 0.68rem;
    color: #3fb950;
    font-weight: 600;
    letter-spacing: 0.3px;
}
.topbar-right { display: flex; gap: 12px; }
.stat-chip {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 5px 12px;
    text-align: center;
}
.stat-chip-val {
    font-size: 0.95rem;
    font-weight: 700;
    color: #f0f6fc;
    display: block;
    line-height: 1.2;
}
.stat-chip-lbl {
    font-size: 0.62rem;
    color: #484f58;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    display: block;
}

/* ── Chip row ── */
.chip-section-lbl {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #484f58;
    font-weight: 600;
    margin-bottom: 0.5rem;
}
div[data-testid="column"] .stButton > button {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 6px !important;
    color: #8b949e !important;
    font-size: 0.76rem !important;
    font-weight: 500 !important;
    padding: 0.38rem 0.9rem !important;
    transition: border-color 0.15s, color 0.15s !important;
    width: 100% !important;
    text-align: left !important;
}
div[data-testid="column"] .stButton > button:hover {
    border-color: #58a6ff !important;
    color: #58a6ff !important;
    background: #161b22 !important;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 10px !important;
    margin-bottom: 1rem !important;
}

/* ── SQL block ── */
[data-testid="stExpander"] {
    background: #0d1117 !important;
    border: 1px solid #21262d !important;
    border-radius: 8px !important;
}
[data-testid="stExpander"] summary {
    font-size: 0.76rem !important;
    color: #6e7681 !important;
}

/* ── KPI mini row ── */
.kpi-row { display: flex; gap: 10px; margin: 0.8rem 0 1rem 0; }
.kpi-item {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 0.6rem 1rem;
    min-width: 100px;
}
.kpi-val {
    font-size: 1rem;
    font-weight: 700;
    color: #f0f6fc;
}
.kpi-lbl {
    font-size: 0.62rem;
    color: #484f58;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    margin-top: 2px;
}

/* ── Insight block ── */
.insight-block {
    background: #161b22;
    border: 1px solid #21262d;
    border-left: 3px solid #388bfd;
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    margin: 0.8rem 0;
}
.insight-lbl {
    font-size: 0.63rem;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #388bfd;
    font-weight: 600;
    margin-bottom: 0.4rem;
}
.insight-text {
    font-size: 0.85rem;
    color: #c9d1d9;
    line-height: 1.65;
}

/* ── Section label ── */
.sect-lbl {
    font-size: 0.63rem;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #484f58;
    font-weight: 600;
    margin: 1rem 0 0.4rem 0;
}

/* ── Follow-up chips ── */
.fu-lbl {
    font-size: 0.63rem;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #484f58;
    font-weight: 600;
    margin: 1rem 0 0.4rem 0;
}

/* ── Data table ── */
[data-testid="stDataFrame"] {
    border: 1px solid #21262d !important;
    border-radius: 8px !important;
    overflow: hidden !important;
}
[data-testid="stDataFrame"] th {
    background: #161b22 !important;
    color: #8b949e !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
}
[data-testid="stDataFrame"] td {
    font-size: 0.78rem !important;
    color: #c9d1d9 !important;
}

/* ── Chat input ── */
[data-testid="stChatInputTextArea"] {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
    color: #c9d1d9 !important;
    font-size: 0.88rem !important;
}
[data-testid="stChatInputTextArea"]:focus {
    border-color: #388bfd !important;
}

/* ── Divider ── */
hr { border-color: #21262d !important; }

/* ── Alert overrides ── */
.stAlert { border-radius: 8px !important; font-size: 0.84rem !important; }

/* Plotly chart transparent bg */
.js-plotly-plot { background: transparent !important; }

/* Welcome cards */
.wc-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin: 1.5rem 0; }
.wc-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 1.2rem;
}
.wc-icon { font-size: 1.4rem; margin-bottom: 0.5rem; display: block; }
.wc-title { font-size: 0.84rem; font-weight: 600; color: #f0f6fc; margin-bottom: 0.3rem; }
.wc-desc  { font-size: 0.74rem; color: #6e7681; line-height: 1.55; }

/* Guard - status badge */
.status-safe {
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 0.68rem; font-weight: 600; color: #3fb950;
    background: rgba(63,185,80,0.08); border: 1px solid rgba(63,185,80,0.2);
    border-radius: 4px; padding: 2px 8px;
}
.status-cache {
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 0.68rem; font-weight: 600; color: #d29922;
    background: rgba(210,153,34,0.08); border: 1px solid rgba(210,153,34,0.2);
    border-radius: 4px; padding: 2px 8px;
}
</style>
""", unsafe_allow_html=True)

# ─── Session state ────────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []   # list of result dicts, full data stored

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sb-brand">
        <span style="font-size:1.4rem">📊</span>
        <div>
            <div class="sb-brand-name">InsightPilot X</div>
            <div class="sb-brand-tag">AI Analytics Copilot</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sb-section">API Key</div>', unsafe_allow_html=True)
    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        placeholder="AIza…",
        label_visibility="collapsed",
    )

    st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sb-section">Role</div>', unsafe_allow_html=True)
    role = st.selectbox(
        "Role",
        ["Sales Manager", "Product Manager", "Executive"],
        label_visibility="collapsed",
    )

    st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sb-section">Database Tables</div>', unsafe_allow_html=True)
    tables = ["customers", "orders", "products", "sales_summary",
              "subscriptions", "customer_health", "product_profitability"]
    pills = "".join(f'<span class="tbl-pill">{t}</span>' for t in tables)
    st.markdown(f'<div class="tbl-pills">{pills}</div>', unsafe_allow_html=True)

    st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sb-section">Saved Insights</div>', unsafe_allow_html=True)
    insights_df = get_saved_insights()
    if not insights_df.empty:
        for _, row in insights_df.head(10).iterrows():
            st.markdown(f"""
            <div class="si-card">
                <div class="si-card-title">{row['title']}</div>
                <div class="si-card-text">{row['business_summary']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown('<p style="font-size:0.74rem;color:#484f58">Saved insights appear here automatically after each query.</p>',
                    unsafe_allow_html=True)

# ─── Top bar ─────────────────────────────────────────────────────────────────
n_saved = len(insights_df) if not insights_df.empty else 0
n_history = len(st.session_state.history)

st.markdown(f"""
<div class="topbar">
    <div class="topbar-left">
        <span style="font-size:1.5rem">📊</span>
        <div>
            <div class="topbar-title">InsightPilot X</div>
            <div class="topbar-sub">Natural language → SQL → Insight</div>
        </div>
        <span class="topbar-badge">● Live</span>
    </div>
    <div class="topbar-right">
        <div class="stat-chip">
            <span class="stat-chip-val">{n_history}</span>
            <span class="stat-chip-lbl">Queries</span>
        </div>
        <div class="stat-chip">
            <span class="stat-chip-val">{n_saved}</span>
            <span class="stat-chip-lbl">Saved</span>
        </div>
        <div class="stat-chip">
            <span class="stat-chip-val">{len(tables)}</span>
            <span class="stat-chip-lbl">Tables</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Auth guard ───────────────────────────────────────────────────────────────
if not api_key:
    st.markdown("""
    <div class="wc-grid">
        <div class="wc-card">
            <span class="wc-icon">💬</span>
            <div class="wc-title">Ask in plain English</div>
            <div class="wc-desc">Type any business question. The AI translates it into SQL and executes it against your database — no SQL knowledge needed.</div>
        </div>
        <div class="wc-card">
            <span class="wc-icon">📈</span>
            <div class="wc-title">Automatic visualizations</div>
            <div class="wc-desc">Every result is paired with an appropriate Plotly chart — bar, line, scatter, or pie — selected intelligently by the AI.</div>
        </div>
        <div class="wc-card">
            <span class="wc-icon">🛡️</span>
            <div class="wc-title">Read-only & safe</div>
            <div class="wc-desc">A guardrail engine blocks all destructive keywords. The database connection is enforced as read-only at the driver level.</div>
        </div>
        <div class="wc-card">
            <span class="wc-icon">🧠</span>
            <div class="wc-title">AI business summaries</div>
            <div class="wc-desc">After each query, Gemini synthesizes the data into a short, actionable business summary you can share with your team.</div>
        </div>
        <div class="wc-card">
            <span class="wc-icon">🔁</span>
            <div class="wc-title">Smart follow-ups</div>
            <div class="wc-desc">The copilot suggests 3 contextual follow-up questions based on the current result to guide deeper analysis.</div>
        </div>
        <div class="wc-card">
            <span class="wc-icon">💾</span>
            <div class="wc-title">Full history preserved</div>
            <div class="wc-desc">All successful queries — including their data tables and AI summaries — are saved and shown in session history below.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.info("Paste your **Gemini API Key** in the sidebar to get started. Get one free at [aistudio.google.com](https://aistudio.google.com/app/apikey).")
    st.stop()

# ─── Init Vanna ───────────────────────────────────────────────────────────────
@st.cache_resource
def init_vanna(key):
    return get_vanna_instance(key)

vn = init_vanna(api_key)

# ─── Role chips ──────────────────────────────────────────────────────────────
chip_map = {
    "Sales Manager": [
        "Monthly sales trend",
        "Total revenue by category",
        "Customer health summary",
        "Region-wise revenue",
        "Repeat purchase rate",
        "Orders by product line",
    ],
    "Product Manager": [
        "Product profitability",
        "Top 5 products by margin",
        "Lifetime value per segment",
        "Churn risk customers",
        "New vs returning customers",
        "Subscription plan breakdown",
    ],
    "Executive": [
        "Overall revenue summary",
        "Month-over-month growth",
        "Top 10 customers by revenue",
        "Best performing categories",
        "Lowest margin products",
        "Subscription health overview",
    ],
}
chips = chip_map.get(role, chip_map["Executive"])

st.markdown('<div class="chip-section-lbl">Quick questions</div>', unsafe_allow_html=True)
c_cols = st.columns(6)
for i, chip in enumerate(chips):
    if c_cols[i].button(chip, key=f"chip_{i}"):
        st.session_state.current_prompt = chip

st.markdown("---")

# ─── Render persisted history ─────────────────────────────────────────────────
def render_result(entry: dict):
    """Re-render a fully stored result entry."""
    sql      = entry["sql"]
    cached   = entry["cached"]
    df       = entry["df"]
    latency  = entry["latency"]
    summary  = entry["summary"]
    followups = entry["followups"]
    log_id   = entry["log_id"]

    with st.expander("SQL  ·  click to inspect", expanded=False):
        st.code(sql, language="sql")
        if cached:
            st.markdown('<span class="status-cache">⚡ Cache hit</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-safe">✓ AI-generated</span>', unsafe_allow_html=True)

    n_rows = len(df)
    n_cols = len(df.columns)
    st.markdown(f"""
    <div class="kpi-row">
        <div class="kpi-item"><div class="kpi-val">{n_rows:,}</div><div class="kpi-lbl">Rows</div></div>
        <div class="kpi-item"><div class="kpi-val">{n_cols}</div><div class="kpi-lbl">Columns</div></div>
        <div class="kpi-item"><div class="kpi-val">{latency:.2f}s</div><div class="kpi-lbl">Latency</div></div>
        <div class="kpi-item"><div class="kpi-val">READ</div><div class="kpi-lbl">Mode</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sect-lbl">Data</div>', unsafe_allow_html=True)
    st.dataframe(df.head(500), use_container_width=True)

    if "fig" in entry and entry["fig"] is not None:
        st.markdown('<div class="sect-lbl">Chart</div>', unsafe_allow_html=True)
        fig = entry["fig"]
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#161b22",
            font=dict(family="Inter", color="#8b949e", size=11),
            margin=dict(l=10, r=10, t=30, b=10),
            xaxis=dict(gridcolor="#21262d", zerolinecolor="#21262d"),
            yaxis=dict(gridcolor="#21262d", zerolinecolor="#21262d"),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"""
    <div class="insight-block">
        <div class="insight-lbl">AI Business Insight</div>
        <div class="insight-text">{summary}</div>
    </div>
    """, unsafe_allow_html=True)

    if followups:
        st.markdown('<div class="fu-lbl">Suggested follow-ups</div>', unsafe_allow_html=True)
        fu_cols = st.columns(3)
        for i, fu in enumerate(followups[:3]):
            if fu_cols[i].button(fu, key=f"fu_h_{log_id}_{i}"):
                st.session_state.current_prompt = fu
                st.rerun()

    st.markdown('<div style="margin-top:0.6rem;font-size:0.68rem;color:#484f58">Was this answer correct?</div>',
                unsafe_allow_html=True)
    fb_cols = st.columns([1, 1, 1, 5])
    if fb_cols[0].button("👍", key=f"fb_y_{log_id}", help="Correct"):
        log_feedback(log_id, "Correct"); st.toast("Thanks!", icon="✅")
    if fb_cols[1].button("🤔", key=f"fb_p_{log_id}", help="Partially correct"):
        log_feedback(log_id, "Partial"); st.toast("Noted.", icon="🔧")
    if fb_cols[2].button("👎", key=f"fb_n_{log_id}", help="Wrong"):
        log_feedback(log_id, "Wrong"); st.toast("Sorry — logged.", icon="❌")


for entry in st.session_state.history:
    with st.chat_message("user", avatar="👤"):
        st.markdown(f"**{entry['prompt']}**")
    with st.chat_message("assistant", avatar="📊"):
        render_result(entry)

# ─── Chat input ───────────────────────────────────────────────────────────────
prompt = st.chat_input("Ask a question about your business data…")
if "current_prompt" in st.session_state:
    prompt = st.session_state.current_prompt
    del st.session_state.current_prompt

# ─── Query pipeline ───────────────────────────────────────────────────────────
if prompt:
    with st.chat_message("user", avatar="👤"):
        st.markdown(f"**{prompt}**")

    with st.chat_message("assistant", avatar="📊"):
        start_time = time.time()

        # 1. Ambiguity
        is_ambiguous, clarify_msg = detect_ambiguity(prompt)
        if is_ambiguous:
            st.warning(f"🤔 {clarify_msg}")
            st.stop()

        # 2. Cache / generate SQL
        with st.status("Translating to SQL…", expanded=False) as sql_status:
            sql = check_cache(prompt)
            cached = bool(sql)
            if not cached:
                sql = vn.generate_sql(question=prompt)
            sql_status.update(
                label="⚡ Cache hit" if cached else "✓ SQL generated",
                state="complete",
            )

        # 3. Guardrails
        is_safe, checked_sql = validate_sql(sql)
        if not is_safe:
            st.error(f"🚫 Security guardrail triggered: {checked_sql}")
            log_query(prompt, "N/A", time.time() - start_time, "Failure", "Guardrail")
            st.stop()
        sql = checked_sql

        # SQL visibility
        with st.expander("SQL  ·  click to inspect", expanded=False):
            st.code(sql, language="sql")
            if cached:
                st.markdown('<span class="status-cache">⚡ Cache hit</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="status-safe">✓ AI-generated</span>', unsafe_allow_html=True)

        # 4. Execute
        with st.spinner("Fetching data…"):
            try:
                df = vn.run_sql(sql)
                status = "Success"
                error_msg = ""
                if not cached and df is not None and not df.empty and "Rate Limit" not in sql:
                    save_cache(prompt, sql)
            except Exception as e:
                df = None
                status = "Failure"
                error_msg = str(e)

        latency = time.time() - start_time
        log_id = log_query(prompt, sql, latency, status, error_msg)

        if status == "Failure":
            st.error(f"**Execution failed:** {error_msg}")
            st.code(sql, language="sql")
            st.stop()

        if df is None or df.empty:
            st.warning("The query returned no data. Try rephrasing your question.")
            st.stop()

        # KPI row
        n_rows = len(df)
        n_cols = len(df.columns)
        st.markdown(f"""
        <div class="kpi-row">
            <div class="kpi-item"><div class="kpi-val">{n_rows:,}</div><div class="kpi-lbl">Rows</div></div>
            <div class="kpi-item"><div class="kpi-val">{n_cols}</div><div class="kpi-lbl">Columns</div></div>
            <div class="kpi-item"><div class="kpi-val">{latency:.2f}s</div><div class="kpi-lbl">Latency</div></div>
            <div class="kpi-item"><div class="kpi-val">READ</div><div class="kpi-lbl">Mode</div></div>
        </div>
        """, unsafe_allow_html=True)

        # Data table
        st.markdown('<div class="sect-lbl">Data</div>', unsafe_allow_html=True)
        st.dataframe(df.head(500), use_container_width=True)

        # Chart
        fig = None
        try:
            with st.spinner("Building chart…"):
                plotly_code = vn.generate_plotly_code(question=prompt, sql=sql, df=df)
                fig = vn.get_plotly_figure(plotly_code=plotly_code, df=df)
                if fig:
                    fig.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="#161b22",
                        font=dict(family="Inter", color="#8b949e", size=11),
                        margin=dict(l=10, r=10, t=30, b=10),
                        xaxis=dict(gridcolor="#21262d", zerolinecolor="#21262d"),
                        yaxis=dict(gridcolor="#21262d", zerolinecolor="#21262d"),
                    )
                    st.markdown('<div class="sect-lbl">Chart</div>', unsafe_allow_html=True)
                    st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass

        # AI insight
        with st.spinner("Generating insight…"):
            insight_data = generate_insights_and_followups(prompt, df, api_key)
        summary   = insight_data.get("summary", "")
        followups = insight_data.get("followups", [])

        st.markdown(f"""
        <div class="insight-block">
            <div class="insight-lbl">AI Business Insight</div>
            <div class="insight-text">{summary}</div>
        </div>
        """, unsafe_allow_html=True)

        # Auto-save
        if not cached and "Rate Limit" not in summary and "Error" not in summary:
            save_insight(prompt[:35] + "…", prompt, sql, summary)

        # Follow-ups
        if followups:
            st.markdown('<div class="fu-lbl">Suggested follow-ups</div>', unsafe_allow_html=True)
            fu_cols = st.columns(3)
            for i, fu in enumerate(followups[:3]):
                if fu_cols[i].button(fu, key=f"fu_new_{log_id}_{i}"):
                    st.session_state.current_prompt = fu
                    st.rerun()

        # Feedback
        st.markdown('<div style="margin-top:0.6rem;font-size:0.68rem;color:#484f58">Was this answer correct?</div>',
                    unsafe_allow_html=True)
        fb_cols = st.columns([1, 1, 1, 5])
        if fb_cols[0].button("👍", key=f"fb_y_{log_id}", help="Correct"):
            log_feedback(log_id, "Correct"); st.toast("Thanks!", icon="✅")
        if fb_cols[1].button("🤔", key=f"fb_p_{log_id}", help="Partially correct"):
            log_feedback(log_id, "Partial"); st.toast("Noted.", icon="🔧")
        if fb_cols[2].button("👎", key=f"fb_n_{log_id}", help="Wrong"):
            log_feedback(log_id, "Wrong"); st.toast("Sorry — logged.", icon="❌")

        # ── Store full result in session so history is real ─────────────────
        st.session_state.history.append({
            "prompt":   prompt,
            "sql":      sql,
            "cached":   cached,
            "df":       df,
            "fig":      fig,
            "latency":  latency,
            "summary":  summary,
            "followups": followups,
            "log_id":   log_id,
        })
