-- Incremental source rows for daily activity and cohort aggregation.
-- One row per signer per day; the date predicate enables block_date partition pruning.
SELECT
  block_date AS activity_date,
  signer_account_id AS user_id,
  COUNT(*) AS transaction_count
FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
WHERE block_date >= DATE('{{start_date}}')
  AND block_date < DATE('{{end_date}}')
  AND signer_account_id IS NOT NULL
GROUP BY activity_date, user_id
ORDER BY activity_date, user_id;
