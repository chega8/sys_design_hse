select
    customer_id,
    count() as transaction_count,
    count(is_fraud) as labeled_count,
    min(transaction_time) as first_transaction,
    max(transaction_time) as last_transaction,
    countIf(is_fraud = 1) as fraud_count,
    100.0 * countIf(is_fraud = 1) / nullIf(count(is_fraud), 0) as fraud_rate,
    avg(amount) as average_amount,
    sum(amount) as total_amount,
    multiIf(labeled_count = 0, 'UNKNOWN', fraud_rate >= 5, 'HIGH', fraud_rate >= 1, 'MEDIUM', 'LOW') as risk_level
from {{ ref('stg_transactions') }}
group by customer_id
