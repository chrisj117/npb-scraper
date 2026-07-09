"""Displays NPB standings and daily score data with Streamlit"""

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

    # Filters
    user_year = hp.create_year_filter()

    # Streamlit dataframe displays
    create_central_standings(user_year)
    create_pacific_standings(user_year)
    create_daily_scores(user_year)


def create_central_standings(user_year):
    st.write("***Central Standings***")
    central_df = hp.load_csv(st.secrets[user_year + "StandingsFinalC_npb_link"])
    # Drop unwanted columns and reorder (must be before sort filters are made)
    central_df = hp.prepare_streamlit_col_order(central_df)
    styler_central = central_df.style
    styler_central.apply(hp.color_by_team, axis=0)
    styler_central = styler_central.set_properties(
        subset=["Team"], **{"font-weight": "bold"}
    )
    st.dataframe(
        styler_central,
        width="stretch",
        hide_index=True,
        row_height=25,
        column_config=hp.get_column_config("team_standings"),
    )


def create_pacific_standings(user_year):
    st.write("***Pacific Standings***")
    pacific_df = hp.load_csv(st.secrets[user_year + "StandingsFinalP_npb_link"])
    # Drop unwanted columns and reorder (must be before sort filters are made)
    pacific_df = hp.prepare_streamlit_col_order(pacific_df)
    styler_pacific = pacific_df.style
    styler_pacific.apply(hp.color_by_team, axis=0)
    styler_pacific = styler_pacific.set_properties(
        subset=["Team"], **{"font-weight": "bold"}
    )
    st.dataframe(
        styler_pacific,
        width="stretch",
        hide_index=True,
        row_height=25,
        column_config=hp.get_column_config("team_standings"),
    )


def create_daily_scores(user_year):
    st.write("***Daily Scores***")
    daily_df = hp.load_csv(st.secrets[user_year + "DailyScoresFinalR_link"])
    # Compress columns into one
    daily_df = daily_df.astype(str)
    daily_df["Scores"] = daily_df[["RunsHome", "RunsAway"]].agg(" - ".join, axis=1)
    # daily_df = daily_df.drop(["RunsHome", "RunsAway"])
    daily_df = daily_df.rename(
        {"HomeTeam": "Home Team", "AwayTeam": "Away Team"}, axis=1
    )

    styler_daily = daily_df[["Home Team", "Scores", "Away Team"]].style
    styler_daily.apply(hp.color_by_team, axis=0)
    styler_daily = styler_daily.set_properties(
        subset=["Home Team", "Away Team"], **{"font-weight": "bold"}
    )
    st.dataframe(
        styler_daily,
        width="content",
        hide_index=True,
        row_height=25,
        column_config=hp.get_column_config("daily_scores"),
    )


if __name__ == "__main__":
    main()
