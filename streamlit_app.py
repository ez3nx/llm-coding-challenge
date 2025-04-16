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
import sys
import base64
from app.services.git_service import GitService
from app.services.visualization_service import display_commit_analytics
from app.services.full_quality_report import generate_full_quality_report, get_pdf_download_link

# Загружаем переменные окружения
load_dotenv()

# Добавляем стилизацию к Streamlit
st.markdown(
    """
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
    .sidebar .element-container:first-child {
        margin-bottom: 2rem;
    }
    h1 {
        color: #333333;
        font-weight: 600;
    }
    h2, h3 {
        color: #333333;
        font-weight: 500;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Заголовок приложения с логотипом
st.markdown(
    """
<div style="display: flex; align-items: center; margin-bottom: 1rem;">
    <div style="font-size: 2.5rem; margin-right: 15px; color: #EF3124;">📊</div>
    <div>
        <h1 style="margin: 0; padding: 0;">Code Quality Reporter</h1>
        <div style="color: #666; font-size: 1.1rem; margin-top: 5px;">
            Analyze developer code quality and generate comprehensive reports
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# Настройка Streamlit
use_llm = st.checkbox("🔮 Enable LLM analysis for commit messages", value=True)


# Инициализация сервисов
@st.cache_resource
def get_services():
    git_service = GitService()
    return git_service


git_service = get_services()
report_service, code_analyzer = 0, 0


# Функция для создания скачиваемой ссылки
def get_download_link(html_content, filename, text):
    b64 = base64.b64encode(html_content.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{filename}" style="text-decoration: none; color: #EF3124; font-weight: 500; display: inline-flex; align-items: center;"><span style="margin-right: 5px;">📥</span> {text}</a>'
    return href


# Боковая панель для настройки
with st.sidebar:
    st.markdown(
        """
    <div style="text-align: center; margin-bottom: 20px;">
        <div style="font-size: 2rem; color: #EF3124; margin-bottom: 10px;">🛠️</div>
        <div style="font-weight: 600; font-size: 1.2rem; color: #333333;">Settings</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Ввод данных репозитория
    repo_name = st.text_input(
        "Repository (owner/repo)", "AlfaInsurance/devQ_testData_JavaProject"
    )

    # Кнопка для загрузки авторов
    if st.button("Load Repository Data", type="primary"):
        with st.spinner("Loading repository data..."):
            try:
                st.session_state.authors = git_service.get_all_commit_authors(repo_name)
                if not st.session_state.authors:
                    st.error("No authors found or repository not accessible")
                else:
                    st.success(
                        f"Successfully loaded {len(st.session_state.authors)} authors"
                    )
                    st.session_state.repo_loaded = True
            except Exception as e:
                st.error(f"Error: {e}")

# Основной интерфейс
if not hasattr(st.session_state, "repo_loaded") or not st.session_state.repo_loaded:
    # Показываем красивый приветственный экран
    st.markdown(
        """
    <div style="text-align: center; margin: 3rem 0;">
        <div style="font-size: 4rem; margin-bottom: 1.5rem;">🔍</div>
        <h2>Welcome to Code Quality Reporter</h2>
        <p style="font-size: 1.1rem; max-width: 600px; margin: 0 auto; color: #666;">
            Please enter a repository name and click 'Load Repository Data' to begin analyzing code quality.
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Добавляем информационные карточки
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
        <div style="background-color: #F5F5F5; padding: 1.5rem; border-radius: 8px; height: 100%;">
            <div style="font-size: 2rem; margin-bottom: 1rem;">📊</div>
            <h3>Developer Analytics</h3>
            <p>Get detailed statistics about developer activity, code changes and commit patterns.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
        <div style="background-color: #F5F5F5; padding: 1.5rem; border-radius: 8px; height: 100%;">
            <div style="font-size: 2rem; margin-bottom: 1rem;">🤖</div>
            <h3>AI-Powered Analysis</h3>
            <p>Leverage LLM technology to analyze code quality, identify best practices and potential issues.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
        <div style="background-color: #F5F5F5; padding: 1.5rem; border-radius: 8px; height: 100%;">
            <div style="font-size: 2rem; margin-bottom: 1rem;">📋</div>
            <h3>Comprehensive Reports</h3>
            <p>Generate detailed reports about code quality, developer performance and improvement areas.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
else:
    # Создаем две колонки для ввода параметров
    col1, col2 = st.columns(2)
    with col1:
        # Формируем опции для выпадающего списка
        author_options = []
        for author in st.session_state.authors:
            display_name = f"{author['name']}"
            if author.get("github_login"):
                display_name += f" ({author['github_login']})"
            display_name += f" - {author.get('commit_count', 0)} commits"
            value = (
                author.get("github_login")
                if author.get("github_login")
                else author.get("email")
            )
            author_options.append((display_name, value, author))

        # Выпадающий список авторов с кастомным стилем
        st.markdown(
            """
        <style>
        div[data-testid="stSelectbox"] > div > div > div {
            background-color: #F5F5F5;
            border-radius: 4px;
            border: none;
            padding: 0.5rem;
        }
        </style>
        """,
            unsafe_allow_html=True,
        )

        selected_author_display = st.selectbox(
            "Select Developer", options=[a[0] for a in author_options], index=0
        )

        # Получаем значение и полные данные выбранного автора
        selected_value = next(
            a[1] for a in author_options if a[0] == selected_author_display
        )
        selected_author_data = next(
            a[2] for a in author_options if a[0] == selected_author_display
        )

    with col2:
        # Выбор временного периода с кастомным стилем
        st.markdown(
            """
        <style>
        div[data-testid="stDateInput"] > div > div > div {
            background-color: #F5F5F5;
            border-radius: 4px;
            border: none;
            padding: 0.5rem;
        }
        </style>
        """,
            unsafe_allow_html=True,
        )

        col_start, col_end = st.columns(2)
        with col_start:
            start_date = st.date_input(
                "Start Date", value=datetime.now() - timedelta(days=30)
            )
        with col_end:
            end_date = st.date_input("End Date", value=datetime.now())

    # Опции анализа с красивыми радио-кнопками
    st.markdown(
        """
    <style>
    div[data-testid="stRadio"] > div {
        display: flex;
        gap: 1rem;
    }
    div[data-testid="stRadio"] > div > label {
        background-color: #F5F5F5;
        border-radius: 4px;
        padding: 0.75rem 1rem;
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.2s;
    }
    div[data-testid="stRadio"] > div > label:hover {
        background-color: #E5E5E5;
    }
    div[data-testid="stRadio"] > div > label > div:first-child {
        margin-right: 0.5rem;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    analysis_type = st.radio(
        "Analysis Type",
        options=["Basic Commit Analysis", "Full Code Quality Report"],
        index=0,
        horizontal=True,
    )

    # Кнопка для запуска анализа
    st.markdown(
        """
    <style>
    div[data-testid="stButton"] > button[kind="primary"] {
        background-color: #EF3124;
        color: white;
        border: none;
        padding: 0.5rem 2rem;
        font-weight: 500;
        transition: all 0.2s;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        background-color: #D62D20;
        border: none;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    def display_quality_report(commits, selected_value, start_date):
        """Отображает полный отчет о качестве кода"""
        report = generate_full_quality_report(commits)
        
        # Оформляем отчет
        st.markdown(
            """
        <div style="background-color: #F5F5F5; padding: 1.5rem; border-radius: 8px; margin-top: 2rem;">
            <h2 style="display: flex; align-items: center; margin-top: 0;">
                <span style="font-size: 1.5rem; margin-right: 0.5rem;">📋</span>
                Full Code Quality Report
            </h2>
        """,
            unsafe_allow_html=True,
        )
        
        # Создаем контейнер с фиксированной шириной и прокруткой
        container = st.container()
        with container:
            # Используем expander для возможности развернуть отчет на весь экран
            with st.expander("View Full Report", expanded=True):
                st.text_area("", report, height=500)
        
        # Добавляем кнопку для скачивания PDF
        st.markdown(
            get_pdf_download_link(
                report,
                f"code_quality_{selected_value}_{start_date.strftime('%Y%m%d')}.pdf",
                "Download as PDF",
            ),
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Analyze", type="primary"):
        # Общий блок для обоих типов анализа - получаем коммиты только один раз
        with st.spinner("🔍 Analyzing commits..."):
            # Если выбран полный отчет, всегда используем LLM
            use_llm_for_analysis = True if analysis_type == "Full Code Quality Report" else use_llm
            
            commits = git_service.get_repository_commits(
                repo_name=repo_name,
                developer_username=selected_value,
                start_date=start_date,
                end_date=end_date,
                use_llm=use_llm_for_analysis,
            )
            
            # Сохраняем коммиты в session_state для возможного последующего использования
            st.session_state.analyzed_commits = commits
            st.session_state.analyzed_author = selected_author_data
            st.session_state.analyzed_dates = (start_date, end_date)
            st.session_state.analysis_displayed = True  # Добавляем флаг, что анализ был отображен
            
            if not commits:
                st.warning("No commits found for the selected developer and date range.")
            else:
                # Отображаем визуализацию для обоих типов анализа
                display_commit_analytics(commits, selected_author_data)
                
                # Если выбран полный отчет, сразу отображаем его
                if analysis_type == "Full Code Quality Report":
                    display_quality_report(commits, selected_value, start_date)
    else:
        # Если кнопка не была нажата, но у нас есть данные анализа, отображаем их снова
        if hasattr(st.session_state, 'analyzed_commits') and st.session_state.analyzed_commits and hasattr(st.session_state, 'analysis_displayed') and st.session_state.analysis_displayed:
            display_commit_analytics(st.session_state.analyzed_commits, st.session_state.analyzed_author)

    # Проверяем, есть ли уже сгенерированный отчет
    if 'quality_report_generated' not in st.session_state:
        st.session_state.quality_report_generated = False

    # Добавляем кнопку для генерации отчета после анализа коммитов
    if hasattr(st.session_state, 'analyzed_commits') and st.session_state.analyzed_commits:
        # Создаем контейнер для отчета
        report_container = st.container()
        
        # Показываем кнопку только если отчет еще не сгенерирован и мы в режиме Basic Commit Analysis
        if not st.session_state.quality_report_generated and ('analysis_type' in locals() and analysis_type == "Basic Commit Analysis"):
            if st.button("📊 Generate Full Quality Report", type="secondary"):
                with st.spinner("🧠 Generating comprehensive quality report..."):
                    # Генерируем отчет
                    report = generate_full_quality_report(st.session_state.analyzed_commits)
                    st.session_state.quality_report = report
                    st.session_state.quality_report_generated = True
        
        # Если отчет был сгенерирован, отображаем его
        if hasattr(st.session_state, 'quality_report_generated') and st.session_state.quality_report_generated and hasattr(st.session_state, 'quality_report'):
            with report_container:
                st.markdown(
                    """
                <div style="background-color: #F5F5F5; padding: 1.5rem; border-radius: 8px; margin-top: 2rem;">
                    <h2 style="display: flex; align-items: center; margin-top: 0;">
                        <span style="font-size: 1.5rem; margin-right: 0.5rem;">📋</span>
                        Full Code Quality Report
                    </h2>
                """,
                    unsafe_allow_html=True,
                )
                st.code(st.session_state.quality_report, language="markdown")
                
                # Добавляем кнопку для скачивания PDF
                st.markdown(
                    get_pdf_download_link(
                        st.session_state.quality_report,
                        f"code_quality_{selected_value}_{start_date.strftime('%Y%m%d')}.pdf",
                        "Download as PDF",
                    ),
                    unsafe_allow_html=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)
