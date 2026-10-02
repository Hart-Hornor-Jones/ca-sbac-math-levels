"""A starting point for your own analysis. Run from the repository root:
    python scripts/example_analysis.py
Needs only pandas. Prints three small tables."""
import pandas as pd

levels = pd.read_csv("data/school_levels_grade11_math.csv", dtype={"cds": str}, encoding="utf-8")
schools = pd.read_csv("data/schools.csv", dtype={"cds": str}, encoding="utf-8")

# Keep published (unsuppressed) rows for all students.
allst = levels[(levels.group_code == 1) & levels.pct_met.notna()].merge(schools, on="cds")

# 1. Pool schools into thirds of UPP, each third holding about a third of tested students.
#    This reproduces the "grouped by a school characteristic" chart (all students, % met).
w = allst.groupby("cds").students_with_scores.median()
s = schools.set_index("cds").upp_pct_2017_2020.dropna().sort_values()
cum = w.reindex(s.index).fillna(0).cumsum() / w.reindex(s.index).fillna(0).sum()
third = pd.cut(cum, [0, 1/3, 2/3, 1.0001], labels=["low UPP", "middle UPP", "high UPP"])
allst["upp_third"] = allst.cds.map(third)
allst["met_n"] = allst.pct_met / 100 * allst.students_with_scores
t = allst.dropna(subset=["upp_third"]).groupby(["year", "upp_third"], observed=True)[["met_n", "students_with_scores"]].sum()
print("Percent met, students pooled within UPP thirds")
print((t.met_n / t.students_with_scores * 100).round(1).unstack())

# 2. The same schools in 2019 and 2025: change in each school's percent met.
p = allst[allst.year.isin([2019, 2025]) & (allst.students_with_scores >= 30)].pivot(index="cds", columns="year", values="pct_met").dropna()
print("\nSchools with 30+ testers in both 2019 and 2025:", len(p))
print("Median change in percent met:", round((p[2025] - p[2019]).median(), 1))

# 3. A within-school comparison: economically disadvantaged students vs. their classmates.
two = levels[levels.group_code.isin([31, 111]) & levels.pct_met.notna()]
g = two.pivot_table(index=["cds", "year"], columns="group_code", values="pct_met").dropna()
print("\nMedian within-school gap in percent met (not disadvantaged minus disadvantaged):")
print((g[111] - g[31]).groupby(level="year").median().round(1).to_string())
