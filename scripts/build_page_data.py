"""Rebuild data.json (what index.html loads) from the CSV files in data/.
Run from the repository root:  python scripts/build_page_data.py
Needs only pandas."""
import json
import pandas as pd

YEARS = [2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025]
SCH_GROUPS = [1, 3, 4, 31, 111, 74, 76, 77, 78, 80, 144, 180, 8, 160, 128, 90, 91, 92, 93, 94]
ST_GROUPS = SCH_GROUPS + [75, 79, 99, 204, 224, 206, 226, 202, 222, 200, 220]

def r1(x):
    return None if pd.isna(x) else round(float(x), 1)

st = pd.read_csv("data/statewide_levels.csv", encoding="utf-8")
st = st[st.subject == "math"]
names = pd.read_csv("data/student_groups.csv", encoding="utf-8").set_index("group_code").group_name.to_dict()
state = {}
for (g, gr), d in st[st.group_code.isin(ST_GROUPS)].groupby(["grade", "group_code"]):
    state.setdefault(str(g), {})[str(gr)] = {str(r.year): [int(r.students_tested), r.pct_level1, r.pct_level2, r.pct_level3, r.pct_level4] for r in d.itertuples()}

sl = pd.read_csv("data/school_levels_grade11_math.csv", dtype={"cds": str}, encoding="utf-8")
sl = sl[sl.pct_level1.notna() & sl.group_code.isin(SCH_GROUPS) & (sl.students_with_scores > 0)]
sc = pd.read_csv("data/schools.csv", dtype={"cds": str}, encoding="utf-8").set_index("cds")
txt = lambda v: v if isinstance(v, str) else None
schools = []
for cds, d in sl.groupby("cds"):
    if cds not in sc.index or not (d.group_code == 1).any():
        continue
    c = sc.loc[cds]
    gd = {}
    for g, e in d.groupby("group_code"):
        gd[str(g)] = [[YEARS.index(r.year), int(r.students_with_scores), r1(r.pct_level1), r1(r.pct_level2), r1(r.pct_level3), r1(r.pct_level4)]
                      for r in e.sort_values("year").itertuples()]
    schools.append([str(c.school), str(c.district), str(c.county), txt(c.region), txt(c.school_type), txt(c.charter),
                    r1(c.upp_pct_2017_2020), r1(c.ag_completion_pct_classes_2017_2019),
                    None if pd.isna(c.tract_median_household_income) else int(c.tract_median_household_income),
                    r1(c.tract_poverty_rate_pct), r1(c.tract_pct_adults_bachelors),
                    float(c.median_students_with_scores) if not pd.isna(c.median_students_with_scores) else 0, gd])
schools.sort(key=lambda s: (s[0].lower(), s[1]))
out = {"years": YEARS, "names": {str(k): names[k] for k in ST_GROUPS}, "state": state, "schools": schools}
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(out, f, separators=(",", ":"), allow_nan=False)
print("wrote data.json:", len(schools), "schools")
