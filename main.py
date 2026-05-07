import os
import sys
import json
import time
import requests
import pandas as pd
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

load_dotenv()

API_KEY = os.getenv("API_KEY")
MODEL = os.getenv("MODEL")
API_URL = os.getenv("API_URL")

INPUT_FILE = "product_info_100.csv"
OUTPUT_FILE = "output.csv"

if not API_KEY or not MODEL:
    raise ValueError("Нет API_KEY или MODEL в файле .env")

df = pd.read_csv(INPUT_FILE, sep=",", encoding="utf-8-sig")
total_rows = len(df)

results = []
BATCH_SIZE = 5

print("--- Запуск пайплайна: Анализ товаров ---")

for i in range(0, total_rows, BATCH_SIZE):
    batch = df.iloc[i:i+BATCH_SIZE]
    print(f"Обрабатываю записи с {i+1} по {min(i+BATCH_SIZE, total_rows)} из {total_rows}...")

    # Формируем текст с товарами для отправки в LLM
    items_text = ""
    for _, row in batch.iterrows():
        # Конкатенируем все текстовые поля в одно описание
        highlights = row.get("highlights", "")
        ingredients = row.get("ingredients", "")
        product_name = row.get("product_name", "")
        
        # Очищаем строковые представления списков
        if pd.notna(highlights):
            highlights = str(highlights).strip()
        else:
            highlights = ""
            
        if pd.notna(ingredients):
            ingredients = str(ingredients).strip()
        else:
            ingredients = ""
        
        # ИСПРАВЛЕНО: используем \n вместо \\n и одинарные кавычки
        items_text += f"ID: {row.get('product_name', '')}\nОписание: {product_name}. Характеристики: {highlights}. Ингредиенты: {ingredients}\n---\n"

    # Строгий промпт для нейросети
    prompt = f"""
Извлеки характеристики для каждого товара из списка.

Верни ТОЛЬКО валидный JSON-массив (начинается с [ и заканчивается ]). Без Markdown-разметки.
Формат ответа должен быть строго такой:
[
  {{
    "id": "ID из текста (сохрани как есть, строкой)",
    "category": "Категория товара (например: Парфюмерия, Уход за волосами, Уход за кожей, Свечи, Дезодорант). Определи по названию и характеристикам.",
    "subcategory": "Подкатегория (например: Eau de Parfum, Travel Spray, Маска, Шампунь, Кондиционер, Свеча, Дезодорант, Набор)",
    "key_features": "Главные особенности через запятую (максимум 3)"
  }}
]

Вот товары:
{items_text}
"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 1500
    }

    max_retries = 3
    success = False

    for attempt in range(max_retries):
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=60)

            if response.status_code == 429:
                print(f"  [!] Rate limit, жду 15 сек... (Попытка {attempt+1}/{max_retries})")
                time.sleep(15)
                continue

            if response.status_code != 200:
                print(f"  [!] Ошибка API: {response.status_code} - {response.text}")
                break

            content = response.json()["choices"][0]["message"]["content"].strip()
            
            # Ищем границы JSON
            start = content.find("[")
            end = content.rfind("]")
            
            if start != -1 and end != -1:
                clean_json = content[start:end+1]
            else:
                clean_json = content

            batch_results = json.loads(clean_json)
            
            if isinstance(batch_results, list):
                results.extend(batch_results)
                success = True
                print("  Шикарно!")
                time.sleep(2)
                break
            else:
                raise ValueError("Модель вернула не список (массив).")

        except Exception as e:
            print(f"  [!] Ошибка парсинга или сети: {e}")
            time.sleep(5)
            continue

    # Fallback при неудаче
    if not success:
        print(f"  [!!!] Пропуск батча (строки {i+1}-{min(i+BATCH_SIZE, total_rows)})")
        for _, row in batch.iterrows():
            results.append({
                "id": row.get("product_name", ""),
                "category": "ошибка",
                "subcategory": "ошибка",
                "key_features": "ошибка"
            })

# Создаем датафрейм из результатов
out_df = pd.DataFrame(results)

# Объединяем исходные данные с извлеченными по product_name
final_df = pd.merge(df, out_df, left_on="product_name", right_on="id", how="left")

# Удаляем дублирующуюся колонку id из merge
if "id" in final_df.columns and "id" != "product_name":
    final_df = final_df.drop(columns=["id"])

# Сохраняем в CSV
final_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print(f"\nГотово! Сохранено в {OUTPUT_FILE}")
print(f"Всего обработано записей: {len(final_df)}")
