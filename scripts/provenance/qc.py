import pandas as pd, glob, numpy as np
sg=pd.concat([pd.read_csv(f,dtype={"cds":str}) for f in sorted(glob.glob("sg_20*.csv"))])
st=pd.read_csv("state_rows_all_groups_tidy.csv"); st=st[(st.subject=="math")]
print("dup cds-year-group:",sg.duplicated(["cds","year","group"]).sum())
sc=sg[sg.L1.notna()].copy(); s=sc[["L1","L2","L3","L4"]].sum(axis=1)
print("level sum range",s.min(),s.max(), "ws missing among scored:",sc.ws.isna().sum(), "ws>tested:",(sc.ws>sc.tested).sum())
# 1. pooled schools vs state, group 1
print("\nAll students G11: pooled scored schools vs statewide row")
for y,g in sc[sc.group==1].groupby("year"):
    w=g.ws; pl=[(g[f"L{i}"]*w).sum()/w.sum() for i in (1,2,3,4)]
    r=st[(st.year==y)&(st.grade==11)&(st.group==1)].iloc[0]
    print(y,f"schools {len(g)}  ws {w.sum():,} / state tested {r.tested:,} ({w.sum()/r.tested*100:.1f}%)  L1 {pl[0]:.1f} vs {r.L1}  L2 {pl[1]:.1f} vs {r.L2}  L3 {pl[2]:.1f} vs {r.L3}  L4 {pl[3]:.1f} vs {r.L4}")
# 2. recovered rows vs old extract
old=pd.read_csv("old_levels.csv",dtype={"cds":str}); old=old[old.L1.notna()]
new1=sc[sc.group==1]
for y in sorted(new1.year.unique()):
    a=set(new1[new1.year==y].cds); b=set(old[old.year==y].cds)
    if a!=b: print("year",y,"new-only",len(a-b),"old-only",len(b-a))
m=new1.merge(old,on=["cds","year"],suffixes=("","_o"))
print("max abs diff L1 vs old:",(m.L1-m.L1_o).abs().max(), " rows compared",len(m))
# 3. subgroup sums
p=sc.pivot_table(index=["cds","year"],columns="group",values="ws")
for a,b,lab in [((3,4),1,"Male+Female"),((31,111),1,"SED+NotSED")]:
    ok=p[[*a,b]].dropna(); d=(ok[a[0]]+ok[a[1]]-ok[b]); print(lab,"= All in",(d==0).mean()*100,"% of",len(ok),"school-years; max diff",d.abs().max())
# coverage of subgroups after suppression, 2019
print("\nShare of statewide G11 group testers captured in published school rows, 2019 / 2025")
for y in (2019,2025):
  for gcode in (3,4,31,111,74,76,77,78,80,144,160,180,8,128,90,94):
    w=sc[(sc.year==y)&(sc.group==gcode)].ws.sum(); r=st[(st.year==y)&(st.grade==11)&(st.group==gcode)]
    if len(r): print(y,gcode,r.iloc[0].group_name[:30],f"{w/r.iloc[0].tested*100:.0f}%")
