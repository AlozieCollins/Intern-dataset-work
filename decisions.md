# Data Quality Assessment — Decision Log

## Purpose

This document records the major judgement calls made during the development
of the HIV facility data quality assessment project and explains why each
decision was made.

The purpose is to make the analysis reproducible and explainable rather than
only documenting the final code.

---

# 1. Data Cleaning Decisions

## 1.1 Standardising State Names

### Decision
Standardise state names before performing analysis.

### Why
The same state could appear in different forms, such as:

- `AKWA IBOM`
- `AKWA-IBOM`
- different casing
- leading/trailing spaces

If these values were not standardised, pandas would treat them as different
states during grouping and aggregation.

### Impact
This prevents incorrect state-level totals and duplicate categories.

---

## 1.2 Standardising Facility Names and IDs

### Decision
Standardise `facility_name` and `facility_id` before analysis.

### Why
Facility identifiers are used to track facilities across months and across
datasets. Differences in formatting can cause the same facility to appear as
multiple facilities.

### Impact
This improves facility matching, duplicate detection, monthly completeness
checks and merging with the facility master list.

---

## 1.3 Treating Missing Values as Missing, Not Zero

### Decision
Convert blank values and representations such as:

- `N/A`
- `-`
- `NULL`
- `nil`
- whitespace

to missing values (`pd.NA`) rather than converting them to zero.

### Why
A missing value means that the facility did not provide a value. A zero means
the facility reported that the value was actually zero.

These two situations have different meanings in a health-data setting.

### Impact
This prevents artificially lowering or changing indicator values.

---

## 1.4 Converting Numeric Text to Numeric Values

### Decision
Clean numeric fields before calculations.

### Why
Some numeric values may contain commas, spaces or other formatting that
prevents pandas from treating them as numbers.

For example:

`1,500` should be interpreted as `1500`.

### Impact
This allows validation rules, aggregations and ratios to work correctly.

---

## 1.5 Parsing Dates Explicitly

### Decision
Convert `report_month` and `date_submitted` into pandas datetime values.

### Why
Dates may be stored as strings and may use different formats.

Using datetime values allows the analysis to:

- derive year/month/quarter
- check reporting periods
- check submission timeliness
- compare submission dates with reporting periods.

---

## 1.6 Using `errors="coerce"` for Invalid Dates

### Decision
Invalid date values are converted to missing values instead of stopping the
entire analysis.

### Why
One malformed date should not prevent the rest of the dataset from being
processed.

The invalid values can subsequently be identified as data-quality problems.

---

## 1.7 Removing Exact Duplicates

### Decision
Remove exact duplicate records.

### Why
If the same record appears more than once with exactly the same information,
counting both records would artificially inflate totals.

### Impact
The analysis uses one copy of an identical record.

---

## 1.8 Flagging Conflicting Facility-Month Duplicates

### Decision
Do not automatically delete facility-month records when duplicate records
contain different values.

### Why
Two records for the same facility and month may represent a genuine data
quality problem rather than harmless duplication.

Automatically deleting one could destroy potentially important information.

### Impact
Conflicting duplicates are treated as issues requiring investigation.

---

# 2. Facility Master List Decisions

## 2.1 Using an Outer Merge

### Decision
Use an outer merge when comparing the service dataset with the facility
master list.

### Why
The purpose is not only to find matching facilities. It is also to identify:

- facilities reporting but missing from the master list
- facilities in the master list that did not report.

### Impact
Both types of mismatch remain visible.

---

## 2.2 Using the Merge Indicator

### Decision
Use the merge indicator to classify records as:

- `both`
- `master-not-reporting`
- `reporting-not-master`

### Why
This makes facility linkage problems easier to identify and quantify.

---

# 3. Missing Data Decisions

## 3.1 Do Not Automatically Replace Missing Values With Zero

### Decision
Missing values remain missing unless there is a specific analytical reason
to treat them differently.

### Why
Replacing missing values with zero would assume that the facility reported
zero, which may be false.

### Impact
Completeness and indicator calculations remain more meaningful.

---

# 4. Validation Rule Decisions

The validation rules were designed around relationships that should normally
exist between related indicators.

---

## R1 — HTS Positives Cannot Exceed HTS Tests

### Rule
`hts_tst_pos <= hts_tst`

### Decision
Flag records where the number of positive tests is greater than the number
tested.

### Why
A positive result must come from the tested population.

---

## R2 — PMTCT Cascade Consistency

### Rule

`pmtct_stat_pos <= pmtct_stat`

and

`pmtct_art <= pmtct_stat_pos`

### Decision
Both relationships must hold.

### Why
The PMTCT cascade follows a logical sequence:

Testing/Status → Positive → ART.

A later stage cannot exceed the population entering the earlier stage.

---

## R3 — Viral Load Cascade Consistency

### Rule

`vl_result_received <= vl_eligible`

and

`vl_suppressed <= vl_result_received`

### Decision
Both relationships are checked.

### Why
A result cannot be received for more people than are eligible, and suppressed
results cannot exceed the number of results received.

---

## R4 — TB Positives Cannot Exceed TB Screened

### Rule
`tb_pos <= tb_screen`

### Decision
Flag records where TB-positive cases exceed people screened.

### Why
A positive case must be identified from the screened population.

---

## R5 — Negative Values

### Decision
Flag negative values in indicators where negative counts are not logically
possible.

### Why
Counts of people, tests, samples or service events should not normally be
negative.

---

## R6 — Positivity Yield

### Decision
Flag positivity yields outside the expected range of approximately
0.1%–15%.

### Why
Extremely low or high positivity may indicate reporting or data-entry
problems requiring investigation.

### Important judgement
This rule is treated as an anomaly flag rather than proof that the record is
incorrect.

---

## R7 — Sudden HTS Increase

### Decision
Flag month-to-month increases in `hts_tst` of 300% or more.

### Why
A very large sudden increase can indicate a reporting or data-entry anomaly.

### Important judgement
The rule identifies records for investigation; it does not automatically
declare the data false.

---

## R8 — 36 Monthly Records

### Decision
Check whether facilities have the expected 36 monthly records covering
2022–2024.

### Why
The dataset represents three years of monthly reporting.

36 expected months provides a simple measure of reporting completeness.

---

## R9 — Submission After Reporting Month

### Decision
Check whether the submission date occurs after the reporting period.

### Why
A report should not normally be submitted before the reporting period has
ended.

---

## R10 — Submission Within 15 Days

### Decision
Use 15 days after the reporting period as the timeliness threshold.

### Why
This provides a consistent definition for identifying late submissions.

---

## R11 — TX_CURR Reconciliation

### Rule

`previous TX_CURR + TX_NEW - TX_ML ≈ current TX_CURR`

### Decision
Use the previous reporting period's value to assess whether the current
`tx_curr` is approximately reconcilable.

### Why
Current patient population should generally be explainable by the previous
population plus new enrolments minus people leaving/transferring/missing
from treatment.

### Important judgement
The relationship is treated as an approximate reconciliation rather than an
absolute equality because programme data can contain legitimate differences,
timing issues and reporting inconsistencies.

---

# 5. Issue Log Decisions

## Decision
Store validation failures in a single issues log containing fields such as:

- `facility_id`
- `report_month`
- `rule`
- `issue`

### Why
A central issue log makes it possible to:

- count failures by rule
- identify affected facilities
- identify affected months
- export problems for investigation.

---

# 6. Indicator Calculation Decisions

## 6.1 Calculate Ratios From Aggregated Numerators and Denominators

### Decision
For grouped indicators, calculate:

`sum(numerator) / sum(denominator)`

rather than averaging individual facility percentages.

### Why
A simple average gives a small facility and a large facility equal weight.

Aggregating the underlying counts gives the overall population-level rate.

---

## 6.2 Exclude Records Failing Core Logical Rules

### Decision
Records failing the major logical consistency checks are excluded from
certain indicator calculations where the invalid values could distort the
indicator.

### Why
For example, if positives exceed tests, calculating positivity from that
record produces a misleading result.

### Important judgement
The records are not deleted from the dataset. They remain available in the
issues log for investigation.

---

# 7. Disaggregation Decisions

## 7.1 Standardise Sex Categories

### Decision
Standardise sex values to:

- Female
- Male

### Why
Different spellings or formatting would create separate categories.

---

## 7.2 Standardise Age Bands

### Decision
Use the agreed age groups:

- 0–14
- 15–24
- 25–35
- 36–50
- 50+

### Why
Consistent age categories are necessary for meaningful comparison between
datasets.

---

## 7.3 Compare Aggregated and Disaggregated Data Only for 2024

### Decision
Limit the comparison to 2024.

### Why
The available sex-age disaggregation dataset covers 2024, so comparing it
against years where disaggregation data is unavailable would be inappropriate.

---

## 7.4 Use Percentage Difference

### Decision
Compare aggregate and disaggregated HTS totals using percentage difference.

### Why
Absolute differences alone do not account for the size of the facility's
reported value.

A difference of 500 is much more important for a facility reporting 1,000
tests than for one reporting 50,000.

---

# 8. Reporting Completeness Decisions

## Decision
Calculate reporting completeness as:

`reports_received / reports_expected`

### Why
This provides a simple measure of how consistently facilities submit expected
reports.

### Important judgement
Expected reports must be defined carefully because a facility should not be
considered late or missing before it was expected to begin reporting.

---

# 9. Visualisation Decisions

## 9.1 National Monthly HTS Trend

### Decision
Plot monthly national HTS testing volume across the 36-month period.

### Why
A monthly trend makes changes in testing activity visible.

---

## 9.2 Three-Month Rolling Average

### Decision
Add a 3-month rolling average.

### Why
Monthly health-programme data can fluctuate considerably.

A rolling average makes the underlying trend easier to see without removing
the original monthly values.

---

## 9.3 Plot Positives Separately

### Decision
Create a separate monthly trend for HTS positives.

### Why
Testing volume and positive results measure different aspects of programme
performance and should not be confused.

---

## 9.4 Facility-by-Month Completeness Heatmap

### Decision
Use a facility × month heatmap to visualise missing reporting periods.

### Why
A heatmap makes patterns of missing months much easier to identify than a
large table.

---

# 10. Laboratory TAT Decisions

## 10.1 Separate Laboratory Turnaround Stages

### Decision
Calculate:

1. Collection → laboratory receipt
2. Laboratory receipt → patient handover
3. Total turnaround time

### Why
A long total turnaround time does not explain where the delay occurred.

Separating the stages helps identify where operational bottlenecks exist.

---

## 10.2 Remove Duplicate Sample IDs

### Decision
Remove duplicate `sample_id` records when identifying unique samples.

### Why
Counting the same sample more than once would distort laboratory indicators.

---

## 10.3 Validate Viral Load Result Values

### Decision
Standardise result representations such as:

- TND
- Not detected
- <50
- LDL

### Why
These values represent meaningful viral-load result categories and need to be
interpreted consistently.

---

## 10.4 Flag Rejected Samples With Results

### Decision
Identify rejected samples that nevertheless have results.

### Why
This represents a potentially contradictory data state requiring
investigation.

---

## 10.5 Flag Valid Samples Without Results

### Decision
Identify valid samples for which no result was recorded.

### Why
This can indicate an incomplete laboratory workflow or missing data.

---

# 11. Age Validation

## Decision
Treat ages outside 0–120 as invalid and convert them to missing values.

### Why
These values are outside a reasonable human age range and are more likely to
represent data-entry errors.

### Important judgement
The value is not silently deleted from the record; it is converted to missing
so that the problem does not produce misleading demographic analysis.

---

# 12. PMTCT Analysis Decisions

## Decision
Analyse the PMTCT cascade using:

`pmtct_stat_pos / pmtct_stat`

and

`pmtct_art / pmtct_stat_pos`

### Why
These two ratios describe different stages of the cascade and help identify
where losses occur.

---

# 13. Viral Load Analysis Decisions

## Decision
Calculate VL coverage as:

`vl_result_received / vl_eligible`

and suppression using the suppressed population relative to the relevant VL
population.

### Why
Coverage and suppression answer different programme questions:

- Are eligible patients receiving VL results?
- Among those with results, how many are suppressed?

---

# 14. Data Preservation Decisions

## Decision
Keep the cleaned dataset separate from the issues log.

### Why
Cleaning and validation answer different questions.

The cleaned dataset represents the standardised data, while the issues log
documents potential quality problems.

Keeping both allows the analysis to remain auditable.

---

# 15. Command-Line Tool Decisions

## 15.1 Use `argparse`

### Decision
Allow the DQA script to accept:

`--input`

and

`--output`

from the command line.

### Why
The script should not depend on hardcoded file paths.

This makes it reusable with different datasets and output folders.

Example:

`python dqa.py --input data --output results_test`

---

## 15.2 Accept Both Files and Folders

### Decision
Allow `--input` to point either to a CSV file or a directory containing CSV
files.

### Why
This makes the tool more flexible for real-world use.

---

## 15.3 Automatically Identify the Main Service File

### Decision
When a directory is provided, look for a CSV containing
`facility_service_data` in its filename.

### Why
The project contains multiple CSV files, but the aggregate service file is
the primary input for the main DQA workflow.

---

## 15.4 Create Output Directory Automatically

### Decision
Use:

`os.makedirs(..., exist_ok=True)`

### Why
The user should not have to manually create the results directory every time
the script is run.

---

# 16. Error Handling Decisions

## Decision
Explicitly check whether the supplied input path exists.

### Why
Without this check, Python would produce a less useful error later in the
workflow.

A clear message such as:

`Input path does not exist: data/`

immediately identifies the problem.

---

# 17. `run_checks()` Design Decision

## Decision
Have `run_checks()` always return a DataFrame.

### Why
The main program expects to do things such as:

- `len(issues_log)`
- `issues_log.empty`
- `issues_log.to_csv()`
- `issues_log.to_excel()`

If `run_checks()` returns `None`, these operations fail.

### Final design

If issues exist:

```python
return pd.concat(issues, ignore_index=True)