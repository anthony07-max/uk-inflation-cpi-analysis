-- Latest month: annual rate and contribution by division, plus change in contribution vs 12 months earlier
WITH latest AS (SELECT MAX(month) AS m FROM division),
cur AS (SELECT d.* FROM division d JOIN latest l ON d.month = l.m),
prev AS (SELECT d.* FROM division d JOIN latest l ON d.month = l.m - INTERVAL 12 MONTH)
SELECT cur.division, cur.annual_rate, ROUND(cur.contribution_pp, 2) AS contribution_pp,
       ROUND(cur.contribution_pp - prev.contribution_pp, 2) AS change_vs_year_ago_pp
FROM cur LEFT JOIN prev USING (division_code)
ORDER BY contribution_pp DESC;
