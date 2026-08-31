"""pbpstats via cdn.nba.com -- the only reachable liveData host from this machine."""
import pbpstats.data_loader.live.pbp.web as PW
import pbpstats.data_loader.live.boxscore.web as BW
CDN="https://cdn.nba.com/static/json/liveData"
def _patch(mod,kind):
    cls=[v for k,v in mod.__dict__.items() if k.endswith('WebLoader')][0]
    def load_data(self,game_id):
        self.game_id=game_id
        self.url=f"{CDN}/{kind}/{kind}_{game_id}.json"
        self.source_data=self._load_request_data()
        if getattr(self,'file_directory',None) is not None: self._save_data_to_file()
        return self.data
    cls.load_data=load_data
_patch(PW,'playbyplay'); _patch(BW,'boxscore')

# ---------------------------------------------------------------------------
# WHY THIS PATCH EXISTS
#   pbpstats ships three data providers. From this host:
#     stats_nba  -> stats.nba.com returns HTTP 200 with a 2-byte body (blocked)
#     data_nba   -> data.nba.com returns 403 (deprecated endpoint)
#     live       -> nba-prod-...s3.amazonaws.com returns 403
#   Only cdn.nba.com/static/json/liveData is reachable, and it serves the same
#   liveData JSON the `live` provider expects. This repoints that loader.
#
# VALIDATED 2026-08-30 against pbp_lineups_all.parquet on 25 shared 2025 games:
#     per-team possessions   parquet 98.40   pbpstats-via-CDN 100.34   (+1.94)
#     mean possession duration  14.743 s     vs 14.471 s
#   The parquet was built from the stats.nba v2 feed; this pull uses liveData,
#   which carries less event detail. THE TWO ARE NOT INTERCHANGEABLE -- splicing
#   them creates a ~2-possession level shift at the join, larger than the
#   0.86-possession BDB-vs-parquet gap that motivated the pace deep dive.
#
# USAGE
#   import pbps_cdn                      # patch must be imported BEFORE Client
#   from pbpstats.client import Client
#   c = Client({'dir': ..., 'Boxscore': {'source':'web','data_provider':'live'},
#                           'Possessions': {'source':'web','data_provider':'live'}})
#   g = c.Game('0022500001')
#   for p in g.possessions.items:
#       p.possession_start_type   # 'OffAtRimMake', 'OffLiveBallTurnover', ...
#       p.start_time, p.end_time  # 'PT11M17.00S'
#       p.offense_team_id, p.period, p.start_score_margin
#
#   ~0.65 s per game; a full season is ~13 minutes.
