"""One row per school (CDS) in the grade-11 math extract, with fixed characteristics used to group schools.
Sources: CDE public schools directory (names, county, district, school type, charter);
LCFF unduplicated pupil percentage (mean of 2016-17..2019-20); A-G completion (cleaned CDE ACGR,
classes of 2017-2019, A-G completers / cohort, flagged school-years dropped); ACS 2015-19 tract
(median household income, poverty rate, % adults with bachelor's) at the school's location.
Output: data/school_characteristics.csv"""
import pandas as pd, glob, numpy as np, os
H=os.path.expanduser("~/mnt")
sg=pd.concat([pd.read_csv(f,dtype={"cds":str}) for f in sorted(glob.glob("data/sg_20*.csv"))])
u=sg[sg.group==1].groupby("cds").agg(years=("year","nunique"),ws_med=("ws","median")).reset_index()
# names from CAASPP entity files (latest year a school appears), CDE directory preferred
ent={}
for y in [2015,2016,2017,2018,2019,2021,2022,2023,2024,2025]:
    f=sorted(glob.glob(f"{H}/Svetlana/CAASPP Data/sb_ca{y}entities_ascii*.txt"))[0]
    for line in open(f,encoding="latin-1"):
        c=line[:14]; rest=line[24:]
        if c[7:14]=="0000000": continue
        f3=[x.strip() for x in __import__("re").split(r"\s{2,}",rest.strip())]+["","",""]
        ent[c]=(f3[0],f3[1],f3[2])
c=pd.read_csv(f"{H}/hs data/ca_school_context_out/cde_public_schools_districts_current_clean.csv",dtype=str).set_index("cds_code")
def nm(r):
    k=r.cds
    if k in c.index:
        x=c.loc[k]; return pd.Series(dict(school=x.cde_school,district=x.cde_district,county=x.cde_county,soctype=x.cde_soctype,charter=x.cde_charter,status=x.cde_status_type,name_src="CDE directory"))
    e=ent.get(k,("","",""))
    return pd.Series(dict(school=e[2],district=e[1],county=e[0],soctype=None,charter=None,status=None,name_src="CAASPP entities"))
u=pd.concat([u,u.apply(nm,axis=1)],axis=1)
REG={"Bay Area":"Alameda Contra_Costa Marin Napa San_Francisco San_Mateo Santa_Clara Solano Sonoma",
 "Sacramento area":"Sacramento Placer El_Dorado Yolo Sutter Yuba",
 "Central Coast":"Monterey San_Benito San_Luis_Obispo Santa_Barbara Santa_Cruz Ventura",
 "San Joaquin Valley":"San_Joaquin Stanislaus Merced Madera Fresno Kings Tulare Kern",
 "Los Angeles County":"Los_Angeles","Orange County":"Orange","Inland Empire":"Riverside San_Bernardino",
 "San Diego and Imperial":"San_Diego Imperial",
 "North State":"Butte Colusa Del_Norte Glenn Humboldt Lake Lassen Mendocino Modoc Nevada Plumas Shasta Sierra Siskiyou Tehama Trinity",
 "Sierra and Eastern":"Alpine Amador Calaveras Inyo Mariposa Mono Tuolumne"}
c2r={cn.replace("_"," "):r for r,v in REG.items() for cn in v.split()}
u["region"]=u.county.map(c2r)
def stype(s):
    if s is None or pd.isna(s): return None
    if s.startswith("High Schools"): return "Regular high school"
    if s.startswith("Continuation"): return "Continuation high school"
    if s.startswith("Alternative"): return "Alternative school of choice"
    if s.startswith("K-12"): return "K-12 school"
    return "Other (community day, court, special ed., etc.)"
u["school_type"]=u.soctype.map(stype)
u["charter"]=u.charter.map({"Y":"Charter","N":"Not charter"})
up=pd.read_csv(f"{H}/Svetlana/Panel Build 2026-06-07/components/upp_lcff.csv",dtype={"cds14":str})
up=up[up.cupc_year.isin(["2016-2017","2017-2018","2018-2019","2019-2020"])].groupby("cds14").upp_pct.mean()
u["upp"]=u.cds.map(up)
ag=pd.read_csv(f"{H}/Svetlana/Data Cleaning 2026-06-07/ag_eligibility_cleaned.csv",dtype={"cds14":str})
ag=ag[ag.year.isin([2017,2018,2019])&ag.ag_met_clean.notna()&(ag.cohort>=10)]
agg=ag.groupby("cds14").agg(m=("ag_met_clean","sum"),n=("cohort","sum")); u["ag_rate"]=u.cds.map(agg.m/agg.n*100)
a=pd.read_csv(f"{H}/hs data/ca_school_context_out/ca_high_school_rows_with_acs_context.csv",dtype={"cds_code":str},
  usecols=["cds_code","school_year","tract_median_household_income","tract_poverty_rate","tract_pct_bachelors_or_more_25plus"])
a=a[a.tract_median_household_income.notna()&(a.tract_median_household_income>0)]
a["d"]=(a.school_year-2019).abs(); a=a.sort_values(["cds_code","d"]).drop_duplicates("cds_code").set_index("cds_code")
u["tract_income"]=u.cds.map(a.tract_median_household_income); u["tract_poverty"]=u.cds.map(a.tract_poverty_rate); u["tract_ba"]=u.cds.map(a.tract_pct_bachelors_or_more_25plus); u["tract_year"]=u.cds.map(a.school_year)
u.to_csv("data/school_characteristics.csv",index=False)
w=u.ws_med
for k in ["region","school_type","charter","upp","ag_rate","tract_income","tract_poverty","tract_ba"]:
    print(f"{k:14s} schools {u[k].notna().mean()*100:5.1f}%  students {(w*u[k].notna()).sum()/w.sum()*100:5.1f}%")
print(u.name_src.value_counts()); print(u.school_type.value_counts(dropna=False)); print(u.tract_year.value_counts().head())
