select
    merchant,
    count() as transaction_count,
    count(is_fraud) as labeled_count,
    countIf(is_fraud = 1) as fraud_count,
    100.0 * countIf(is_fraud = 1) / nullIf(count(is_fraud), 0) as fraud_rate,
    sum(amount) as turnover,
    avg(amount) as average_amount,
    toUInt8(labeled_count >= 100 and fraud_rate >= 1) as is_suspicious
from {{ ref('stg_transactions') }}
group by merchant
