"""SQL analysis (DuckDB), SARIMA forecast with rolling backtest, charts and key findings.
Run after clean.py. Writes charts/*.png, data/processed/*.csv and data/processed/key_findings.json."""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")  # avoids BLAS thread oversubscription in the many small SARIMA fits
import json, pathlib, warnings
import numpy as np, pandas as pd, duckdb, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mt
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
PROC, CH, SQL = ROOT / "data" / "processed", ROOT / "charts", ROOT / "sql"
CH.mkdir(exist_ok=True)
plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": .3, "font.size": 10})
NAVY, RED, TEAL, GOLD, GREY = "#1f3b73", "#c8102e", "#00857c", "#e3a21a", "#7f7f7f"
PCT = mt.FuncFormatter(lambda x, _: f"{x:g}%")

headline = pd.read_csv(PROC / "headline_monthly.csv", parse_dates=["month"])
division = pd.read_csv(PROC / "division_monthly.csv", parse_dates=["month"], dtype={"division_code": str})
bank_rate = pd.read_csv(PROC / "bank_rate_monthly.csv", parse_dates=["month"])
con = duckdb.connect()
for name, df in {"headline": headline, "division": division, "bank_rate": bank_rate}.items():
    con.register(name, df)
sql = lambda f: con.execute((SQL / f).read_text()).df()
F = {}

# 1. Headline and core trend --------------------------------------------------------
h = headline[headline.month >= "2015-01-01"].reset_index(drop=True)
latest = h.iloc[-1]
peak = h.loc[h.cpi.idxmax()]
core_peak = h.loc[h.core_cpi.idxmax()]
first_above = h.loc[(h.month >= "2021-01-01") & (h.cpi > 2), "month"].min()
after_peak = h[h.month > h.loc[h.cpi.idxmax(), "month"]]
back_at_or_below = after_peak.loc[after_peak.cpi <= 2, "month"].min()
F.update(latest_month=latest.month.strftime("%B %Y"), cpi_latest=latest.cpi, cpih_latest=latest.cpih,
         core_latest=latest.core_cpi, services_latest=latest.services, goods_latest=latest.goods,
         cpi_peak=peak.cpi, cpi_peak_month=peak.month.strftime("%B %Y"),
         core_peak=core_peak.core_cpi, core_peak_month=core_peak.month.strftime("%B %Y"),
         cpih_peak=h.cpih.max(), cpih_peak_month=h.loc[h.cpih.idxmax(), "month"].strftime("%B %Y"),
         first_month_above_target=first_above.strftime("%B %Y"),
         first_month_at_or_below_2_after_peak=back_at_or_below.strftime("%B %Y") if pd.notna(back_at_or_below) else None,
         months_at_or_below_2_since_2021=int((h[h.month >= "2021-01-01"].cpi <= 2).sum()),
         price_level_rise_since_jan2021_pct=round((latest.cpi_index / h.loc[h.month == "2021-01-01", "cpi_index"].iloc[0] - 1) * 100, 1),
         avg_cpi_2015_2019=round(h[h.month.dt.year.between(2015, 2019)].cpi.mean(), 2))

fig, ax = plt.subplots(figsize=(10, 4.6))
ax.plot(h.month, h.cpi, color=NAVY, lw=2.2, label="CPI (headline)")
ax.plot(h.month, h.cpih, color=TEAL, lw=1.3, label="CPIH (incl. owner occupiers' housing)")
ax.plot(h.month, h.core_cpi, color=GOLD, lw=1.8, label="Core CPI (ex energy, food, alcohol & tobacco)")
ax.axhline(2, color=RED, ls="--", lw=1, label="2% inflation target")
ax.annotate(f"Peak {peak.cpi}%\n{peak.month:%b %Y}", (peak.month, peak.cpi), xytext=(30, -10),
            textcoords="offset points", fontsize=8, arrowprops=dict(arrowstyle="-", color=GREY))
ax.yaxis.set_major_formatter(PCT); ax.legend(loc="upper left", fontsize=8)
ax.set(title=f"UK consumer price inflation, Jan 2015 to {latest.month:%b %Y} (12-month rate)")
fig.tight_layout(); fig.savefig(CH / "01_headline_core_cpih.png"); plt.close(fig)

# 2. Contributions by division (SQL) ------------------------------------------------
annual = sql("01_annual_summary.sql"); annual.to_csv(PROC / "annual_summary.csv", index=False)
surge = sql("02_surge_contributions.sql"); surge.to_csv(PROC / "surge_contributions.csv", index=False)
peakc = sql("03_peak_month_contributions.sql"); peakc.to_csv(PROC / "peak_month_contributions.csv", index=False)
latest_div = sql("05_latest_division_rates.sql"); latest_div.to_csv(PROC / "latest_division_rates.csv", index=False)
surge_months = h[(h.month.between("2022-01-01", "2023-12-01")) & (h.cpi >= 7)].month
top3 = surge.head(3)
F.update(surge_start=surge_months.min().strftime("%B %Y"), surge_end=surge_months.max().strftime("%B %Y"),
         surge_months=int(len(surge_months)), surge_avg_cpi=round(h[h.month.isin(surge_months)].cpi.mean(), 2),
         surge_top_divisions=[{"division": r.division, "avg_contribution_pp": r.avg_contribution_pp,
                               "share_pct": r.share_of_cpi_pct} for r in top3.itertuples()],
         surge_top3_share_pct=round(top3.share_of_cpi_pct.sum(), 1),
         peak_top_divisions=[{"division": r.division, "contribution_pp": r.contribution_at_peak_pp,
                              "rate": r.rate_at_peak} for r in peakc.head(3).itertuples()],
         latest_top_divisions=[{"division": r.division, "contribution_pp": r.contribution_pp, "rate": r.annual_rate}
                               for r in latest_div.head(3).itertuples()])

piv = division[division.month >= "2019-01-01"].pivot(index="month", columns="division", values="contribution_pp")
order = surge.division.tolist()
piv = piv[order]
top = order[:6]
plot = piv[top].copy(); plot["All other divisions"] = piv[order[6:]].sum(axis=1)
colors = [NAVY, RED, GOLD, TEAL, "#6a51a3", "#8c564b", "#c7c7c7"]
fig, ax = plt.subplots(figsize=(11, 5))
pos_bottom = np.zeros(len(plot)); neg_bottom = np.zeros(len(plot))
for col, c in zip(plot.columns, colors):
    v = plot[col].fillna(0).values
    b = np.where(v >= 0, pos_bottom, neg_bottom)
    ax.bar(plot.index, v, bottom=b, width=26, color=c, label=col)
    pos_bottom += np.where(v >= 0, v, 0); neg_bottom += np.where(v < 0, v, 0)
hh = h[h.month >= "2019-01-01"]
ax.plot(hh.month, hh.cpi, color="black", lw=1.6, label="CPI annual rate")
ax.yaxis.set_major_formatter(mt.FuncFormatter(lambda x, _: f"{x:.0f}pp"))
ax.set(title="What made up CPI inflation? Contribution of each COICOP division (percentage points)")
ax.legend(fontsize=8, ncol=2, loc="upper left")
fig.tight_layout(); fig.savefig(CH / "02_contributions_stacked.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(9, 5))
s = surge.sort_values("avg_contribution_pp")
ax.barh(s.division, s.avg_contribution_pp, color=[RED if d in top3.division.values else NAVY for d in s.division])
for y, (v, sh) in enumerate(zip(s.avg_contribution_pp, s.share_of_cpi_pct)):
    ax.text(v + .05, y, f"{v:.2f}pp ({sh:.0f}%)", va="center", fontsize=8)
ax.set(title=f"Average contribution to CPI during the surge ({F['surge_start'][:3]} {F['surge_start'][-4:]} to "
             f"{F['surge_end'][:3]} {F['surge_end'][-4:]}, CPI ≥ 7%)", xlabel="Percentage points of the annual rate")
fig.tight_layout(); fig.savefig(CH / "03_surge_drivers.png"); plt.close(fig)

# 3. Food and energy ----------------------------------------------------------------
e = h[h.month >= "2019-01-01"]
food_pk, hen_pk, fuel_pk = e.loc[e.food_nonalc_bev.idxmax()], e.loc[e.household_energy.idxmax()], e.loc[e.motor_fuels.idxmax()]
F.update(food_peak=food_pk.food_nonalc_bev, food_peak_month=food_pk.month.strftime("%B %Y"), food_latest=latest.food_nonalc_bev,
         household_energy_peak=hen_pk.household_energy, household_energy_peak_month=hen_pk.month.strftime("%B %Y"),
         gas_peak=e.gas.max(), electricity_peak=e.electricity.max(),
         motor_fuels_peak=fuel_pk.motor_fuels, motor_fuels_peak_month=fuel_pk.month.strftime("%B %Y"),
         household_energy_latest=latest.household_energy, energy_latest=latest.energy)
fig, ax = plt.subplots(figsize=(10, 4.6))
ax.plot(e.month, e.food_nonalc_bev, color=GOLD, lw=2, label="Food & non-alcoholic beverages")
ax.plot(e.month, e.household_energy, color=RED, lw=2, label="Household energy (electricity, gas, other fuels)")
ax.plot(e.month, e.motor_fuels, color=NAVY, lw=1.5, label="Motor fuels & lubricants")
ax.plot(e.month, e.cpi, color="black", lw=1, ls="--", label="CPI all items")
ax.yaxis.set_major_formatter(PCT); ax.legend(fontsize=8, loc="upper left")
ax.set(title="Food and energy inflation, 12-month rate")
fig.tight_layout(); fig.savefig(CH / "04_food_energy.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(10, 4.2))
ax.plot(h.month, h.goods, color=NAVY, lw=2, label="Goods")
ax.plot(h.month, h.services, color=RED, lw=2, label="Services")
ax.axhline(2, color=GREY, ls="--", lw=1)
ax.yaxis.set_major_formatter(PCT); ax.legend()
ax.set(title="Goods vs services CPI inflation: goods drove the surge, services kept it sticky")
fig.tight_layout(); fig.savefig(CH / "05_goods_vs_services.png"); plt.close(fig)
svc_pk = h.loc[h.services.idxmax()]; gd_pk = h.loc[h.goods.idxmax()]
F.update(goods_peak=gd_pk.goods, goods_peak_month=gd_pk.month.strftime("%B %Y"),
         services_peak=svc_pk.services, services_peak_month=svc_pk.month.strftime("%B %Y"))

# 4. Bank Rate ----------------------------------------------------------------------
real = sql("04_real_bank_rate.sql"); real.to_csv(PROC / "real_bank_rate.csv", index=False)
br_d = pd.read_csv(PROC / "bank_rate_daily.csv", parse_dates=["date"])
changes = br_d[br_d.bank_rate.diff() != 0].iloc[1:]
first_hike = changes[(changes.date >= "2021-01-01") & (changes.bank_rate.diff().fillna(1) > 0)].iloc[0]
br_peak = br_d.bank_rate.max()
br_peak_from = br_d.loc[br_d.bank_rate == br_peak, "date"].min()
first_cut = changes[(changes.date > br_peak_from)].iloc[0]
neg = real[real.month >= "2021-01-01"]
min_real = neg.loc[neg.real_bank_rate.idxmin()]
pos_after = neg[(neg.month > min_real.month) & (neg.positive_real_rate == 1)].month.min()
F.update(bank_rate_latest=float(br_d.bank_rate.iloc[-1]), bank_rate_latest_date=br_d.date.iloc[-1].strftime("%d %B %Y"),
         first_hike_date=first_hike.date.strftime("%d %B %Y"), first_hike_to=float(first_hike.bank_rate),
         bank_rate_peak=float(br_peak), bank_rate_peak_from=br_peak_from.strftime("%d %B %Y"),
         first_cut_date=first_cut.date.strftime("%d %B %Y"), first_cut_to=float(first_cut.bank_rate),
         hikes_in_cycle=int(((changes.date >= "2021-12-01") & (changes.date <= br_peak_from) & (changes.bank_rate.diff() > 0)).sum()),
         min_real_rate=float(min_real.real_bank_rate), min_real_rate_month=min_real.month.strftime("%B %Y"),
         real_rate_positive_from=pos_after.strftime("%B %Y") if pd.notna(pos_after) else None,
         real_rate_latest=float(real.real_bank_rate.iloc[-1]))
fig, ax = plt.subplots(figsize=(10, 4.6))
ax.plot(h.month, h.cpi, color=NAVY, lw=2, label="CPI annual inflation")
bb = br_d[br_d.date >= "2015-01-01"]
ax.step(bb.date, bb.bank_rate, where="post", color=RED, lw=2, label="Bank Rate")
ax.fill_between(real.month, real.real_bank_rate, 0, color=GREY, alpha=.25, label="Real Bank Rate (Bank Rate − CPI)")
ax.axhline(0, color="black", lw=.6)
ax.yaxis.set_major_formatter(PCT); ax.legend(fontsize=8, loc="lower left")
ax.set(title="CPI inflation vs Bank of England Bank Rate")
fig.tight_layout(); fig.savefig(CH / "06_cpi_vs_bank_rate.png"); plt.close(fig)

# 5. SARIMA forecast on the log CPI index with rolling-origin backtest -----------------
idx = headline.set_index("month").cpi_index.dropna()
idx = idx[idx.index >= "2010-01-01"].asfreq("MS")
y = np.log(idx)
ORDER, SORDER, H = (1, 1, 1), (0, 1, 1, 12), 12

def fit(series):
    return SARIMAX(series, order=ORDER, seasonal_order=SORDER).fit(disp=False)

def annual_rate_path(series_log, fc_log):
    full = pd.concat([series_log, fc_log])
    return (np.exp(full - full.shift(12)) - 1)[fc_log.index] * 100

actual_rate = headline.set_index("month").cpi
origins = pd.date_range(y.index[-1] - pd.DateOffset(months=36), y.index[-1] - pd.DateOffset(months=1), freq="MS")
bt = []
for o in origins:
    train = y[:o]
    fc = fit(train).forecast(H)
    rates = annual_rate_path(train, fc)
    naive = actual_rate[o]
    for hz, (m, r) in enumerate(rates.items(), 1):
        if m in actual_rate.index and m <= y.index[-1]:
            bt.append({"origin": o, "horizon": hz, "month": m, "forecast": r, "naive": naive, "actual": actual_rate[m]})
bt = pd.DataFrame(bt)
bt["err_sarima"] = (bt.forecast - bt.actual).abs(); bt["err_naive"] = (bt.naive - bt.actual).abs()
bt.to_csv(PROC / "backtest.csv", index=False)
mae = bt.groupby("horizon")[["err_sarima", "err_naive"]].mean().round(2)
mae.to_csv(PROC / "backtest_mae_by_horizon.csv")

model = fit(y)
fc = model.get_forecast(H)
mean_log, ci = fc.predicted_mean, fc.conf_int(alpha=.2)
fc_rate = annual_rate_path(y, mean_log)
lo_rate = annual_rate_path(y, ci.iloc[:, 0]); hi_rate = annual_rate_path(y, ci.iloc[:, 1])
fcdf = pd.DataFrame({"month": fc_rate.index, "forecast_cpi_rate": fc_rate.round(2).values,
                     "lower_80": lo_rate.round(2).values, "upper_80": hi_rate.round(2).values,
                     "forecast_index": np.exp(mean_log).round(2).values})
fcdf.to_csv(PROC / "forecast.csv", index=False)
F.update(model=f"SARIMA{ORDER}x{SORDER} on log CPI index, fitted Jan 2010 to {y.index[-1]:%b %Y}",
         backtest_origins=f"{origins[0]:%b %Y} to {origins[-1]:%b %Y} ({len(origins)} origins)",
         mae_h1_sarima=float(mae.loc[1, "err_sarima"]), mae_h1_naive=float(mae.loc[1, "err_naive"]),
         mae_h3_sarima=float(mae.loc[3, "err_sarima"]), mae_h3_naive=float(mae.loc[3, "err_naive"]),
         mae_h6_sarima=float(mae.loc[6, "err_sarima"]), mae_h6_naive=float(mae.loc[6, "err_naive"]),
         mae_h12_sarima=float(mae.loc[12, "err_sarima"]) if 12 in mae.index else None,
         mae_h12_naive=float(mae.loc[12, "err_naive"]) if 12 in mae.index else None,
         forecast_month=fcdf.month.iloc[-1].strftime("%B %Y"), forecast_rate=float(fcdf.forecast_cpi_rate.iloc[-1]),
         forecast_lower80=float(fcdf.lower_80.iloc[-1]), forecast_upper80=float(fcdf.upper_80.iloc[-1]),
         forecast_3m_month=fcdf.month.iloc[2].strftime("%B %Y"), forecast_3m_rate=float(fcdf.forecast_cpi_rate.iloc[2]))

hist = h[h.month >= "2021-01-01"]
fig, ax = plt.subplots(figsize=(10, 4.6))
ax.plot(hist.month, hist.cpi, color=NAVY, lw=2, label="Actual CPI annual rate")
ax.plot(fcdf.month, fcdf.forecast_cpi_rate, color=RED, lw=2, ls="--", label="SARIMA forecast")
ax.fill_between(fcdf.month, fcdf.lower_80, fcdf.upper_80, color=RED, alpha=.15, label="80% interval")
ax.axhline(2, color=GREY, ls=":", lw=1)
ax.yaxis.set_major_formatter(PCT); ax.legend(fontsize=8)
ax.set(title=f"CPI inflation forecast to {fcdf.month.iloc[-1]:%b %Y} (SARIMA on log price index)")
fig.tight_layout(); fig.savefig(CH / "07_forecast.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 4.2))
ax.plot(mae.index, mae.err_sarima, marker="o", color=RED, label="SARIMA")
ax.plot(mae.index, mae.err_naive, marker="o", color=GREY, label="Naive (no change in annual rate)")
ax.set(title=f"Backtest: mean absolute error by horizon ({len(origins)} monthly origins)",
       xlabel="Months ahead", ylabel="MAE (percentage points)"); ax.legend()
fig.tight_layout(); fig.savefig(CH / "08_backtest_error.png"); plt.close(fig)

(PROC / "key_findings.json").write_text(json.dumps(F, indent=2, default=str))
print(json.dumps(F, indent=2, default=str))
print("\nSurge contributions:\n", surge.to_string(index=False))
print("\nPeak month:\n", peakc.to_string(index=False))
print("\nLatest:\n", latest_div.to_string(index=False))
print("\nAnnual:\n", annual.to_string(index=False))
print("\nBacktest MAE:\n", mae.to_string())
