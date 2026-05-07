## Описание проекта

Скрипт читает структурированные данные товаров из CSV (Sephora) → отправляет текстовые поля (`product_name`, `highlights`, `ingredients`) в LLM (Gemini через OpenRouter) для определения категорий → объединяет результат с исходником и сохраняет в новый CSV.

**Входные данные (`product_info_100.csv`):**
- `product_name` — Название товара
- `brand_name` — Бренд (уже известен)
- `highlights` — Список характеристик (например: `[\'Fresh Scent\', \'Unisex\']`)
- `ingredients` — Состав товара
- `price_usd` — Цена в USD (уже известна)

**Выходные данные (`output.csv`):**
- Все исходные колонки
- `category` — Общая категория (например: Парфюмерия, Уход за волосами, Уход за кожей, Свечи, Дезодорант)
- `subcategory` — Точный тип товара (например: Eau de Parfum, Travel Spray, Шампунь, Маска)
- `key_features` — Топ-3 ключевых особенности через запятую

## Технический стек
- Python 3.8+
- `requests` — Прямая работа с API OpenRouter
- `pandas` — Обработка таблиц
- `python-dotenv` — Управление ключами

## Особенности реализации
- **Батчевая обработка:** Отправка по 5 товаров за один API-запрос для экономии времени и лимитов.
- **Контекстный промпт:** LLM получает название, характеристики и ингредиенты для точной классификации.
- **Отказоустойчивость:** Автоматический retry при ошибках сети или Rate Limit (429). При полном сбое батча — заполняется `ошибка`.
- **Слияние данных:** Итоговый файл содержит и исходные данные, и результаты классификации.

## Установка и запуск

1. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Создайте файл `.env` в корне проекта:**
   ```
   API_KEY=your_openrouter_api_key_here
   MODEL=google/gemini-2.0-flash-001
   API_URL=https://openrouter.ai/api/v1/chat/completions
   ```

3. **Подготовьте входные данные:**
   - Файл `product_info_100.csv` должен лежать в корне проекта.
   - Формат: колонки `product_name`, `brand_name`, `highlights`, `ingredients`, `price_usd`.

4. **Запустите скрипт:**
   ```bash
   python main.py
   ```

5. **Результат** появится в файле `output.csv`.

## Структура проекта

```
.
├── .env                  # API-ключи (не коммитить!)
├── .gitignore            # Исключения для Git
├── main.py         # Исправленный скрипт
├── product_info_100.csv  # Исходные данные
├── output.csv            # Результат работы
├── requirements.txt      # Зависимости
└── README.md             # Этот файл
```

## Пример данных

**Вход (`product_info_100.csv`):**
```csv
product_name,brand_name,highlights,ingredients,price_usd
"La Habana Eau de Parfum","19-69","[\'Unisex/ Genderless Scent\', \'Layerable Scent\', \'Warm &Spicy Scent\']","[\'Alcohol Denat...\']",195.0
```

**Выход (`output.csv`):**
```csv
product_name,brand_name,highlights,ingredients,price_usd,category,subcategory,key_features
"La Habana Eau de Parfum","19-69","[\'Unisex/ Genderless Scent\', ...]","[\'Alcohol Denat...\']",195.0,"Парфюмерия","Eau de Parfum","Unisex, Layerable, Warm & Spicy"
```

## Ограничения и особенности

- **Кодировка:** Входной и выходной файлы в `utf-8-sig` (с BOM для корректного открытия в Excel).
- **Пустые поля:** Если `highlights` или `ingredients` пустые, LLM классифицирует только по названию.
- **Стоимость API:** ~100 товаров ≈ 20 запросов. Следите за балансом на OpenRouter.
- **Детерминированность:** `temperature=0.1` для стабильных результатов, но категории могут немного варьироваться между запусками.

## Безопасность

- `.env` содержит секреты — **не публикуйте его**.
- При компрометации ключа немедленно отзовите его в [личном кабинете OpenRouter](https://openrouter.ai/keys).
