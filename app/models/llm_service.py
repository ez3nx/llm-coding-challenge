import os
import requests
from dotenv import load_dotenv

load_dotenv()

YANDEX_API_KEY = os.getenv("YANDEX_GPT_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def ask_qwen(prompt: str, model="qwen/qwen-2.5-coder-32b-instruct", max_tokens=400, temperature=0.4):
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
