"""BigDataBall team name -> stats.nba.com team_id, plus the GAME_ID join.

Closes the two open items in the schema doc:

  * "GAME-ID | joins to GAME_ID -- verify the format matches"
    Verified: BigDataBall stores the id as an integer with the leading '00'
    league prefix stripped. `str.zfill(10)` restores the stats.nba.com form.
    Confirmed across all 7,752 rows -- every one yields prefix '00', and the
    season-type digit decodes exactly as documented (2 regular, 4 playoff,
    5 play-in).

  * "odds.TEAM_H (name string) --> stats.nba.com team_id [MAPPING TABLE NEEDED]"
    Below. All 30 franchises, no relocations or renames inside the 2017-2025
    window (Brooklyn 2012, New Orleans 2013 and Charlotte 2014 all predate it),
    so a single static table is safe for this project.

The team_id values are from the standard stats.nba.com block (1610612737-66).
They are asserted from reference knowledge, NOT derived from your files --
run `verify()` against a real pbp file before trusting them.
"""

import pandas as pd

# BigDataBall name -> (abbreviation, stats.nba.com team_id)
TEAMS = {
    "Atlanta":       ("ATL", 1610612737),
    "Boston":        ("BOS", 1610612738),
    "Cleveland":     ("CLE", 1610612739),
    "New Orleans":   ("NOP", 1610612740),
    "Chicago":       ("CHI", 1610612741),
    "Dallas":        ("DAL", 1610612742),
    "Denver":        ("DEN", 1610612743),
    "Golden State":  ("GSW", 1610612744),
    "Houston":       ("HOU", 1610612745),
    "LA Clippers":   ("LAC", 1610612746),
    "LA Lakers":     ("LAL", 1610612747),
    "Miami":         ("MIA", 1610612748),
    "Milwaukee":     ("MIL", 1610612749),
    "Minnesota":     ("MIN", 1610612750),
    "Brooklyn":      ("BKN", 1610612751),
    "New York":      ("NYK", 1610612752),
    "Orlando":       ("ORL", 1610612753),
    "Indiana":       ("IND", 1610612754),
    "Philadelphia":  ("PHI", 1610612755),
    "Phoenix":       ("PHX", 1610612756),
    "Portland":      ("POR", 1610612757),
    "Sacramento":    ("SAC", 1610612758),
    "San Antonio":   ("SAS", 1610612759),
    "Oklahoma City": ("OKC", 1610612760),
    "Toronto":       ("TOR", 1610612761),
    "Utah":          ("UTA", 1610612762),
    "Memphis":       ("MEM", 1610612763),
    "Washington":    ("WAS", 1610612764),
    "Detroit":       ("DET", 1610612765),
    "Charlotte":     ("CHA", 1610612766),
}

NAME_TO_ID = {k: v[1] for k, v in TEAMS.items()}
NAME_TO_ABBR = {k: v[0] for k, v in TEAMS.items()}
ID_TO_ABBR = {v[1]: v[0] for v in TEAMS.values()}


def game_id(series):
    """BigDataBall GAME-ID -> stats.nba.com 10-char string. Never store as int."""
    return (series.astype(str)
                  .str.replace(r"\.0$", "", regex=True)
                  .str.zfill(10))


def decode_game_id(gid):
    """0021800764 -> {'league': '00', 'type': 'regular', 'season': '2018-19', ...}"""
    types = {"1": "preseason", "2": "regular", "3": "all-star",
             "4": "playoff", "5": "play-in"}
    yr = int(gid[3:5])
    return {"league": gid[:2], "type": types.get(gid[2], "unknown"),
            "season": f"20{yr:02d}-{yr + 1:02d}", "number": int(gid[5:])}


def verify(pbp_path, sample_games=200):
    """Check the asserted team_ids against a real pbp file.

    Reads distinct (PLAYER1_TEAM_ID, PLAYER1_TEAM_ABBREVIATION) pairs and
    compares them to the table. Any mismatch printed here means the table is
    wrong and must be corrected before it is used as a join key.
    """
    import duckdb
    q = f"""SELECT DISTINCT PLAYER1_TEAM_ID AS tid,
                   PLAYER1_TEAM_ABBREVIATION AS abbr
            FROM read_parquet('{pbp_path}')
            WHERE PLAYER1_TEAM_ID IS NOT NULL"""
    got = duckdb.connect().execute(q).fetchdf()
    got["tid"] = got["tid"].astype("Int64")
    bad, missing = [], []
    for _, r in got.iterrows():
        exp = ID_TO_ABBR.get(int(r["tid"]))
        if exp is None:
            missing.append((int(r["tid"]), r["abbr"]))
        elif exp != r["abbr"]:
            bad.append((int(r["tid"]), r["abbr"], exp))
    print(f"distinct team ids in pbp: {len(got)}")
    if bad:
        print("MISMATCHES (table is wrong):")
        for t, a, e in bad:
            print(f"   {t}: pbp says {a}, table says {e}")
    if missing:
        print("ids in pbp not in table:", missing)
    if not bad and not missing:
        print("all team ids and abbreviations agree with the table")
    return got


if __name__ == "__main__":
    df = pd.DataFrame([(n, a, i) for n, (a, i) in TEAMS.items()],
                      columns=["bigdataball_name", "abbr", "team_id"])
    df.to_csv("team_mapping.csv", index=False)
    print(df.to_string(index=False))
    print("\nwrote team_mapping.csv")
