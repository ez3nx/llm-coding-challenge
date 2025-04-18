import os
from typing import List, Dict, Any
from datetime import datetime
from github import Github
from typing import Union
from datetime import timedelta
from dotenv import load_dotenv
from app.models.llm_service import ask_qwen, revise_code_review_with_gemini
from app.utils.criteria_loader import load_review_criteria


from app.services.full_quality_report import (
    generate_full_quality_report,
    get_pdf_download_link,
)

load_dotenv()


class GitService:
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.github_client = Github(self.github_token)

    def get_developer_mrs(
        self,
        developer_username: str,
        repo_name: str,
        start_date: Union[str, datetime, None],
        end_date: Union[str, datetime, None],
    ) -> List[Dict[str, Any]]:
        """
        Получает все MRs разработчика за указанный период
        Args:
            developer_username: Имя пользователя разработчика
            repo_name: Имя репозитория
            start_date: Начальная дата периода (строка 'YYYY-MM-DD' или datetime)
            end_date: Конечная дата периода (строка 'YYYY-MM-DD' или datetime)
        Returns:
            Список словарей с информацией о MRs
        """

        if start_date and isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d")

        if end_date and isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        else:

            end_date = datetime.now()

        if not start_date:
            start_date = end_date - timedelta(days=365)

        print(f"Поиск PR от {developer_username} в репозитории {repo_name}")
        print(f"Период: с {start_date} по {end_date}")

        repo = self.github_client.get_repo(repo_name)

        pull_requests = repo.get_pulls(state="all")

        developer_mrs = []
        for pr in pull_requests:

            if pr.user.login != developer_username:
                continue

            pr_date = pr.merged_at if pr.merged_at else pr.created_at

            if not pr_date:
                continue

            if (start_date and pr_date < start_date) or (
                end_date and pr_date > end_date
            ):
                continue

            mr_data = {
                "mr_id": str(pr.number),
                "title": pr.title,
                "url": pr.html_url,
                "state": pr.state,
                "created_at": pr.created_at,
                "merged_at": pr.merged_at,
                "closed_at": pr.closed_at,
                "branch": pr.head.ref,
                "files_changed": self._count_files_changed(pr),
                "lines_added": pr.additions,
                "lines_removed": pr.deletions,
                "is_merged": pr.merged,
                "commits": pr.commits,
            }

            if pr.changed_files <= 50:  # Ограничиваем для производительности
                mr_data["code_changes"] = self._get_code_changes(pr)
            else:
                mr_data["code_changes"] = []
                mr_data["skipped_code_changes"] = True

            developer_mrs.append(mr_data)

        print(f"Найдено {len(developer_mrs)} PR от разработчика {developer_username}")
        return developer_mrs

    def get_all_commit_authors(self, repo_name: str) -> List[Dict[str, Any]]:
        """
        Получает список всех авторов коммитов в репозитории

        Args:
            repo_name: Имя репозитория в формате "владелец/репозиторий"

        Returns:
            Список словарей с информацией об авторах
        """
        try:
            print(f"Получение списка авторов коммитов для репозитория {repo_name}")

            repo = self.github_client.get_repo(repo_name)

            authors_dict = {}

            all_commits = repo.get_commits()

            count = 0

            for commit in all_commits:
                count += 1
                if count % 100 == 0:
                    print(f"Обработано {count} коммитов...")

                author_name = commit.commit.author.name
                author_email = commit.commit.author.email

                github_user = None
                github_login = None
                if commit.author:
                    github_user = commit.author
                    github_login = github_user.login

                key = author_email.lower()

                if key not in authors_dict:
                    authors_dict[key] = {
                        "name": author_name,
                        "email": author_email,
                        "github_login": github_login,
                        "commit_count": 1,
                        "first_commit_date": commit.commit.author.date,
                        "last_commit_date": commit.commit.author.date,
                    }
                else:
                    authors_dict[key]["commit_count"] += 1

                    if (
                        commit.commit.author.date
                        > authors_dict[key]["last_commit_date"]
                    ):
                        authors_dict[key][
                            "last_commit_date"
                        ] = commit.commit.author.date

                    if (
                        commit.commit.author.date
                        < authors_dict[key]["first_commit_date"]
                    ):
                        authors_dict[key][
                            "first_commit_date"
                        ] = commit.commit.author.date

                    if not authors_dict[key]["github_login"] and github_login:
                        authors_dict[key]["github_login"] = github_login

            # Преобразуем словарь в список и сортируем по количеству коммитов
            authors_list = list(authors_dict.values())
            authors_list.sort(key=lambda x: x["commit_count"], reverse=True)

            print(f"Найдено {len(authors_list)} уникальных авторов")
            return authors_list

        except Exception as e:
            print(f"Ошибка при получении авторов коммитов: {e}")
            return []

    def _count_files_changed(self, pull_request) -> int:
        """Подсчитывает количество измененных файлов в PR"""
        return pull_request.changed_files

    def _get_code_changes(self, pull_request) -> List[Dict[str, Any]]:
        """
        Извлекает изменения кода из PR
        Returns:
            Список изменений с информацией о файле, добавленных/удаленных строках и патче
        """
        changes = []
        try:
            files = pull_request.get_files()
            for file in files:
                # Пропускаем бинарные файлы и файлы, которые не содержат кода
                if self._is_code_file(file.filename):
                    change = {
                        "filename": file.filename,
                        "status": file.status,
                        "additions": file.additions,
                        "deletions": file.deletions,
                        "patch": (
                            file.patch if hasattr(file, "patch") and file.patch else ""
                        ),
                        "raw_url": file.raw_url if hasattr(file, "raw_url") else "",
                    }
                    changes.append(change)
        except Exception as e:
            print(f"Ошибка при получении изменений кода: {e}")
        return changes

    def _is_code_file(self, filename: str) -> bool:
        """Проверяет, является ли файл кодовым (не бинарным, не конфигом и т.д.)"""
        code_extensions = [
            ".py",
            ".js",
            ".ts",
            ".java",
            ".c",
            ".cpp",
            ".cs",
            ".go",
            ".rb",
            ".php",
            ".swift",
            ".kt",
            ".rs",
            ".scala",
            ".sh",
            ".html",
            ".css",
            ".sql",
            ".jsx",
            ".tsx",
            ".vue",
            ".xml",
            ".json",
            ".yml",
            ".yaml",
        ]
        _, ext = os.path.splitext(filename)
        return ext.lower() in code_extensions

    def get_repository_commits(
        self,
        repo_name: str,
        developer_username: str = None,
        start_date=None,
        end_date=None,
        load_all_history: bool = False,
        use_llm: bool = True,  # 👈 добавили флаг
        full_report: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Получает историю коммитов репозитория с возможностью фильтрации и LLM-анализом.
        """
        import datetime

        if load_all_history:
            start_date = None
            print("Запрошена полная история коммитов")
        else:
            if isinstance(start_date, str):
                start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            elif (
                start_date
                and isinstance(start_date, datetime.date)
                and not isinstance(start_date, datetime.datetime)
            ):
                start_date = datetime.datetime.combine(start_date, datetime.time.min)

            if start_date is None:
                start_date = datetime.datetime.now() - datetime.timedelta(days=30)

        if isinstance(end_date, str):
            end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        elif (
            end_date
            and isinstance(end_date, datetime.date)
            and not isinstance(end_date, datetime.datetime)
        ):
            end_date = datetime.datetime.combine(end_date, datetime.time.max)

        if end_date is None:
            end_date = datetime.datetime.now()

        print(f"Поиск коммитов в репозитории {repo_name}")
        if developer_username:
            print(f"Автор: {developer_username}")

        if start_date:
            print(f"Период: с {start_date} по {end_date}")
        else:
            print(f"Период: вся история по {end_date}")

        repo = self.github_client.get_repo(repo_name)

        commits = []
        try:
            author = developer_username if developer_username else None
            all_commits = repo.get_commits(
                author=author, since=start_date, until=end_date
            )

            for commit in all_commits:
                commit_data = {
                    "sha": commit.sha,
                    "message": commit.commit.message,
                    "author": commit.commit.author.name,
                    "author_email": commit.commit.author.email,
                    "date": commit.commit.author.date,
                    "url": commit.html_url,
                    "stats": {
                        "additions": commit.stats.additions,
                        "deletions": commit.stats.deletions,
                        "total": commit.stats.total,
                    },
                    "files": [],
                }
                # Изменённые файлы
                for file in commit.files:
                    file_data = {
                        "filename": file.filename,
                        "status": file.status,
                        "additions": file.additions,
                        "deletions": file.deletions,
                        "changes": file.changes,
                    }
                    if hasattr(file, "patch") and file.patch:
                        file_data["patch"] = file.patch
                    commit_data["files"].append(file_data)

                # Добавляем LLM-анализа, если включён
                if use_llm:

                    def extract_attr(file, key, default=""):
                        if isinstance(file, dict):
                            return file.get(key, default)
                        return getattr(file, key, default)

                    try:
                        file_patches = "\n\n".join(
                            f"--- {extract_attr(file, 'filename')} ---\n{extract_attr(file, 'patch')}"
                            for file in commit_data["files"]
                            if extract_attr(file, "patch")
                        )

                        criteria = load_review_criteria()
                        criteria_text = "Вот список критериев для оценки кода:\n\n"
                        for section in criteria.get("sections", []):
                            criteria_text += (
                                f"## {section['title']}\n{section['description']}\n\n"
                            )

                        prompt = f"""
                        Ты — опытный senior-разработчик на Java, Python и PHP с большим опытом code review. 
                        Проанализируй следующий diff кода и предоставь объективный, сбалансированный анализ на русском языке.

                        🔹 Твоя цель — честно и справедливо оценить качество изменений:
                        - Не придирайся к незначительным недочётам, если они не влияют на стабильность, читаемость или поддержку кода.
                        - Не анализируй код вне представленного diff — только то, что действительно изменилось.
                        - Не указывай "отсутствие логирования", "нет комментариев" и другие общие замечания, если это не нарушает текущий контекст diff.
                        - Если изменений немного, сосредоточься только на реальных ошибках или улучшениях.

                        🔹 Оцени по следующим критериям:

                        {criteria_text}

                        🔹 Структурируй ответ в Markdown строго по этому шаблону:

                        ### 📋 Краткое описание изменений 
                        Кратко опиши суть изменений (2–4 предложения).

                        ### ✅ Best practice
                        - Укажи, какие хорошие практики были соблюдены.

                        ### ⚠️ Уязвимости
                        - Перечисли только реальные проблемы и уязвимости.
                        - Не указывай надуманные или гипотетические замечания.
                        - Не оцени "отсутствие логирования" или "магические строки", если их нет в diff.

                        ### 🧩 Паттерны и антипаттерны
                        - Укажи применённые паттерны, если они действительно присутствуют.
                        - Не выдумывай антипаттерны, если их нет.

                        ### 📊 Итоговая оценка
                        - Объективно оцени качество изменений по шкале от 0 до 10.
                        - Оценка 9-10 - отлично, 7-8 - хорошо
                        - Не снижай оценку, если изменения мелкие и не вносят новых проблем.
                            
                        diff для анализа кода:
                        {file_patches}
                        """

                        raw_review = ask_qwen(prompt)
                        try:
                            revised_review = revise_code_review_with_gemini(
                                diff=file_patches, first_review=raw_review
                            )

                            commit_data["llm_summary"] = revised_review
                            commit_data["llm_summary_raw"] = raw_review

                        except Exception as e:
                            print(f"[Ошибка ревизора Gemini]: {e}")

                            commit_data["llm_summary"] = raw_review

                    except Exception as e:
                        commit_data["llm_summary"] = f"[Ошибка LLM]: {e}"

                commits.append(commit_data)

            print(f"Найдено {len(commits)} коммитов")
            if full_report:
                report = generate_full_quality_report(commits)
                print(report)

                pdf_link = get_pdf_download_link(
                    markdown_content=report,
                    filename=f"code_quality_{developer_username}.pdf",
                    link_text="📥 Скачать Альфа-отчет",
                )

        except Exception as e:
            print(f"Ошибка при получении коммитов: {e}")

        return commits
