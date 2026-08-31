import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import pandas as pd, numpy as np, prepare_data as PD
SC='/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/'
raw=PD.read_master(verbose=False)
n=lambda c: pd.to_numeric(raw[c],errors='coerce'); gid=pd.to_numeric(raw['GAME-ID'],errors='coerce')
d=pd.DataFrame({'gid':gid,'date':pd.to_datetime(raw['DATE'],errors='coerce'),
                'TEAM_H':raw.TEAM_H,'TEAM_R':raw.TEAM_R})
for s in ('H','R'):
    d['fg'+s]=n('FG_'+s); d['fga'+s]=n('FGA_'+s); d['tp'+s]=n('3P_'+s); d['tpa'+s]=n('3PA_'+s)
d=d[(gid//10000000)==2].dropna()
rows=[]
for s,o in (('H','R'),('R','H')):
    rows.append(pd.DataFrame({'date':d.date,'team':d['TEAM_'+s],'opp':d['TEAM_'+o],
        'home':1 if s=='H' else 0,
        'tpm':d['tp'+s],'tpa':d['tpa'+s],
        'twm':d['fg'+s]-d['tp'+s],'twa':d['fga'+s]-d['tpa'+s]}))
L=pd.concat(rows,ignore_index=True)
L['season']=L.date.dt.year.where(L.date.dt.month>=8,L.date.dt.year-1)
L.to_pickle(SC+'shoot.pkl')
print('team-games: %d   seasons %s'%(len(L),sorted(L.season.unique())))
print()
print('LEAGUE BASELINE')
for lab,m,a in (('3P',L.tpm,L.tpa),('2P',L.twm,L.twa)):
    p=m.sum()/a.sum(); print('  %s%%  %.4f   attempts/team-game %.1f'%(lab,p,a.mean()))
print()
def reliability(g,mcol,acol,lab):
    """observed cross-unit sd vs binomial-noise sd -> how much is real"""
    p=g[mcol]/g[acol]
    a=g[acol]
    pbar=g[mcol].sum()/g[acol].sum()
    noise=np.sqrt((pbar*(1-pbar)/a)).mean()
    obs=p.std()
    true=np.sqrt(max(obs**2-noise**2,0))
    rel=true**2/obs**2 if obs>0 else 0
    print('  %-34s n=%3d  obs sd %.4f  binom sd %.4f  TRUE sd %.4f  reliability %.3f'%(
      lab,len(p),obs,noise,true,rel))
    return p
print('TEAM-SEASON SHOOTING, all games')
for lab,mc,ac in (('3P%','tpm','tpa'),('2P%','twm','twa')):
    g=L.groupby(['team','season'])[[mc,ac]].sum()
    reliability(g,mc,ac,lab+' team-season')
print()
print('SPLIT BY VENUE')
for v,vn in ((1,'HOME'),(0,'ROAD')):
    s=L[L.home==v]
    for lab,mc,ac in (('3P%','tpm','tpa'),('2P%','twm','twa')):
        g=s.groupby(['team','season'])[[mc,ac]].sum()
        reliability(g,mc,ac,'%s %s team-season'%(lab,vn))
