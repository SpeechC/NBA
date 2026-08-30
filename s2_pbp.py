import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
COLS=["GAME_ID","PERIOD","EVENTNUM","PCTIMESTRING","STARTTIME","EVENTMSGTYPE",
      "EVENTMSGACTIONTYPE","PLAYER1_TEAM_ABBREVIATION","SEASON","SEASON_TYPE","GAMEDATE"]
p=pd.read_parquet("/mnt/c/NBA2/out/pbp_lineups_all.parquet",columns=COLS)
p=p[p.SEASON_TYPE.astype(str).str.contains("Regular",na=False)]
for c in ["PERIOD","EVENTNUM","PCTIMESTRING","STARTTIME","EVENTMSGTYPE","EVENTMSGACTIONTYPE"]:
    p[c]=pd.to_numeric(p[c],errors="coerce")
p=p.drop_duplicates(["GAME_ID","EVENTNUM"])
p["tm"]=p.PLAYER1_TEAM_ABBREVIATION
p["is_fga"]=p.EVENTMSGTYPE.isin([1,2])
p["sc"]=p.PCTIMESTRING-p.STARTTIME          # shot-clock elapsed, from the data's own delimiters
f=p[p.is_fga&p.sc.notna()&(p.sc>=0)&(p.sc<=24)]
print(f"FGA with a valid shot-clock elapsed: {len(f):,}")
print("  early-clock share by threshold:")
for c in [4,5,6,7,8,10]:
    print(f"    <= {c:>2}s : {(f.sc<=c).mean():.4f}")
p["trans"]=(p.is_fga&(p.sc>=0)&(p.sc<=7)).astype(int)
p["live_to"]=((p.EVENTMSGTYPE==5)&(p.EVENTMSGACTIONTYPE.isin([1,2]))).astype(int)
p["any_to"]=(p.EVENTMSGTYPE==5).astype(int)
p["fga_ok"]=(p.is_fga&p.sc.notna()).astype(int)
tg=p[p.tm.notna()].groupby(["GAME_ID","tm"]).agg(
    fga=("fga_ok","sum"),trans=("trans","sum"),live=("live_to","sum"),tot=("any_to","sum"))
tg=tg[tg.fga>=40]
tg["trans_share"]=tg.trans/tg.fga
print(f"\nteam-games {len(tg):,}")
print(f"  TRANSITION share  mean {tg.trans_share.mean():.4f} sd {tg.trans_share.std():.4f}"
      f"  p10 {tg.trans_share.quantile(.1):.3f}  p90 {tg.trans_share.quantile(.9):.3f}")
print(f"  LIVE-BALL TO/gm   mean {tg.live.mean():.2f} sd {tg.live.std():.2f}"
      f"  (share of all TO {(tg.live/tg.tot).mean():.3f})")
tg=tg.reset_index()
tg["GAMEDATE"]=tg.GAME_ID.map(p.groupby("GAME_ID").GAMEDATE.first())
tg["SEASON"]=tg.GAME_ID.map(p.groupby("GAME_ID").SEASON.first())
tg.to_csv(SP+"s2_pbp_states.csv",index=False)
print("saved",SP+"s2_pbp_states.csv")
