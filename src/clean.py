"""Extract the series used in the analysis from the ONS MM23 file and tidy the Bank Rate data.
Writes tidy CSVs to data/processed/."""
import pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

# Headline and analytical series (ONS CDID -> column name)
HEADLINE = {
    "D7G7": "cpi", "L55O": "cpih", "DKO8": "core_cpi", "D7NM": "goods", "D7NN": "services",
    "D7G8": "food_nonalc_bev", "DKL5": "energy", "D7GT": "household_energy",
    "D7I7": "electricity", "D7I8": "gas", "D7IO": "motor_fuels", "D7BT": "cpi_index", "L522": "cpih_index",
}
# CPI COICOP divisions: annual rate CDID, contribution-to-annual-rate CDID
DIVISIONS = [
    ("01", "Food & non-alcoholic beverages", "D7G8", "WUMA"),
    ("02", "Alcohol & tobacco", "D7G9", "WUMB"),
    ("03", "Clothing & footwear", "D7GA", "WUMC"),
    ("04", "Housing & household services", "D7GB", "WUMD"),
    ("05", "Furniture & household goods", "D7GC", "WUMP"),
    ("06", "Health", "D7GD", "WUMQ"),
    ("07", "Transport", "D7GE", "WUMW"),
    ("08", "Communication", "D7GF", "WUMX"),
    ("09", "Recreation & culture", "D7GG", "WUNC"),
    ("10", "Education", "D7GH", "WUND"),
    ("11", "Restaurants & hotels", "D7GI", "WUNE"),
    ("12", "Misc goods & services", "D7GJ", "WUNG"),
]

def load_mm23():
    d = pd.read_csv(RAW / "mm23.csv", header=None, low_memory=False, dtype=str)
    cdids = d.iloc[1].tolist()
    body = d.iloc[7:].copy()
    body.columns = ["period"] + cdids[1:]
    monthly = body[body.period.str.match(r"^\d{4} [A-Z]{3}$", na=False)].copy()
    monthly["month"] = pd.to_datetime(monthly.period, format="%Y %b")
    return monthly.set_index("month").drop(columns="period")

def main():
    mm = load_mm23()
    head = mm[list(HEADLINE)].apply(pd.to_numeric, errors="coerce").rename(columns=HEADLINE)
    head = head[head.index >= "1989-01-01"].dropna(how="all")
    head.reset_index().to_csv(PROC / "headline_monthly.csv", index=False)

    rows = []
    for code, name, rate_id, contrib_id in DIVISIONS:
        s = mm[[rate_id, contrib_id]].apply(pd.to_numeric, errors="coerce").dropna(how="all")
        rows.append(pd.DataFrame({"month": s.index, "division_code": code, "division": name,
                                  "annual_rate": s[rate_id].values, "contribution_pp": s[contrib_id].values}))
    div = pd.concat(rows)
    div = div[div.month >= "2015-01-01"]
    div.to_csv(PROC / "division_monthly.csv", index=False)

    br = pd.read_csv(RAW / "bank_rate.csv")
    br.columns = ["date", "bank_rate"]
    br["date"] = pd.to_datetime(br.date, format="%d %b %Y")
    br.to_csv(PROC / "bank_rate_daily.csv", index=False)
    m = br.set_index("date").bank_rate.resample("MS").last().ffill().rename_axis("month").reset_index()
    m.to_csv(PROC / "bank_rate_monthly.csv", index=False)
    print(f"headline: {len(head)} months ({head.index.min():%b %Y} to {head.index.max():%b %Y}); "
          f"divisions: {len(div)} rows; bank rate: {len(br)} days")

if __name__ == "__main__":
    main()
