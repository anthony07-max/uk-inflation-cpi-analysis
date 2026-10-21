"""Streamlit dashboard: UK consumer price inflation. Run: streamlit run app/streamlit_app.py"""
import json, pathlib
import pandas as pd, plotly.express as px, plotly.graph_objects as go, streamlit as st

P = pathlib.Path(__file__).resolve().parents[1] / "data" / "processed"
st.set_page_config(page_title="UK Inflation (CPI/CPIH)", layout="wide")

@st.cache_data
def load():
    h = pd.read_csv(P / "headline_monthly.csv", parse_dates=["month"])
    d = pd.read_csv(P / "division_monthly.csv", parse_dates=["month"], dtype={"division_code": str})
    b = pd.read_csv(P / "bank_rate_daily.csv", parse_dates=["date"])
    fc = pd.read_csv(P / "forecast.csv", parse_dates=["month"])
    mae = pd.read_csv(P / "backtest_mae_by_horizon.csv")
    surge = pd.read_csv(P / "surge_contributions.csv")
    return h, d, b, fc, mae, surge, json.loads((P / "key_findings.json").read_text())
h, d, b, fc, mae, surge, F = load()

st.title("UK consumer price inflation: CPI, CPIH and the 2022-23 surge")
st.caption(f"ONS MM23 consumer price indices and Bank of England Bank Rate, latest month {F['latest_month']}. "
           "Contains public sector information licensed under the Open Government Licence v3.0. "
           "Built by Anthony Adusei-Poku (github.com/anthony07-max).")
c = st.columns(5)
c[0].metric("CPI", f"{F['cpi_latest']}%", f"peak {F['cpi_peak']}% ({F['cpi_peak_month']})", delta_color="off")
c[1].metric("CPIH", f"{F['cpih_latest']}%")
c[2].metric("Core CPI", f"{F['core_latest']}%", f"peak {F['core_peak']}% ({F['core_peak_month']})", delta_color="off")
c[3].metric("Services CPI", f"{F['services_latest']}%")
c[4].metric("Bank Rate", f"{F['bank_rate_latest']}%", f"real {F['real_rate_latest']:+.2f} pts", delta_color="off")

t1, t2, t3, t4, t5 = st.tabs(["Headline & core", "What drove it", "Food & energy", "Bank Rate", "Forecast"])
LABELS = {"cpi": "CPI", "cpih": "CPIH", "core_cpi": "Core CPI", "goods": "Goods", "services": "Services",
          "food_nonalc_bev": "Food & non-alc. drinks", "energy": "Energy (all)", "household_energy": "Household energy",
          "electricity": "Electricity", "gas": "Gas", "motor_fuels": "Motor fuels"}
with t1:
    start = st.slider("From year", 1989, int(h.month.dt.year.max()), 2015)
    sel = st.multiselect("Series", list(LABELS), default=["cpi", "core_cpi", "cpih"], format_func=LABELS.get)
    hh = h[h.month.dt.year >= start].melt("month", sel, var_name="series", value_name="annual_rate")
    hh["series"] = hh.series.map(LABELS)
    fig = px.line(hh, x="month", y="annual_rate", color="series", labels={"annual_rate": "12-month rate (%)"})
    fig.add_hline(y=2, line_dash="dash", line_color="red", annotation_text="2% target")
    st.plotly_chart(fig, width="stretch")
with t2:
    yr = st.slider("Show from", 2015, int(d.month.dt.year.max()), 2019, key="c")
    dd = d[d.month.dt.year >= yr]
    fig = px.bar(dd, x="month", y="contribution_pp", color="division", labels={"contribution_pp": "Percentage points"},
                 title="Contribution of each COICOP division to the CPI annual rate")
    fig.add_trace(go.Scatter(x=h[h.month.dt.year >= yr].month, y=h[h.month.dt.year >= yr].cpi, name="CPI", line=dict(color="black")))
    fig.update_layout(barmode="relative", height=550)
    st.plotly_chart(fig, width="stretch")
    st.subheader(f"Average contribution during the surge ({F['surge_start']} to {F['surge_end']})")
    st.dataframe(surge, width="stretch", hide_index=True)
    div = st.selectbox("Division detail", sorted(d.division.unique()))
    st.plotly_chart(px.line(d[d.division == div], x="month", y="annual_rate", title=f"{div}: 12-month rate (%)"), width="stretch")
with t3:
    sel = st.multiselect("Series", ["food_nonalc_bev", "household_energy", "electricity", "gas", "motor_fuels", "energy", "cpi"],
                         default=["food_nonalc_bev", "household_energy", "motor_fuels", "cpi"], format_func=LABELS.get, key="fe")
    ee = h[h.month >= "2019-01-01"].melt("month", sel, var_name="series", value_name="annual_rate")
    ee["series"] = ee.series.map(LABELS)
    st.plotly_chart(px.line(ee, x="month", y="annual_rate", color="series"), width="stretch")
with t4:
    bb = b[b.date >= "2015-01-01"]
    fig = go.Figure([go.Scatter(x=h[h.month >= "2015-01-01"].month, y=h[h.month >= "2015-01-01"].cpi, name="CPI annual rate"),
                     go.Scatter(x=bb.date, y=bb.bank_rate, name="Bank Rate", line=dict(shape="hv"))])
    st.plotly_chart(fig, width="stretch")
    st.write(f"Bank Rate rose {F['hikes_in_cycle']} times from {F['first_hike_date']} to a peak of {F['bank_rate_peak']}% "
             f"({F['bank_rate_peak_from']}). The real Bank Rate bottomed at {F['min_real_rate']} points in {F['min_real_rate_month']} "
             f"and turned positive in {F['real_rate_positive_from']}.")
with t5:
    hist = h[h.month >= "2021-01-01"]
    fig = go.Figure([go.Scatter(x=hist.month, y=hist.cpi, name="Actual"),
                     go.Scatter(x=fc.month, y=fc.forecast_cpi_rate, name="SARIMA forecast", line=dict(dash="dash")),
                     go.Scatter(x=list(fc.month) + list(fc.month[::-1]), y=list(fc.upper_80) + list(fc.lower_80[::-1]),
                                fill="toself", opacity=.2, line=dict(width=0), name="80% interval")])
    st.plotly_chart(fig, width="stretch")
    st.write(f"{F['model']}. Rolling backtest over {F['backtest_origins']}: 1-month-ahead MAE {F['mae_h1_sarima']} pts "
             f"(naive {F['mae_h1_naive']}), 12-month-ahead MAE {F['mae_h12_sarima']} pts (naive {F['mae_h12_naive']}).")
    st.plotly_chart(px.line(mae, x="horizon", y=["err_sarima", "err_naive"], markers=True,
                            labels={"value": "MAE (pts)", "horizon": "Months ahead"}), width="stretch")
