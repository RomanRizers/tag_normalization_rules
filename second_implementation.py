"""
Второй вариант реализации (с использованием расстояния Левенштейна)
Этот модуль содержит функции и классы для обработки тегов,
включая нормализацию тегов, поиск наилучшего совпадения и
применение правил для тегов с учетом синонимов.
"""

import collections
import difflib
from typing import NamedTuple, Optional
from datetime import datetime
from delete_cache import load_cache, save_cache, clean_cache


class AllowedTagRecord(NamedTuple):
    """Запись в таблице правил для допустимых тегов."""
    allowed_name: str
    synonyms: str | None = None
    immutable: bool = False
    separated: bool = False

def normalize_tag(tag: str) -> str:
    """Приводит тег к стандартному формату с нижним регистром и заменяет пробелы и дефисы на нижнее подчеркивание."""
    return tag.replace(" ", "_").replace("-", "_").lower()

def find_best_match(tag: str, allowed_tags_with_synonyms: dict) -> Optional[str]:
    """Находит лучшее совпадение для заданного тега на основе расстояния Левенштейна.
    
    Аргументы:
        tag (str): Тег, для которого нужно найти совпадение.
        allowed_tags_with_synonyms (dict): Словарь разрешенных тегов и синонимов.
    
    Возвращает:
        Optional[str]: Лучшее совпадение для заданного тега, если оно найдено; иначе None.
    """
    normalized_tag = normalize_tag(tag)
    matches = difflib.get_close_matches(normalized_tag, allowed_tags_with_synonyms.keys(), n=1, cutoff=0.6)
    return allowed_tags_with_synonyms.get(matches[0]) if matches else None

def split_composite_tag(tag: str, allowed_tags: dict) -> list:
    """Разделяет составные теги на отдельные части, если это возможно.
    
    Аргументы:
        tag (str): Тег для разделения.
        allowed_tags (dict): Словарь разрешенных тегов.
    
    Возвращает:
        list: Список разрешенных тегов, если они найдены.
    """
    parts = []
    current_part = ""
    for char in tag:
        if char.isupper() and current_part:
            parts.append(current_part)
            current_part = char
        else:
            current_part += char
    if current_part:
        parts.append(current_part)
    return [allowed_tags[normalize_tag(part)] for part in parts if normalize_tag(part) in allowed_tags]

def apply_tag_rules(
    tags: str,
    rules: tuple[AllowedTagRecord, ...],
    delayed_clean: bool = False,
) -> str:
    """Применяет правила для обработки тегов и возвращает нормализованные теги."""
    print(f"\nИсходные теги: {tags}")

    # Загружаем кэш недействительных тегов
    invalid_tags_cache = load_cache()
    clean_cache(invalid_tags_cache)

    # Создаем словарь с нормализованными тегами и синонимами
    allowed_tags = {normalize_tag(record.allowed_name): record.allowed_name for record in rules}
    allowed_tags_with_synonyms = allowed_tags.copy()

    for record in rules:
        if record.synonyms:
            for synonym in record.synonyms.split(', '):
                allowed_tags_with_synonyms[normalize_tag(synonym)] = record.allowed_name

    result_tags = []

    for tag in tags.split(";"):
        tag = tag.strip()
        print(f"Обработка тега '{tag}'")
        # Проверка, если тег существует как полный
        normalized_tag = normalize_tag(tag)
        if normalized_tag in allowed_tags_with_synonyms:
            result_tags.append(allowed_tags_with_synonyms[normalized_tag])
        else:
            split_tags = split_composite_tag(tag, allowed_tags_with_synonyms)
            if split_tags:
                result_tags.extend(split_tags)
            else:
                best_match = find_best_match(tag, allowed_tags_with_synonyms)
                if best_match:
                    result_tags.append(best_match)
                elif delayed_clean:
                    invalid_tags_cache[tag] = datetime.now().isoformat()  # Запоминаем текущее время
                    print(f"Тег '{tag}' добавлен в кэш: не найдено подходящее совпадение.")
                else:
                    print(f"Тег '{tag}' удалён: не найдено подходящее совпадение.")

    if delayed_clean:
        for invalid_tag in list(invalid_tags_cache.keys()):
            if invalid_tag not in result_tags:
                continue
            else:
                print(f"Тег '{invalid_tag}' устарел и удалён из результата.")
                del invalid_tags_cache[invalid_tag]

    save_cache(invalid_tags_cache)
    final_tags = list(collections.OrderedDict.fromkeys(result_tags))

    # Формируем итоговую строку тегов
    final_tags_str = "; ".join(final_tags)
    print(f"Итоговые теги: {final_tags_str}")
    return final_tags_str

if __name__ == "__main__":
    rules = (
        AllowedTagRecord("SRS", immutable=True),
        AllowedTagRecord("web_engine"),
        AllowedTagRecord("sms", "сообщения, messages"),
        AllowedTagRecord("x86", "QEMU, кему"),
        AllowedTagRecord("svc", "Service"),
        AllowedTagRecord("contacts", "контакты"),
        AllowedTagRecord("display", "lcd, дисплей"),
        AllowedTagRecord("AUTO", immutable=True),
        AllowedTagRecord("lock_screen", "экран блокировки"),
    )

    for input_tags, expected_tags in (
        ("WebEngine; AUTO", "web_engine; AUTO"),
        ("экран блокировки; дисплэй", "lock_screen; display"),
        ("КеМу", "x86"),
        ("DisplaySvc", "display; svc"),
        ("SomeTrashTag", ""),
        ("", ""),
        ("unknown-tag; lcd", "display"),
        ("auto", "AUTO"),
    ):
        RESULT = apply_tag_rules(input_tags, rules, delayed_clean=True)
        assert RESULT == expected_tags, f"Failed on {input_tags}: expected '{expected_tags}', got '{RESULT}'"
