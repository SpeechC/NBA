"""Scrape WNBA 2026 quarter scores + start times from basketball-reference.
Polite: 3s/page, ~330 pages -> ~17 min. Output: wnba_2026_halves.csv"""
import re, time, requests, pandas as pd
hdr={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0","Accept":"text/html"}
BASE="https://www.basketball-reference.com"
s=requests.get(f"{BASE}/wnba/years/2026_games.html",headers=hdr,timeout=30).text
links=sorted(set(re.findall(r'href="(/wnba/boxscores/\d{9}[A-Z]{3}\.html)"',s)))
# schedule rows: capture start time if present
sched={}
for m in re.finditer(r'<tr[^>]*>(.*?)</tr>',s,re.S):
    row=m.group(1)
    lk=re.search(r'href="(/wnba/boxscores/\d{9}[A-Z]{3}\.html)"',row)
    if not lk: continue
    tm=re.search(r'>(\d{1,2}:\d{2}\s*[ap]m?)</',row,re.I)
    sched[lk.group(1)]=tm.group(1) if tm else ""
print(f"{len(links)} boxscores; start-time present on {sum(1 for v in sched.values() if v)}")
rows=[]
for i,lk in enumerate(links,1):
    try:
        t=requests.get(BASE+lk,headers=hdr,timeout=30).text.replace("<!--","").replace("-->","")
        m=re.search(r'<table[^>]*id="line-score"[^>]*>.*?</table>',t,re.S)
        if not m: continue
        trs=re.findall(r'<tr[^>]*>(.*?)</tr>',m.group(0),re.S)
        parsed=[]
        for r_ in trs:
            cells=[c.strip() for c in re.findall(r'<t[dh][^>]*>(?:<[^>]+>)*([^<]*)',r_)]
            cells=[c for c in cells if c and c!="&nbsp;"]
            if len(cells)>=6 and not cells[0].isdigit() and cells[0] not in ("1","T"):
                parsed.append(cells)
        if len(parsed)!=2: continue
        def unpack(c):
            name=c[0]; nums=[x for x in c[1:] if re.fullmatch(r'\d+',x)]
            return name, [int(x) for x in nums]      # Q1..Qn..T (T last)
        an,av=unpack(parsed[0]); hn,hv=unpack(parsed[1])
        rows.append({"box":lk,"date":lk.split("/")[-1][:8],"away":an,"home":hn,
                     "a_q1":av[0],"a_q2":av[1],"a_q3":av[2],"a_q4":av[3],"a_final":av[-1],
                     "h_q1":hv[0],"h_q2":hv[1],"h_q3":hv[2],"h_q4":hv[3],"h_final":hv[-1],
                     "n_ot":len(av)-5,"start_et":sched.get(lk,"")})
    except Exception as e:
        print("ERR",lk,type(e).__name__)
    if i%50==0: print(f"{i}/{len(links)}  rows {len(rows)}",flush=True)
    time.sleep(3)
pd.DataFrame(rows).to_csv("/home/dpope/projects/nba_entropy_replication/wnba_2026_halves.csv",index=False)
print(f"DONE: {len(rows)} games written")
