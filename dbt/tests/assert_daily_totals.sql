select 1 as mismatch
where
    (select sum(transaction_count) from {{ ref('mart_daily_state_metrics') }})
    != (select count() from {{ ref('stg_transactions') }})
    or (select sum(total_amount) from {{ ref('mart_daily_state_metrics') }})
    != (select sum(amount) from {{ ref('stg_transactions') }})
