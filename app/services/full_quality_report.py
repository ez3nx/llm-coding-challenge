def generate_full_quality_report(commits: list) -> str:
    """
    Собирает единый отчет по качеству кода на основе LLM-анализов всех коммитов.
    """
    if not commits:
        return "Нет коммитов для анализа."

    combined_summary = "📋 Full Code Quality Report\n\n"

    for commit in commits:
        sha = commit.get("sha", "???")
        author = commit.get("author", "Unknown")
        date = commit.get("date")
        summary = commit.get("llm_summary", "").strip()

        combined_summary += (
            f"🔹 Commit: {sha} ({date})\n"
            f"👤 Author: {author}\n"
            f"📝 Summary:\n{summary}\n\n"
            + "-" * 40 + "\n\n"
        )

    return combined_summary
