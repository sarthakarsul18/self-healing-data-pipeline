import streamlit as st
import pandas as pd
import tempfile
import os
from graph import app as pipeline

# -------------------- Page Config --------------------
st.set_page_config(
    page_title="Self‑Healing Data Pipeline",
    layout="wide",
    page_icon="🩺",
    initial_sidebar_state="collapsed"
)

# -------------------- Dark Theme Custom CSS --------------------
st.markdown("""
<style>
    /* ===== GLOBAL DARK BACKGROUND ===== */
    .stApp {
        background: linear-gradient(145deg, #0f0c29, #302b63, #24243e);
        color: #e0e0e0;
    }

    /* ===== HEADER GLOW ===== */
    .main-header {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #00d2ff, #3a7bd5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 5px;
        letter-spacing: -0.5px;
    }
    .sub-header {
        text-align: center;
        font-size: 1.1rem;
        color: #b0b0c0;
        margin-bottom: 30px;
    }

    /* ===== METRIC CARDS ===== */
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(15px);
        border-radius: 24px;
        padding: 25px 15px;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px rgba(0, 212, 255, 0.05);
        transition: all 0.3s ease;
        margin-bottom: 10px;
    }
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 40px rgba(0, 212, 255, 0.15);
        border-color: rgba(0, 212, 255, 0.3);
    }
    .metric-label {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #8a8aa3;
        margin-bottom: 8px;
        font-weight: 500;
    }
    .metric-value {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(180deg, #ffffff, #a0c0ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1;
    }

    /* ===== SECTION TITLES ===== */
    .section-title {
        font-size: 1.8rem;
        font-weight: 700;
        margin-top: 40px;
        margin-bottom: 20px;
        padding-left: 15px;
        border-left: 5px solid #00d2ff;
        color: #ffffff;
        background: linear-gradient(90deg, rgba(0,210,255,0.1) 0%, transparent 70%);
        padding: 8px 20px;
        border-radius: 8px;
    }

    /* ===== BUTTON STYLES ===== */
    div.stButton > button {
        background: linear-gradient(135deg, #00d2ff, #3a7bd5);
        color: white;
        font-weight: 700;
        font-size: 1.1rem;
        border: none;
        border-radius: 50px;
        padding: 0.8rem 2.5rem;
        box-shadow: 0 4px 15px rgba(0, 210, 255, 0.4);
        transition: all 0.3s ease;
        letter-spacing: 1px;
    }
    div.stButton > button:hover {
        background: linear-gradient(135deg, #3a7bd5, #00d2ff);
        box-shadow: 0 6px 25px rgba(0, 210, 255, 0.6);
        transform: scale(1.02);
    }

    /* ===== FILE UPLOADER ===== */
    div[data-testid="stFileUploader"] {
        background: rgba(255,255,255,0.03);
        border-radius: 20px;
        padding: 20px;
        border: 2px dashed rgba(255,255,255,0.15);
        transition: 0.3s;
    }
    div[data-testid="stFileUploader"]:hover {
        border-color: #00d2ff;
        background: rgba(0,210,255,0.03);
    }

    /* ===== EXPANDER ===== */
    .streamlit-expanderHeader {
        background: rgba(255,255,255,0.05);
        border-radius: 15px;
        font-weight: 600;
        color: #ffffff !important;
    }
    .streamlit-expanderContent {
        background: rgba(0,0,0,0.2);
        border-radius: 0 0 15px 15px;
    }

    /* ===== DATAFRAME STYLING ===== */
    [data-testid="stDataFrame"] {
        background: rgba(255,255,255,0.03);
        border-radius: 20px;
        padding: 10px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .stDataFrame table {
        border-collapse: separate;
        border-spacing: 0 4px;
    }
    .stDataFrame thead th {
        background: rgba(0,210,255,0.15);
        color: #ffffff;
        font-weight: 600;
    }
    .stDataFrame tbody td {
        background: rgba(255,255,255,0.02);
        color: #d0d0d0;
    }

    /* ===== DOWNLOAD BUTTON ===== */
    div.stDownloadButton > button {
        background: transparent;
        border: 2px solid #00d2ff;
        color: #00d2ff;
        font-weight: 700;
        border-radius: 50px;
        padding: 0.6rem 2rem;
        transition: 0.3s;
    }
    div.stDownloadButton > button:hover {
        background: rgba(0,210,255,0.1);
        box-shadow: 0 0 20px rgba(0,210,255,0.3);
    }

    /* ===== SUCCESS/SPINNER ===== */
    .stSpinner > div {
        border-color: #00d2ff !important;
    }
    .stSuccess {
        background: rgba(0,255,135,0.1);
        border-radius: 10px;
        padding: 10px;
    }

    /* ===== SCROLLBAR ===== */
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #0f0c29;
    }
    ::-webkit-scrollbar-thumb {
        background: #302b63;
        border-radius: 10px;
    }

    /* ===== CREATOR CREDIT (NEW) ===== */
    .creator-credit {
        text-align: center;
        margin-top: 50px;
        padding: 20px 0;
        border-top: 1px solid rgba(255,255,255,0.1);
        font-size: 0.9rem;
        color: #8a8aa3;
        letter-spacing: 1px;
    }
    .creator-credit span {
        background: linear-gradient(90deg, #00d2ff, #3a7bd5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 600;
    }
    .creator-credit i {
        font-style: normal;
        color: #ffd700;
        margin: 0 5px;
    }
</style>
""", unsafe_allow_html=True)

# -------------------- Header --------------------
st.markdown('<div class="main-header">🩺 Self‑Healing Data Pipeline</div>', unsafe_allow_html=True)
st.markdown("""
<div class="sub-header">
    <b>Groq</b> · <b>LangGraph</b> · <b>RAG</b> &nbsp;|&nbsp;
    Auto‑detect & heal schema mismatches, missing values, duplicates & more
</div>
""", unsafe_allow_html=True)

# -------------------- Upload Section --------------------
uploaded_file = st.file_uploader(
    "📂 Upload your CSV file",
    type=["csv"],
    help="Even messy column names are fine – the AI will fix them."
)

if uploaded_file is not None:
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    # Centered run button
    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        run_button = st.button("🚀 Launch Self‑Healing", use_container_width=True)

    if run_button:
        with st.spinner("🔍 Scanning issues... 🧠 AI mapping columns... 🛠️ Healing data..."):
            state = pipeline.invoke({
                "file_path": tmp_path,
                "df": None,
                "issues": {},
                "original_issues": {},
                "final_issues": {},
                "mapping": {},
                "actions": [],
                "healed_csv_path": "",
                "retry_count": 0
            })

        st.success("✨ Healing complete – your data is now production‑ready!")

        # -------------------- Original Issues Cards --------------------
        st.markdown('<div class="section-title">🔍 Issues Detected in Uploaded File</div>', unsafe_allow_html=True)
        orig = state["original_issues"]
        cols = st.columns(5)
        labels_vals = [
            ("Missing Cols", len(orig.get("missing_columns", []))),
            ("Null Values", sum(orig.get("missing_values", {}).values())),
            ("Duplicates", orig.get("duplicate_rows", 0)),
            ("Bad Emails", orig.get("invalid_emails", 0)),
            ("Negatives", orig.get("negative_values", 0))
        ]
        for col, (label, val) in zip(cols, labels_vals):
            col.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{val}</div>
            </div>
            """, unsafe_allow_html=True)

        # -------------------- Final Validation Cards --------------------
        st.markdown('<div class="section-title">✅ Validation After Healing</div>', unsafe_allow_html=True)
        final = state["final_issues"]
        cols = st.columns(5)
        labels_vals = [
            ("Missing Cols", len(final.get("missing_columns", []))),
            ("Null Values", sum(final.get("missing_values", {}).values())),
            ("Duplicates", final.get("duplicate_rows", 0)),
            ("Bad Emails", final.get("invalid_emails", 0)),
            ("Negatives", final.get("negative_values", 0))
        ]
        for col, (label, val) in zip(cols, labels_vals):
            col.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{val}</div>
            </div>
            """, unsafe_allow_html=True)

        # -------------------- Healing Actions (Expander) --------------------
        with st.expander("🛠️ Healing Actions Applied", expanded=True):
            actions = state["actions"]
            if actions:
                for i, act in enumerate(actions, 1):
                    st.markdown(f"<span style='color:#b0ffb0;'>✔</span> {i}. {act}", unsafe_allow_html=True)
            else:
                st.info("No healing needed – data already clean.")

        # -------------------- Healed Data Preview --------------------
        st.markdown('<div class="section-title">📊 Healed Data Preview</div>', unsafe_allow_html=True)
        df_healed = state["df"]
        st.dataframe(
            df_healed.head(10),
            use_container_width=True,
            hide_index=True,
            column_config={
                "transaction_id": "Transaction ID",
                "customer_email": "Customer Email",
                "purchase_amount": st.column_config.NumberColumn("Amount", format="%.2f"),
                "purchase_date": "Date"
            }
        )

        # -------------------- Download Button --------------------
        _, dl_col, _ = st.columns([1, 2, 1])
        with dl_col:
            with open(state["healed_csv_path"], "rb") as f:
                st.download_button(
                    label="⬇️ Download Healed CSV",
                    data=f,
                    file_name="healed_data.csv",
                    mime="text/csv",
                    use_container_width=True
                )

# -------------------- Creator Credit (Footer) --------------------
st.markdown("""
<div class="creator-credit">
    <i>⚡</i> Built with passion by <span>Sarthak Arsul</span> <i>⚡</i>
</div>
""", unsafe_allow_html=True)