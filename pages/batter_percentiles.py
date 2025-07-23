"""Displays NPB batter percentiles with Streamlit"""

import pages.helper as hp
import streamlit as st
import pandas as pd


def main():
    """
    Main entry point for the Streamlit NPB batter percentile dashboard.

    Loads batting and fielding data from GitHub, allows user selection of year,
    minimum plate appearances, and player. Calculates a custom defense metric
    for each player by combining fielding stats. Merges batting and defense
    data, then displays a percentile bar chart and raw statistics for the
    selected player using the display_player_percentile() function.

    Returns:
        None
    """
    bat_df = hp.load_csv(
        "https://raw.githubusercontent.com/chrisj117/npb-scraper/refs/heads/"
        + "master/stats/2025/streamlit_src/2025StatsFinalBR.csv"
    )
    field_df = hp.load_csv(
        "https://raw.githubusercontent.com/chrisj117/npb-scraper/refs/heads/"
        + "master/stats/2025/streamlit_src/2025FieldingFinalR.csv"
    )
    # Drop all sub-10 PA players to help alleviate merging errors
    bat_df = bat_df.drop(bat_df[bat_df.PA < 10].index)

    # User input boxes
    year_list = ["2025"]
    year = st.selectbox("Year", year_list)
    drop_pa = st.number_input(
        "Minimum plate appearances",
        value=50,
        min_value=25,
        step=50,
        max_value=bat_df["PA"].max(),
    )
    # Drop players below PA threshold
    bat_df = bat_df.drop(bat_df[bat_df.PA < drop_pa].index)
    bat_df = bat_df.sort_values("Player")
    player_list = bat_df["Player"]
    player = st.selectbox("Player", player_list)

    # Def Value stat calculation
    temp_df = field_df["Player"].drop_duplicates()
    # Each TZR in fielding must have Pos Adj applied to it
    field_df["TZR"] = field_df["TZR"].apply(pd.to_numeric, errors="coerce")
    field_df["TZR"] = field_df["TZR"].fillna(0)
    field_df["Pos Adj"] = field_df["Pos Adj"].apply(
        pd.to_numeric, errors="coerce"
    )
    field_df["TZR"] = field_df["TZR"] + field_df["Pos Adj"]
    # Combine all TZRs and Inn per player
    temp_df = pd.merge(
        temp_df,
        field_df.groupby("Player", as_index=False)["TZR"].sum(),
        on="Player",
    )
    temp_df = pd.merge(
        temp_df,
        field_df.groupby("Player", as_index=False)["Inn"].sum(),
        on="Player",
    )
    temp_df = pd.merge(
        temp_df,
        field_df.groupby("Player", as_index=False)["RngR"].sum(),
        on="Player",
    )
    temp_df = pd.merge(
        temp_df,
        field_df.groupby("Player", as_index=False)["ARM"].sum(),
        on="Player",
    )
    temp_df = pd.merge(
        temp_df,
        field_df.groupby("Player", as_index=False)["DPR"].sum(),
        on="Player",
    )
    temp_df = pd.merge(
        temp_df,
        field_df.groupby("Player", as_index=False)["Framing"].sum(),
        on="Player",
    )
    # Calculate Def Value (similar to TZR/143) and prep for plotting
    temp_df["Def Value"] = (temp_df["TZR"] / temp_df["Inn"]) * 1287
    cumulative_df = pd.merge(
        bat_df,
        temp_df[
            ["Player", "Def Value", "RngR", "ARM", "DPR", "Framing", "Inn"]
        ],
        on="Player",
        how="inner",
    )
    cumulative_df["Range"] = (
        cumulative_df["RngR"] / cumulative_df["Inn"]
    ) * 1287
    cumulative_df["Arm"] = (cumulative_df["ARM"] / cumulative_df["Inn"]) * 1287
    cumulative_df["DPR"] = (cumulative_df["DPR"] / cumulative_df["Inn"]) * 1287
    cumulative_df["Framing"] = (
        cumulative_df["Framing"] / cumulative_df["Inn"]
    ) * 1287

    # Number formatting
    format_maps = {
        "Range": "{:.1f}",
        "Arm": "{:.1f}",
        "DPR": "{:.1f}",
        "Framing": "{:.1f}",
        "Def Value": "{:.1f}",
    }
    for key, value in format_maps.items():
        cumulative_df[key] = cumulative_df[key].apply(value.format)

    hp.display_player_percentile(cumulative_df, player, year, "BR")
    st.caption("[Yakyu Cosmopolitan](https://www.yakyucosmo.com/)")


if __name__ == "__main__":
    main()
