"""
Первый вариант реализации (с использованием коэффициента схожести Тэнимото)
Этот модуль содержит функции и классы для обработки тегов,
включая нормализацию тегов, поиск наилучшего совпадения и
применение правил для тегов с учетом синонимов.
"""

from typing import NamedTuple, Optional
import collections
from datetime import datetime
from delete_cache import load_cache, save_cache, clean_cache

class AllowedTagRecord(NamedTuple):
    """Запись в таблице правил."""
    allowed_name: str
    synonyms: str | None = None
    immutable: bool = False
    separated: bool = False

def normalize_tag(tag: str) -> str:
    """Приводит тег к стандартному формату с нижним регистром."""
    return tag.replace(" ", "_").replace("-", "_").lower()

def is_tokens_fuzzy_equal(first_token: str, second_token: str) -> float:
    """Определяет коэффициент схожести Тэнимото между двумя строками.

    Аргументы:
        first_token (str): Первый токен для сравнения.
        second_token (str): Второй токен для сравнения.
    
    Возвращает:
        float: Коэффициент схожести между токенами.
    """
    equal_subtokens_count = 0
    subtoken_length = 1
    used_tokens = [False] * (len(second_token) - subtoken_length + 1)
    for i in range(len(first_token) - subtoken_length + 1):
        subtoken_first = first_token[i:i + subtoken_length]
        for j in range(len(second_token) - subtoken_length + 1):
            if not used_tokens[j]:
                subtoken_second = second_token[j:j + subtoken_length]
                if subtoken_first == subtoken_second:
                    equal_subtokens_count += 1
                    used_tokens[j] = True
                    break

    subtoken_first_count = len(first_token) - subtoken_length + 1
    subtoken_second_count = len(second_token) - subtoken_length + 1

    tanimoto = equal_subtokens_count / (subtoken_first_count + subtoken_second_count - equal_subtokens_count)
    return tanimoto

def find_best_match(tag: str, allowed_tags_with_synonyms: dict) -> Optional[str]:
    """Находит лучшее совпадение для заданного тега на основе коэффициента Тэнимото.

    Аргументы:
        tag (str): Тег, для которого ищем лучшее совпадение.
        allowed_tags_with_synonyms (dict): Словарь допустимых тегов с синонимами.
    
    Возвращает:
        Optional[str]: Лучше совпадающий тег или None, если совпадение не найдено.
    """
    normalized_tag = normalize_tag(tag)
    best_match = None
    best_score = 0.6  # Минимальный порог для совпадения
    print(f"Поиск лучшего совпадения для '{tag}' (нормализованный: '{normalized_tag}'):")
    for allowed_tag in allowed_tags_with_synonyms.keys():
        score = is_tokens_fuzzy_equal(normalized_tag, allowed_tag)
        print(f"  Проверка '{allowed_tag}': коэффициент схожести = {score:.2f}")
        if score > best_score:
            best_score = score
            best_match = allowed_tag

    if best_match:
        print(f"  Найдено лучшее совпадение: '{best_match}' с коэффициентом {best_score:.2f}")
    else:
        print("  Нет подходящего совпадения.")

    return allowed_tags_with_synonyms.get(best_match) if best_match else None

def split_composite_tag(tag: str, allowed_tags: dict) -> list:
    """Разделяет составные теги на отдельные части, если это возможно.

    Аргументы:
        tag (str): Составной тег для разделения.
        allowed_tags (dict): Словарь допустимых тегов.
    
    Возвращает:
        list: Список нормализованных тегов или пустой список, если разбиение невозможно.
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
    # Проверяем части на соответствие разрешённым тегам
    return [allowed_tags[normalize_tag(part)] for part in parts if normalize_tag(part) in allowed_tags]

def apply_tag_rules(
    tags: str,
    rules: tuple[AllowedTagRecord, ...],
    delayed_clean: bool = False
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
        print(f"Обработка тега '{tag}'...")

        # Проверка, если тег существует как полный
        normalized_tag = normalize_tag(tag)
        if normalized_tag in allowed_tags_with_synonyms:
            result_tags.append(allowed_tags_with_synonyms[normalized_tag])
            print(f"Тег найден: '{allowed_tags_with_synonyms[normalized_tag]}'")
        else:
            # Разделение на части и проверка каждой
            split_tags = split_composite_tag(tag, allowed_tags_with_synonyms)
            if split_tags:
                result_tags.extend(split_tags)
                print(f"Найдены составные теги: {split_tags}")
            else:
                # Ищем лучшее совпадение
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
        ("экран блокировки; дисплэй", "lock_screen; display"), # Пропущенный тег display в expected_tags
        ("КеМу", "x86"),
        ("DisplaySvc", "display; svc"),
        ("SomeTrashTag", ""),
        ("", ""),
        ("unknown-tag; lcd", "display"),
        ("auto", "AUTO"),
    ):
        RESULT = apply_tag_rules(input_tags, rules, delayed_clean=True)
        assert RESULT == expected_tags, f"Failed on {input_tags}: expected '{expected_tags}', got '{RESULT}'"
