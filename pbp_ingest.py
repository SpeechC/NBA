"""Memory-safe ingest for large play-by-play CSVs.

Two rules this enforces, both learned the hard way on machines with less RAM than
the naive path wants:

  * never `pd.read_csv()` a multi-GB file directly -- string columns materialise as
    Python objects and peak at roughly twice the final size during parsing;
  * never leave the working copy on /mnt/c -- that is the WSL2 Windows bridge, and
    it is far slower than the native Linux filesystem on every read.

Profiling uses DuckDB, which queries the file on disk without loading it, so you can
inspect a 5 GB CSV in seconds and decide dtypes before committing memory to it.

Usage:
    python pbp_ingest.py profile  /path/to/pbp.csv
    python pbp_ingest.py convert  /path/to/pbp.csv  /home/dpope/data/pbp.parquet
"""

import os
import sys

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

DATA_DIR = "/home/dpope/data"
CHUNK = 500_000

# Tried in order. Real exports routinely defeat the dialect sniffer -- dfMaster_OT
# does, because its header row contains embedded newlines inside quoted fields --
# so fall back to an explicit dialect with strict mode off rather than giving up.
READ_OPTS = [
    "sample_size=-1",
    "delim=',', quote='\"', escape='\"', header=true, strict_mode=false, sample_size=-1",
    "delim=',', quote='\"', escape='\"', header=true, strict_mode=false, "
    "null_padding=true, ignore_errors=true, sample_size=-1",
]


def reader(path):
    """Return a DuckDB table expression that can actually read this file."""
    con = duckdb.connect()
    for opts in READ_OPTS:
        rel = f"read_csv('{path}', {opts})"
        try:
            con.execute(f"SELECT * FROM {rel} LIMIT 1").fetchone()
            return rel
        except Exception:
            continue
    raise RuntimeError(f"could not parse {path} with any known CSV dialect")


def profile(path, sample_rows=200_000):
    """Describe a CSV without loading it: shape, dtypes, cardinality, nulls."""
    con = duckdb.connect()
    rel = reader(path)
    n = con.execute(f"SELECT count(*) FROM {rel}").fetchone()[0]
    cols = con.execute(f"DESCRIBE SELECT * FROM {rel}").fetchdf()
    print(f"rows: {n:,}   columns: {len(cols)}   "
          f"file: {os.path.getsize(path) / 1e9:.2f} GB")
    if os.path.realpath(path).startswith("/mnt/"):
        print("  WARNING: file is on the Windows mount (drvfs). Copy to "
              f"{DATA_DIR} before repeated reads -- it is much slower there.")

    stats = []
    for c, t in zip(cols["column_name"], cols["column_type"]):
        q = (f'SELECT count(DISTINCT "{c}") AS nuniq, '
             f'  sum(CASE WHEN "{c}" IS NULL THEN 1 ELSE 0 END) AS nulls '
             f'FROM (SELECT "{c}" FROM {rel} LIMIT {sample_rows})')
        r = con.execute(q).fetchone()
        stats.append({"column": c, "type": t, "distinct(sample)": r[0],
                      "nulls(sample)": r[1],
                      "categorical?": "yes" if t == "VARCHAR" and r[0] < 5000 else ""})
    import pandas as pd
    print(pd.DataFrame(stats).to_string(index=False))
    return n, cols


def convert(src, dst, chunk=CHUNK):
    """Stream a CSV to Parquet in chunks; low-cardinality strings become dictionaries."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    con = duckdb.connect()
    rel = reader(src)
    # DuckDB streams the conversion itself, so peak memory stays near one row group
    con.execute(f"""
        COPY (SELECT * FROM {rel})
        TO '{dst}' (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE {chunk})
    """)
    a, b = os.path.getsize(src), os.path.getsize(dst)
    pf = pq.ParquetFile(dst)
    print(f"wrote {dst}")
    print(f"  {a / 1e9:.2f} GB -> {b / 1e9:.2f} GB  ({a / b:.1f}x smaller)")
    print(f"  {pf.metadata.num_rows:,} rows, {pf.metadata.num_columns} columns, "
          f"{pf.metadata.num_row_groups} row groups")
    return dst


def scan(parquet, columns=None, where=None):
    """Read only the columns (and rows) you need, straight off disk."""
    con = duckdb.connect()
    cols = ", ".join(f'"{c}"' for c in columns) if columns else "*"
    q = f"SELECT {cols} FROM read_parquet('{parquet}')"
    if where:
        q += f" WHERE {where}"
    return con.execute(q).fetchdf()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "profile":
        profile(sys.argv[2])
    elif cmd == "convert":
        dst = sys.argv[3] if len(sys.argv) > 3 else os.path.join(
            DATA_DIR, os.path.basename(sys.argv[2]).rsplit(".", 1)[0] + ".parquet")
        convert(sys.argv[2], dst)
    else:
        print(__doc__)
