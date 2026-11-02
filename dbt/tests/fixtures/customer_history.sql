select
    customer_id,
    toDateTime('2020-01-01 12:00:00') as transaction_time,
    toDecimal64(10, 2) as amount,
    cast(if(customer_id = 'unknown', null, number = 0 and customer_id != 'low') as Nullable(UInt8)) as is_fraud
from (
    select 'high' as customer_id, number from numbers(20)
    union all
    select 'medium' as customer_id, number from numbers(100)
    union all
    select 'low' as customer_id, 0 as number
    union all
    select 'unknown' as customer_id, 0 as number
)
