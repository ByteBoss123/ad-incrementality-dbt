-- Decile segments of the covariate (predicted baseline) for outcome {Y}.
WITH d AS (
  SELECT treatment, y, NTILE(10) OVER (ORDER BY c) AS decile
  FROM `{DATASET}.scored_{Y}`
)
SELECT decile, treatment, COUNT(*) AS n, AVG(y) AS mean_y, VAR_SAMP(y) AS var_y
FROM d
GROUP BY decile, treatment
ORDER BY decile, treatment
