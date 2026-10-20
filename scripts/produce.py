import argparse
import csv
import json
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from confluent_kafka import Producer


FLOAT_COLUMNS = ('lat', 'lon', 'merchant_lat', 'merchant_lon')
REQUIRED = {
    'transaction_time', 'merch', 'cat_id', 'amount', 'name_1', 'name_2',
    'gender', 'street', 'one_city', 'us_state', 'post_code', 'lat', 'lon',
    'population_city', 'jobs', 'merchant_lat', 'merchant_lon',
}


def convert(row, filename, number):
    record = dict(row)
    amount = Decimal(row['amount'])
    if not amount.is_finite() or amount != amount.quantize(Decimal('0.01')):
        raise ValueError(f'{filename}:{number}: некорректная сумма')
    record['amount'] = str(amount)
    record['transaction_time'] = datetime.strptime(
        row['transaction_time'], '%Y-%m-%d %H:%M'
    ).strftime('%Y-%m-%d %H:%M:%S')
    for column in FLOAT_COLUMNS:
        record[column] = float(row[column])
    record['population_city'] = int(row['population_city'])
    record['target'] = int(row['target']) if row.get('target') else None
    record['source_file'] = filename
    record['source_row'] = number
    return record


def main():
    parser = argparse.ArgumentParser(description='CSV -> Kafka, одно сообщение на транзакцию')
    parser.add_argument('files', nargs='+', type=Path)
    parser.add_argument('--bootstrap-servers', default=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092'))
    parser.add_argument('--topic', default='transactions')
    args = parser.parse_args()
    if len({p.name for p in args.files}) != len(args.files):
        parser.error('Имена входных файлов должны быть уникальны')
    for path in args.files:
        with path.open(newline='', encoding='utf-8-sig') as f:
            columns = set(next(csv.reader(f)))
            if not REQUIRED <= columns or columns - REQUIRED - {'target'}:
                parser.error(f'Неожиданные колонки в {path}')

    producer = Producer({
        'bootstrap.servers': args.bootstrap_servers,
        'enable.idempotence': True,
        'acks': 'all',
        'compression.type': 'gzip',
        'linger.ms': 20,
        'delivery.timeout.ms': 120000,
    })
    errors = []
    delivered = 0

    def on_delivery(error, message):
        nonlocal delivered
        if error:
            errors.append(str(error))
        else:
            delivered += 1

    total = 0
    for path in args.files:
        number = 0
        with path.open(newline='', encoding='utf-8-sig') as f:
            for number, row in enumerate(csv.DictReader(f), 1):
                record = convert(row, path.name, number)
                payload = json.dumps(record, ensure_ascii=False, allow_nan=False).encode()
                while True:
                    if errors:
                        raise RuntimeError(errors[0])
                    try:
                        producer.produce(args.topic, key=f'{path.name}:{number}',
                                         value=payload, on_delivery=on_delivery)
                        break
                    except BufferError:
                        producer.poll(0.2)
                producer.poll(0)
                total += 1
                if total % 100000 == 0:
                    print(f'Отправлено в очередь: {total:,}')
        print(f'{path.name}: прочитано {number:,} строк')
    remaining = producer.flush(120)
    if remaining or errors or delivered != total:
        raise RuntimeError(f'Доставлено {delivered}/{total}; в очереди {remaining}; ошибки {errors[:3]}')
    print(f'Kafka подтвердила все {delivered:,} сообщений')


if __name__ == '__main__':
    main()
