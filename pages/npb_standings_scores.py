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
    central_df = hp.load_csv(
        "https://raw.githubusercontent.com/chrisj117/npb-scraper/refs/heads/"
        + "master/stats/2025/streamlit_src/2025StandingsFinalC.csv"
    )
    st.dataframe(
        central_df,
        use_container_width=True,
        hide_index=True,
        row_height=25,
        column_config=hp.get_column_config("standings"),
    )

    st.write("Pacific Standings")
    pacific_df = hp.load_csv(
        "https://raw.githubusercontent.com/chrisj117/npb-scraper/refs/heads/"
        + "master/stats/2025/streamlit_src/2025StandingsFinalP.csv"
    )
    st.dataframe(
        pacific_df,
        use_container_width=True,
        hide_index=True,
        row_height=25,
        column_config=hp.get_column_config("standings"),
    )

    st.write("Latest Scores")
    display_df = hp.load_csv(
        "https://raw.githubusercontent.com/chrisj117/npb-scraper/refs/heads/"
        + "master/stats/2025/streamlit_src/2025DailyScoresFinalR.csv"
    )
    # Compress columns into one
    display_df = display_df.astype(str)
    display_df["Scores"] = display_df[["RunsHome", "RunsAway"]].agg(
        " - ".join, axis=1
    )
    display_df["Results"] = display_df[["HomeTeam", "Scores", "AwayTeam"]].agg(
        " ".join, axis=1
    )
    st.dataframe(
        display_df["Results"],
        use_container_width=True,
        hide_index=True,
        row_height=25,
    )


if __name__ == "__main__":
    main()
