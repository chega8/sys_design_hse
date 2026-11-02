select
    concat(source_file, ':', toString(source_row)) as transaction_id,
    transaction_time,
    toDate(transaction_time) as transaction_date,
    {{ dbt_date.day_of_week('transaction_time', isoweek=true) }} as weekday,
    toHour(transaction_time) as transaction_hour,
    upperUTF8(trimBoth(us_state)) as us_state,
    lowerUTF8(trimBoth(cat_id)) as category,
    lowerUTF8(trimBoth(merch)) as merchant,
    {{ dbt_utils.generate_surrogate_key(['name_1', 'name_2', 'street', 'post_code']) }} as customer_id,
    toDecimal64(amount, 2) as amount,
    {{ amount_bucket('amount') }} as amount_bucket,
    target as is_fraud
from {{ source('raw', 'transactions') }}
