-- Real Bank Rate (Bank Rate minus CPI annual inflation), month by month
SELECT h.month, h.cpi, b.bank_rate, ROUND(b.bank_rate - h.cpi, 2) AS real_bank_rate,
       CASE WHEN b.bank_rate - h.cpi > 0 THEN 1 ELSE 0 END AS positive_real_rate
FROM headline h
JOIN bank_rate b ON b.month = h.month
WHERE h.month >= DATE '2015-01-01'
ORDER BY h.month;
