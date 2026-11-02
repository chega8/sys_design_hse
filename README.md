# ДЗ2. Kafka и ClickHouse

Нужно загрузить транзакции из CSV через Kafka в ClickHouse и найти категорию самой
крупной транзакции в каждом штате. Затем оптимизировать таблицу и сравнить результаты.

Данные: [Kaggle](https://www.kaggle.com/t/1918f3f6435300327d38d6c596f97394).
Используются `train.csv` и `test.csv`, вместе 1 048 575 строк. Файл
`sample_submition.csv` для этой задачи не нужен.

## Как устроено

`produce.py` читает CSV и отправляет строки в топик `transactions` (3 партиции).
ClickHouse читает его через Kafka Engine, а materialized view записывает данные
в таблицу MergeTree.

В test нет `target`, поэтому он записывается как `NULL`. Суммы хранятся в Decimal,
почтовые индексы — строками, чтобы не терять начальные нули.

## Запуск

Нужен Docker с Compose v2. Файлы `train.csv` и `test.csv` нужно положить в `data/`.
На стенде использовалась Colima с 4 CPU и 6 ГБ памяти.

```bash
mkdir -p data results
# Скопировать train.csv и test.csv в data/
docker compose build loader
docker compose up -d --wait
docker compose run --rm --no-deps loader
```

Создание топика и таблиц настроено в Compose. Python-скрипты тоже запускаются
в контейнере. ClickHouse доступен на `localhost:8123`, логин и пароль — `student`.

После загрузки:

```bash
docker compose run --rm --no-deps loader python -m unittest discover -s tests -v
docker compose run --rm --no-deps loader python scripts/verify_export.py /data/train.csv /data/test.csv
```

Проверка ждёт загрузки строк, сверяет их количество и отсутствие дублей по паре
«исходный файл, номер строки». Также она считает ответ отдельно по CSV и сравнивает
его с ClickHouse. Результат запроса сохраняется в
[results/max_transaction_by_state.csv](results/max_transaction_by_state.csv),
проверки — в [results/validation.json](results/validation.json).
На загруженных данных всё совпало: 1 048 575 строк, 51 штат (включая DC).

## Запрос

Запрос находится в `sql/02_max_transaction.sql`:

```sql
SELECT
    us_state,
    argMax(cat_id, tuple(amount, cat_id)) AS category,
    max(amount) AS max_amount
FROM homework.transactions
GROUP BY us_state
ORDER BY us_state
FORMAT CSVWithNames;
```

Здесь ищется именно максимальная отдельная транзакция, а не сумма по категории.
Если суммы одинаковые, выбирается лексикографически наибольшая категория.
`max_amount` оставлен в CSV для проверки. Для пунктов 2 и 3 задания используется
один и тот же запрос.

## Оптимизация

Исходная схема в `sql/00_baseline.sql`: обычные строки, стандартное сжатие,
`ORDER BY tuple()`. В итоговой схеме (`sql/01_schema.sql`) сделаны изменения:

- Для повторяющихся строк, например штатов и категорий, используется `LowCardinality`.
- Добавлены кодеки `ZSTD(1)`, для времени и номера строки — `Delta + ZSTD(1)`.
- Таблица отсортирована по `(us_state, transaction_time)`.
- Добавлена агрегатная проекция `state_max` с максимумами по штатам.

Основное ускорение дала проекция: запрос читает уже посчитанные агрегаты.
Без неё всё равно приходится просматривать все строки, так как фильтра в запросе нет.

Для повторения замеров после загрузки:

```bash
docker compose run --rm --no-deps loader python scripts/benchmark.py
```

Скрипт копирует данные в отдельную baseline-таблицу и объединяет части обеих таблиц
через `OPTIMIZE FINAL`. Для каждого варианта делает два прогрева и семь замеров.
Используется один поток, query cache выключен. Результаты всех вариантов сравниваются.

Замеры на macOS / Apple Silicon, Colima (4 CPU, 6 ГБ), ClickHouse 25.3.3.42:

| Вариант | Медиана времени HTTP, мс | Прочитано строк | Прочитано байт |
|---|---:|---:|---:|
| Исходная таблица | 67.789 | 1 048 575 | 40 396 855 |
| Оптимизированная без проекции | 61.653 | 1 048 575 | 10 485 750 |
| Оптимизированная с проекцией | 2.293 | 51 | 8 781 |

Получилось примерно в 29.6 раза быстрее. Это замеры на прогретых данных локального
стенда; на другой машине время может отличаться. Использование проекции проверяется
через `system.query_log`, план запроса сохранён в `results/explain.txt`.

Размер таблицы уменьшился с 71 783 555 до 45 559 203 байт, то есть примерно на 36.5%.
Проекция занимает 1 233 байта и входит в размер итоговой таблицы.
Все повторы замеров лежат в `results/benchmark.csv`, размеры — в `results/storage.csv`
и `results/projection_storage.csv`.

## Повторный запуск

Остановить контейнеры с сохранением данных:

```bash
docker compose down
```

Повторно запускать producer в тот же топик не нужно: он загрузит данные ещё раз.
При сбоях Kafka Engine тоже возможны дубли, их обнаруживает скрипт проверки.
Для полной перезагрузки нужно удалить оба тома (данные Kafka и ClickHouse):

```bash
docker compose down -v
docker compose up -d --wait
docker compose run --rm --no-deps loader
docker compose run --rm --no-deps loader python scripts/verify_export.py /data/train.csv /data/test.csv
```

Исходные CSV и результаты при этом остаются. Изменения DDL применяются при создании
чистого тома; редактирование `CREATE TABLE IF NOT EXISTS` существующую таблицу не меняет.

Если при сборке возникает ошибка сертификата `CERTIFICATE_VERIFY_FAILED`, можно
передать доверенный PEM bundle:

```bash
CA_CERT_PATH=/absolute/path/to/ca-bundle.pem docker compose \
  -f docker-compose.yml -f docker-compose.ca.yml build loader
```
