SELECT
    us_state,
    argMax(cat_id, tuple(amount, cat_id)) AS category,
    max(amount) AS max_amount
FROM homework.transactions
GROUP BY us_state
ORDER BY us_state
FORMAT CSVWithNames;
