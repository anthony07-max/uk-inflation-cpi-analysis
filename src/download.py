"""Download public UK inflation and interest-rate data into data/raw/.

Sources
- ONS, Consumer price inflation time series (dataset MM23), full CSV. Open Government Licence v3.0.
  https://www.ons.gov.uk/economy/inflationandpriceindices/datasets/consumerpriceindices
- Bank of England Statistical Interactive Database, Official Bank Rate (series IUDBEDR, daily).
  https://www.bankofengland.co.uk/boeapps/database/
"""
import pathlib, requests

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
FILES = {
    "mm23.csv": "https://www.ons.gov.uk/file?uri=/economy/inflationandpriceindices/datasets/consumerpriceindices/current/mm23.csv",
    "bank_rate.csv": ("https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes"
                      "&Datefrom=01/Jan/2010&Dateto=now&SeriesCodes=IUDBEDR&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N"),
}
HEADERS = {"User-Agent": "Mozilla/5.0 (portfolio project; UK open data)"}

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        print("Downloading", url)
        r = requests.get(url, headers=HEADERS, timeout=180)
        r.raise_for_status()
        (RAW / name).write_bytes(r.content)
        print(f"  saved {name} ({len(r.content)/1e6:.1f} MB)")

if __name__ == "__main__":
    main()
