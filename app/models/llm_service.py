import os
import requests
#import openai
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

YANDEX_API_KEY = os.getenv("YANDEX_GPT_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
#openai.api_key = os.getenv("OPENAI_API_KEY")
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

# def ask_openai(prompt: str, model="gpt-3.5-turbo", temperature=0.3, max_tokens=1200):
#     try:
#         response = openai.ChatCompletion.create(
#             model=model,
#             messages=[
#                 {"role": "system", "content": "You are an experienced senior developer doing code review."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=temperature,
#             max_tokens=max_tokens
#         )
#         return response.choices[0].message.content
#     except Exception as e:
#         print(f"❌ Ошибка OpenAI: {e}")
#         return "⚠️ Ошибка при обращении к OpenAI"

def ask_gemini(prompt: str):
    model = genai.GenerativeModel("gemini-2.5-pro-exp-03-25")  # или gemini-pro

    try:
        response = model.generate_content(
            [{"role": "user", "parts": [prompt]}],
            generation_config={
                "temperature": 0.4,
                "max_output_tokens": 2048
            }
        )
        return response.text
    except Exception as e:
        print(f"❌ Ошибка Gemini: {e}")
        return "⚠️ Ошибка при обращении к Gemini"

def revise_code_review_with_gemini(diff: str, first_review: str, temperature=0.4, max_tokens=2048):
    """
    Проверка и корректировка отчета AI по коду.
    Модель получает оригинальный diff и сгенерированный отчет, после чего:
    - проверяет наличие галлюцинаций,
    - убирает несуществующие элементы,
    - корректирует необоснованные замечания,
    - либо подтверждает корректность.
    """
    prompt = f"""
Ты — опытный ревизор AI-кода.

Тебе переданы два блока:
1. Diff — изменения в коде.
2. Отчет от другой модели, которая провела анализ этих изменений.

Твоя задача — ПЕРЕПРОВЕРИТЬ отчет:
- Найди в отчете замечания, которые НЕ относятся к diff — и УДАЛИ их.
- Если замечания справедливы, перепиши их, усилив аргументацию.
- Не добавляй ничего нового — только ревизия существующего отчета.
- В конце обязательно напиши:
✅ Всё корректно — если всё совпадает  
✏️ Исправлено — если ты внёс правки

Вот Diff:
{diff}

---

Вот Отчет от первой модели:
{first_review}

---
"""
    return ask_gemini(prompt, temperature=temperature, max_tokens=max_tokens)
