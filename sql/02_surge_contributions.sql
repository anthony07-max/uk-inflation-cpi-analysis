-- Which COICOP divisions drove the 2022-23 surge?
-- Surge window = every month in 2022-2023 when CPI annual inflation was 7% or higher.
WITH surge AS (
    SELECT month FROM headline
    WHERE month BETWEEN DATE '2022-01-01' AND DATE '2023-12-01' AND cpi >= 7
)
SELECT d.division_code, d.division,
       ROUND(AVG(d.contribution_pp), 2) AS avg_contribution_pp,
       ROUND(100 * AVG(d.contribution_pp) / (SELECT AVG(cpi) FROM headline WHERE month IN (SELECT month FROM surge)), 1)
                                         AS share_of_cpi_pct,
       ROUND(AVG(d.annual_rate), 1)      AS avg_annual_rate,
       ROUND(MAX(d.annual_rate), 1)      AS peak_annual_rate,
       COUNT(*)                          AS months
FROM division d
WHERE d.month IN (SELECT month FROM surge)
GROUP BY 1, 2
ORDER BY avg_contribution_pp DESC;
