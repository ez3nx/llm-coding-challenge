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
            # Полный анализ качества кода
            st.session_state.analysis_started = True

            # Шаг 1: Получение MRs разработчика
            with st.status("Fetching developer's merge requests...") as status:
                mrs = git_service.get_developer_mrs(
                    developer_username=selected_value,
                    repo_name=repo_name,
                    start_date=start_date,
                    end_date=end_date,
                )

                if not mrs:
                    status.update(label="No merge requests found", state="error")
                    st.warning(
                        "No merge requests found for the selected developer in the specified period"
                    )
                    st.session_state.analysis_started = False
                else:
                    status.update(
                        label=f"Found {len(mrs)} merge requests", state="complete"
                    )

                    # Шаг 2: Анализ кода в каждом MR
                    with st.status("Analyzing code quality...") as status:
                        all_issues = []

                        # Обработка каждого MR
                        progress_bar = st.progress(0)
                        for i, mr in enumerate(mrs):
                            status.update(
                                label=f"Analyzing MR #{mr['mr_id']}: {mr['title']}"
                            )

                            # Получаем изменения кода из MR
                            code_changes = mr.get("code_changes", [])

                            # Анализируем изменения кода
                            if code_changes:
                                mr_issues = code_analyzer.analyze_code_changes(
                                    code_changes
                                )

                                # Добавляем ID MR к каждой проблеме
                                for issue in mr_issues:
                                    issue["mr_id"] = mr["mr_id"]

                                all_issues.extend(mr_issues)

                            # Обновляем прогресс
                            progress_bar.progress((i + 1) / len(mrs))

                        status.update(
                            label=f"Analysis complete. Found {len(all_issues)} issues.",
                            state="complete",
                        )

                    # Шаг 3: Формирование итогового отчета
                    with st.status("Generating report...") as status:
                        # Получаем общую оценку качества кода
                        quality_summary = (
                            code_analyzer.summarize_developer_code_quality(all_issues)
                        )

                        # Формируем отчет
                        report = report_service.generate_developer_report(
                            developer_info=selected_author_data,
                            mrs_data=mrs,
                            code_issues=all_issues,
                            quality_summary=quality_summary,
                            start_date=datetime.combine(
                                start_date, datetime.min.time()
                            ),
                            end_date=datetime.combine(end_date, datetime.max.time()),
                        )

                        # Генерируем HTML-версию отчета
                        html_report = report_service.generate_html_report(report)

                        status.update(
                            label="Report generated successfully", state="complete"
                        )

                    # Шаг 4: Отображение результатов
                    st.subheader("Code Quality Analysis Results")

                    # Основные метрики
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(
                            "Overall Quality Score", f"{quality_summary['score']}/100"
                        )
                    with col2:
                        st.metric("Total Issues", len(all_issues))
                    with col3:
                        st.metric("Merge Requests Analyzed", len(mrs))

                    # Подробный отчет
                    with st.expander("Detailed Report", expanded=True):
                        # Сильные стороны и области для улучшения
                        col1, col2 = st.columns(2)
                        with col1:
                            st.subheader("Strengths")
                            for strength in quality_summary.get("strengths", []):
                                st.markdown(f"- {strength}")

                        with col2:
                            st.subheader("Areas for Improvement")
                            for area in quality_summary.get("improvement_areas", []):
                                st.markdown(f"- {area}")

                        # Общее резюме
                        st.subheader("Summary")
                        st.write(quality_summary.get("summary", ""))

                        # Статистика по типам проблем
                        st.subheader("Issue Statistics")

                        # Создаем словарь для счетчиков
                        severity_counts = quality_summary.get("issue_counts", {}).get(
                            "by_severity", {}
                        )
                        category_counts = quality_summary.get("issue_counts", {}).get(
                            "by_category", {}
                        )

                        # Отображаем счетчики
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("By Severity:")
                            for severity, count in severity_counts.items():
                                st.write(f"- {severity.capitalize()}: {count}")

                        with col2:
                            st.write("By Category:")
                            for category, count in category_counts.items():
                                st.write(f"- {category.capitalize()}: {count}")

                    # Скачивание отчета
                    st.markdown(
                        get_download_link(
                            html_report,
                            f"code_quality_{selected_value}_{start_date.strftime('%Y%m%d')}.html",
                            "Download Full HTML Report",
                        ),
                        unsafe_allow_html=True,
                    )

                    # Отображаем список MR с проблемами
                    st.subheader("Merge Requests Analysis")
                    for mr in mrs:
                        mr_id = mr.get("mr_id")
                        mr_issues = [
                            issue for issue in all_issues if issue.get("mr_id") == mr_id
                        ]

                        with st.expander(
                            f"MR #{mr_id}: {mr.get('title', '')} - {len(mr_issues)} issues"
                        ):
                            st.write(
                                f"**URL:** [{mr.get('url', '')}]({mr.get('url', '')})"
                            )
                            st.write(f"**Created:** {mr.get('created_at', '')}")
                            st.write(f"**Branch:** {mr.get('branch', '')}")
                            st.write(
                                f"**Changes:** +{mr.get('lines_added', 0)} -{mr.get('lines_removed', 0)} in {mr.get('files_changed', 0)} files"
                            )

                            if mr_issues:
                                st.write("**Issues:**")
                                for issue in mr_issues:
                                    with st.expander(
                                        f"{issue.get('description', 'Issue')} - {issue.get('severity', 'medium').capitalize()}"
                                    ):
                                        st.write(
                                            f"**File:** {issue.get('file_path', '')}"
                                        )
                                        st.write(
                                            f"**Location:** {issue.get('location', '')}"
                                        )
                                        st.write(
                                            f"**Category:** {issue.get('category', 'other').capitalize()}"
                                        )
                                        st.write(
                                            f"**Recommendation:** {issue.get('recommendation', '')}"
                                        )
