select
    weekday,
    transaction_hour,
    count() as transaction_count,
    count(is_fraud) as labeled_count,
    countIf(is_fraud = 1) as fraud_count,
    100.0 * countIf(is_fraud = 1) / nullIf(count(is_fraud), 0) as fraud_rate,
    avg(amount) as average_amount
from {{ ref('stg_transactions') }}
group by weekday, transaction_hour
