import os
from typing import List, Dict, Any
from datetime import datetime
from github import Github
from typing import Union
from datetime import timedelta


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
        # Преобразование строковых дат в datetime
        if start_date and isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d")

        if end_date and isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        else:
            # Если конечная дата не указана, используем текущую
            end_date = datetime.now()

        # Если начальная дата не указана, используем дату год назад
        if not start_date:
            start_date = end_date - timedelta(days=365)

        print(f"Поиск PR от {developer_username} в репозитории {repo_name}")
        print(f"Период: с {start_date} по {end_date}")

        repo = self.github_client.get_repo(repo_name)

        # Получаем все PR, включая merged и closed
        pull_requests = repo.get_pulls(state="all")

        developer_mrs = []
        for pr in pull_requests:
            # Проверяем, создан ли PR указанным разработчиком
            if pr.user.login != developer_username:
                continue

            # Получаем дату для проверки (или created_at, или merged_at)
            pr_date = pr.merged_at if pr.merged_at else pr.created_at

            # Пропускаем PR без даты (хотя такого быть не должно)
            if not pr_date:
                continue

            # Проверяем, попадает ли PR в указанный временной диапазон
            if (start_date and pr_date < start_date) or (
                end_date and pr_date > end_date
            ):
                continue

            # Собираем данные о PR
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

            # Добавляем изменения кода, если PR не слишком большой
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

            # Получаем репозиторий
            repo = self.github_client.get_repo(repo_name)

            # Словарь для отслеживания уникальных авторов
            # Ключ - email, значение - информация об авторе
            authors_dict = {}

            # Получаем все коммиты (может занять время для больших репозиториев)
            all_commits = repo.get_commits()

            # Счетчик для отображения прогресса
            count = 0

            for commit in all_commits:
                count += 1
                if count % 100 == 0:
                    print(f"Обработано {count} коммитов...")

                # Получаем информацию об авторе коммита
                author_name = commit.commit.author.name
                author_email = commit.commit.author.email

                # Если GitHub пользователь связан с коммитом
                github_user = None
                github_login = None
                if commit.author:
                    github_user = commit.author
                    github_login = github_user.login

                # Добавляем или обновляем информацию об авторе
                key = (
                    author_email.lower()
                )  # Используем email в нижнем регистре как ключ

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
                    # Обновляем существующую запись
                    authors_dict[key]["commit_count"] += 1

                    # Обновляем дату последнего коммита, если текущий коммит новее
                    if (
                        commit.commit.author.date
                        > authors_dict[key]["last_commit_date"]
                    ):
                        authors_dict[key][
                            "last_commit_date"
                        ] = commit.commit.author.date

                    # Обновляем дату первого коммита, если текущий коммит старше
                    if (
                        commit.commit.author.date
                        < authors_dict[key]["first_commit_date"]
                    ):
                        authors_dict[key][
                            "first_commit_date"
                        ] = commit.commit.author.date

                    # Если у нас нет GitHub логина, но он есть в текущем коммите
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
    start_date = None,
    end_date = None,
    load_all_history: bool = False  # Новый параметр
) -> List[Dict[str, Any]]:
        """
        Получает историю коммитов репозитория с возможностью фильтрации
        Args:
            repo_name: Имя репозитория
            developer_username: Имя пользователя разработчика (если нужно фильтровать)
            start_date: Начальная дата периода (None для всей истории, если load_all_history=True)
            end_date: Конечная дата периода (None для текущей даты)
            load_all_history: Если True, загружает всю историю коммитов (игнорирует start_date)
        Returns:
            Список словарей с информацией о коммитах
        """
        import datetime  # Импортируем здесь для избежания проблем с типами
        
        # Если нужна вся история, устанавливаем start_date в None
        if load_all_history:
            start_date = None
            print("Запрошена полная история коммитов")
        else:
            # Преобразование строковых дат в datetime
            if isinstance(start_date, str):
                start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            elif start_date is not None and isinstance(start_date, datetime.date) and not isinstance(start_date, datetime.datetime):
                start_date = datetime.datetime.combine(start_date, datetime.time.min)
            
            # Если начальная дата не указана и не запрошена вся история, используем дату месяц назад
            if start_date is None:
                start_date = datetime.datetime.now() - datetime.timedelta(days=30)
        
        # Обработка конечной даты
        if isinstance(end_date, str):
            end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        elif end_date is not None and isinstance(end_date, datetime.date) and not isinstance(end_date, datetime.datetime):
            end_date = datetime.datetime.combine(end_date, datetime.time.max)
        
        # Если конечная дата не указана, используем текущую
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

        # Получаем все коммиты
        commits = []
        try:
            # Используем author для фильтрации по имени разработчика
            author = developer_username if developer_username else None

            # Получаем коммиты с фильтрацией по автору
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

                # Добавляем информацию об измененных файлах
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

                commits.append(commit_data)

            print(f"Найдено {len(commits)} коммитов")

        except Exception as e:
            print(f"Ошибка при получении коммитов: {e}")

        return commits
