-- Daily NEAR activity for the requested date range, with lifetime cohort membership.
--
-- Transaction counts and daily active users read only [start_date, end_date). The separate
-- history scan reads only block_date and signer_account_id to establish first activity,
-- previous activity, and complete cohort sizes. For repeated production runs, persist this
-- compact history state instead of rescanning from genesis.
--
-- Definitions:
--   * new_users: first activity on MainNet occurred on this date
--   * old_users: first activity was before this date (includes returning users)
--   * returning_users: old users active today after at least one full inactive day
--   * cohort: users grouped by their first activity date on MainNet
--   * retention_rate: active members of a cohort on a date / full cohort size

WITH activity_window AS (
  SELECT
    block_date AS activity_date,
    signer_account_id AS user_id,
    COUNT(DISTINCT transaction_hash) AS transactions
  FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
  WHERE block_date >= DATE('{{start_date}}')
    AND block_date < DATE('{{end_date}}')
    AND signer_account_id IS NOT NULL
  GROUP BY activity_date, user_id
),
historical_user_days AS (
  SELECT DISTINCT
    block_date AS activity_date,
    signer_account_id AS user_id
  FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
  WHERE block_date >= DATE '2020-04-22'
    AND block_date < DATE('{{end_date}}')
    AND signer_account_id IS NOT NULL
),
user_history AS (
  SELECT
    activity_date,
    user_id,
    MIN(activity_date) OVER (PARTITION BY user_id) AS cohort_date,
    LAG(activity_date) OVER (PARTITION BY user_id ORDER BY activity_date) AS previous_activity_date
  FROM historical_user_days
),
window_with_history AS (
  SELECT
    activity_window.activity_date,
    activity_window.user_id,
    activity_window.transactions,
    user_history.cohort_date,
    user_history.previous_activity_date
  FROM activity_window
  INNER JOIN user_history USING (activity_date, user_id)
),
daily_metrics AS (
  SELECT
    activity_date,
    SUM(transactions) AS transactions,
    COUNT(DISTINCT user_id) AS active_users,
    COUNTIF(cohort_date = activity_date) AS new_users,
    COUNTIF(cohort_date < activity_date) AS old_users,
    COUNTIF(
      cohort_date < activity_date
      AND previous_activity_date < DATE_SUB(activity_date, INTERVAL 1 DAY)
    ) AS returning_users
  FROM window_with_history
  GROUP BY activity_date
),
cohort_sizes AS (
  SELECT
    cohort_date,
    COUNT(DISTINCT user_id) AS cohort_size
  FROM user_history
  WHERE activity_date = cohort_date
  GROUP BY cohort_date
),
cohort_activity AS (
  SELECT
    cohort_date,
    activity_date,
    DATE_DIFF(activity_date, cohort_date, DAY) AS cohort_age_days,
    COUNT(DISTINCT user_id) AS retained_users
  FROM window_with_history
  GROUP BY cohort_date, activity_date, cohort_age_days
)
SELECT
  daily.activity_date,
  daily.transactions,
  daily.active_users,
  daily.new_users,
  daily.old_users,
  daily.returning_users,
  cohort.cohort_date,
  cohort.cohort_age_days,
  sizes.cohort_size,
  cohort.retained_users,
  SAFE_DIVIDE(cohort.retained_users, sizes.cohort_size) AS retention_rate,
  'first_activity_on_mainnet' AS cohort_basis
FROM daily_metrics AS daily
INNER JOIN cohort_activity AS cohort USING (activity_date)
INNER JOIN cohort_sizes AS sizes USING (cohort_date)
ORDER BY daily.activity_date, cohort.cohort_date;
