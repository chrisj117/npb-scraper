"""Displays NPB pitcher percentiles with Streamlit"""

import streamlit as st
import pages.helper as hp


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
    st.set_page_config(layout="centered")

    # User input boxes
    r1c1, r1c2 = st.columns([1, 1])
    with r1c1:
        user_year = hp.create_year_filter()
        pitch_df = hp.load_csv(st.secrets[user_year + "StatsFinalPR_link"])
        # Drop all sub-5 IP players to help alleviate merging errors
        pitch_df = pitch_df.drop(pitch_df[pitch_df.IP < 5].index)
    with r1c2:
        drop_ip = hp.create_ip_filter(pitch_df, "percentile")
    # Drop players below IP threshold
    pitch_df = pitch_df.drop(pitch_df[pitch_df.IP < drop_ip].index)
    user_pitcher = hp.create_player_filter(pitch_df, "Pitcher")

    # Display data
    hp.display_player_percentile(pitch_df, user_pitcher, user_year, "PR")


if __name__ == "__main__":
    main()
