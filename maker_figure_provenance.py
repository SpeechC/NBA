import sys, numpy as np; sys.path.insert(0,'/mnt/d/Kalshi/nba')
from scipy.stats import norm
import nba_live_trader as T
SIG=18.0; N=400000
BETS={'crewshock':200,'pacegap':380,'move':350,'final7':58}
rng=np.random.default_rng(11)
MU=rng.uniform(215,240,N)[:,None]; i=np.arange(11)[None,:]
K=np.round(MU)-15+3*i+0.5
pmkt=1-norm.cdf((K-MU)/SIG)
bid=np.clip(np.round(pmkt-0.01,2),0.01,None)
ask=np.clip(np.round(bid+0.02,2),None,0.99)
px=np.round(np.minimum(bid+0.01,ask-0.01),2)
fee=np.ceil(0.07*px*(1-px)*1000)/1000.0
ok=(px>=0.12)&(px<=0.88); r=np.arange(N)
rows={}
for name in ('crewshock','move','final7','pacegap'):
    D=T.STRATS[name]['delta']
    ptru=1-norm.cdf((K-MU-D)/SIG)
    shown=ptru-px-fee
    jm=np.where(ok,shown,-9.9).argmax(1)
    jl=np.where(ok,np.abs(K-MU),9e9).argmin(1)
    u=rng.random(N)
    out={}
    for tag,j in (('maxEV',jm),('line',jl)):
        p,f,t=px[r,j],fee[r,j],ptru[r,j]
        pnl=(u<t).astype(float)-p-f
        out[tag]=dict(hit=t.mean(), ev=pnl.mean(), se=pnl.std()/np.sqrt(N),
                      outlay=(p+f).mean())
    rows[name]=out
print('SETTLEMENT-VERIFIED, 400,000 boards each.  1 contract, resting bid, 2c book.\n')
h=f"{'':<10}|{'MAX-EV RUNG':^30}|{'LINE RUNG':^30}"
print(h); print(f"{'strategy':<10}|{'hit%':>8}{'EV/ct':>10}{'ROI':>10}|{'hit%':>8}{'EV/ct':>10}{'ROI':>10}")
print('-'*len(h))
for k,o in rows.items():
    a,b=o['maxEV'],o['line']
    print(f"{k:<10}|{100*a['hit']:>7.1f}%{100*a['ev']:>9.2f}c{100*a['ev']/a['outlay']:>9.1f}%"
          f"|{100*b['hit']:>7.1f}%{100*b['ev']:>9.2f}c{100*b['ev']/b['outlay']:>9.1f}%")
print()
print(f"{'SEASON @ 1 CONTRACT':<22}{'bets':>6}{'premium':>10}{'P&L':>9}{'ROI':>8}{'hit%':>8}")
print('-'*63)
tot={}
for tag,lbl in (('maxEV','max-EV rung (current)'),('line','line rung')):
    P=sum(BETS[k]*rows[k][tag]['ev'] for k in BETS)
    Q=sum(BETS[k]*rows[k][tag]['outlay'] for k in BETS)
    W=sum(BETS[k]*rows[k][tag]['hit'] for k in BETS); n=sum(BETS.values())
    tot[tag]=(P,Q,W)
    print(f"{lbl:<22}{n:>6}{Q:>9.2f}$ {P:>+8.2f}$ {100*P/Q:>7.1f}%{100*W/n:>7.1f}%")
dP=tot['maxEV'][0]-tot['line'][0]
print(f"\n  max-EV earns {dP:+.2f}$ more per season ({100*dP/tot['line'][0]:+.0f}%),")
print(f"  on {tot['line'][1]-tot['maxEV'][1]:.2f}$ LESS premium deployed.")
print(f"  The line rung's hit% is the one that resembles the backtest.")
