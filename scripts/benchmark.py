import csv
import json
import statistics
import time
import uuid
from pathlib import Path

from common import query


def main():
    if int(query('SELECT count() FROM homework.transactions')) == 0:
        raise RuntimeError('Сначала загрузите данные')
    query(Path('sql/00_baseline.sql').read_text())
    query('TRUNCATE TABLE homework.transactions_baseline')
    query('INSERT INTO homework.transactions_baseline SELECT * FROM homework.transactions')
    # Только для сопоставимого замера на статическом наборе, не для обычной загрузки.
    for table in ('transactions_baseline', 'transactions'):
        query(f'OPTIMIZE TABLE homework.{table} FINAL')
    sql = Path('sql/02_max_transaction.sql').read_text()
    variants = [
        ('baseline', sql.replace('homework.transactions', 'homework.transactions_baseline'), 0),
        ('optimized_no_projection', sql, 0),
        ('optimized', sql, 1),
    ]
    reference = query(sql)
    records = []
    for name, statement, projection in variants:
        settings = dict(max_threads=1, use_query_cache=0, optimize_use_projections=projection,
                        log_queries=1)
        for _ in range(2):
            assert query(statement, **settings) == reference
        for repeat in range(1, 8):
            query_id = 'hw-' + uuid.uuid4().hex
            start = time.perf_counter()
            result = query(statement, query_id=query_id, **settings)
            elapsed = (time.perf_counter() - start) * 1000
            assert result == reference
            records.append({'variant': name, 'repeat': repeat, 'query_id': query_id,
                            'client_ms': round(elapsed, 3)})
    query('SYSTEM FLUSH LOGS')
    ids = ','.join("'" + r['query_id'] + "'" for r in records)
    logs = json.loads(query(f'''SELECT query_id, query_duration_ms, read_rows, read_bytes,
        memory_usage, projections FROM system.query_log
        WHERE type = 'QueryFinish' AND query_id IN ({ids}) FORMAT JSON'''))['data']
    by_id = {r.pop('query_id'): r for r in logs}
    for record in records:
        record.update(by_id[record['query_id']])
        if record['variant'] == 'optimized' and not record['projections']:
            raise AssertionError('Оптимизатор не использовал проекцию')
        record['projections'] = json.dumps(record['projections'])
    out = Path('results')
    out.mkdir(exist_ok=True)
    with (out / 'benchmark.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(records)
    storage = query('''SELECT table, sum(rows) AS rows, sum(bytes_on_disk) AS bytes_on_disk,
        sum(data_compressed_bytes) AS data_compressed_bytes
        FROM system.parts WHERE active AND database = 'homework'
        AND table IN ('transactions', 'transactions_baseline')
        GROUP BY table ORDER BY table FORMAT CSVWithNames''')
    (out / 'storage.csv').write_text(storage)
    (out / 'projection_storage.csv').write_text(query('''SELECT name, sum(rows) AS rows,
        sum(bytes_on_disk) AS bytes_on_disk FROM system.projection_parts
        WHERE active AND database = 'homework' AND table = 'transactions'
        GROUP BY name FORMAT CSVWithNames'''))
    explain_sql = sql.split('FORMAT')[0]
    (out / 'explain.txt').write_text(query('EXPLAIN indexes = 1 ' + explain_sql))
    for name, _, _ in variants:
        part = [r for r in records if r['variant'] == name]
        print(f"{name}: median client_ms={statistics.median(r['client_ms'] for r in part):.3f}, "
              f"read_rows={part[0]['read_rows']}, read_bytes={part[0]['read_bytes']}")
    print(storage)


if __name__ == '__main__':
    main()
