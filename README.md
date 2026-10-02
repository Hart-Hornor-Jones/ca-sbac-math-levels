# SBAC math achievement levels, California, 2015–2025

An interactive page (`index.html`) showing California Smarter Balanced (CAASPP) math results by achievement level. It has four views: statewide by student group, high schools counted by the share of students at a level, high schools grouped by a school characteristic, and one school at a time.

The page reads `data.json`. That file is built entirely from the CSV files in `data/`, which are meant for independent analysis.

## Data files

Years are spring test years (2019 = the 2018–19 school year). There was no test in 2020. In 2021 fewer than half of students tested.

### `data/statewide_levels.csv`

California totals. Math and English, grades 3–8 and 11, every student group the state reports. One row per year × subject × grade × group.

| column | meaning |
|---|---|
| `year`, `subject` (`math`/`ela`), `grade` | |
| `group_code`, `group_name`, `group_category` | the state's student-group codes (1 = all students) |
| `students_enrolled`, `students_tested` | |
| `mean_scale_score` | |
| `pct_level1` … `pct_level4` | percent of tested students at each achievement level |
| `pct_met` | Level 3 + Level 4 |

### `data/school_levels_grade11_math.csv`

One row per school × year × student group, grade 11 math. It covers 28 student groups (see `student_groups.csv`, column `in_school_file`).

| column | meaning |
|---|---|
| `cds` | 14-digit County-District-School code. Read it as text to keep the leading zeros. |
| `year`, `group_code` | |
| `students_enrolled`, `students_tested` | |
| `students_with_scores` | the base for the percentages. Use it as the weight when pooling schools. |
| `mean_scale_score`, `pct_level1` … `pct_level4`, `pct_met` | blank when the state suppressed the result |

The state suppresses any result for fewer than 11 students. Suppressed rows keep their counts and have blank scores (except in 2017 and 2018, whose source files omit suppressed rows). Percentages are rounded, so the four levels add to 99–102. In 2015 and 2016 they are whole numbers.

### `data/schools.csv`

One row per school in the school file, with fixed characteristics.

| column | meaning |
|---|---|
| `cds`, `school`, `district`, `county` | names from the CDE school directory, or from the CAASPP entity files when a school is not in the directory (`name_source`) |
| `region` | ten regions built from counties (listed on the page under "About the data") |
| `school_type`, `charter` | from the CDE directory |
| `latitude`, `longitude` | from the CDE directory |
| `upp_pct_2017_2020` | unduplicated pupil percentage: the share of students who are low-income (free or reduced-price meals), English learners, or foster youth, counted once. Average of 2016–17 through 2019–20. This is not a poverty rate. |
| `ag_completion_pct_classes_2017_2019` | share of the four-year graduating cohort completing the UC/CSU A–G sequence, classes of 2017–2019 pooled. School-years with known CDE reporting errors are left out. |
| `tract_median_household_income` | census tract of the school's location; American Community Survey five-year estimates ending in `tract_acs_end_year` (2019 for most schools), nominal dollars |
| `tract_poverty_rate_pct` | share of tract residents below the federal poverty line |
| `tract_pct_adults_bachelors` | share of tract adults 25+ with a bachelor's degree or more |
| `median_students_with_scores` | the school's median number of grade-11 math testers per year (all students). The page uses it to weight schools when splitting them into thirds, quarters or fifths. |

### `data/student_groups.csv`

Group codes, names and categories, with a flag for whether each group appears in the school file.

### `data/cut_scores.csv`

Scale-score cut points for each grade and subject: the lowest score, the first score of Levels 2, 3 and 4, and the highest score. They come from the CAASPP Smarter Balanced Technical Report (2016–17, Table 7.8). The cut points have not changed since 2015. In 2026 the state renamed the levels (Minimal, Developing, Proficient, Advanced) and kept the same cut scores.

## Scripts

- `scripts/build_page_data.py` rebuilds `data.json` from `data/`. Run it from the repository root. It needs only pandas.
- `scripts/example_analysis.py` is a starting point. It pools schools by UPP, compares the same schools in 2019 and 2025, and computes a within-school gap between economically disadvantaged students and their classmates.
- `scripts/provenance/` holds the scripts that produced the CSV files from the CDE raw files. Those raw files are not included; they are too large. The scripts read local paths and are kept as a record, not to be run from the repository.

## Checks

- Pooling the school rows for all students reproduces the statewide level shares within 0.4 percentage points in every year.
- With charter schools left out, the pooled school rows match the state's district totals within 0.2 points for San Diego Unified and Fresno Unified.
- Economically disadvantaged plus not disadvantaged equals all students at every school and year.

## Sources

California Department of Education: CAASPP Smarter Balanced research files 2015–2025 (statewide and school rows); public schools directory; LCFF unduplicated pupil counts; adjusted cohort graduation files (A–G). U.S. Census Bureau: American Community Survey five-year estimates. CAASPP Smarter Balanced Technical Report 2016–17 (cut scores).
