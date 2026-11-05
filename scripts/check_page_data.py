"""Check data.json against the CSV files and, optionally, against an earlier data.json.
Run from the repository root:
    python scripts/check_page_data.py                 checks data.json against data/
    python scripts/check_page_data.py old_data.json   also checks that every block of the
                                                      earlier file (years, names, state, schools)
                                                      is reproduced exactly, that the earlier
                                                      file is a byte-for-byte prefix of the new
                                                      one (new blocks are only appended), and
                                                      reports the math grade-11 block separately
To get the earlier file from git:  git show main:data.json > old_data.json
Needs only pandas. Exits with status 1 if any check fails."""
import json
import sys
import pandas as pd

failures = []

def check(ok, msg):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok:
        failures.append(msg)

with open("data.json", encoding="utf-8") as f:
    new = json.load(f)

# 1. The statewide blocks reproduce the CSV exactly, for both subjects.
st = pd.read_csv("data/statewide_levels.csv", encoding="utf-8")
for subject, key in [("math", "state"), ("ela", "state_ela")]:
    block = new[key]
    rows = st[st.subject == subject]
    n = 0
    bad = 0
    for r in rows.itertuples():
        g, gr, y = str(r.grade), str(r.group_code), str(r.year)
        if gr not in new["names"]:
            continue
        n += 1
        v = block.get(g, {}).get(gr, {}).get(y)
        want = [int(r.students_tested), r.pct_level1, r.pct_level2, r.pct_level3, r.pct_level4]
        if v != want:
            bad += 1
        if new["enrolled"][subject].get(g, {}).get(gr, {}).get(y) != int(r.students_enrolled):
            bad += 1
    check(bad == 0 and n > 0, f"{subject}: {n} statewide rows match data.json ({bad} differ)")
    sums = [sum(v[1:5]) for gd in block.values() for yd in gd.values() for v in yd.values()]
    check(all(99 <= s <= 102 for s in sums), f"{subject}: the four levels add to 99-102 in every statewide row")
    check(sorted(block.keys(), key=int) == ["3", "4", "5", "6", "7", "8", "11"], f"{subject}: grades 3-8 and 11 present")

cs = pd.read_csv("data/cut_scores.csv", encoding="utf-8")
check(all(new["cuts"][r.subject][str(r.grade)] == [r.lowest_score, r.level2_from, r.level3_from, r.level4_from, r.highest_score] for r in cs.itertuples()),
      "cut scores match cut_scores.csv")

# 2. Every school row's four levels add to 99-102 and the years index is in range.
bad = 0
for s in new["schools"]:
    for rows in s[12].values():
        for a in rows:
            if not (0 <= a[0] < len(new["years"])) or not (99 <= sum(a[2:6]) <= 102):
                bad += 1
check(bad == 0, f"school rows: year index in range and levels add to 99-102 ({bad} bad rows)")

# 3. The school_groups block: the eight groups the schools block leaves out, and suppressed rows, against the CSV.
sg = new["school_groups"]
groups = pd.read_csv("data/student_groups.csv", encoding="utf-8")
in_file = groups[groups.in_school_file == "yes"]
check(sg["names"] == {str(r.group_code): r.group_name for r in in_file.itertuples()},
      f"school_groups.names lists the {len(in_file)} groups flagged in_school_file in student_groups.csv")
check(len(sg["extra"]) == len(new["schools"]) and len(sg["suppressed"]) == len(new["schools"]),
      "school_groups.extra and .suppressed have one entry per school, in the order of the schools block")
sl = pd.read_csv("data/school_levels_grade11_math.csv", dtype={"cds": str}, encoding="utf-8")
sc = pd.read_csv("data/schools.csv", dtype={"cds": str}, encoding="utf-8")
# Recover each school's cds from its name, district and county (schools.csv has them; data.json does not);
# a few schools share all three, and those are told apart by their all-students rows.
yidx = {y: i for i, y in enumerate(new["years"])}
by_key = {}
for r in sc.itertuples():
    by_key.setdefault((r.school, r.district, r.county), []).append(r.cds)
all_pub = sl[sl.pct_level1.notna() & (sl.students_with_scores > 0) & (sl.group_code == 1)]
all_rows = {}
for r in all_pub.itertuples():
    all_rows.setdefault(r.cds, []).append([yidx[r.year], int(r.students_with_scores), round(r.pct_level1, 1), round(r.pct_level2, 1), round(r.pct_level3, 1), round(r.pct_level4, 1)])
cds_of = []
for s in new["schools"]:
    cands = [c for c in by_key.get((s[0], s[1], s[2]), []) if all_rows.get(c) == s[12]["1"]]
    cds_of.append(cands[0] if len(cands) == 1 else None)
check(all(c is not None for c in cds_of) and len(set(cds_of)) == len(cds_of), "every school in data.json maps to one cds in schools.csv")
base = set(k for s in new["schools"] for k in s[12])
extra_codes = set(k for e in sg["extra"] for k in e)
check(not (base & extra_codes) and base | extra_codes == set(sg["names"]),
      f"schools block ({len(base)} groups) and school_groups.extra ({len(extra_codes)} groups) partition the {len(sg['names'])} school-file groups")
pub = sl[sl.pct_level1.notna() & (sl.students_with_scores > 0) & sl.group_code.astype(str).isin(extra_codes)]
want = {}
for r in pub.itertuples():
    want.setdefault(r.cds, {}).setdefault(str(r.group_code), []).append(
        [yidx[r.year], int(r.students_with_scores), round(r.pct_level1, 1), round(r.pct_level2, 1), round(r.pct_level3, 1), round(r.pct_level4, 1)])
got_n = sum(len(v) for e in sg["extra"] for v in e.values())
bad = sum(1 for cds, e in zip(cds_of, sg["extra"]) if e != want.get(cds, {}))
check(bad == 0, f"school_groups.extra: {got_n} published rows for the extra groups match the CSV at every school ({bad} schools differ)")
in_json = set(cds_of)
check(got_n == sum(len(v) for cds, d in want.items() if cds in in_json for v in d.values()),
      "school_groups.extra holds every published extra-group row of the schools in data.json")
sums = [sum(a[2:6]) for e in sg["extra"] for v in e.values() for a in v]
check(all(99 <= x <= 102 for x in sums), "school_groups.extra: the four levels add to 99-102 in every row")
sup = sl[sl.pct_level1.isna() & sl.group_code.astype(str).isin(set(sg["names"]))]
wsup = {}
for r in sup.itertuples():
    wsup.setdefault(r.cds, {}).setdefault(str(r.group_code), []).append([yidx[r.year], int(r.students_tested)])
bad = sum(1 for cds, e in zip(cds_of, sg["suppressed"]) if e != wsup.get(cds, {}))
nsup = sum(len(v) for e in sg["suppressed"] for v in e.values())
check(bad == 0, f"school_groups.suppressed: {nsup} suppressed rows match the CSV at every school ({bad} schools differ)")
overlap = 0
for s, e, u in zip(new["schools"], sg["extra"], sg["suppressed"]):
    rows = dict(s[12]); rows.update(e)
    for g, lst in u.items():
        have = set(a[0] for a in rows.get(g, []))
        overlap += sum(1 for a in lst if a[0] in have)
check(overlap == 0, f"no school x year x group is both published and suppressed ({overlap} overlaps)")

# 4. Optional: compare with an earlier data.json.
if len(sys.argv) > 1:
    with open(sys.argv[1], encoding="utf-8") as f:
        old = json.load(f)
    check(old["state"]["11"] == new["state"]["11"], "math grade 11 statewide block identical to the earlier data.json")
    for k in old:
        check(k in new and old[k] == new[k], f"block '{k}' identical to the earlier data.json")
    # Byte-level check of the shared blocks, serialized the same way the build script does.
    dump = lambda o: json.dumps(o, separators=(",", ":"), allow_nan=False)
    check(all(dump(old[k]) == dump(new[k]) for k in old if k in new), "shared blocks serialize to identical bytes")
    with open(sys.argv[1], "rb") as f:
        old_bytes = f.read().rstrip()
    with open("data.json", "rb") as f:
        new_bytes = f.read()
    check(old_bytes.endswith(b"}") and new_bytes.startswith(old_bytes[:-1]) and (new_bytes == old_bytes or new_bytes[len(old_bytes) - 1] == ord(",")),
          f"the earlier data.json ({len(old_bytes):,} bytes) is reproduced byte for byte as a prefix of the new one ({len(new_bytes):,} bytes); new blocks are only appended")
    check([k for k in new if k not in old] in ([], ["school_groups"]), "the only block added since the earlier file is school_groups")

print()
if failures:
    print(len(failures), "check(s) failed")
    sys.exit(1)
print("all checks passed")
