-- CUPED-adjusted lift for outcome {Y}. Covariate c = BigQuery ML prediction from f0..f11.
WITH stats AS (
  SELECT AVG(c) AS mc, COVAR_POP(y, c) / VAR_POP(c) AS theta
  FROM `{DATASET}.scored_{Y}`
),
adj AS (
  SELECT s.treatment, s.y, s.y - st.theta * (s.c - st.mc) AS ystar, st.theta
  FROM `{DATASET}.scored_{Y}` s CROSS JOIN stats st
)
SELECT
  treatment,
  COUNT(*) AS n,
  AVG(y) AS mean_y,
  VAR_SAMP(y) AS var_y,
  AVG(ystar) AS mean_ystar,
  VAR_SAMP(ystar) AS var_ystar,
  ANY_VALUE(theta) AS theta
FROM adj
GROUP BY treatment
ORDER BY treatment
