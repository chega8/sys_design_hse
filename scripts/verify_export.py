import argparse
import csv
import io
import json
import time
from decimal import Decimal
from pathlib import Path

from common import query


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('files', nargs='+', type=Path)
    parser.add_argument('--timeout', type=int, default=300)
    args = parser.parse_args()
    expected = {}
    counts = {}
    for path in args.files:
        count = 0
        with path.open(newline='', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                count += 1
                value = (Decimal(row['amount']), row['cat_id'])
                state = row['us_state']
                if state not in expected or value > expected[state]:
                    expected[state] = value
        counts[path.name] = count
    total = sum(counts.values())
    deadline = time.monotonic() + args.timeout
    while True:
        loaded = int(query('SELECT count() FROM homework.transactions'))
        if loaded >= total:
            break
        if time.monotonic() > deadline:
            raise TimeoutError(f'ClickHouse получил {loaded} строк из {total}')
        print(f'ClickHouse: {loaded:,}/{total:,}')
        time.sleep(2)
    actual_counts = json.loads(query('''SELECT source_file, count() AS n,
        uniqExact(source_row) AS unique_rows FROM homework.transactions
        GROUP BY source_file FORMAT JSON'''))['data']
    actual = {r['source_file']: int(r['n']) for r in actual_counts}
    if actual != counts or any(int(r['n']) != int(r['unique_rows']) for r in actual_counts):
        raise AssertionError(f'Неполная загрузка или дубликаты: {actual}; ожидалось {counts}')
    sql = Path('sql/02_max_transaction.sql').read_text()
    output = query(sql)
    result = {r['us_state']: (Decimal(r['max_amount']), r['category'])
              for r in csv.DictReader(io.StringIO(output))}
    if result != expected:
        raise AssertionError('Ответ ClickHouse не совпадает с независимым расчётом по CSV')
    # Тот же запрос без проекции должен вернуть в точности тот же CSV.
    if query(sql, optimize_use_projections=0) != output:
        raise AssertionError('Результаты с проекцией и без неё различаются')
    Path('results').mkdir(exist_ok=True)
    Path('results/max_transaction_by_state.csv').write_text(output)
    report = {'source_rows': counts, 'total_rows': total, 'states': len(result),
              'unique_source_rows': True, 'matches_csv_reference': True,
              'matches_without_projection': True,
              'clickhouse_version': query('SELECT version()').strip()}
    Path('results/validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print('Результат сохранён в results/max_transaction_by_state.csv')


if __name__ == '__main__':
    main()
