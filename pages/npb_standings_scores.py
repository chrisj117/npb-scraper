"""Displays NPB standings and daily score data with Streamlit"""

from datetime import datetime
import streamlit as st
import pages.helper as hp


def main():
    """
    Main entry point for the Streamlit NPB standings and daily score dashboard.

    Loads NPB standings and daily score statistics from GitHub. Formats
    statistics for display. Shows the resulting data in multiple Streamlit
    dataframes.

    Returns:
        None
    """
    st.set_page_config(layout="wide")
    st.write("Central Standings")
    central_df = hp.load_csv(
        st.secrets[str(datetime.now().year) + "StandingsFinalC_npb_link"]
    )
    st.dataframe(
        central_df.style.apply(hp.color_by_team, axis=0),
        width="stretch",
        hide_index=True,
        row_height=25,
        column_config=hp.get_column_config("standings"),
    )

    st.write("Pacific Standings")
    pacific_df = hp.load_csv(
        st.secrets[str(datetime.now().year) + "StandingsFinalP_npb_link"]
    )
    st.dataframe(
        pacific_df.style.apply(hp.color_by_team, axis=0),
        width="stretch",
        hide_index=True,
        row_height=25,
        column_config=hp.get_column_config("standings"),
    )

    st.write("Latest Scores")
    daily_df = hp.load_csv(
        st.secrets[str(datetime.now().year) + "DailyScoresFinalR_link"]
    )
    # Compress columns into one
    daily_df = daily_df.astype(str)
    daily_df["Scores"] = daily_df[["RunsHome", "RunsAway"]].agg(" - ".join, axis=1)
    daily_df["Results"] = daily_df[["HomeTeam", "Scores", "AwayTeam"]].agg(
        " ".join, axis=1
    )
    st.dataframe(
        daily_df["Results"],
        width="stretch",
        hide_index=True,
        row_height=25,
    )


if __name__ == "__main__":
    main()
