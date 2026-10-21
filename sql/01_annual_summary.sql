-- Calendar-year averages of headline, core and CPIH inflation, with the average Bank Rate
SELECT year(h.month) AS year,
       ROUND(AVG(h.cpi), 2)       AS avg_cpi,
       ROUND(AVG(h.core_cpi), 2)  AS avg_core_cpi,
       ROUND(AVG(h.cpih), 2)      AS avg_cpih,
       ROUND(AVG(h.services), 2)  AS avg_services,
       ROUND(AVG(b.bank_rate), 2) AS avg_bank_rate,
       MAX(h.cpi)                 AS max_cpi,
       COUNT(*)                   AS months
FROM headline h
LEFT JOIN bank_rate b ON b.month = h.month
WHERE h.month >= DATE '2015-01-01'
GROUP BY 1
ORDER BY 1;
