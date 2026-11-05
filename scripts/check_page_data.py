"""Check data.json against the CSV files and, optionally, against an earlier data.json.
Run from the repository root:
    python scripts/check_page_data.py                 checks data.json against data/
    python scripts/check_page_data.py old_data.json   also checks that every block of the
                                                      earlier file (years, names, state, schools)
                                                      is reproduced exactly, and reports the
                                                      math grade-11 block separately
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

# 3. Optional: compare with an earlier data.json.
if len(sys.argv) > 1:
    with open(sys.argv[1], encoding="utf-8") as f:
        old = json.load(f)
    check(old["state"]["11"] == new["state"]["11"], "math grade 11 statewide block identical to the earlier data.json")
    for k in old:
        check(k in new and old[k] == new[k], f"block '{k}' identical to the earlier data.json")
    # Byte-level check of the shared blocks, serialized the same way the build script does.
    dump = lambda o: json.dumps(o, separators=(",", ":"), allow_nan=False)
    check(all(dump(old[k]) == dump(new[k]) for k in old if k in new), "shared blocks serialize to identical bytes")

print()
if failures:
    print(len(failures), "check(s) failed")
    sys.exit(1)
print("all checks passed")
