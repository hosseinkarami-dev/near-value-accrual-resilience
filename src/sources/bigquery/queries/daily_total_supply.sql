SELECT
  block_height,
  block_hash,
  block_timestamp_utc,
  block_date AS utc_date,
  total_supply
FROM `{{table}}`
WHERE block_date >= DATE('{{start_date}}')
  AND block_date < DATE('{{end_date}}')
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY block_date
  ORDER BY block_timestamp_utc DESC, block_height DESC
) = 1
ORDER BY block_date
