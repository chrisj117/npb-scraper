"""Displays NPB pitcher percentiles with Streamlit"""

import pages.helper as hp
import streamlit as st


def main():
    """
    Main entry point for the Streamlit NPB pitcher percentile dashboard.

    Loads pitching data from GitHub, allows user selection of year,
    minimum innings pitched, and player. Displays a percentile bar chart and 
    raw statistics for the selected player using the 
    display_player_percentile() function.

    Returns:
        None
    """
    pitch_df = hp.load_csv(
        "https://raw.githubusercontent.com/chrisj117/npb-scraper/refs/heads/"
        + "master/stats/2025/streamlit_src/2025StatsFinalPR.csv"
    )
    # Drop all sub-5 IP players to help alleviate merging errors
    pitch_df = pitch_df.drop(
        pitch_df[pitch_df.IP < 5].index
    )

    # User input boxes
    year_list = ["2025"]
    year = st.selectbox("Year", year_list)
    drop_ip = st.number_input(
        "Minimum innings pitched",
        value=25.0,
        min_value=10.0,
        step=25.0,
        max_value=pitch_df["IP"].max(),
        format="%0.1f",
    )
    pitch_df = pitch_df.drop(pitch_df[pitch_df.IP < drop_ip].index)
    pitch_df = pitch_df.sort_values('Pitcher')
    pitcher_list = pitch_df["Pitcher"]
    pitcher = st.selectbox("Pitcher", pitcher_list)

    # Number formatting
    format_maps = {
        "WHIP": "{:.2f}",
    }
    for key, value in format_maps.items():
        pitch_df[key] = pitch_df[key].apply(value.format)

    # Display data
    hp.display_player_percentile(pitch_df, pitcher, year, "PR")
    st.caption("[Yakyu Cosmopolitan](https://www.yakyucosmo.com/)")


if __name__ == "__main__":
    main()
