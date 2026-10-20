CREATE DATABASE IF NOT EXISTS homework;

CREATE TABLE IF NOT EXISTS homework.transactions
(
    source_file LowCardinality(String),
    source_row UInt64 CODEC(Delta, ZSTD(1)),
    transaction_time DateTime('UTC') CODEC(Delta, ZSTD(1)),
    merch LowCardinality(String),
    cat_id LowCardinality(String),
    amount Decimal(18, 2) CODEC(ZSTD(1)),
    name_1 String CODEC(ZSTD(1)),
    name_2 String CODEC(ZSTD(1)),
    gender LowCardinality(String),
    street String CODEC(ZSTD(1)),
    one_city LowCardinality(String),
    us_state LowCardinality(String),
    post_code String CODEC(ZSTD(1)),
    lat Float64,
    lon Float64,
    population_city UInt32,
    jobs LowCardinality(String),
    merchant_lat Float64,
    merchant_lon Float64,
    target Nullable(UInt8),
    PROJECTION state_max
    (
        SELECT us_state, argMax(cat_id, tuple(amount, cat_id)), max(amount)
        GROUP BY us_state
    )
)
ENGINE = MergeTree
ORDER BY (us_state, transaction_time);

CREATE TABLE IF NOT EXISTS homework.transactions_kafka
(
    source_file String,
    source_row UInt64,
    transaction_time DateTime('UTC'),
    merch String,
    cat_id String,
    amount Decimal(18, 2),
    name_1 String,
    name_2 String,
    gender String,
    street String,
    one_city String,
    us_state String,
    post_code String,
    lat Float64,
    lon Float64,
    population_city UInt32,
    jobs String,
    merchant_lat Float64,
    merchant_lon Float64,
    target Nullable(UInt8)
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:9092',
    kafka_topic_list = 'transactions',
    kafka_group_name = 'clickhouse-transactions-v1',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 3,
    kafka_thread_per_consumer = 1,
    kafka_flush_interval_ms = 1000;

CREATE MATERIALIZED VIEW IF NOT EXISTS homework.transactions_mv
TO homework.transactions
AS SELECT * FROM homework.transactions_kafka;
