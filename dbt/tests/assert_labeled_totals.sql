select 1 as mismatch
where
    (select sum(labeled_count) from {{ ref('mart_fraud_by_category') }})
    != (select count(is_fraud) from {{ ref('stg_transactions') }})
    or (select sum(fraud_count) from {{ ref('mart_fraud_by_category') }})
    != (select countIf(is_fraud = 1) from {{ ref('stg_transactions') }})
