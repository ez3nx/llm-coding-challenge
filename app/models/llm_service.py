import os
import requests
from dotenv import load_dotenv
import google.generativeai as genai
from app.utils.criteria_loader import load_review_criteria

load_dotenv()

YANDEX_API_KEY = os.getenv("YANDEX_GPT_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def ask_qwen(prompt: str, model="qwen/qwen-2.5-coder-32b-instruct", max_tokens=1200, temperature=0.3):
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    url = "https://openrouter.ai/api/v1/chat/completions"
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        print(f"❌ Ошибка OpenRouter: {response.status_code} {response.text}")
        return "⚠️ Ошибка при обращении к OpenRouter"



def ask_yandex_gpt(prompt: str, temperature=0.4, max_tokens=800):
    """Создание итогового отчета (весь текст) через YandexGPT 32k"""
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt/latest",  # или yandexgpt-lite, если не про
        "completionOptions": {
            "stream": False,
            "temperature": temperature,
            "maxTokens": max_tokens
        },
        "messages": [
            {"role": "user", "text": prompt}
        ]
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["result"]["alternatives"][0]["message"]["text"]
    else:
        print(f"❌ Ошибка YandexGPT: {response.status_code} {response.text}")
        return "⚠️ Ошибка при обращении к YandexGPT"


def ask_gemini(prompt: str):
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "google/gemini-2.5-pro-exp-03-25:free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 3072
    }

    url = "https://openrouter.ai/api/v1/chat/completions"
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        print(f"❌ Ошибка OpenRouter: {response.status_code} {response.text}")
        return "⚠️ Ошибка при обращении к OpenRouter"

def revise_code_review_with_gemini(diff: str, first_review: str, temperature=0.3, max_tokens=3072):
    """
    Проверка и корректировка отчета AI по коду.
    Модель получает оригинальный diff и сгенерированный отчет, после чего:
    - проверяет наличие галлюцинаций,
    - убирает несуществующие элементы,
    - корректирует необоснованные замечания,
    - либо подтверждает корректность.
    """
    criteria = load_review_criteria()
    criteria_text = "Вот список критериев для оценки кода:\n\n"
    for section in criteria.get("sections", []):
        criteria_text += f"## {section['title']}\n{section['description']}\n\n"
    prompt = f"""
    Ты — опытный senior-разработчик. Твоя задача — перепроверить отчёт, сгенерированный другой моделью, по diff изменений кода.

    Вот как действовать:

    1. 📌 Если в отчёте есть утверждения, которые не соответствуют **текущему diff** — удали их.
    2. ✏️ Если замечания сформулированы неточно или недостаточно обоснованно — перепиши их с улучшением.
    3. ✅ Если всё корректно и замечания справедливы — подтверди.
    4. ❌ НИКОГДА не добавляй новых пунктов или комментариев — только работа с тем, что уже есть.
    5. 💬 В конце обязательно напиши один из вариантов:
       - `✅ Всё корректно` — если ничего менять не пришлось
       - `✏️ Исправлено` — если ты внёс правки

    ---

    🧩 Структура ответа — Markdown. Используй только следующую структуру:

    ### 📋 Краткое описание изменений
    (Оставь, перепиши или удали — в зависимости от отчёта)

    ### ✅ Best practice
    (Оставь, перепиши или удали)

    ### ⚠️ Проблемы и уязвимости
    (Оставь, перепиши или удали)

    ### 🧩 Паттерны и антипаттерны
    (Оставь, перепиши или удали)

    ### 📊 Итоговая оценка
    (Оставь, перепиши или удали)

    ---

    🎯 Diff:
    {diff}

    ---

    📄 Отчёт от первой модели:
    {first_review}
    """
    return ask_gemini(prompt, temperature=temperature, max_tokens=max_tokens)
