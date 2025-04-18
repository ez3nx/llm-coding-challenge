import json
import os


def load_review_criteria(json_path: str = None) -> dict:
    """
    Загружает JSON с критериями code review.
    По умолчанию берёт файл из `app/criteria/review_criteria.json`.
    """
    if not json_path:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        json_path = os.path.join(base_dir, "criteria", "review_criteria.json")

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Ошибка при загрузке критериев: {e}")
        return {}
