"""
Модуль для управления кэшем недействительных тегов.
Этот модуль предоставляет функции для загрузки, сохранения и очистки кэша недействительных тегов.
"""

import json
import os
from datetime import datetime, timedelta

CACHE_FILE = "invalid_tags_cache.json"
CACHE_EXPIRATION_DAYS = 14

def load_cache() -> dict:
    """Загружает кэш недействительных тегов из файла, если он существует."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as file:
            return json.load(file)
    return {}

def save_cache(invalid_tags: dict) -> None:
    """Сохраняет кэш недействительных тегов в файл."""
    with open(CACHE_FILE, "w") as file:
        json.dump(invalid_tags, file)

def clean_cache(invalid_tags: dict) -> None:
    """Удаляет устаревшие теги из кэша."""
    current_time = datetime.now()
    for tag in list(invalid_tags.keys()):
        if current_time - datetime.fromisoformat(invalid_tags[tag]) > timedelta(days=CACHE_EXPIRATION_DAYS):
            del invalid_tags[tag]
