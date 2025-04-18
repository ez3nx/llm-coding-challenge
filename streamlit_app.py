import streamlit as st

st.set_page_config(
    page_title="Code Quality Reporter",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import base64
from app.services.git_service import GitService
from app.services.visualization_service import display_commit_analytics
from app.services.full_quality_report import generate_full_quality_report, get_pdf_download_link

load_dotenv()

# Стили
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stButton button {
        border-radius: 4px;
        font-weight: 500;
    }
    .stButton button[data-baseweb="button"] {
        background-color: #EF3124;
        color: white;
    }
    .stCheckbox label p {
        font-size: 1rem;
    }
    .sidebar .block-container {
        padding-top: 2rem;
    }
    h1 { color: #333; font-weight: 600; }
    h2, h3 { color: #333; font-weight: 500; }
</style>
""", unsafe_allow_html=True)

# Шапка
st.markdown("""
<div style="display: flex; align-items: center; margin-bottom: 1rem;">
    <div style="font-size: 2.5rem; margin-right: 15px; color: #EF3124;">📊</div>
    <div>
        <h1 style="margin: 0; padding: 0;">Code Quality Reporter</h1>
        <div style="color: #666; font-size: 1.1rem; margin-top: 5px;">
            Analyze developer code quality and generate comprehensive reports
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

use_llm = st.checkbox("🌍 Enable LLM analysis for commit messages", value=True)

@st.cache_resource
def get_services():
    return GitService()

git_service = get_services()

# Sidebar: repo
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; margin-bottom: 20px;">
        <div style="font-size: 2rem; color: #EF3124; margin-bottom: 10px;">🛠️</div>
        <div style="font-weight: 600; font-size: 1.2rem; color: #333;">Settings</div>
    </div>
    """, unsafe_allow_html=True)

    repo_name = st.text_input("Repository (owner/repo)", "AlfaInsurance/devQ_testData_JavaProject")
    if st.button("Load Repository Data", type="primary"):
        with st.spinner("Loading repository data..."):
            try:
                st.session_state.authors = git_service.get_all_commit_authors(repo_name)
                st.session_state.repo_loaded = bool(st.session_state.authors)
                if not st.session_state.repo_loaded:
                    st.error("No authors found or repository not accessible")
                else:
                    st.success(f"Successfully loaded {len(st.session_state.authors)} authors")
            except Exception as e:
                st.error(f"Error: {e}")

if not st.session_state.get("repo_loaded"):
    st.markdown("""
    <div style="text-align: center; margin: 3rem 0;">
        <div style="font-size: 4rem; margin-bottom: 1.5rem;">🔍</div>
        <h2>Welcome to Code Quality Reporter</h2>
        <p style="font-size: 1.1rem; max-width: 600px; margin: 0 auto; color: #666;">
            Please enter a repository name and click 'Load Repository Data' to begin analyzing code quality.
        </p>
    </div>
    """, unsafe_allow_html=True)
else:
    col1, col2 = st.columns(2)
    with col1:
        author_options = [(f"{a['name']} - {a.get('commit_count', 0)} commits",
                           a.get("github_login") or a.get("email"), a) for a in st.session_state.authors]
        selected_display = st.selectbox("Select Developer", [a[0] for a in author_options], index=0)
        selected_value = next(a[1] for a in author_options if a[0] == selected_display)
        selected_author_data = next(a[2] for a in author_options if a[0] == selected_display)

    with col2:
        col_start, col_end = st.columns(2)
        with col_start:
            start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=30))
        with col_end:
            end_date = st.date_input("End Date", value=datetime.now())

    if st.button("Analyze", type="primary"):
        with st.spinner("🔍 Analyzing commits..."):
            commits = git_service.get_repository_commits(
                repo_name=repo_name,
                developer_username=selected_value,
                start_date=start_date,
                end_date=end_date,
                use_llm=use_llm,
            )
            st.session_state.analyzed_commits = commits
            st.session_state.analyzed_author = selected_author_data
            st.session_state.analyzed_dates = (start_date, end_date)
            st.session_state.quality_report_generated = False

            if not commits:
                st.warning("No commits found for the selected developer and date range.")
            else:
                display_commit_analytics(commits, selected_author_data)
    elif st.session_state.get("analyzed_commits"):
        display_commit_analytics(st.session_state.analyzed_commits, st.session_state.analyzed_author)

# Отчет внизу
if st.session_state.get("analyzed_commits"):
    st.markdown("---")
    st.subheader("📊 Full Code Quality Report")

    if st.button("📊 Generate Full Quality Report", key="generate_final_report"):
        with st.spinner("🧠 Generating comprehensive quality report..."):
            report = generate_full_quality_report(st.session_state.analyzed_commits)
            st.session_state.quality_report = report
            st.session_state.quality_report_generated = True

    if st.session_state.get("quality_report_generated") and st.session_state.get("quality_report"):
        st.markdown("""
            <div style="background-color: #F5F5F5; padding: 1.5rem; border-radius: 8px;">
                <h2 style="display: flex; align-items: center; margin-top: 0;">
                    <span style="font-size: 1.5rem; margin-right: 0.5rem;">📋</span>
                    Full Code Quality Report
                </h2>
            """, unsafe_allow_html=True)

        st.markdown(
            f"""
                <div style="
                    max-height: 500px;
                    overflow-y: auto;
                    overflow-x: hidden;
                    white-space: pre-wrap;
                    font-family: monospace;
                    font-size: 0.95rem;
                    padding: 1rem;
                    background-color: #ffffff;
                    border: 1px solid #ccc;
                    border-radius: 8px;
                    margin-top: 1rem;
                ">
                    {st.session_state.quality_report}
                </div>
                """,
            unsafe_allow_html=True
        )

        st.markdown(
            get_pdf_download_link(
                st.session_state.quality_report,
                f"code_quality_{selected_value}_{start_date.strftime('%Y%m%d')}.pdf",
                "Download as PDF"
            ),
            unsafe_allow_html=True
        )
        st.markdown("</div>", unsafe_allow_html=True)
