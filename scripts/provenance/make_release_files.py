import pandas as pd, glob, numpy as np
R="repo/data/"
st=pd.read_csv("state_rows_all_groups_tidy.csv")
names=st.drop_duplicates("group").set_index("group")[["group_name","group_cat"]]
s=st.rename(columns={"group":"group_code","group_cat":"group_category","enrolled":"students_enrolled","tested":"students_tested","mean":"mean_scale_score","L1":"pct_level1","L2":"pct_level2","L3":"pct_level3","L4":"pct_level4","met":"pct_met"})
s=s[["year","subject","grade","group_code","group_name","group_category","students_enrolled","students_tested","mean_scale_score","pct_level1","pct_level2","pct_level3","pct_level4","pct_met"]].sort_values(["subject","grade","group_code","year"])
s.to_csv(R+"statewide_levels.csv",index=False)
sg=pd.concat([pd.read_csv(f,dtype={"cds":str}) for f in sorted(glob.glob("sg_20*.csv"))])
sg["group_name"]=sg.group.map(names.group_name); sg["group_category"]=sg.group.map(names.group_cat)
sg["pct_met"]=(sg.L3+sg.L4).round(2)
ch=pd.read_csv("school_characteristics.csv",dtype={"cds":str})
keep=set(ch.cds)
sg=sg[sg.cds.isin(keep)]
o=sg.rename(columns={"group":"group_code","enrolled":"students_enrolled","tested":"students_tested","ws":"students_with_scores","mean":"mean_scale_score","L1":"pct_level1","L2":"pct_level2","L3":"pct_level3","L4":"pct_level4"})
o=o[["cds","year","group_code","students_enrolled","students_tested","students_with_scores","mean_scale_score","pct_level1","pct_level2","pct_level3","pct_level4","pct_met"]].sort_values(["cds","group_code","year"])
o["students_with_scores"]=o.students_with_scores.astype("Int64")
o.to_csv(R+"school_levels_grade11_math.csv",index=False)
ll=pd.read_csv("school_latlon.csv",dtype={"cds":str})
c=ch.merge(ll,on="cds",how="left")
c=c.rename(columns={"upp":"upp_pct_2017_2020","ag_rate":"ag_completion_pct_classes_2017_2019","tract_income":"tract_median_household_income","tract_poverty":"tract_poverty_rate_pct","tract_ba":"tract_pct_adults_bachelors","tract_year":"tract_acs_end_year","ws_med":"median_students_with_scores"})
c=c[["cds","school","district","county","region","school_type","charter","latitude","longitude","upp_pct_2017_2020","ag_completion_pct_classes_2017_2019","tract_median_household_income","tract_poverty_rate_pct","tract_pct_adults_bachelors","tract_acs_end_year","median_students_with_scores","name_src"]].rename(columns={"name_src":"name_source"})
for k in ["school","district","county"]: c[k]=c[k].astype(str).str.strip()
c["tract_acs_end_year"]=c.tract_acs_end_year.astype("Int64")
c.sort_values("cds").to_csv(R+"schools.csv",index=False)
cut=[]
CS={"ela":{3:(2114,2367,2432,2490,2623),4:(2131,2416,2473,2533,2663),5:(2201,2442,2502,2582,2701),6:(2210,2457,2531,2618,2724),7:(2258,2479,2552,2649,2745),8:(2288,2487,2567,2668,2769),11:(2299,2493,2583,2682,2795)},
 "math":{3:(2189,2381,2436,2501,2621),4:(2204,2411,2485,2549,2659),5:(2219,2455,2528,2579,2700),6:(2235,2473,2552,2610,2748),7:(2250,2484,2567,2635,2778),8:(2265,2504,2586,2653,2802),11:(2280,2543,2628,2718,2862)}}
for sub,d in CS.items():
    for g,(lo,a,b,cc,hi) in d.items(): cut.append(dict(subject=sub,grade=g,lowest_score=lo,level2_from=a,level3_from=b,level4_from=cc,highest_score=hi))
pd.DataFrame(cut).to_csv(R+"cut_scores.csv",index=False)
gl=st.drop_duplicates("group")[["group","group_name","group_cat"]].rename(columns={"group":"group_code","group_cat":"group_category"}).sort_values("group_code")
gl["in_school_file"]=gl.group_code.isin(set(o.group_code)).map({True:"yes",False:"no"})
gl.to_csv(R+"student_groups.csv",index=False)
import os
for f in sorted(os.listdir(R)): print(f, round(os.path.getsize(R+f)/1e6,2),"MB", len(pd.read_csv(R+f)),"rows")
