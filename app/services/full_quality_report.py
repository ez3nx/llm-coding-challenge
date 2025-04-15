from app.models.llm_service import ask_yandex_gpt

def generate_full_quality_report(commits: list) -> str:
    """
    Генерирует единый LLM-отчет на основе всех `llm_summary` из коммитов.
    """
    if not commits:
        return "Нет коммитов для анализа."

    summaries = []
    for commit in commits:
        sha = commit.get("sha", "???")
        author = commit.get("author", "Unknown")
        date = commit.get("date")
        summary = commit.get("llm_summary", "").strip()

        if summary:
            summaries.append(f"📦 Commit: {sha} — {author} — {date}\n{summary}")

    combined_prompt = (
        "Ты — аналитик качества кода. Вот сводки по коммитам одного разработчика:\n\n"
        + "\n\n".join(summaries)
        + "\n\n📊 Сформируй единый вывод о его подходе к разработке, сильных/слабых сторонах и общем качестве кода."
    )

    return ask_yandex_gpt(combined_prompt)
