-- Contributions in the peak month of CPI inflation, compared with two years earlier (pp of the annual rate)
WITH peak AS (SELECT month FROM headline WHERE month >= DATE '2021-01-01' ORDER BY cpi DESC, month LIMIT 1)
SELECT d.division, 
       ROUND(d.contribution_pp, 2)  AS contribution_at_peak_pp,
       d.annual_rate                AS rate_at_peak,
       ROUND(e.contribution_pp, 2)  AS contribution_2y_earlier_pp
FROM division d
JOIN peak p ON d.month = p.month
LEFT JOIN division e ON e.division_code = d.division_code AND e.month = d.month - INTERVAL 24 MONTH
ORDER BY contribution_at_peak_pp DESC;
