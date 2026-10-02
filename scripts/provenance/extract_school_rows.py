"""School-grain CAASPP grade-11 MATH by student group, 2015-2025 (all years in CAASPP Data).
Adapted from SBAC by SES 2026-09-17/09_extract_school_by_econ.py. Adds the 'students with scores'
count (the base the level percentages are computed on) as `ws`. Output: data/school_groups_g11_math.csv
"""
import re, os, sys, glob
import pandas as pd
HOME=os.path.expanduser("~"); RAW=f"{HOME}/mnt/Svetlana/CAASPP Data"
GROUPS={1,3,4,31,111,74,75,76,77,78,79,80,144,160,180,8,170,99,128,90,91,92,93,94,121,7,120,142}
OUT="data/school_groups_g11_math.csv"
old=re.compile(r"(\d{2})(\d{2})([ \d]{7})([ \d]{7})\s*(\d{4}\.\d)")
oldsup=re.compile(r"(\d{2})(\d{2})([ \d]{7})([ \d]{7})\s+\*")
years=[int(a) for a in sys.argv[1:]]
for y in years:
    f=sorted(glob.glob(f"{RAW}/sb_ca{y}_all_ascii_v*.txt"))[0]
    new=re.compile(r"%dB(\d{2})(\d{3})(\d{2})([ \d]{9})([ \d]{9})([ \d]{9})(\d{4}\.\d)(.*)"%y)
    newsup=re.compile(r"%dB(\d{2})(\d{3})(\d{2})([ \d]{9})([ \d]{9})\s+\*"%y)
    out=[]; bad=0
    for line in open(f,encoding="latin-1"):
        if y<=2023:
            cds=line[:14]
            if cds[7:14]=="0000000": continue
            try: grp=int(line[22:25])
            except: continue
            if grp not in GROUPS: continue
            m=old.search(line[26:])
            if m:
                grade,test,enr,tst,mean=m.groups(); w=3 if y<=2016 else 6
                rest=line[26+m.end():]
                try:
                    p=[float(rest[i*w:(i+1)*w]) for i in range(5)]
                    ws=int(rest[30:37]) if w==6 else int(rest[15:].split()[0])
                except ValueError:
                    if bad<3: print("unparsed:",line[:170].rstrip())
                    bad+=1; continue
            else:
                m=oldsup.search(line[26:])
                if not m: continue
                grade,test,enr,tst=m.groups(); mean=None; p=[None]*5; ws=None
        else:
            cds=line[:7]+line[47:54]
            if cds[7:14]=="0000000": continue
            m=new.search(line)
            if m:
                test,grp,grade,enr,tst,ws,mean,rest=m.groups(); grp=int(grp)
                if grp not in GROUPS: continue
                p=[float(rest[i*15:i*15+6]) for i in range(5)]; ws=int(ws)
            else:
                m=newsup.search(line)
                if not m: continue
                test,grp,grade,enr,tst=m.groups(); grp=int(grp)
                if grp not in GROUPS: continue
                mean=None; p=[None]*5; ws=None
        grade=int(grade); test=int(test)
        if test!=2 or grade!=11: continue
        if mean is not None:
            a,b,c,d,e=p
            if abs(a+b-c)>1.01 or abs(c+d+e-100)>1.51:
                if bad<3: print("bad sums:",cds,grp,p)
                bad+=1; continue
        out.append(dict(cds=cds,year=y,group=grp,enrolled=int(enr),tested=int(tst),ws=ws,
            mean=None if mean is None else float(mean),L4=p[0],L3=p[1],L2=p[3],L1=p[4]))
    d=pd.DataFrame(out)
    d.to_csv(f"data/sg_{y}.csv",index=False)
    print(y,"rows",len(d),"scored",d["mean"].notna().sum(),"bad",bad,"groups",sorted(d[d["mean"].notna()].group.unique()),flush=True)
