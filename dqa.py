import argparse
import os
import pandas as pd


def clean(df):
    """
    Clean the HIV facility reporting dataset.

    Cleaning includes:
    - Standardising text fields
    - Cleaning dates
    - Deriving year, month and quarter
    - Cleaning numeric columns
    - Standardising missing values
    - Removing exact duplicate rows
    - Flagging conflicting facility-month records
    """

    df = df.copy()


    text_cols = [
        "state",
        "facility_name",
        "facility_id"
    ]

    for col in text_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype("string")
                .str.strip()
                .str.upper()
            )

    if "state" in df.columns:
        state_mapping = {
            "FCT": "FCT",
            "FEDERAL CAPITAL TERRITORY": "FCT",
            'F.C.T.': "FCT",
            "CROSS-RIVER": "CROSS RIVER",
            "AKWA-IBOM": "AKWA IBOM"
        }

        df["state"] = df["state"].replace(state_mapping)

    

    missing_values = [
        "", "N/A", "-", 'NULL', "nil"
    ]

    df = df.replace(missing_values, pd.NA)

    

    if "report_month" in df.columns:

        df["report_month"] = pd.to_datetime(
            df["report_month"],
            format="mixed",
            dayfirst=True,
            errors="coerce"
        )

        # Derived date fields
        df["year"] = df["report_month"].dt.year
        df["month"] = df["report_month"].dt.month
        df["quarter"] = df["report_month"].dt.quarter

        # Check that report month is within 2022-2024
        df["date_valid_period"] = (
            df["report_month"].dt.year.between(2022, 2024)
        )

        # Check that report month is month-end
        df["date_is_month_end"] = (
            df["report_month"].dt.is_month_end
        )


    if "date_submitted" in df.columns:

        df["date_submitted"] = pd.to_datetime(
            df["date_submitted"],
            format="mixed",
            dayfirst=True,
            errors="coerce"
        )

    numeric_cols = [
        "hts_tst",
        "hts_tst_pos",
        "pmtct_stat",
        "pmtct_stat_pos",
        "pmtct_art",
        "vl_eligible",
        "vl_result_received",
        "vl_suppressed",
        "tb_screen",
        "tb_pos",
        "tx_curr",
        "tx_new",
        "tx_ml"
    ]

    for col in numeric_cols:

        if col in df.columns:

            df[col] = (
                df[col]
                .astype("string")
                .str.replace(",", "", regex=False)
                .str.strip()
            )

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )


    df = df.drop_duplicates().reset_index(drop=True)

    return df


def run_checks(df):
    """
    Run validation rules R1-R11.

    Returns an issues log containing:
    facility_id, report_month, rule and issue.
    """

    df = df.copy()

    issues = []

    def add_issue(mask, rule, message):

        if mask.any():

            columns = []

            if "facility_id" in df.columns:
                columns.append("facility_id")

            if "report_month" in df.columns:
                columns.append("report_month")

            problem_rows = df.loc[mask, columns].copy()

            problem_rows["rule"] = rule
            problem_rows["issue"] = message

            issues.append(problem_rows)

    if "hts_tst" in df.columns and "hts_tst_pos" in df.columns:

        mask = (
            df["hts_tst_pos"].notna()
            & df["hts_tst"].notna()
            & (df["hts_tst_pos"] > df["hts_tst"])
        )

        add_issue(
            mask,
            "R1",
            "hts_tst_pos exceeds hts_tst"
        )



    if {
        "pmtct_stat",
        "pmtct_stat_pos",
        "pmtct_art"
    }.issubset(df.columns):

        mask_1 = (
            df["pmtct_stat_pos"].notna()
            & df["pmtct_stat"].notna()
            & (
                df["pmtct_stat_pos"]
                > df["pmtct_stat"]
            )
        )

        mask_2 = (
            df["pmtct_art"].notna()
            & df["pmtct_stat_pos"].notna()
            & (
                df["pmtct_art"]
                > df["pmtct_stat_pos"]
            )
        )

        add_issue(
            mask_1 | mask_2,
            "R2",
            "PMTCT cascade relationship is invalid"
        )



    if {
        "vl_eligible",
        "vl_result_received",
        "vl_suppressed"
    }.issubset(df.columns):

        mask_1 = (
            df["vl_result_received"].notna()
            & df["vl_eligible"].notna()
            & (
                df["vl_result_received"]
                > df["vl_eligible"]
            )
        )

        mask_2 = (
            df["vl_suppressed"].notna()
            & df["vl_result_received"].notna()
            & (
                df["vl_suppressed"]
                > df["vl_result_received"]
            )
        )

        add_issue(
            mask_1 | mask_2,
            "R3",
            "Viral load cascade relationship is invalid"
        )



    if {
        "tb_pos",
        "tb_screen"
    }.issubset(df.columns):

        mask = (
            df["tb_pos"].notna()
            & df["tb_screen"].notna()
            & (
                df["tb_pos"]
                > df["tb_screen"]
            )
        )

        add_issue(
            mask,
            "R4",
            "tb_pos exceeds tb_screen"
        )



    indicator_cols = [
        "hts_tst",
        "hts_tst_pos",
        "pmtct_stat",
        "pmtct_stat_pos",
        "pmtct_art",
        "vl_eligible",
        "vl_result_received",
        "vl_suppressed",
        "tb_screen",
        "tb_pos",
        "tx_curr",
        "tx_new",
        "tx_ml"
    ]

    available_indicator_cols = [
        col for col in indicator_cols
        if col in df.columns
    ]

    if available_indicator_cols:

        negative_mask = (
            df[available_indicator_cols]
            .lt(0)
            .any(axis=1)
        )

        add_issue(
            negative_mask,
            "R5",
            "One or more indicators contain a negative value"
        )



    if {
        "hts_tst",
        "hts_tst_pos"
    }.issubset(df.columns):

        positivity_yield = (
            df["hts_tst_pos"]
            / df["hts_tst"]
            * 100
        )

        mask = (
            df["hts_tst"].notna()
            & df["hts_tst_pos"].notna()
            & (df["hts_tst"] > 0)
            & (
                (positivity_yield < 0.1)
                | (positivity_yield > 15)
            )
        )

        add_issue(
            mask,
            "R6",
            "HIV positivity yield is outside 0.1%-15%"
        )

    
    if {
        "facility_id",
        "report_month",
        "hts_tst"
    }.issubset(df.columns):

        temp = df.sort_values(
            ["facility_id", "report_month"]
        ).copy()

        temp["previous_hts_tst"] = (
            temp.groupby("facility_id")["hts_tst"]
            .shift(1)
        )

        temp["hts_change_pct"] = (
            (
                temp["hts_tst"]
                - temp["previous_hts_tst"]
            )
            / temp["previous_hts_tst"]
            * 100
        )

        mask = (
            temp["previous_hts_tst"].notna()
            & (temp["previous_hts_tst"] > 0)
            & temp["hts_tst"].notna()
            & (temp["hts_change_pct"] >= 300)
        )

        problem_rows = temp.loc[
            mask,
            ["facility_id", "report_month"]
        ].copy()

        problem_rows["rule"] = "R7"
        problem_rows["issue"] = (
            "Month-on-month change in hts_tst "
            "is 300% or greater"
        )

        issues.append(problem_rows)

    
    if {
        "facility_id",
        "report_month"
    }.issubset(df.columns):

        facility_months = (
            df.groupby("facility_id")["report_month"]
            .nunique()
        )

        incomplete_facilities = (
            facility_months[
                facility_months < 36
            ]
        )

        for facility_id in incomplete_facilities.index:

            problem_rows = pd.DataFrame({
                "facility_id": [facility_id],
                "report_month": [pd.NaT],
                "rule": ["R8"],
                "issue": [
                    f"Facility has only "
                    f"{incomplete_facilities.loc[facility_id]} "
                    f"monthly records instead of 36"
                ]
            })

            issues.append(problem_rows)

    
    if {
        "report_month",
        "date_submitted"
    }.issubset(df.columns):

        period_end = (
            df["report_month"]
            + pd.offsets.MonthEnd(0)
        )

        mask = (
            df["date_submitted"].notna()
            & df["report_month"].notna()
            & (
                df["date_submitted"]
                <= period_end
            )
        )

        add_issue(
            mask,
            "R9",
            "date_submitted is not after the reporting period end"
        )

   
    if {
        "report_month",
        "date_submitted"
    }.issubset(df.columns):

        period_end = (
            df["report_month"]
            + pd.offsets.MonthEnd(0)
        )

        days_to_submit = (
            df["date_submitted"]
            - period_end
        ).dt.days

        mask = (
            df["date_submitted"].notna()
            & df["report_month"].notna()
            & (days_to_submit > 15)
        )

        add_issue(
            mask,
            "R10",
            "Report was submitted more than 15 days after period end"
        )

   
    if {
        "facility_id",
        "report_month",
        "tx_curr",
        "tx_new",
        "tx_ml"
    }.issubset(df.columns):

        temp = df.sort_values(
            ["facility_id", "report_month"]
        ).copy()

        temp["previous_tx_curr"] = (
            temp.groupby("facility_id")["tx_curr"]
            .shift(1)
        )

        temp["expected_tx_curr"] = (
            temp["previous_tx_curr"]
            + temp["tx_new"]
            - temp["tx_ml"]
        )

        # Difference between reported and expected
        temp["tx_curr_difference"] = (
            temp["tx_curr"]
            - temp["expected_tx_curr"]
        )

        
        tolerance = 0.05

        mask = (
            temp["previous_tx_curr"].notna()
            & temp["tx_curr"].notna()
            & temp["tx_new"].notna()
            & temp["tx_ml"].notna()
            & (
                temp["tx_curr_difference"].abs()
                > tolerance
            )
        )

        problem_rows = temp.loc[
            mask,
            ["facility_id", "report_month"]
        ].copy()

        problem_rows["rule"] = "R11"
        problem_rows["issue"] = (
            "tx_curr does not approximately equal "
            "previous tx_curr + tx_new - tx_ml"
        )

        issues.append(problem_rows)

 
    if issues:
        issues_log = pd.concat(
            issues,
            ignore_index=True
        )

    else:

        issues_log = pd.DataFrame(
            columns=[
                "facility_id",
                "report_month",
                "rule",
                "issue"
            ]
        )

    return issues_log


def main():

    parser = argparse.ArgumentParser(
        description="HIV Facility Data Quality Assessment"
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to input CSV file or folder"
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Folder where results will be saved"
    )

    args = parser.parse_args()

    
    os.makedirs(args.output, exist_ok=True)

    if os.path.isfile(args.input):

        df = pd.read_csv(args.input)

    elif os.path.isdir(args.input):

        csv_files = [
            file
            for file in os.listdir(args.input)
            if file.endswith(".csv")
        ]

        if not csv_files:
            raise FileNotFoundError(
                "No CSV files found in input folder."
            )


        aggregate_files = [
            file for file in csv_files
            if "facility_service_data" in file.lower()
        ]

        if aggregate_files:

            input_file = os.path.join(
                args.input,
                aggregate_files[0]
            )

        else:

            input_file = os.path.join(
                args.input,
                csv_files[0]
            )

        df = pd.read_csv(input_file)

    else:

        raise FileNotFoundError(
            f"Input path does not exist: {args.input}"
        )

    print(f"Input rows: {len(df):,}")

    clean_df = clean(df)

    print(f"Rows after cleaning: {len(clean_df):,}")

    issues_log = run_checks(clean_df)

    print(
        f"Validation issues found: "
        f"{len(issues_log):,}"
    )



    clean_df.to_csv(
        os.path.join(
            args.output,
            "cleaned_data.csv"
        ),
        index=False
    )

    issues_log.to_csv(
        os.path.join(
            args.output,
            "issues_log.csv"
        ),
        index=False
    )

    if not issues_log.empty:

        rule_summary = (
            issues_log["rule"]
            .value_counts()
            .rename_axis("rule")
            .reset_index(name="issue_count")
        )

    else:

        rule_summary = pd.DataFrame(
            columns=["rule", "issue_count"]
        )

    rule_summary.to_csv(
        os.path.join(
            args.output,
            "rule_summary.csv"
        ),
        index=False
    )

    report_path = os.path.join(
        args.output,
        "dqa_summary.xlsx"
    )

    with pd.ExcelWriter(report_path) as writer:

        rule_summary.to_excel(
            writer,
            sheet_name="Rule Summary",
            index=False
        )

        issues_log.to_excel(
            writer,
            sheet_name="Validation Issues",
            index=False
        )

        clean_df.to_excel(
            writer,
            sheet_name="Cleaned Data",
            index=False
        )

    print("\nDQA completed successfully.")
    print(f"Results saved to: {args.output}")



if __name__ == "__main__":
    main()
