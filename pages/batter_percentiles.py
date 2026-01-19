"""Displays NPB batter percentiles with Streamlit"""

import streamlit as st
import pandas as pd
import pages.helper as hp


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
    st.set_page_config(layout="centered")

    # User input boxes
    r1c1, r1c2 = st.columns([1, 1])
    with r1c1:
        user_year = hp.create_year_filter()
        bat_df = hp.load_csv(st.secrets[user_year + "StatsFinalBR_link"])
        field_df = hp.load_csv(st.secrets[user_year + "FieldingFinalR_link"])
        # Drop all sub-10 PA players to help alleviate merging errors
        bat_df = bat_df.drop(bat_df[bat_df.PA < 10].index)
    with r1c2:
        drop_pa = hp.create_pa_filter(bat_df, "percentile")
    # Drop players below PA threshold
    bat_df = bat_df.drop(bat_df[bat_df.PA < drop_pa].index)
    # Drop players that have no position (delayed fielding updates)
    bat_df = bat_df.dropna(subset=["Pos"])
    # Drop pitchers
    bat_df = bat_df.drop(bat_df[bat_df.Pos == "1"].index)
    user_player = hp.create_player_filter(bat_df, "Player")

    # Def Value stat calculation
    temp_df = field_df["Player"].drop_duplicates()
    # Each TZR in fielding must have Pos Adj applied to it
    field_df["TZR"] = field_df["TZR"].apply(pd.to_numeric, errors="coerce")
    field_df["TZR"] = field_df["TZR"].fillna(0)
    field_df["Pos Adj"] = field_df["Pos Adj"].apply(pd.to_numeric, errors="coerce")
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
    # Drop players with no recorded stat (NaNs), then sum + merge
    temp_df = pd.merge(
        temp_df,
        field_df.dropna(subset="RngR").groupby("Player", as_index=False)["RngR"].sum(),
        on="Player",
        how="left",
    )
    temp_df = pd.merge(
        temp_df,
        field_df.dropna(subset="ARM").groupby("Player", as_index=False)["ARM"].sum(),
        on="Player",
        how="left",
    )
    temp_df = pd.merge(
        temp_df,
        field_df.dropna(subset="DPR").groupby("Player", as_index=False)["DPR"].sum(),
        on="Player",
        how="left",
    )
    temp_df = pd.merge(
        temp_df,
        field_df.dropna(subset="Framing")
        .groupby("Player", as_index=False)["Framing"]
        .sum(),
        on="Player",
        how="left",
    )
    # Calculate Def Value (similar to TZR/143) and prep for plotting
    temp_df["Def Value"] = (temp_df["TZR"] / temp_df["Inn"]) * 1287
    cumulative_df = pd.merge(
        bat_df,
        temp_df[["Player", "Def Value", "RngR", "ARM", "DPR", "Framing", "Inn"]],
        on="Player",
        how="inner",
    )
    cumulative_df["Range"] = (cumulative_df["RngR"] / cumulative_df["Inn"]) * 1287
    cumulative_df["Arm"] = (cumulative_df["ARM"] / cumulative_df["Inn"]) * 1287
    cumulative_df["DPR"] = (cumulative_df["DPR"] / cumulative_df["Inn"]) * 1287
    cumulative_df["Framing"] = (cumulative_df["Framing"] / cumulative_df["Inn"]) * 1287

    # Number formatting
    format_maps = {
        "Range": "{:.1f}",
        "Arm": "{:.1f}",
        "DPR": "{:.1f}",
        "Framing": "{:.1f}",
        "Def Value": "{:.1f}",
        "ISO": "{:.3f}",
        "BABIP": "{:.3f}",
    }
    for key, value in format_maps.items():
        cumulative_df[key] = cumulative_df[key].apply(value.format)

    hp.display_player_percentile(cumulative_df, user_player, user_year, "BR")


if __name__ == "__main__":
    main()
