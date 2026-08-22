"""Download the official NBA injury-report PDF archive for the panel seasons.

Source pattern (verified live for 2019 and 2022):
  https://ak-static.cms.nba.com/referee/injury/Injury-Report_{YYYY-MM-DD}_{HH}{AM|PM}.pdf

Design:
  - dates = every regular-season game date in the master for seasons 2020+
    (the injury-report policy era that overlaps our panel), PLUS the day
    before each (the mandated ~5PM day-before report).
  - stamps = hourly grid 06AM..11PM plus 12AM (19 probes/date). Reports are
    published at varying hours; probing the grid and keeping the 200s builds
    the intraday sequence the prereg needs.
  - polite: single-threaded, ~0.12s between requests, honest UA.
  - resumable: manifest.csv appends (date, stamp, status, bytes); dates fully
    probed are skipped on rerun. PDFs land in /home/dpope/data/injury_reports/
    (local FS -- thousands of small files are slow on /mnt/c).
  - 2025-26: if a whole season yields zero hits under this naming (a probe
    403'd), it is recorded in the manifest and handled separately.

This script DOWNLOADS ONLY. No parsing, no outcome joins -- PREREG_injury.md
governs everything downstream.
"""
import csv
import os
import time
import urllib.request
import warnings

import pandas as pd

warnings.filterwarnings("ignore")

BASE = ("https://ak-static.cms.nba.com/referee/injury/"
        "Injury-Report_{d}_{s}.pdf")
OUT = "/home/dpope/data/injury_reports"
MAN = os.path.join(OUT, "manifest.csv")
STAMPS = (["12AM"] + [f"{h:02d}AM" for h in range(6, 12)]
          + ["12PM"] + [f"{h:02d}PM" for h in range(1, 12)])
UA = {"User-Agent": "Mozilla/5.0 (research; contact: local)"}
DELAY = 0.12


def game_dates():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    lbl = season_label(raw).astype(str)
    d = raw[lbl.str.contains("Regular Season", na=False)].copy()
    d["yr"] = lbl[lbl.str.contains("Regular Season", na=False)] \
        .str.extract(r"(\d{4})")[0].astype(int)
    d = d[d["yr"] >= 2020]
    dt = pd.to_datetime(d["DATE"], errors="coerce").dropna().dt.normalize()
    days = set(dt) | set(dt - pd.Timedelta(days=1))
    return sorted(x.strftime("%Y-%m-%d") for x in days)


def main():
    os.makedirs(OUT, exist_ok=True)
    done = set()
    if os.path.exists(MAN):
        m = pd.read_csv(MAN)
        done = set(zip(m["date"], m["stamp"]))
        print(f"resuming: {len(done):,} probes already recorded")
    dates = game_dates()
    print(f"{len(dates):,} dates x {len(STAMPS)} stamps = "
          f"{len(dates)*len(STAMPS):,} probes")

    new = hits = 0
    with open(MAN, "a", newline="") as fh:
        w = csv.writer(fh)
        if not done:
            w.writerow(["date", "stamp", "status", "bytes"])
        for d in dates:
            if all((d, s) in done for s in STAMPS):
                continue
            for s in STAMPS:
                if (d, s) in done:
                    continue
                url = BASE.format(d=d, s=s)
                path = os.path.join(OUT, f"Injury-Report_{d}_{s}.pdf")
                try:
                    req = urllib.request.Request(url, headers=UA)
                    with urllib.request.urlopen(req, timeout=25) as r:
                        data = r.read()
                    if data[:4] == b"%PDF":
                        with open(path, "wb") as f:
                            f.write(data)
                        w.writerow([d, s, 200, len(data)])
                        hits += 1
                    else:
                        w.writerow([d, s, "not_pdf", len(data)])
                except urllib.error.HTTPError as e:
                    w.writerow([d, s, e.code, 0])
                except Exception as e:
                    w.writerow([d, s, f"err:{type(e).__name__}", 0])
                new += 1
                if new % 500 == 0:
                    fh.flush()
                    print(f"  {new:,} probes, {hits:,} PDFs", flush=True)
                time.sleep(DELAY)
    print(f"DONE: {new:,} new probes, {hits:,} PDFs saved to {OUT}")
    m = pd.read_csv(MAN)
    m["yr"] = m["date"].str[:4]
    ok = m[m["status"] == "200"] if m["status"].dtype == object else \
        m[m["status"] == 200]
    print("PDFs by calendar year:")
    print(ok.groupby("yr").size().to_string())


if __name__ == "__main__":
    main()
