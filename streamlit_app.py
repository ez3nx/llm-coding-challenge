import streamlit as st
st.set_page_config(page_title="Code Quality Reporter", page_icon="📊", layout="wide")
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sys
import base64
from app.services.git_service import GitService
# Добавляем директорию app в путь импорта
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "app")))



# Импортируем наши сервисные классы
from app.services.git_service import GitService
from app.services.full_quality_report import generate_full_quality_report

# from app.services.code_analyzer import CodeAnalyzer
# from app.services.report_service import ReportService

# Загружаем переменные окружения
load_dotenv()

# Настройка Streamlit


use_llm = st.checkbox("🔮 Включить LLM-анализ commit-сообщений", value=True)
# Инициализация сервисов
@st.cache_resource
def get_services():
    git_service = GitService()
    # code_analyzer = CodeAnalyzer()
    # report_service = ReportService()
    # return git_service, code_analyzer, report_service
    return git_service


# git_service, code_analyzer, report_service = get_services()
git_service = get_services()
report_service, code_analyzer = 0, 0

# Функция для создания скачиваемой ссылки
def get_download_link(html_content, filename, text):
    b64 = base64.b64encode(html_content.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{filename}">📥 {text}</a>'
    return href


# Заголовок приложения
st.title("📊 Code Quality Reporter")
st.markdown("Analyze developer code quality and generate comprehensive reports")

# Боковая панель для настройки
with st.sidebar:
    st.header("Settings")

    # Ввод данных репозитория
    repo_name = st.text_input(
        "Repository (owner/repo)", "AlfaInsurance/devQ_testData_JavaProject"
    )

    # Кнопка для загрузки авторов
    if st.button("Load Repository Data"):
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
    st.info("Please enter a repository name and click 'Load Repository Data' to begin")
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

        # Выпадающий список авторов
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
        # Выбор временного периода
        col_start, col_end = st.columns(2)
        with col_start:
            start_date = st.date_input(
                "Start Date", value=datetime.now() - timedelta(days=30)
            )
        with col_end:
            end_date = st.date_input("End Date", value=datetime.now())

    # Опции анализа
    analysis_type = st.radio(
        "Analysis Type",
        options=["Basic Commit Analysis", "Full Code Quality Report"],
        index=0,
    )

    # Кнопка для запуска анализа
    if st.button("Analyze", type="primary"):
        if analysis_type == "Basic Commit Analysis":
            # Базовый анализ коммитов
            with st.spinner("Analyzing commits..."):
                commits = git_service.get_repository_commits(
                    repo_name=repo_name,
                    developer_username=selected_value,
                    start_date=start_date,
                    end_date=end_date,
                    use_llm=use_llm # добавил чекбокс llm

                )

                if not commits:
                    st.info("No commits found for the selected period")
                else:
                    st.success(f"Found {len(commits)} commits")

                    # Отображаем коммиты
                    for i, commit in enumerate(commits):

                        # Получаем первую строку сообщения коммита
                        message_first_line = (
                            commit["message"].splitlines()[0]
                            if commit["message"]
                            else "No message"
                        )

                        # Используем полученную строку в f-строке
                        with st.expander(f"{message_first_line}"):
                            st.write(f"**Date:** {commit['date']}")
                            st.write(f"**Author:** {commit['author']}")
                            st.write(f"**SHA:** [{commit['sha'][:7]}]({commit['url']})")
                            st.write(f"**Additions:** {commit['stats']['additions']}")
                            st.write(f"**Deletions:** {commit['stats']['deletions']}")
                            st.write(f"**Files changed:** {len(commit['files'])}")

                            if commit["files"]:
                                st.write("**Modified files:**")
                                for file in commit["files"]:
                                    st.write(
                                        f"- {file['filename']} (+{file['additions']}/-{file['deletions']})"
                                    )
                            if use_llm and "llm_summary" in commit:
                                st.markdown(f"🤖 **LLM Summary:** {commit['llm_summary']}")


                    # Добавляем статистику
                    total_additions = sum(
                        commit["stats"]["additions"] for commit in commits
                    )
                    total_deletions = sum(
                        commit["stats"]["deletions"] for commit in commits
                    )
                    total_files = sum(len(commit["files"]) for commit in commits)

                    st.subheader("Summary Statistics")
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Total Commits", len(commits))
                    col2.metric("Lines Added", total_additions)
                    col3.metric("Lines Deleted", total_deletions)
                    col4.metric("Files Changed", total_files)

        else:
            # Новый путь: анализ всех коммитов и генерация финального отчета
            with st.spinner("🔍 Analyzing full commit history..."):
                commits = git_service.get_repository_commits(
                    repo_name=repo_name,
                    developer_username=selected_value,
                    start_date=start_date,
                    end_date=end_date,
                    use_llm=True,
                    full_report=True  # 👈

                )
                if not commits:
                    st.warning("No commits found for the selected developer and date range.")
                else:
                    report = generate_full_quality_report(commits)
                    st.subheader("📋 Full Code Quality Report")
                    st.code(report, language="markdown")
                    # Скачивание отчета
                    st.markdown(
                        get_download_link(
                            report,
                            f"full_code_quality_{selected_value}_{start_date.strftime('%Y%m%d')}.txt",
                            "📥 Download Full Report",
                        ),
                        unsafe_allow_html=True,
                    )

