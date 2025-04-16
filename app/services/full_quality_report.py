import io
# from weasyprint import HTML, CSS
from xhtml2pdf import pisa
from markdown2 import Markdown
import base64

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


def get_pdf_download_link(markdown_content, filename, text):
    """Создает ссылку для скачивания отчета в формате PDF с поддержкой кириллицы"""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_LEFT
    import io
    import base64
    import os
    import tempfile
    from markdown2 import markdown
    import re
    
    # Создаем временный файл для встроенного шрифта
    # Это бинарные данные для Arial Unicode MS или другого шрифта с поддержкой кириллицы
    # В реальном коде здесь будет полный файл шрифта
    
    # Создаем шрифт для кириллицы
    temp_dir = tempfile.mkdtemp()
    font_path = os.path.join(temp_dir, "cyrillic_font.ttf")
    
    # Вместо встроенного шрифта, скачаем его из интернета
    import urllib.request
    
    # Определяем URL для скачивания шрифта DejaVu Sans с поддержкой кириллицы
    font_url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"
    
    try:
        # Скачиваем шрифт
        urllib.request.urlretrieve(font_url, font_path)
        font_name = "DejaVuSans"
        
        # Регистрируем шрифт
        pdfmetrics.registerFont(TTFont(font_name, font_path))
        
        # Создаем PDF
        pdf_bytes = io.BytesIO()
        doc = SimpleDocTemplate(pdf_bytes, pagesize=A4)
        
        # Создаем стили с указанием шрифта
        styles = getSampleStyleSheet()
        normal_style = ParagraphStyle(
            'CustomNormal',
            fontName=font_name,
            fontSize=12,
            leading=14,
            alignment=TA_LEFT
        )
        title_style = ParagraphStyle(
            'CustomTitle',
            fontName=font_name,
            fontSize=18,
            leading=22,
            alignment=TA_LEFT
        )
        
        # Создаем элементы документа
        elements = [
            Paragraph("Code Quality Report", title_style),
            Spacer(1, 0.25*inch)
        ]
        
        # Преобразуем Markdown в HTML для использования в Paragraph
        html_content = markdown(markdown_content)
        
        # Упрощаем HTML для использования в reportlab
        # Удаляем HTML теги, которые не поддерживаются reportlab
        plain_html = re.sub(r'<pre.*?>.*?</pre>', 
                           lambda m: re.sub(r'<.*?>', '', m.group(0)), 
                           html_content, 
                           flags=re.DOTALL)
        plain_html = re.sub(r'<(?!p|b|i|u|br|/p|/b|/i|/u|/br)[^>]*>', '', plain_html)
        
        # Разбиваем текст на абзацы
        for paragraph in plain_html.split('<p>'):
            if paragraph.strip():
                # Очищаем абзац от закрывающих тегов
                clean_paragraph = paragraph.replace('</p>', '')
                
                # Экранируем XML спецсимволы
                safe_text = clean_paragraph.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                
                # Добавляем абзац в документ
                elements.append(Paragraph(safe_text, normal_style))
                elements.append(Spacer(1, 0.1*inch))
        
        # Строим документ
        doc.build(elements)
        pdf_bytes.seek(0)
        
        # Кодируем PDF в base64 для создания ссылки
        b64 = base64.b64encode(pdf_bytes.read()).decode()
        href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}" style="text-decoration: none; color: #EF3124; font-weight: 500; display: inline-flex; align-items: center;"><span style="margin-right: 5px;">📥</span> {text}</a>'
        return href
    
    except Exception as e:
        # В случае ошибки возвращаем сообщение об ошибке
        return f'<p style="color: red;">Ошибка при создании PDF: {str(e)}</p>'
    
    finally:
        # Удаляем временные файлы
        if os.path.exists(font_path):
            os.remove(font_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)