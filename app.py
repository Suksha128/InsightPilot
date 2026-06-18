import streamlit as st
import time
import os
import re
import pandas as pd
from data_manager import (
    db_exists, get_schema, get_db_size_mb, DUCK_PATH,
    preview_table, drop_table, reset_database, ingest_file,
)
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
    delete_insight,
    generate_insights_and_followups,
)

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="InsightPilotX",
    page_icon="📊",
)

# ─── Session State ────────────────────────────────────────────────────────────
if "history"     not in st.session_state: st.session_state.history = []
if "db_ready"    not in st.session_state: st.session_state.db_ready = db_exists()
if "active_page" not in st.session_state: st.session_state.active_page = "upload"
if "dark_mode"   not in st.session_state: st.session_state.dark_mode = True

dm = st.session_state.dark_mode

# ─── Theme tokens ─────────────────────────────────────────────────────────────
if dm:
    BG        = "#0f1117"
    SURFACE   = "#161b22"
    SURFACE2  = "#0d1117"
    BORDER    = "#21262d"
    BORDER2   = "#30363d"
    TEXT      = "#e6edf3"
    TEXT2     = "#8b949e"
    TEXT3     = "#484f58"
    ACCENT    = "#2f81f7"
    ACCENT_BG = "rgba(47,129,247,0.08)"
    SUCCESS   = "#3fb950"
    WARN      = "#d29922"
    SB_BG     = "#161b22"
else:
    BG        = "#ffffff"
    SURFACE   = "#f6f8fa"
    SURFACE2  = "#ffffff"
    BORDER    = "#d0d7de"
    BORDER2   = "#d0d7de"
    TEXT      = "#1f2328"
    TEXT2     = "#636c76"
    TEXT3     = "#9198a1"
    ACCENT    = "#0969da"
    ACCENT_BG = "rgba(9,105,218,0.06)"
    SUCCESS   = "#1a7f37"
    WARN      = "#9a6700"
    SB_BG     = "#f6f8fa"

# ─── Inject CSS ───────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

*, html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    box-sizing: border-box;
}}

.stApp {{
    background-color: {BG};
    color: {TEXT};
}}

#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ padding: 0 2rem 4rem 2rem; max-width: 100%; }}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background-color: {SB_BG} !important;
    border-right: 1px solid {BORDER} !important;
}}
[data-testid="stSidebar"] * {{ color: {TEXT2} !important; }}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] strong {{ color: {TEXT} !important; }}
[data-testid="stSidebar"] .stTextInput input {{
    background: {SURFACE2} !important;
    border: 1px solid {BORDER2} !important;
    border-radius: 6px !important;
    color: {TEXT} !important;
    font-size: 0.83rem !important;
}}
[data-testid="stSidebar"] .stSelectbox > div > div {{
    background: {SURFACE2} !important;
    border: 1px solid {BORDER2} !important;
    border-radius: 6px !important;
    color: {TEXT} !important;
}}

/* ── Navbar ── */
.navbar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 0 1rem 0;
    border-bottom: 1px solid {BORDER};
    margin-bottom: 2rem;
}}
.navbar-brand {{
    display: flex;
    align-items: center;
    gap: 10px;
}}
.navbar-logo {{
    width: 32px;
    height: 32px;
    background: {ACCENT};
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
    color: #fff;
}}
.navbar-name {{
    font-size: 1rem;
    font-weight: 700;
    color: {TEXT};
    letter-spacing: -0.3px;
}}
.navbar-version {{
    font-size: 0.65rem;
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 1px 7px;
    color: {TEXT3};
    font-weight: 500;
    letter-spacing: 0.3px;
    text-transform: uppercase;
}}
.navbar-right {{
    display: flex;
    align-items: center;
    gap: 16px;
}}
.nav-stat {{
    font-size: 0.75rem;
    color: {TEXT3};
}}
.nav-stat span {{
    font-weight: 600;
    color: {TEXT2};
}}

/* ── Sidebar brand ── */
.sb-brand {{
    padding: 1.1rem 0 0.8rem 0;
    border-bottom: 1px solid {BORDER};
    margin-bottom: 0.8rem;
}}
.sb-brand-name {{
    font-size: 0.95rem;
    font-weight: 700;
    color: {TEXT} !important;
    letter-spacing: -0.3px;
}}
.sb-brand-tag {{
    font-size: 0.65rem;
    color: {TEXT3} !important;
    margin-top: 1px;
}}
.sb-label {{
    font-size: 0.63rem;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: {TEXT3} !important;
    font-weight: 600;
    margin: 1rem 0 0.35rem 0;
}}
.sb-divider {{ height: 1px; background: {BORDER}; margin: 0.75rem 0; }}

/* Table pills */
.tbl-pills {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 0.3rem; }}
.tbl-pill {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 0.67rem;
    color: {TEXT2} !important;
    font-family: 'SFMono-Regular', 'Consolas', monospace;
}}

/* Saved insight cards */
.si-card {{
    background: {SURFACE2};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 0.55rem 0.75rem;
    margin-bottom: 0.45rem;
}}
.si-card-title {{
    font-size: 0.73rem;
    font-weight: 600;
    color: {ACCENT} !important;
    margin-bottom: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.si-card-text {{
    font-size: 0.67rem;
    color: {TEXT3} !important;
    line-height: 1.5;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}}

/* ── Nav buttons in sidebar ── */
[data-testid="stSidebar"] .stButton > button {{
    background: transparent !important;
    border: 1px solid {BORDER} !important;
    border-radius: 6px !important;
    color: {TEXT2} !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    padding: 0.4rem 0.8rem !important;
    transition: all 0.15s !important;
    width: 100% !important;
    text-align: left !important;
    margin-bottom: 4px !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background: {SURFACE} !important;
    border-color: {BORDER2} !important;
    color: {TEXT} !important;
}}

/* ── Quick-question chips ── */
.chip-label {{
    font-size: 0.63rem;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: {TEXT3};
    font-weight: 600;
    margin-bottom: 0.45rem;
}}
div[data-testid="column"] .stButton > button {{
    background: {SURFACE} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 6px !important;
    color: {TEXT2} !important;
    font-size: 0.76rem !important;
    font-weight: 400 !important;
    padding: 0.35rem 0.75rem !important;
    transition: border-color 0.15s, color 0.15s !important;
    width: 100% !important;
    text-align: left !important;
}}
div[data-testid="column"] .stButton > button:hover {{
    border-color: {ACCENT} !important;
    color: {ACCENT} !important;
    background: {ACCENT_BG} !important;
}}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {{
    background: {SURFACE} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
    margin-bottom: 1rem !important;
}}

/* ── Expander ── */
[data-testid="stExpander"] {{
    background: {SURFACE2} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
}}
[data-testid="stExpander"] summary {{
    font-size: 0.76rem !important;
    color: {TEXT3} !important;
    font-weight: 500 !important;
}}

/* ── KPI row ── */
.kpi-row {{ display: flex; gap: 10px; margin: 0.75rem 0 1rem 0; }}
.kpi-item {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 0.65rem 1rem;
    min-width: 100px;
}}
.kpi-val {{
    font-size: 1.05rem;
    font-weight: 700;
    color: {TEXT};
}}
.kpi-lbl {{
    font-size: 0.61rem;
    color: {TEXT3};
    text-transform: uppercase;
    letter-spacing: 0.4px;
    margin-top: 2px;
}}

/* ── Insight block ── */
.insight-block {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-left: 3px solid {ACCENT};
    border-radius: 8px;
    padding: 0.85rem 1.1rem;
    margin: 0.75rem 0;
}}
.insight-lbl {{
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: {ACCENT};
    font-weight: 600;
    margin-bottom: 0.35rem;
}}
.insight-text {{
    font-size: 0.85rem;
    color: {TEXT2};
    line-height: 1.65;
}}

/* ── Section / follow-up labels ── */
.sect-lbl, .fu-lbl {{
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: {TEXT3};
    font-weight: 600;
    margin: 1rem 0 0.4rem 0;
}}

/* Status badges */
.badge-ai {{
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 0.67rem; font-weight: 600; color: {SUCCESS};
    background: rgba(63,185,80,0.08); border: 1px solid rgba(63,185,80,0.2);
    border-radius: 4px; padding: 2px 7px;
}}
.badge-cache {{
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 0.67rem; font-weight: 600; color: {WARN};
    background: rgba(210,153,34,0.08); border: 1px solid rgba(210,153,34,0.2);
    border-radius: 4px; padding: 2px 7px;
}}

/* ── Data table ── */
[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
    overflow: hidden !important;
}}

/* ── File Uploader ── */
[data-testid="stFileUploader"] > section,
[data-testid="stFileUploadDropzone"] {{
    background-color: {SURFACE} !important;
    color: {TEXT} !important;
}}
[data-testid="stFileUploader"] div,
[data-testid="stFileUploader"] span,
[data-testid="stFileUploader"] small {{
    color: {TEXT2} !important;
}}
[data-testid="stFileUploader"] button {{
    background-color: {SURFACE2} !important;
    color: {TEXT} !important;
    border-color: {BORDER2} !important;
}}

/* ── Chat input ── */
[data-testid="stChatInputTextArea"] {{
    background: {SURFACE} !important;
    border: 1px solid {BORDER2} !important;
    border-radius: 8px !important;
    color: {TEXT} !important;
    font-size: 0.88rem !important;
}}

/* ── Upload page ── */
.upload-title {{
    font-size: 1.3rem;
    font-weight: 700;
    color: {TEXT};
    letter-spacing: -0.4px;
    margin-bottom: 0.25rem;
}}
.upload-sub {{
    font-size: 0.82rem;
    color: {TEXT2};
    margin-bottom: 1.5rem;
}}
.fmt-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin-bottom: 1.5rem;
}}
.fmt-card {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 1rem 1.1rem;
}}
.fmt-ext {{
    font-size: 0.82rem;
    font-weight: 700;
    color: {ACCENT};
    font-family: monospace;
    margin-bottom: 0.3rem;
}}
.fmt-desc {{
    font-size: 0.72rem;
    color: {TEXT2};
    line-height: 1.5;
}}

/* ── Schema card ── */
.schema-card {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.7rem;
}}
.schema-tbl {{ font-size: 0.85rem; font-weight: 700; color: {TEXT}; margin-bottom: 3px; }}
.schema-meta {{ font-size: 0.67rem; color: {TEXT3}; margin-bottom: 6px; }}
.schema-cols {{ display: flex; flex-wrap: wrap; gap: 4px; }}
.schema-col {{
    background: {SURFACE2};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 1px 6px;
    font-size: 0.65rem;
    color: {TEXT2};
    font-family: monospace;
}}
.schema-col-type {{ color: {TEXT3}; }}

/* ── Welcome cards ── */
.wc-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin: 1.5rem 0; }}
.wc-card {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 1.2rem;
}}
.wc-icon {{ font-size: 1.3rem; display: block; margin-bottom: 0.5rem; }}
.wc-title {{ font-size: 0.84rem; font-weight: 600; color: {TEXT}; margin-bottom: 0.25rem; }}
.wc-desc  {{ font-size: 0.74rem; color: {TEXT2}; line-height: 1.55; }}

hr {{ border-color: {BORDER} !important; }}
.stAlert {{ border-radius: 8px !important; font-size: 0.84rem !important; }}
</style>
""", unsafe_allow_html=True)


# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div class="sb-brand">
        <div class="sb-brand-name">InsightPilotX</div>
        <div class="sb-brand-tag">Business Intelligence Copilot</div>
    </div>""", unsafe_allow_html=True)

    # Theme toggle
    col_t1, col_t2 = st.columns([3, 2])
    col_t1.markdown(f'<div class="sb-label" style="margin-top:0.5rem">Appearance</div>', unsafe_allow_html=True)
    theme_label = "🌙 Dark" if dm else "☀️ Light"
    if col_t2.button(theme_label, key="theme_toggle"):
        st.session_state.dark_mode = not dm
        st.rerun()

    st.markdown(f'<div class="sb-divider"></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sb-label">API Key</div>', unsafe_allow_html=True)
    api_key = st.text_input("Groq API Key", type="password",
                             placeholder="gsk_…", label_visibility="collapsed")

    st.markdown(f'<div class="sb-divider"></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sb-label">Pages</div>', unsafe_allow_html=True)
    if st.button("📁  Data Manager", use_container_width=True):
        st.session_state.active_page = "upload"; st.rerun()
    if st.button("💬  Ask Questions", use_container_width=True):
        st.session_state.active_page = "query"; st.rerun()
    if st.button("💾  Saved Insights", use_container_width=True):
        st.session_state.active_page = "insights"; st.rerun()

    if st.session_state.db_ready:
        schema_sb = get_schema()
        st.markdown(f'<div class="sb-divider"></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sb-label">Tables</div>', unsafe_allow_html=True)
        pills = "".join(f'<span class="tbl-pill">{t}</span>' for t in schema_sb.keys())
        st.markdown(f'<div class="tbl-pills">{pills}</div>', unsafe_allow_html=True)
        st.markdown(f'<p style="font-size:0.67rem;color:{TEXT3};margin-top:5px">{get_db_size_mb():.1f} MB</p>',
                    unsafe_allow_html=True)

    insights_df = get_saved_insights()
    if not insights_df.empty:
        st.markdown(f'<div class="sb-divider"></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sb-label">Saved Insights</div>', unsafe_allow_html=True)
        for _, row in insights_df.head(6).iterrows():
            st.markdown(f"""
            <div class="si-card">
                <div class="si-card-title">{row['title']}</div>
                <div class="si-card-text">{row['business_summary']}</div>
            </div>""", unsafe_allow_html=True)


# ─── Navbar ──────────────────────────────────────────────────────────────────
n_hist  = len(st.session_state.history)
n_saved = len(insights_df) if not insights_df.empty else 0
n_tbls  = len(get_schema())

st.markdown(f"""
<div class="navbar">
    <div class="navbar-brand">
        <div class="navbar-logo">📊</div>
        <div>
            <span class="navbar-name">InsightPilot</span>
        </div>
    </div>
    <div class="navbar-right">
        <div class="nav-stat"><span>{n_tbls}</span> tables</div>
        <div class="nav-stat"><span>{n_hist}</span> queries</div>
        <div class="nav-stat"><span>{n_saved}</span> saved</div>
    </div>
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DATA MANAGER
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.active_page == "upload":

    st.markdown(f"""<style>
    .dm-title{{font-size:1.3rem;font-weight:700;color:{TEXT};letter-spacing:-0.3px;margin-bottom:3px}}
    .dm-sub{{font-size:0.8rem;color:{TEXT2};margin-bottom:1.6rem}}
    .dm-lbl{{font-size:0.63rem;font-weight:600;text-transform:uppercase;letter-spacing:0.7px;color:{TEXT3};margin-bottom:0.6rem}}
    .fmt-grid2{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:1.1rem}}
    .fmt-card2{{background:{SURFACE};border:1px solid {BORDER};border-radius:8px;padding:0.75rem 0.9rem;display:flex;align-items:flex-start;gap:9px}}
    .fmt-icon2{{font-size:1rem;margin-top:1px;flex-shrink:0}}
    .fmt-ext2{{font-size:0.75rem;font-weight:700;color:{ACCENT};font-family:monospace;margin-bottom:2px}}
    .fmt-dsc2{{font-size:0.69rem;color:{TEXT2};line-height:1.45}}
    .pdiv{{height:1px;background:{BORDER};margin:1.1rem 0}}
    .tip-row{{font-size:0.72rem;color:{TEXT2};margin:3px 0 5px 0;line-height:1.5}}
    .db-bar{{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:0.8rem}}
    .db-bar-l{{font-size:0.84rem;font-weight:700;color:{TEXT}}}
    .db-bar-r{{font-size:0.67rem;color:{TEXT3}}}
    .tbl-card{{background:{SURFACE};border:1px solid {BORDER};border-radius:10px;padding:0.85rem 1rem;margin-bottom:0.55rem}}
    .tbl-hdr{{display:flex;align-items:center;justify-content:space-between;margin-bottom:4px}}
    .tbl-name{{font-size:0.82rem;font-weight:600;color:{TEXT};font-family:'SFMono-Regular',monospace}}
    .tbl-badge{{background:{SURFACE2};border:1px solid {BORDER};border-radius:4px;padding:1px 7px;font-size:0.63rem;color:{TEXT3};font-weight:500}}
    .tbl-meta{{font-size:0.67rem;color:{TEXT3};margin-bottom:7px}}
    .col-chip{{display:inline-block;background:{SURFACE2};border:1px solid {BORDER};border-radius:4px;padding:2px 6px;font-size:0.63rem;color:{TEXT2};font-family:monospace;margin:2px 2px 2px 0}}
    .col-type{{color:{TEXT3}}}
    .empty-state{{text-align:center;padding:4rem 1rem}}
    .empty-ico{{font-size:2.5rem;margin-bottom:0.75rem}}
    .empty-ttl{{font-size:0.88rem;font-weight:600;color:{TEXT};margin-bottom:0.3rem}}
    .empty-sub{{font-size:0.74rem;color:{TEXT2};max-width:240px;margin:0 auto;line-height:1.6}}
    </style>""", unsafe_allow_html=True)

    left, right = st.columns([1, 1.65], gap="large")

    with left:
        st.markdown('<div class="dm-title">Data Manager</div>', unsafe_allow_html=True)
        st.markdown('<div class="dm-sub">Upload your files — all data stays on your machine.</div>', unsafe_allow_html=True)

        st.markdown('<div class="dm-lbl">Supported formats</div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="fmt-grid2">
            <div class="fmt-card2"><span class="fmt-icon2">📄</span><div>
                <div class="fmt-ext2">.csv</div>
                <div class="fmt-dsc2">Any size. Large files use DuckDB native reader — no memory limit.</div></div></div>
            <div class="fmt-card2"><span class="fmt-icon2">⚡</span><div>
                <div class="fmt-ext2">.parquet</div>
                <div class="fmt-dsc2">Fastest format. GB-scale columnar files load in seconds.</div></div></div>
            <div class="fmt-card2"><span class="fmt-icon2">📊</span><div>
                <div class="fmt-ext2">.xlsx / .xls</div>
                <div class="fmt-dsc2">Each sheet becomes a separate table automatically.</div></div></div>
            <div class="fmt-card2"><span class="fmt-icon2">🗄️</span><div>
                <div class="fmt-ext2">.db / .sqlite</div>
                <div class="fmt-dsc2">All tables migrated from SQLite in one step.</div></div></div>
        </div>""", unsafe_allow_html=True)

        st.markdown('<div class="dm-lbl">Upload files</div>', unsafe_allow_html=True)
        uploaded_files = st.file_uploader(
            "Upload", type=["csv","parquet","xlsx","xls","db","sqlite","sqlite3","json"],
            accept_multiple_files=True, label_visibility="collapsed",
        )

        if uploaded_files:
            st.markdown(f'<p style="font-size:0.71rem;color:{TEXT2};margin:4px 0 8px">{len(uploaded_files)} file(s) selected</p>',
                        unsafe_allow_html=True)
            if st.button("⬆  Import files", type="primary", use_container_width=True):
                all_tables = []
                for uf in uploaded_files:
                    sz = f"{uf.size/(1024*1024):.1f} MB"
                    st.markdown(f'<p class="tip-row"><strong>{uf.name}</strong> · {sz}</p>', unsafe_allow_html=True)
                    prog = st.progress(0)
                    tables, err = ingest_file(uf, progress_cb=lambda f, p=prog: p.progress(min(f,1.0)))
                    prog.progress(1.0)
                    if err:
                        st.error(f"Failed: {err}")
                    else:
                        st.success(f"✓  {', '.join(tables)}")
                        all_tables.extend(tables)
                if all_tables:
                    st.session_state.db_ready = True
                    st.session_state.history  = []
                    st.cache_resource.clear()
                    st.rerun()

        st.markdown('<div class="pdiv"></div>', unsafe_allow_html=True)
        st.markdown('<div class="dm-lbl">Tips</div>', unsafe_allow_html=True)
        for t in [
            "Upload multiple files at once — each becomes its own table.",
            "Column names are cleaned automatically (spaces → underscores).",
            "Re-uploading the same filename replaces the existing table.",
            "Switch to <strong>Ask Questions</strong> after uploading.",
        ]:
            st.markdown(f'<p class="tip-row">→ {t}</p>', unsafe_allow_html=True)

    with right:
        schema = get_schema()
        if not schema:
            st.markdown(f"""<div class="empty-state">
                <div class="empty-ico">📂</div>
                <div class="empty-ttl">No data loaded yet</div>
                <div class="empty-sub">Upload a file on the left — your schema will appear here instantly.</div>
            </div>""", unsafe_allow_html=True)
        else:
            total_rows = sum(v["row_count"] for v in schema.values())
            total_cols = sum(len(v["columns"]) for v in schema.values())
            st.markdown(f"""<div class="db-bar">
                <span class="db-bar-l">Schema Explorer</span>
                <span class="db-bar-r">{len(schema)} tables · {total_rows:,} rows · {total_cols} cols · {get_db_size_mb():.1f} MB</span>
            </div>""", unsafe_allow_html=True)

            rc1, rc2 = st.columns([5, 1])
            if rc2.button("Reset", type="secondary"):
                reset_database()
                st.session_state.db_ready = False
                st.session_state.history  = []
                st.cache_resource.clear()
                st.rerun()

            st.markdown('<div style="height:0.4rem"></div>', unsafe_allow_html=True)

            for tname, info in schema.items():
                chips = "".join(
                    f'<span class="col-chip">{c["name"]}<span class="col-type"> {c["type"]}</span></span>'
                    for c in info["columns"]
                )
                st.markdown(f"""<div class="tbl-card">
                    <div class="tbl-hdr">
                        <span class="tbl-name">{tname}</span>
                        <span class="tbl-badge">{info["row_count"]:,} rows</span>
                    </div>
                    <div class="tbl-meta">{len(info["columns"])} columns</div>
                    <div>{chips}</div>
                </div>""", unsafe_allow_html=True)
                with st.expander(f"Preview — {tname}", expanded=False):
                    try:
                        st.dataframe(preview_table(tname), use_container_width=True, height=220)
                    except Exception as e:
                        st.error(str(e))

    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: QUERY COPILOT
# ══════════════════════════════════════════════════════════════════════════════

if not st.session_state.db_ready:
    st.warning("No data loaded. Go to **Data Manager** in the sidebar first.")
    st.stop()

if not api_key:
    st.markdown("""
    <div class="wc-grid">
        <div class="wc-card"><span class="wc-icon">💬</span>
            <div class="wc-title">Ask in plain English</div>
            <div class="wc-desc">Type any business question. The AI writes and runs the query for you — no SQL needed.</div></div>
        <div class="wc-card"><span class="wc-icon">📈</span>
            <div class="wc-title">Instant charts</div>
            <div class="wc-desc">Every result is automatically paired with a relevant chart — bar, line, scatter, or pie.</div></div>
        <div class="wc-card"><span class="wc-icon">🧠</span>
            <div class="wc-title">Business summaries</div>
            <div class="wc-desc">After each query, the AI writes a short, actionable summary of what the data means.</div></div>
        <div class="wc-card"><span class="wc-icon">🛡️</span>
            <div class="wc-title">Read-only by design</div>
            <div class="wc-desc">All queries are validated. No writes, deletes, or destructive operations — ever.</div></div>
        <div class="wc-card"><span class="wc-icon">🔁</span>
            <div class="wc-title">Smart follow-ups</div>
            <div class="wc-desc">The copilot suggests follow-up questions based on your results to guide deeper analysis.</div></div>
        <div class="wc-card"><span class="wc-icon">💾</span>
            <div class="wc-title">Auto-saved history</div>
            <div class="wc-desc">Every insight is saved to your sidebar automatically — no manual saving needed.</div></div>
    </div>""", unsafe_allow_html=True)
    st.info("Enter your **Groq API Key** in the sidebar to continue. Free key at [console.groq.com/keys](https://console.groq.com/keys).")
    st.stop()

# ─── Validate key ─────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def validate_api_key(key: str):
    try:
        from groq import Groq
        Groq(api_key=key).chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content":"ping"}],
            max_tokens=1,
        )
        return True, ""
    except Exception as e:
        err = str(e)
        if "401" in err or "invalid_api_key" in err.lower():
            return False, "Invalid API key. Get yours at [console.groq.com/keys](https://console.groq.com/keys)."
        if "429" in err: return True, ""
        return False, f"Could not verify key: {err}"

with st.spinner("Verifying key…"):
    ok, err = validate_api_key(api_key)
if not ok:
    st.error(err); st.stop()

# ─── Init Vanna ───────────────────────────────────────────────────────────────
@st.cache_resource
def init_vanna(key, _mtime):
    return get_vanna_instance(key)

duck_mtime = os.path.getmtime(DUCK_PATH) if os.path.exists(DUCK_PATH) else 0
vn = init_vanna(api_key, duck_mtime)

# ─── Dynamic chips from real table names ─────────────────────────────────────
schema     = get_schema()
tbl_names  = list(schema.keys())

def chip(t): return f"Show summary of {t}"
suggestions = [
    chip(tbl_names[0]) if tbl_names else "Show all tables",
    f"Row counts across all tables",
    chip(tbl_names[1]) if len(tbl_names) > 1 else "Show column types",
    "Which table has the most records?",
    f"Top 10 rows from {tbl_names[-1]}" if tbl_names else "Describe the data",
    "Show columns with missing values",
]

st.markdown(f'<div class="chip-label">Suggested questions</div>', unsafe_allow_html=True)
c_cols = st.columns(6)
for i, s in enumerate(suggestions[:6]):
    if c_cols[i].button(s, key=f"chip_{i}"):
        st.session_state.current_prompt = s

st.markdown("---")


# ─── Render one stored result ─────────────────────────────────────────────────
def render_result(entry):
    sql, cached, df = entry["sql"], entry["cached"], entry["df"]
    latency, summary, followups = entry["latency"], entry["summary"], entry["followups"]
    log_id = entry["log_id"]

    with st.expander("View SQL", expanded=False):
        st.code(sql, language="sql")
        badge = f'<span class="badge-cache">⚡ From cache</span>' if cached \
                else f'<span class="badge-ai">✓ AI generated</span>'
        st.markdown(badge, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="kpi-row">
        <div class="kpi-item"><div class="kpi-val">{len(df):,}</div><div class="kpi-lbl">Rows</div></div>
        <div class="kpi-item"><div class="kpi-val">{len(df.columns)}</div><div class="kpi-lbl">Columns</div></div>
        <div class="kpi-item"><div class="kpi-val">{latency:.2f}s</div><div class="kpi-lbl">Time</div></div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f'<div class="sect-lbl">Results</div>', unsafe_allow_html=True)
    st.dataframe(df.head(500), use_container_width=True)

    if entry.get("fig"):
        st.markdown(f'<div class="sect-lbl">Chart</div>', unsafe_allow_html=True)
        fig = entry["fig"]
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor=SURFACE,
            font=dict(family="Inter", color=TEXT2, size=11),
            margin=dict(l=10, r=10, t=30, b=10),
            xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
            yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"""
    <div class="insight-block">
        <div class="insight-lbl">Insight</div>
        <div class="insight-text">{summary}</div>
    </div>""", unsafe_allow_html=True)

    if followups:
        st.markdown(f'<div class="fu-lbl">Follow-up questions</div>', unsafe_allow_html=True)
        fcols = st.columns(3)
        for i, fu in enumerate(followups[:3]):
            if fcols[i].button(fu, key=f"fu_h_{log_id}_{i}"):
                st.session_state.current_prompt = fu; st.rerun()

    fb = st.columns([1,1,1,6])
    fb[0].button("👍", key=f"fb_y_{log_id}", help="Correct",  on_click=log_feedback, args=(log_id,"Correct"))
    fb[1].button("🤔", key=f"fb_p_{log_id}", help="Partial",  on_click=log_feedback, args=(log_id,"Partial"))
    fb[2].button("👎", key=f"fb_n_{log_id}", help="Wrong",    on_click=log_feedback, args=(log_id,"Wrong"))


# ─── History ─────────────────────────────────────────────────────────────────
for entry in st.session_state.history:
    with st.chat_message("user", avatar="👤"):
        st.markdown(f"**{entry['prompt']}**")
    with st.chat_message("assistant", avatar="📊"):
        render_result(entry)

# ─── Input ───────────────────────────────────────────────────────────────────
prompt = st.chat_input("Ask a question about your data…")
if "current_prompt" in st.session_state:
    prompt = st.session_state.current_prompt
    del st.session_state.current_prompt

# ─── Pipeline ────────────────────────────────────────────────────────────────
if prompt:
    with st.chat_message("user", avatar="👤"):
        st.markdown(f"**{prompt}**")

    with st.chat_message("assistant", avatar="📊"):
        t0 = time.time()

        is_amb, clarify = detect_ambiguity(prompt)
        if is_amb:
            st.warning(f"🤔 {clarify}"); st.stop()

        # ── Direct analytics shortcuts ──
        # 1. Most records (already handled above)
        if re.search(r"which table has the most records", prompt, re.IGNORECASE):
            import duckdb
            con = duckdb.connect(DUCK_PATH, read_only=True)
            try:
                tables = con.execute("SHOW TABLES").fetchall()
                max_tbl = None
                max_cnt = -1
                for (tbl,) in tables:
                    try:
                        cnt = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
                        if cnt > max_cnt:
                            max_cnt = cnt
                            max_tbl = tbl
                    except Exception:
                        continue
                if max_tbl is not None:
                    st.markdown(f"**Table with most records:** `{max_tbl}` (**{max_cnt:,}** rows)")
                else:
                    st.warning("No tables found in the database.")
            finally:
                con.close()
            st.stop()
        # 2. Show summary of a specific table (first few rows & schema)
        m = re.search(r"show summary of (.+)", prompt, re.IGNORECASE)
        if m:
            tbl = m.group(1).strip()
            import duckdb
            con = duckdb.connect(DUCK_PATH, read_only=True)
            try:
                # Show first 5 rows
                df_head = con.execute(f"SELECT * FROM {tbl} LIMIT 5").df()
                # Show column names and types
                cols_info = con.execute(f"PRAGMA table_info('{tbl}')").df()
                st.markdown(f"**Preview of `{tbl}` (first 5 rows)**")
                st.dataframe(df_head)
                st.markdown(f"**Schema of `{tbl}`**")
                st.dataframe(cols_info[['name', 'type']].rename(columns={'name':'Column','type':'Type'}))
            except Exception as e:
                st.error(f"Unable to show summary for table `{tbl}`: {e}")
            finally:
                con.close()
            st.stop()
        # 3. Row counts across all tables
        if re.search(r"row counts across all tables", prompt, re.IGNORECASE):
            import duckdb
            con = duckdb.connect(DUCK_PATH, read_only=True)
            try:
                tables = con.execute("SHOW TABLES").fetchall()
                rows = []
                for (tbl,) in tables:
                    try:
                        cnt = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
                        rows.append((tbl, cnt))
                    except Exception:
                        rows.append((tbl, None))
                df_counts = pd.DataFrame(rows, columns=["Table", "RowCount"]).set_index("Table")
                st.markdown("**Row counts for all tables**")
                st.dataframe(df_counts)
            finally:
                con.close()
            st.stop()
        # 4. Show columns with missing values
        if re.search(r"show columns with missing values", prompt, re.IGNORECASE):
            import duckdb
            con = duckdb.connect(DUCK_PATH, read_only=True)
            try:
                tables = con.execute("SHOW TABLES").fetchall()
                missing = []
                for (tbl,) in tables:
                    # Get column list
                    cols = con.execute(f"PRAGMA table_info('{tbl}')").fetchall()
                    for col_tuple in cols:
                        col_name = col_tuple[1]
                        try:
                            null_cnt = con.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {col_name} IS NULL").fetchone()[0]
                            if null_cnt > 0:
                                missing.append((tbl, col_name, null_cnt))
                        except Exception:
                            continue
                if missing:
                    df_missing = pd.DataFrame(missing, columns=["Table", "Column", "NullCount"]).set_index(["Table", "Column"]) 
                    st.markdown("**Columns containing NULL values**")
                    st.dataframe(df_missing)
                else:
                    st.info("No NULL values found in any column.")
            finally:
                con.close()
            st.stop()
        # 5. Top 10 rows from a table
        m = re.search(r"top 10 rows from (.+)", prompt, re.IGNORECASE)
        if m:
            tbl = m.group(1).strip()
            import duckdb
            con = duckdb.connect(DUCK_PATH, read_only=True)
            try:
                df_top = con.execute(f"SELECT * FROM {tbl} LIMIT 10").df()
                st.markdown(f"**Top 10 rows from `{tbl}`**")
                st.dataframe(df_top)
            except Exception as e:
                st.error(f"Unable to fetch top rows for `{tbl}`: {e}")
            finally:
                con.close()
            st.stop()
        # 6. Show all tables (list)
        if re.search(r"show all tables", prompt, re.IGNORECASE):
            import duckdb
            con = duckdb.connect(DUCK_PATH, read_only=True)
            try:
                tables = con.execute("SHOW TABLES").fetchdf()
                st.markdown("**Available tables**")
                st.dataframe(tables)
            finally:
                con.close()
            st.stop()
        # 7. Show column types (schema overview)
        if re.search(r"show column types", prompt, re.IGNORECASE):
            import duckdb
            con = duckdb.connect(DUCK_PATH, read_only=True)
            try:
                schema = {}
                tables = con.execute("SHOW TABLES").fetchall()
                for (tbl,) in tables:
                    cols = con.execute(f"PRAGMA table_info('{tbl}')").fetchdf()
                    schema[tbl] = cols[['name','type']].rename(columns={'name':'Column','type':'Type'})
                st.markdown("**Schema overview (column types)**")
                for tbl, df_cols in schema.items():
                    st.subheader(tbl)
                    st.dataframe(df_cols)
            finally:
                con.close()
            st.stop()
        # Existing LLM flow
        with st.status("Generating query…", expanded=False) as ss:
            sql = check_cache(prompt); cached = bool(sql)
            if not cached: sql = vn.generate_sql(question=prompt)
            ss.update(label="⚡ From cache" if cached else "✓ Query ready", state="complete")



        ok2, chk = validate_sql(sql)
        if not ok2:
            st.error(f"Blocked: {chk}")
            log_query(prompt, "N/A", time.time()-t0, "Failure", "Guardrail"); st.stop()
        sql = chk

        with st.expander("View SQL", expanded=False):
            st.code(sql, language="sql")
            badge = f'<span class="badge-cache">⚡ From cache</span>' if cached \
                    else f'<span class="badge-ai">✓ AI generated</span>'
            st.markdown(badge, unsafe_allow_html=True)

        with st.spinner("Running query…"):
            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    df = vn.run_sql(sql); status = "Success"; emsg = ""
                    if not cached and df is not None and not df.empty and "Rate Limit" not in sql:
                        save_cache(prompt, sql)
                    break  # Success! Exit retry loop
                except Exception as e:
                    emsg = str(e); status = "Failure"; df = None
                    if attempt < max_retries and not cached:
                        # ── Self-Correction Loop ──
                        st.toast(f"Self-correcting query (Attempt {attempt+1}/{max_retries})…", icon="🔧")
                        correction_prompt = (
                            f"The following DuckDB query failed with this error:\n{emsg}\n\n"
                            f"Original Query:\n{sql}\n\n"
                            f"Please provide ONLY the fixed SQL query. No explanation or markdown."
                        )
                        new_sql = vn.submit_prompt(correction_prompt)
                        if "```sql" in new_sql.lower():
                            new_sql = new_sql.split("```sql")[1].split("```")[0].strip()
                        elif "```" in new_sql:
                            new_sql = new_sql.split("```")[1].split("```")[0].strip()
                        
                        ok2, chk = validate_sql(new_sql)
                        if ok2: sql = chk

        lat = time.time() - t0
        lid = log_query(prompt, sql, lat, status, emsg)

        if status == "Failure":
            st.error(f"Query failed: {emsg}"); st.code(sql, language="sql"); st.stop()
        if df is None or df.empty:
            st.warning("No data returned. Try rephrasing."); st.stop()

        st.markdown(f"""
        <div class="kpi-row">
            <div class="kpi-item"><div class="kpi-val">{len(df):,}</div><div class="kpi-lbl">Rows</div></div>
            <div class="kpi-item"><div class="kpi-val">{len(df.columns)}</div><div class="kpi-lbl">Columns</div></div>
            <div class="kpi-item"><div class="kpi-val">{lat:.2f}s</div><div class="kpi-lbl">Time</div></div>
        </div>""", unsafe_allow_html=True)

        st.markdown(f'<div class="sect-lbl">Results</div>', unsafe_allow_html=True)
        st.dataframe(df.head(500), use_container_width=True)

        fig = None
        try:
            with st.spinner("Building chart…"):
                code = vn.generate_plotly_code(question=prompt, sql=sql, df=df)
                # Vanna's generated code might have fig.show(renderer='browser') or similar. 
                # Use regex to strip any form of fig.show(...) robustly.
                import re
                code = re.sub(r"fig\.show\s*\([^)]*\)", "", code)
                fig  = vn.get_plotly_figure(plotly_code=code, df=df)
                if fig:
                    fig.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=SURFACE,
                        font=dict(family="Inter", color=TEXT2, size=11),
                        margin=dict(l=10,r=10,t=30,b=10),
                        xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
                        yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
                    )
                    st.markdown(f'<div class="sect-lbl">Chart</div>', unsafe_allow_html=True)
                    st.plotly_chart(fig, use_container_width=True)
        except Exception: pass

        with st.spinner("Summarising…"):
            idata = generate_insights_and_followups(prompt, df, api_key)
        summary   = idata.get("summary", "")
        followups = idata.get("followups", [])

        st.markdown(f"""
        <div class="insight-block">
            <div class="insight-lbl">Insight</div>
            <div class="insight-text">{summary}</div>
        </div>""", unsafe_allow_html=True)

        if not cached and "Rate Limit" not in summary and "Error" not in summary:
            save_insight(prompt[:35]+"…", prompt, sql, summary)

        if followups:
            st.markdown(f'<div class="fu-lbl">Follow-up questions</div>', unsafe_allow_html=True)
            fcols = st.columns(3)
            for i, fu in enumerate(followups[:3]):
                if fcols[i].button(fu, key=f"fu_new_{lid}_{i}"):
                    st.session_state.current_prompt = fu; st.rerun()

        fb = st.columns([1,1,1,6])
        fb[0].button("👍", key=f"fb_y_{lid}", help="Correct", on_click=log_feedback, args=(lid,"Correct"))
        fb[1].button("🤔", key=f"fb_p_{lid}", help="Partial", on_click=log_feedback, args=(lid,"Partial"))
        fb[2].button("👎", key=f"fb_n_{lid}", help="Wrong",   on_click=log_feedback, args=(lid,"Wrong"))

        st.session_state.history.append({
            "prompt": prompt, "sql": sql, "cached": cached,
            "df": df, "fig": fig, "latency": lat,
            "summary": summary, "followups": followups, "log_id": lid,
        })
