from app.models.llm_service import ask_yandex_gpt
from datetime import datetime


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

    combined_diff_summary = "\n\n".join(summaries)
    try:
        date_from = datetime.strptime(
            str(commits[-1].get("date")), "%Y-%m-%d %H:%M:%S%z"
        ).date()
        date_to = datetime.strptime(
            str(commits[0].get("date")), "%Y-%m-%d %H:%M:%S%z"
        ).date()
    except Exception:
        # fallback: если формат неожиданен
        date_from = commits[-1].get("date", "")[:10]
        date_to = commits[0].get("date", "")[:10]
    prompt = f"""
    Ты — технический аналитик качества кода. На вход ты получаешь LLM-анализы коммитов разработчика. 
    На их основе тебе нужно построить **структурированный и строго форматированный отчет**, 
    как будто он будет передан руководству или в HR.

    🔻 Структура, по которой нужно формировать финальный отчет (ПИШИ НА РУССКОМ):

    ---

    ### Общая информация:
    - ФИО: Укажи, если есть имя автора, иначе "N/A"
    - Количество обработанных коммитов: {len(commits)}
    - Диапазон коммитов: от {date_from} до {date_to}

    ### Метрики качества кода:
    - Общая оценка качества кода по 10-балльной шкале

    ### Выявленные проблемы:
    Собери и структурируй все найденные замечания из коммитов, используя следующую структуру:
    - Ссылка на MR:
    - Краткое описание MR:
    - Сложность: обязательно одно из значений — Низкая / Средняя / Высокая
    - Проблемы: (если были)
    - Паттерны и антипаттерны: (если есть)
    
    И такая структура на каждый MR
    ---

    ⚠️ Очень важно:
    - Строго следуй структуре
    - Пиши кратко, чётко и по делу
    - Не повторяй один и тот же вывод
    - Не добавляй вводных "по данным ниже"

    Вот анализы коммитов:\n\n{combined_diff_summary}
        """

    return ask_yandex_gpt(prompt)


def get_pdf_download_link(markdown_content, filename, link_text):
    """Создает ссылку для скачивания отчета в формате PDF с улучшенным стилем"""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.lib.colors import HexColor
    import base64, io, os, traceback

    try:
        font_path = os.path.join("fonts", "DejaVuSans.ttf")
        font_name = "DejaVuSans"
        pdfmetrics.registerFont(TTFont(font_name, font_path))

        pdf_bytes = io.BytesIO()
        doc = SimpleDocTemplate(
            pdf_bytes,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=70,
            bottomMargin=50,
        )

        # Стили
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "Title",
            fontName=font_name,
            fontSize=20,
            alignment=TA_CENTER,
            textColor=HexColor("#000000"),
            spaceAfter=20,
            leading=24,
        )

        brand_style = ParagraphStyle(
            "Brand",
            fontName=font_name,
            fontSize=14,
            alignment=TA_LEFT,
            textColor=HexColor("#EF3124"),
            spaceAfter=12,
        )

        normal_style = ParagraphStyle(
            "Normal",
            fontName=font_name,
            fontSize=11,
            leading=16,
            spaceAfter=10,
            alignment=TA_LEFT,
        )

        # Сборка PDF
        elements = []
        elements.append(Paragraph("Альфа Страхование", brand_style))
        elements.append(Paragraph("Отчет об оценке качества кода", title_style))
        elements.append(Spacer(1, 0.3 * inch))

        for para in markdown_content.split("\n\n"):
            clean = para.strip()

            if clean:
                # Удаляем markdown bold и не вставляем html теги
                clean = clean.replace("**", "").replace("__", "")
                elements.append(Paragraph(clean.replace("\n", "<br/>"), normal_style))
                elements.append(Spacer(1, 0.1 * inch))

        doc.build(elements)
        pdf_bytes.seek(0)

        b64 = base64.b64encode(pdf_bytes.read()).decode()
        href = f"""
        <a href="data:application/pdf;base64,{b64}" download="{filename}" 
           style="text-decoration: none; color: #EF3124; font-weight: 500; 
           display: inline-flex; align-items: center; margin-top: 1rem;">
           <span style="margin-right: 5px;">📥</span> {link_text}</a>
        """
        return href

    except Exception:
        return f'<pre style="color:red;">Ошибка при создании PDF:\n{traceback.format_exc()}</pre>'
