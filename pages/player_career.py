"""Displays NPB player career data with Streamlit"""

from datetime import datetime
import streamlit as st
import pandas as pd
import numpy as np
import pages.helper as hp


def main():
    """
    Main entry point for the Streamlit NPB player career overview page.

    Loads player biographical data, batting statistics, and pitching statistics
    from Dropbox-hosted CSV files. Provides an interactive interface with:

    - A player selection dropdown filtered to English-name entries
    - A vertical bio table showing player details (name, position, bats/throws, birthdate)
    - Batting and Pitching tabs, each containing:
        - A column filter for selecting which statistics to display
        - A season multiselect for filtering specific years
        - Dynamically recalculated totals/averages based on selected seasons
        - A styled dataframe with zebra striping and bolded totals row

    Batting stats include standard (H, HR, RBI, etc.) and advanced metrics (OPS+, BABIP,
    wSB, etc.). Pitching stats include standard (W, L, ERA, etc.) and advanced metrics
    (FIP, kwERA, CSW%, etc.). Percentage columns are normalized from decimal to whole-number
    format. Pitcher innings pitched (IP) values are converted between internal and display
    formats.

    Returns:
        None
    """
    st.set_page_config(layout="wide")
    career_bio_df = hp.load_csv(st.secrets["career_bio_link"])
    career_bat_df = hp.load_csv(st.secrets["career_bat_link"])
    career_pitch_df = hp.load_csv(st.secrets["career_pitch_link"])

    # Preprocess bio
    bio_display_df = career_bio_df.drop_duplicates(subset=["Link"])
    # Filter to only English names (ASCII characters)
    bio_display_df = bio_display_df[
        bio_display_df["Player"].str.contains(r"^[\x00-\x7F]+$", na=False)
    ]
    bio_display_df = bio_display_df.rename(
        {"T": "Throws", "B": "Bats", "BirthDate": "Born"}, axis=1
    )
    user_player = hp.create_player_filter(
        bio_display_df, "Player", key="career_player_names"
    )
    user_link = career_bio_df.loc[career_bio_df["Player"] == user_player, "Link"].iloc[
        0
    ]
    # Reset year selections when player changes
    if st.session_state.get("career_last_link") != user_link:
        st.session_state["career_last_link"] = user_link
        # Force-reset multiselect keys so they reflect the new player's years
        st.session_state["bat_year_selection"] = sorted(
            career_bat_df.loc[career_bat_df["Link"] == user_link, "Year"].tolist()
        )
        st.session_state["pitch_year_selection"] = sorted(
            career_pitch_df.loc[career_pitch_df["Link"] == user_link, "Year"].tolist()
        )
    # Convert bat positions to letter notation
    pos_dict = {
        "1": "P",
        "2": "C",
        "3": "1B",
        "4": "2B",
        "5": "3B",
        "6": "SS",
        "7": "LF",
        "8": "CF",
        "9": "RF",
        "DH": "DH",
        "UTL": "UTL",
        "N/A": "N/A",
    }
    career_bat_df["Pos"] = career_bat_df["Pos"].map(pos_dict).fillna("")
    # Create player bio table
    bio_display_df = bio_display_df[bio_display_df["Link"] == user_link]
    bio_display_df = bio_display_df.drop(["Unnamed: 0", "Link"], axis=1)

    # Get years where BF > 1 for this specific player
    pitch_years_with_bf = career_pitch_df[
        (career_pitch_df["Link"] == user_link) & (career_pitch_df["BF"] > 1)
    ]["Year"].unique()
    # Update Pos only for matching years in career_bat_df
    career_bat_df.loc[
        (career_bat_df["Link"] == user_link)
        & (career_bat_df["Year"].isin(pitch_years_with_bf))
        & (career_bat_df["Pos"].isna() | (career_bat_df["Pos"] == "")),
        "Pos",
    ] = "P"
    bio_display_df["Pos"] = (
        career_bat_df["Pos"][career_bat_df["Link"] == user_link]
        .drop_duplicates()
        .to_string(index=False)
        .replace("\n", " ")
        .strip()
    )

    # If the player has no pos in all years, drop the pos col
    if bio_display_df["Pos"].isna().all() or (bio_display_df["Pos"] == "").all():
        bio_display_df = bio_display_df.drop("Pos", axis=1)

    # Create a vertical table by transposing the dataframe
    transposed = bio_display_df.T.fillna("")
    # Make the original column names into a data column instead of index
    transposed = transposed.reset_index()
    transposed.columns = ["Player", user_player]
    transposed = transposed.drop(index=transposed.index[0])

    bat_tab, pitch_tab = st.tabs(["Batting", "Pitching"])
    with bat_tab:
        # Preprocess bat
        bat_display_df = normalize_pct_cols(career_bat_df)
        bat_display_df["Team"] = bat_display_df["Team"].str.split().str[0]
        bat_display_df = bat_display_df.merge(
            career_bio_df[["Link", "BirthDate"]], on="Link", how="left"
        )
        bat_display_df["Age"] = bat_display_df.apply(
            lambda row: (
                calculate_npb_age(pd.to_datetime(row["BirthDate"]), int(row["Year"]))
                if pd.notna(row["BirthDate"])
                else None
            ),
            axis=1,
        )

        # Split filters away from dataframe
        with st.container(border=True):
            bat_display_df = bat_display_df[bat_display_df["Link"] == user_link]
            bat_display_df = bat_display_df.drop(["Player"], axis=1)

            # Reorganize columns
            bat_display_df = bat_display_df[
                [
                    "Year",
                    "Age",
                    "Pos",
                    "Team",
                    "G",
                    "PA",
                    "AB",
                    "R",
                    "H",
                    "2B",
                    "3B",
                    "HR",
                    "TB",
                    "RBI",
                    "SB",
                    "CS",
                    "SH",
                    "SF",
                    "SO",
                    "BB",
                    "HP",
                    "GDP",
                    "AVG",
                    "OBP",
                    "SLG",
                    "OPS",
                    "OPS+",
                    "ISO",
                    "BABIP",
                    "K%",
                    "BB%",
                    "BB/K",
                    "wSB",
                    "PullAIR%",
                    "Chase%",
                    "Z-Con%",
                    "Swing%",
                    "SwStr%",
                    "TTO%",
                ]
            ]
            user_cols = hp.create_stat_cols_filter(
                bat_display_df, mode="career_bat_cols", key="career_bat_cols"
            )

        # Display dataframes
        r1c1, _ = st.columns([3, 7], vertical_alignment="center")
        with r1c1:
            # Convert to string and display with index hidden
            st.table(
                transposed.astype(str)
                .set_index("Player")
                .style.set_table_styles(
                    [
                        {
                            "selector": "thead th:nth-child(1)",
                            "props": [("width", "75px"), ("min-width", "75px")],
                        },
                        {
                            "selector": "thead th:nth-child(2)",
                            "props": [("color", "#31333f")],
                        },
                    ]
                )
            )

        # Use multiselect to choose which seasons to display
        available_years = sorted(bat_display_df["Year"].tolist())
        # Default options set by session state after user chooses player
        selected_years = st.multiselect(
            "Select seasons to display",
            options=available_years,
            key="bat_year_selection",
        )

        # Recalculate totals based on selected years
        filtered_df = bat_display_df[
            bat_display_df["Year"].isin(sorted(selected_years))
        ].copy()
        recalc_totals = recalculate_bat_totals(filtered_df, bat_display_df)

        filtered_df = filtered_df.sort_values(by=["Year"])
        # Reset index for row zebra coloring
        filtered_df = filtered_df.reset_index()
        for col, val in recalc_totals.items():
            # Ensure column type matches value's type
            if isinstance(val, float):
                filtered_df[col] = filtered_df[col].astype(float)
            elif isinstance(val, int):
                filtered_df[col] = filtered_df[col].astype(int)
            filtered_df.loc["Total", col] = val
        filtered_df = filtered_df.convert_dtypes()
        filtered_df["Year"] = (
            filtered_df["Year"].astype("Int64").astype(str).replace("<NA>", "")
        )
        filtered_df["Age"] = (
            filtered_df["Age"].astype("Int64").astype(str).replace("<NA>", "")
        )
        filtered_df.index = filtered_df.index.astype(str)

        st.dataframe(
            filtered_df[user_cols]
            .style.apply(apply_zebra_rows, axis=1)
            .apply(highlight_totals_row, axis=1),
            width="stretch",
            hide_index=True,
            row_height=25,
            height="content",
            column_order=user_cols,
            column_config=hp.get_column_config("B"),
        )

    with pitch_tab:
        # Preprocess pitch
        pitch_display_df = normalize_pct_cols(career_pitch_df)
        pitch_display_df["IP"] = hp.convert_ip_column_in(pitch_display_df)
        pitch_display_df["Team"] = pitch_display_df["Team"].str.split().str[0]
        pitch_display_df = pitch_display_df.merge(
            career_bio_df[["Link", "BirthDate"]], on="Link", how="left"
        )
        pitch_display_df["Age"] = pitch_display_df.apply(
            lambda row: (
                calculate_npb_age(pd.to_datetime(row["BirthDate"]), int(row["Year"]))
                if pd.notna(row["BirthDate"])
                else None
            ),
            axis=1,
        )

        # Split filters away from dataframe
        with st.container(border=True):
            pitch_display_df = pitch_display_df[pitch_display_df["Link"] == user_link]
            pitch_display_df = pitch_display_df.drop(["Pitcher"], axis=1)

            # Reorganize columns before passing to column filter to properly apply order
            pitch_display_df = pitch_display_df[
                [
                    "Year",
                    "Age",
                    "Team",
                    "G",
                    "W",
                    "L",
                    "SV",
                    "HLD",
                    "CG",
                    "SHO",
                    "BF",
                    "IP",
                    "H",
                    "HR",
                    "SO",
                    "BB",
                    "HB",
                    "WP",
                    "R",
                    "ER",
                    "ERA",
                    "FIP",
                    "kwERA",
                    "WHIP",
                    "ERA+",
                    "FIP-",
                    "kwERA-",
                    "Diff",
                    "HR%",
                    "K%",
                    "BB%",
                    "K-BB%",
                    "GB%",
                    "Chase%",
                    "Con%",
                    "SwStr%",
                    "CSW%",
                    "FB Velo",
                ]
            ]
            user_cols = hp.create_stat_cols_filter(
                pitch_display_df, mode="career_pitch_cols", key="career_pitch_cols"
            )

        # Display dataframes
        r1c1, _ = st.columns([3, 7], vertical_alignment="center")
        with r1c1:
            # Convert to string and display with index hidden
            st.table(
                transposed.astype(str)
                .set_index("Player")
                .style.set_table_styles(
                    [
                        {
                            "selector": "thead th:nth-child(1)",
                            "props": [("width", "75px"), ("min-width", "75px")],
                        },
                        {
                            "selector": "thead th:nth-child(2)",
                            "props": [("color", "#31333f")],
                        },
                    ]
                )
            )

        # Use multiselect to choose which seasons to display
        available_years = sorted(pitch_display_df["Year"].tolist())
        # Default options set by session state after user chooses player
        selected_years = st.multiselect(
            "Select seasons to display",
            options=available_years,
            key="pitch_year_selection",
        )

        # Recalculate totals based on selected years
        filtered_df = pitch_display_df[pitch_display_df["Year"].isin(selected_years)]
        recalc_totals = recalculate_pitch_totals(filtered_df, pitch_display_df)

        filtered_df = filtered_df.sort_values(by=["Year"])
        # Reset index for row zebra coloring
        filtered_df = filtered_df.reset_index()
        for col, val in recalc_totals.items():
            # Ensure column type matches value's type
            if isinstance(val, float):
                filtered_df[col] = filtered_df[col].astype(float)
            elif isinstance(val, int):
                filtered_df[col] = filtered_df[col].astype(int)
            filtered_df.loc["Total", col] = val
        filtered_df = filtered_df.convert_dtypes()
        filtered_df["Year"] = (
            filtered_df["Year"].astype("Int64").astype(str).replace("<NA>", "")
        )
        filtered_df["Age"] = (
            filtered_df["Age"].astype("Int64").astype(str).replace("<NA>", "")
        )
        filtered_df.index = filtered_df.index.astype(str)

        filtered_df["IP"] = hp.convert_ip_column_out(filtered_df)
        st.dataframe(
            filtered_df[user_cols]
            .style.apply(apply_zebra_rows, axis=1)
            .apply(highlight_totals_row, axis=1),
            width="stretch",
            hide_index=True,
            row_height=25,
            height="content",
            column_order=user_cols,
            column_config=hp.get_column_config("P"),
        )


def normalize_pct_cols(convert_df):
    """TODO docs"""
    # Convert to best matched type and use column_config for trailing zeroes
    for col in convert_df.columns.tolist():
        if "%" in col:
            # Convert to numeric first, coercing errors to NaN
            convert_df[col] = pd.to_numeric(convert_df[col], errors="coerce") * 100
    return convert_df


def highlight_totals_row(row):
    """Apply styling to highlight the Totals row"""
    if row.name == "Total":
        return ["font-weight:bold;"] * len(row)
    return [""] * len(row)


def calculate_npb_age(birthdate, year):
    """Calculates the age of a player based on their birthdate according to the standard
    for NPB (June 30th)

    Parameters:
    birthdate (datetime object): The birthdate of the player

    Returns:
    npb_age (int): The age of the player at the start of the NPB season"""
    cutoff = datetime(year, 6, 30)
    npb_age = (
        cutoff.year
        - birthdate.year
        - ((cutoff.month, cutoff.day) < (birthdate.month, birthdate.day))
    )
    return npb_age


def apply_zebra_rows(row):
    # row.name is the row index position for styler
    if row.name != "Total" and int(row.name) % 2:
        bg = "#f8f9fb"
    else:
        bg = "white"
    return [f"background-color: {bg}"] * len(row)


def wavg_ignore_missing(df, value_col, weight_col):
    """TODO: docstring"""
    # keep only rows where BOTH value and weight exist (and weight > 0)
    m = df[value_col].notna() & df[weight_col].notna() & (df[weight_col] > 0)
    if not m.any():
        return np.nan
    return np.average(df.loc[m, value_col], weights=df.loc[m, weight_col])


def recalculate_pitch_totals(selected_df, original_df):
    """Recalculate pitch totals based on selected rows only."""
    totals = {}

    # Basic sum stats
    numeric_cols = selected_df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        totals[col] = selected_df[col].sum()

    # Non-numeric columns that need special handling
    totals["Team"] = "Totals"
    totals["Year"] = np.nan
    totals["Age"] = np.nan

    # Recalculate rate stats from selected data
    ip_val = totals.get("IP", 0)
    if ip_val != 0:
        totals["ERA"] = (totals.get("ER", 0) * 9) / ip_val
        totals["WHIP"] = (totals.get("BB", 0) + totals.get("H", 0)) / ip_val
    else:
        totals["ERA"] = np.nan
        totals["WHIP"] = np.nan

    bf_val = totals.get("BF", 0)
    if bf_val != 0:
        totals["K%"] = (totals.get("SO", 0) / bf_val) * 100
        totals["BB%"] = (totals.get("BB", 0) / bf_val) * 100
        totals["K-BB%"] = totals["K%"] - totals["BB%"]
        totals["HR%"] = (totals.get("HR", 0) / bf_val) * 100
        totals["kwERA"] = 4.80 - (
            10 * ((totals.get("SO", 0) - totals.get("BB", 0)) / bf_val)
        )
    else:
        totals["K%"] = np.nan
        totals["BB%"] = np.nan
        totals["K-BB%"] = np.nan
        totals["HR%"] = np.nan
        totals["kwERA"] = np.nan

    # Weighted averages for advanced stats
    totals["ERA+"] = wavg_ignore_missing(selected_df, "ERA+", "BF")
    totals["kwERA-"] = wavg_ignore_missing(selected_df, "kwERA-", "BF")
    totals["FIP"] = wavg_ignore_missing(selected_df, "FIP", "BF")
    totals["FIP-"] = wavg_ignore_missing(selected_df, "FIP-", "BF")
    totals["Chase%"] = wavg_ignore_missing(selected_df, "Chase%", "BF")
    totals["Con%"] = wavg_ignore_missing(selected_df, "Con%", "BF")
    totals["CSW%"] = wavg_ignore_missing(selected_df, "CSW%", "BF")
    totals["FB Velo"] = wavg_ignore_missing(selected_df, "FB Velo", "BF")
    totals["GB%"] = wavg_ignore_missing(selected_df, "GB%", "BF")
    totals["SwStr%"] = wavg_ignore_missing(selected_df, "SwStr%", "BF")

    # Calculate Diff (ERA - FIP)
    if "FIP" in totals and "ERA" in totals:
        totals["Diff"] = totals["ERA"] - totals["FIP"]

    return totals


def recalculate_bat_totals(selected_df, original_df):
    """Recalculate pitch totals based on selected rows only."""
    totals = {}

    # Basic sum stats
    numeric_cols = selected_df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        totals[col] = selected_df[col].sum()

    # Non-numeric columns that need special handling
    totals["Team"] = "Totals"
    totals["Year"] = np.nan
    totals["Age"] = np.nan
    totals["Pos"] = ""

    # Recalculate rate stats from selected data
    ab_val = totals.get("AB", 0)
    if ab_val != 0:
        totals["SLG"] = totals.get("TB", 0) / ab_val
        totals["AVG"] = totals.get("H", 0) / ab_val
    else:
        totals["AVG"] = np.nan
        totals["SLG"] = np.nan
    obp_denominator = (
        totals.get("AB", 0)
        + totals.get("BB", 0)
        + totals.get("HP", 0)
        + totals.get("SF", 0)
    )
    if obp_denominator != 0:
        totals["OBP"] = (
            totals.get("H", 0) + totals.get("BB", 0) + totals.get("HP", 0)
        ) / obp_denominator
    else:
        totals["OBP"] = np.nan
    totals["OPS"] = totals.get("OBP", 0) + totals.get("SLG", 0)
    totals["ISO"] = totals.get("SLG", 0) - totals.get("AVG", 0)
    if totals.get("PA", 0) != 0:
        totals["K%"] = (totals.get("SO", 0) / totals.get("PA", 0)) * 100
        totals["BB%"] = (totals.get("BB", 0) / totals.get("PA", 0)) * 100
        totals["TTO%"] = (
            (totals.get("HR", 0) + totals.get("SO", 0) + totals.get("BB", 0))
            / totals.get("PA", 0)
        ) * 100
    else:
        totals["K%"] = np.nan
        totals["BB%"] = np.nan
        totals["TTO%"] = np.nan
    if totals.get("SO", 0) != 0:
        totals["BB/K"] = totals.get("BB", 0) / totals.get("SO", 0)
    else:
        totals["BB/K"] = np.nan

    babip_denominator = (
        totals.get("AB", 0)
        - totals.get("SO", 0)
        - totals.get("HR", 0)
        + totals.get("SF", 0)
    )
    if babip_denominator != 0:
        totals["BABIP"] = (totals.get("H", 0) - totals.get("HR", 0)) / babip_denominator
    else:
        totals["BABIP"] = np.nan

    # Weighted averages for advanced stats
    totals["OPS+"] = wavg_ignore_missing(selected_df, "OPS+", "PA")
    totals["PullAIR%"] = wavg_ignore_missing(selected_df, "PullAIR%", "PA")
    totals["Chase%"] = wavg_ignore_missing(selected_df, "Chase%", "PA")
    totals["Z-Con%"] = wavg_ignore_missing(selected_df, "Z-Con%", "PA")
    totals["Swing%"] = wavg_ignore_missing(selected_df, "Swing%", "PA")
    totals["SwStr%"] = wavg_ignore_missing(selected_df, "SwStr%", "PA")

    return totals


if __name__ == "__main__":
    main()
