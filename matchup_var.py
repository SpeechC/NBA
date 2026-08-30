import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings('ignore')
from scipy import stats
from prepare_data import read_master, season_label
raw=read_master(verbose=False); raw['season']=season_label(raw).astype(str)
d=raw[raw.season.str.contains('Regular Season',na=False)].copy()
n=lambda c: pd.to_numeric(raw[c],errors='coerce')
d['ph']=n('PTS_H'); d['pr']=n('PTS_R'); d['close']=n('CLOSING TOTAL_H')
d=d.dropna(subset=['ph','pr','close']); d=d[d.close.between(150,300)]
d['total']=d.ph+d.pr; d['dev']=d.total-d.close
d['yr']=d.season.str.extract(r'(\d{4})').astype(int)
d=d.reset_index(drop=True); d['gi']=d.index

# ---- leave-one-out team-season sd of OWN points (no circularity) ----
L=pd.concat([d[['gi','yr','TEAM_H','ph']].rename(columns={'TEAM_H':'team','ph':'pts'}),
             d[['gi','yr','TEAM_R','pr']].rename(columns={'TEAM_R':'team','pr':'pts'})])
agg=L.groupby(['team','yr']).pts.agg(N='count',S='sum',Q=lambda s:(s**2).sum())
L=L.join(agg,on=['team','yr'])
L=L[L.N>=40]
Np,Sp,Qp=L.N-1,L.S-L.pts,L.Q-L.pts**2
L['loo_sd']=np.sqrt(((Qp-Sp**2/Np)/(Np-1)).clip(lower=1))
# z within season
L['z']=L.groupby('yr').loo_sd.transform(lambda s:(s-s.mean())/s.std())
w=L.pivot_table(index='gi',columns=None,values=['loo_sd','z'],aggfunc=list)
p=L.groupby('gi').agg(sd1=('loo_sd','min'),sd2=('loo_sd','max'),
                      zmin=('z','min'),zmax=('z','max'),zsum=('z','sum'),k=('z','size'))
p=p[p.k==2]
m=d.set_index('gi').join(p,how='inner')
print(f'matchup panel n = {len(m):,}\n')

# ---- POWER, priced BEFORE the test ----
ss=L.groupby('yr').loo_sd.agg(['mean','std','count'])
obs_sd=L.groupby(['team','yr']).loo_sd.first().std()
med_n=agg.N.median(); med_sd=L.loo_sd.median()
noise=med_sd/np.sqrt(2*med_n); true=np.sqrt(max(obs_sd**2-noise**2,0)); rel=true**2/(true**2+noise**2)
print('POWER, PRICED FIRST')
print(f'  observed cross-team sd of team-sd {obs_sd:.3f}   noise floor {noise:.3f}')
print(f'  => TRUE team-sd dispersion {true:.3f}   reliability {rel:.3f}')
hi=m[(m.zmin>m.zmin.quantile(0)) ]
tq=L.groupby(['team','yr']).z.first()
thi,tlo=tq.quantile(2/3),tq.quantile(1/3)
HH=m[(m.zmin>=thi)]; LL=m[(m.zmax<=tlo)]
gapz=HH[['zmin','zmax']].mean().mean()-LL[['zmin','zmax']].mean().mean()
true_gap=rel*gapz*obs_sd
pred_ratio=(med_sd+true_gap/2)/(med_sd-true_gap/2)
print(f'  HH vs LL measured-z gap {gapz:+.3f} -> SHRUNK true team-sd gap {true_gap:.3f} pts')
print(f'  => PREDICTED sd(total) ratio HH/LL = {pred_ratio:.4f}')
se=np.sqrt(1/(2*len(HH))+1/(2*len(LL)))
print(f'  n(HH)={len(HH)}  n(LL)={len(LL)}  se(log sd ratio) {se:.4f} -> MDE ratio {np.exp(1.96*se):.4f}')
print(f'  {"UNDERPOWERED" if np.exp(1.96*se)>pred_ratio else "POWERED"} for the shrunk prediction\n')

print('THE ANSWER — variance by matchup type')
print(f"  {'bucket':<26}{'n':>7}{'sd(total)':>11}{'sd(dev)':>10}{'mean line':>11}")
for lab,s in [('HH  both high-variance',HH),('LL  both low-variance',LL),
              ('mixed',m[~m.index.isin(HH.index)&~m.index.isin(LL.index)]),
              ('LEAGUE (all games)',m)]:
    print(f'  {lab:<26}{len(s):>7,}{s.total.std():>11.2f}{s.dev.std():>10.2f}{s.close.mean():>11.1f}')
F=HH.total.var()/LL.total.var()
print(f'\n  HH/LL sd(total) ratio {np.sqrt(F):.4f}  (predicted {pred_ratio:.4f})'
      f'  F p={2*min(stats.f.cdf(F,len(HH)-1,len(LL)-1),1-stats.f.cdf(F,len(HH)-1,len(LL)-1)):.4f}')
Fd=HH.dev.var()/LL.dev.var()
print(f'  HH/LL sd(dev)   ratio {np.sqrt(Fd):.4f}'
      f'   F p={2*min(stats.f.cdf(Fd,len(HH)-1,len(LL)-1),1-stats.f.cdf(Fd,len(HH)-1,len(LL)-1)):.4f}')

print('\nCONTINUOUS (all 9k games, max power): combined prior-team dispersion')
m['comb']=np.sqrt(m.sd1**2+m.sd2**2)
for tag,y in [('total',(m.total-m.total.mean())**2),('dev  ',m.dev**2)]:
    X=np.column_stack([np.ones(len(m)),m.comb.values]); yy=y.values
    b,*_=np.linalg.lstsq(X,yy,rcond=None); r=yy-X@b
    se2=np.sqrt(np.diag((r@r/(len(yy)-2))*np.linalg.pinv(X.T@X)))
    print(f'  {tag}^2 ~ comb      beta {b[1]:+9.3f} (t={b[1]/se2[1]:+.2f})')
X=np.column_stack([np.ones(len(m)),m.comb.values,m.close.values]); yy=(m.dev**2).values
b,*_=np.linalg.lstsq(X,yy,rcond=None); r=yy-X@b
se2=np.sqrt(np.diag((r@r/(len(yy)-2))*np.linalg.pinv(X.T@X)))
print(f'  dev^2 ~ comb + LINE  comb {b[1]:+8.3f} (t={b[1]/se2[1]:+.2f})   line {b[2]:+7.3f} (t={b[2]/se2[2]:+.2f})')
print(f'\n  corr(comb, closing line) = {m.comb.corr(m.close):+.4f}')
