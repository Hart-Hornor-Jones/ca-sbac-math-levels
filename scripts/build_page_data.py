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
  school_groups  the rest of the school file: the eight student groups the "schools" block
             leaves out, the suppressed school x year x group results, and group names

The "state" block is unchanged from the first release of the page, and every block that an
earlier data.json had is reproduced byte for byte: new blocks are only ever appended at the
end of the file, so older copies can be compared with scripts/check_page_data.py."""
import json
import pandas as pd

YEARS = [2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025]
SCH_GROUPS = [1, 3, 4, 31, 111, 74, 76, 77, 78, 80, 144, 180, 8, 160, 128, 90, 91, 92, 93, 94]
ST_GROUPS = SCH_GROUPS + [75, 79, 99, 204, 224, 206, 226, 202, 222, 200, 220]
# The school file carries 28 groups (student_groups.csv, in_school_file = yes). The "schools" block
# keeps the 20 in SCH_GROUPS, as in the first release; the other eight go in "school_groups".
EXTRA_SCH_GROUPS = [7, 75, 79, 99, 120, 121, 142, 170]
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

sl_all = pd.read_csv("data/school_levels_grade11_math.csv", dtype={"cds": str}, encoding="utf-8")
sl = sl_all[sl_all.pct_level1.notna() & sl_all.group_code.isin(SCH_GROUPS) & (sl_all.students_with_scores > 0)]
sc = pd.read_csv("data/schools.csv", dtype={"cds": str}, encoding="utf-8").set_index("cds")
txt = lambda v: v if isinstance(v, str) else None

def group_rows(d):
    """group code -> [[year index, students with scores, pct Level 1..4], ...], years in order"""
    gd = {}
    for g, e in d.groupby("group_code"):
        gd[str(g)] = [[YEARS.index(r.year), int(r.students_with_scores), r1(r.pct_level1), r1(r.pct_level2), r1(r.pct_level3), r1(r.pct_level4)]
                      for r in e.sort_values("year").itertuples()]
    return gd

schools = []
school_cds = []
for cds, d in sl.groupby("cds"):
    if cds not in sc.index or not (d.group_code == 1).any():
        continue
    c = sc.loc[cds]
    gd = group_rows(d)
    school_cds.append(cds)
    schools.append([str(c.school), str(c.district), str(c.county), txt(c.region), txt(c.school_type), txt(c.charter),
                    r1(c.upp_pct_2017_2020), r1(c.ag_completion_pct_classes_2017_2019),
                    None if pd.isna(c.tract_median_household_income) else int(c.tract_median_household_income),
                    r1(c.tract_poverty_rate_pct), r1(c.tract_pct_adults_bachelors),
                    float(c.median_students_with_scores) if not pd.isna(c.median_students_with_scores) else 0, gd])
order = sorted(range(len(schools)), key=lambda i: (schools[i][0].lower(), schools[i][1]))
schools = [schools[i] for i in order]
school_cds = [school_cds[i] for i in order]

# The rest of the school file, one entry per school in the same order as "schools":
#   extra       group code -> rows, same layout as in "schools", for the eight groups it leaves out
#   suppressed  group code -> [[year index, students tested], ...] for every school x year x group
#               result the state suppressed (blank scores, fewer than 11 students). The 2017 and 2018
#               files omit such rows, and the 2024 and 2025 files omit nearly all of them, so a group
#               with no row at all in a year is not reported either.
sg = pd.read_csv("data/student_groups.csv", encoding="utf-8")
sch_group_codes = sorted(sg[sg.in_school_file == "yes"].group_code)
assert sorted(SCH_GROUPS + EXTRA_SCH_GROUPS) == sch_group_codes, "the school file's groups changed"
pos = {cds: i for i, cds in enumerate(school_cds)}
extra = [{} for _ in schools]
suppressed = [{} for _ in schools]
ex = sl_all[sl_all.pct_level1.notna() & sl_all.group_code.isin(EXTRA_SCH_GROUPS) & (sl_all.students_with_scores > 0)]
for cds, d in ex.groupby("cds"):
    if cds in pos:
        extra[pos[cds]] = group_rows(d)
sup = sl_all[sl_all.pct_level1.isna() & sl_all.group_code.isin(sch_group_codes)]
for cds, d in sup.groupby("cds"):
    if cds not in pos:
        continue
    for g, e in d.groupby("group_code"):
        suppressed[pos[cds]][str(g)] = [[YEARS.index(r.year), int(r.students_tested)] for r in e.sort_values("year").itertuples()]
school_groups = {"names": {str(k): names[k] for k in sch_group_codes}, "extra": extra, "suppressed": suppressed}

# Keys are appended in this order so that an earlier data.json is a byte-for-byte prefix of the new one.
out = {"years": YEARS, "names": {str(k): names[k] for k in ST_GROUPS}, "state": state, "state_ela": state_ela,
       "enrolled": enrolled, "cuts": cuts, "schools": schools, "school_groups": school_groups}
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(out, f, separators=(",", ":"), allow_nan=False)
print("wrote data.json:", len(schools), "schools;", sum(len(v) for v in state.values()), "math and",
      sum(len(v) for v in state_ela.values()), "ELA grade-group series;",
      sum(len(r) for e in extra for r in e.values()), "rows for the", len(EXTRA_SCH_GROUPS), "extra school groups;",
      sum(len(r) for e in suppressed for r in e.values()), "suppressed school rows")
