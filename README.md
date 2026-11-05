# SBAC math achievement levels, California, 2015–2025

An interactive page (`index.html`) showing California Smarter Balanced (CAASPP) results by achievement level. It has four views:

- **Statewide by student group.** Grade 11 math by default. Dropdowns switch the subject (math or English language arts) and the grade (3–8 and 11), show one chart per year or all years on one axis, and compare two student groups. A "follow a cohort" option strings together grade 3 in one year, grade 4 the next, and so on through grade 8 and then grade 11 three years later, drawn with the same level-stacked bars. Cohorts are named by their first and last tested grades (for example "Grade 3 in 2015 to grade 11 in 2023") and listed when at least two of their grades were tested. The 2020 gap is marked "No test" and 2021 is hatched; a note under the chart gives the share of enrolled students who tested in 2021. These are synthetic cohorts: each bar is everyone tested in that grade and year, not the same students followed.
- **High schools counted by the share of students at a level.**
- **High schools grouped by a school characteristic.**
- **One school at a time.**

The three school views show grade 11 math only; the school file holds no other grade or subject.

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

### `data.json`

What the page loads. Built by `scripts/build_page_data.py`; compact JSON, one object with these keys.

| key | contents |
|---|---|
| `years` | the ten test years in order: 2015–2019, 2021–2025 |
| `names` | group code → group name, for the 31 statewide groups the page offers |
| `state` | statewide **math**: grade → group code → year → `[students_tested, pct_level1, pct_level2, pct_level3, pct_level4]`. Grades 3–8 and 11. This block is unchanged from the first release of the page. |
| `state_ela` | the same layout for **English language arts** |
| `enrolled` | subject (`math`/`ela`) → grade → group code → year → `students_enrolled`. The page uses it for the share tested in 2021. |
| `cuts` | subject → grade → `[lowest_score, level2_from, level3_from, level4_from, highest_score]`, from `cut_scores.csv` |
| `schools` | one array per high school, grade 11 math only: `[school, district, county, region, school_type, charter, upp_pct_2017_2020, ag_completion_pct_classes_2017_2019, tract_median_household_income, tract_poverty_rate_pct, tract_pct_adults_bachelors, median_students_with_scores, rows]`, where `rows` is group code → list of `[year_index, students_with_scores, pct_level1, pct_level2, pct_level3, pct_level4]` and `year_index` indexes `years`. Suppressed rows are left out. |

Percentages in `state` and `state_ela` are as published (whole numbers in 2015 and 2016, two decimals from 2017); school percentages are rounded to one decimal.

## Scripts

- `scripts/build_page_data.py` rebuilds `data.json` from `data/`. Run it from the repository root. It needs only pandas.
- `scripts/check_page_data.py` checks `data.json` against the CSV files (every statewide row for both subjects, cut scores, level sums). Given an earlier copy of `data.json` (`git show main:data.json > old_data.json`, then `python scripts/check_page_data.py old_data.json`) it also checks that every block of the earlier file, and the math grade-11 block in particular, is reproduced exactly, byte for byte.
- `scripts/check_render.js` loads the page in headless Chromium (Node and Playwright needed: `npm install playwright` and `npx playwright install chromium`). It checks that every subject × grade × view combination renders without console errors, that every column in every cohort view adds to 100% of the axis, and, given an earlier `index.html` and `data.json` as arguments, that the default view's chart markup is identical to the earlier page.
- `scripts/example_analysis.py` is a starting point. It pools schools by UPP, compares the same schools in 2019 and 2025, and computes a within-school gap between economically disadvantaged students and their classmates.
- `scripts/provenance/` holds the scripts that produced the CSV files from the CDE raw files. Those raw files are not included; they are too large. The scripts read local paths and are kept as a record, not to be run from the repository.

## Checks

- `data.json` reproduces every statewide row of `statewide_levels.csv` for both subjects, and the `years`, `names`, `state` and `schools` blocks are byte-identical to the first release (`scripts/check_page_data.py`).
- Every subject × grade × view of the statewide figure renders without console errors, and the cohort view's stacked bars add to 100% in every drawn column, for every cohort, subject, level mode and a comparison group (`scripts/check_render.js`).
- Pooling the school rows for all students reproduces the statewide level shares within 0.4 percentage points in every year.
- With charter schools left out, the pooled school rows match the state's district totals within 0.2 points for San Diego Unified and Fresno Unified.
- Economically disadvantaged plus not disadvantaged equals all students at every school and year.

## Sources

California Department of Education: CAASPP Smarter Balanced research files 2015–2025 (statewide and school rows); public schools directory; LCFF unduplicated pupil counts; adjusted cohort graduation files (A–G). U.S. Census Bureau: American Community Survey five-year estimates. CAASPP Smarter Balanced Technical Report 2016–17 (cut scores).
