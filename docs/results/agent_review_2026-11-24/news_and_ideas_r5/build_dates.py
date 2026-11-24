import csv,pickle,datetime as dt
B="https://www.bls.gov/schedule/%d/home.htm"
bls={
'CPI':{2021:"10/13 11/10 12/10",2022:"1/12 2/10 3/10 4/12 5/11 6/10 7/13 8/10 9/13 10/13 11/10 12/13",2023:"1/12 2/14 3/14 4/12 5/10 6/13 7/12 8/10 9/13 10/12 11/14 12/12",2024:"1/11 2/13 3/12 4/10 5/15 6/12 7/11 8/14 9/11 10/10 11/13 12/11",2025:"1/15 2/12 3/12 4/10 5/13 6/11 7/15 8/12 9/11 10/24 12/18",2026:"1/13 2/13 3/11 4/10 5/12 6/10 7/14 8/12 9/11 10/14"},
'PPI':{2021:"10/14 11/9 12/14",2022:"1/13 2/15 3/15 4/13 5/12 6/14 7/14 8/11 9/14 10/12 11/15 12/9",2023:"1/18 2/16 3/15 4/13 5/11 6/14 7/13 8/11 9/14 10/11 11/15 12/13",2024:"1/12 2/16 3/14 4/11 5/14 6/13 7/12 8/13 9/12 10/11 11/14 12/12",2025:"1/14 2/13 3/13 4/11 5/15 6/12 7/16 8/14 9/10 11/25",2026:"1/14 1/30 2/27 3/18 4/14 5/13 6/11 7/15 8/13 9/10 10/15"},
'NFP':{2021:"10/8 11/5 12/3",2022:"1/7 2/4 3/4 4/1 5/6 6/3 7/8 8/5 9/2 10/7 11/4 12/2",2023:"1/6 2/3 3/10 4/7 5/5 6/2 7/7 8/4 9/1 10/6 11/3 12/8",2024:"1/5 2/2 3/8 4/5 5/3 6/7 7/5 8/2 9/6 10/4 11/1 12/6",2025:"1/10 2/7 3/7 4/4 5/2 6/6 7/3 8/1 9/5 11/20 12/16",2026:"1/9 2/11 3/6 4/3 5/8 6/5 7/2 8/7 9/4 10/2"},
'JOLTS':{2021:"10/12 11/12 12/8",2022:"1/4 2/1 3/9 3/29 5/3 6/1 7/6 8/2 8/30 10/4 11/1 11/30",2023:"1/4 2/1 3/8 4/4 5/2 5/31 7/6 8/1 8/29 10/3 11/1 12/5",2024:"1/3 1/30 3/6 4/2 5/1 6/4 7/2 7/30 9/4 10/1 10/29 12/3",2025:"1/7 2/4 3/11 4/1 4/29 6/3 7/1 7/29 9/3 9/30 12/9",2026:"1/7 2/5 3/13 3/31 5/5 6/2 6/30 8/4 9/1 9/29"}}
tm={'CPI':'08:30','PPI':'08:30','NFP':'08:30','JOLTS':'10:00'}
gdp={2022:("https://www.bea.gov/news/2022/gross-domestic-product-fourth-quarter-and-year-2021-advance-estimate","1/27 2/24 3/30 4/28 5/26 6/29 7/28 8/25 9/29 10/27 11/30 12/22"),
2023:("https://www.bea.gov/news/2023/gross-domestic-product-fourth-quarter-and-year-2022-advance-estimate (schedule table; via search snippet)","1/26 2/23 3/30 4/27 5/25 6/29 7/27 8/30 9/28 10/26 11/29 12/21"),
2024:("https://www.bea.gov/news/2024/gross-domestic-product-fourth-quarter-and-year-2023-advance-estimate","1/25 2/28 3/28 4/25 5/30 6/27 7/25 8/29 9/26 10/30 11/27 12/19"),
2025:("https://www.bea.gov/news/schedule/full-2025","1/30 2/27 3/27 4/30 5/29 6/26 7/30 8/28 9/25 10/30 12/23")}
rows=[]
for k,yy in bls.items():
    for y,s in yy.items():
        for md in s.split():
            m,d=map(int,md.split('/')); rows.append((dt.date(y,m,d),k,tm[k],B%y))
for y,(u,s) in gdp.items():
    for md in s.split():
        m,d=map(int,md.split('/')); rows.append((dt.date(y,m,d),'GDP','08:30',u))
for k,d,t,u in pickle.load(open('/tmp/fomc_rows.pkl','rb')): rows.append((d,k,t,u))
lo,hi=dt.date(2021,10,1),dt.date(2026,10,31)
rows=sorted(r for r in rows if lo<=r[0]<=hi)
bad=[r for r in rows if r[0].weekday()>=5]; print("weekend rows",bad)
with open('dates_us_releases.csv','w',newline='') as f:
    w=csv.writer(f);w.writerow(['date','event','time_et','source_url']);[w.writerow([r[0],r[1],r[2],r[3]]) for r in rows]
from collections import Counter;print(len(rows),Counter(r[1] for r in rows))
