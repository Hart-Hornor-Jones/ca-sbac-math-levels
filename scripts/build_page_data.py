"""Rebuild data.json (what index.html loads) from the CSV files in data/.
Run from the repository root:  python scripts/build_page_data.py
Needs only pandas.

data.json keys (see README.md, "data.json"):
  years      the ten test years, in order (2020 had no test)
  names      group code -> group name, for the statewide groups
  state      statewide math: grade -> group code -> year -> [tested, L1, L2, L3, L4]
  state_ela  the same for English language arts
  enrolled   subject -> grade -> group code -> year -> students enrolled
  cuts       subject -> grade -> [lowest, Level 2 from, Level 3 from, Level 4 from, highest]
  schools    one row per high school, grade 11 math only

The "state" block is unchanged from the first release of the page, so older
copies of data.json can be compared with scripts/check_page_data.py."""
import json
import pandas as pd

YEARS = [2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025]
SCH_GROUPS = [1, 3, 4, 31, 111, 74, 76, 77, 78, 80, 144, 180, 8, 160, 128, 90, 91, 92, 93, 94]
ST_GROUPS = SCH_GROUPS + [75, 79, 99, 204, 224, 206, 226, 202, 222, 200, 220]
SUBJECTS = ["math", "ela"]

def r1(x):
    return None if pd.isna(x) else round(float(x), 1)

st_all = pd.read_csv("data/statewide_levels.csv", encoding="utf-8")
st_all = st_all[st_all.group_code.isin(ST_GROUPS)]
names = pd.read_csv("data/student_groups.csv", encoding="utf-8").set_index("group_code").group_name.to_dict()

def levels_by_grade(st):
    """grade -> group code -> year -> [students tested, pct Level 1..4]"""
    out = {}
    for (g, gr), d in st.groupby(["grade", "group_code"]):
        out.setdefault(str(g), {})[str(gr)] = {str(r.year): [int(r.students_tested), r.pct_level1, r.pct_level2, r.pct_level3, r.pct_level4] for r in d.itertuples()}
    return out

def enrolled_by_grade(st):
    """grade -> group code -> year -> students enrolled"""
    out = {}
    for (g, gr), d in st.groupby(["grade", "group_code"]):
        out.setdefault(str(g), {})[str(gr)] = {str(r.year): int(r.students_enrolled) for r in d.itertuples()}
    return out

by_subject = {s: st_all[st_all.subject == s] for s in SUBJECTS}
state = levels_by_grade(by_subject["math"])
state_ela = levels_by_grade(by_subject["ela"])
enrolled = {s: enrolled_by_grade(by_subject[s]) for s in SUBJECTS}

cs = pd.read_csv("data/cut_scores.csv", encoding="utf-8")
cuts = {}
for r in cs.itertuples():
    cuts.setdefault(r.subject, {})[str(r.grade)] = [int(r.lowest_score), int(r.level2_from), int(r.level3_from), int(r.level4_from), int(r.highest_score)]

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
out = {"years": YEARS, "names": {str(k): names[k] for k in ST_GROUPS}, "state": state, "state_ela": state_ela,
       "enrolled": enrolled, "cuts": cuts, "schools": schools}
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(out, f, separators=(",", ":"), allow_nan=False)
print("wrote data.json:", len(schools), "schools;", sum(len(v) for v in state.values()), "math and",
      sum(len(v) for v in state_ela.values()), "ELA grade-group series")
