"""Displays NPB standings and daily score data with Streamlit"""

import pages.helper as hp
import streamlit as st


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
    central_df = hp.load_csv(st.secrets["2025StandingsFinalC_link"])
    st.dataframe(
        central_df,
        use_container_width=True,
        hide_index=True,
        row_height=25,
        column_config=hp.get_column_config("standings"),
    )

    st.write("Pacific Standings")
    pacific_df = hp.load_csv(st.secrets["2025StandingsFinalP_link"])
    st.dataframe(
        pacific_df,
        use_container_width=True,
        hide_index=True,
        row_height=25,
        column_config=hp.get_column_config("standings"),
    )

    st.write("Latest Scores")
    daily_df = hp.load_csv(st.secrets["2025DailyScoresFinalR_link"])
    # Compress columns into one
    daily_df = daily_df.astype(str)
    daily_df["Scores"] = daily_df[["RunsHome", "RunsAway"]].agg(
        " - ".join, axis=1
    )
    daily_df["Results"] = daily_df[["HomeTeam", "Scores", "AwayTeam"]].agg(
        " ".join, axis=1
    )
    st.dataframe(
        daily_df["Results"],
        use_container_width=True,
        hide_index=True,
        row_height=25,
    )


if __name__ == "__main__":
    main()
