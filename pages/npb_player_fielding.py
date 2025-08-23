"""Displays NPB fielding data with Streamlit"""

import streamlit as st
import pages.helper as hp


def main():
    """
    Main entry point for the Streamlit NPB fielding dashboard.

    Loads player fielding statistics from GitHub for the 2025 season.
    Provides interactive filters for minimum innings played, league, position,
    team, and statistic columns. Applies user-selected filters and formats key
    fielding statistics for display. Shows the resulting fielding data in a
    Streamlit dataframe.

    Returns:
        None
    """
    st.set_page_config(layout="wide")
    display_df = hp.load_csv(
        "https://raw.githubusercontent.com/chrisj117/npb-scraper/refs/heads/"
        + "master/stats/2025/streamlit_src/2025FieldingFinalR.csv"
    )
    # Split filters away from dataframe
    with st.container(border=True):
        # Smaller filters split by cols, larger filters receive exclusive cols
        r1c1, r1c2, r1c3 = st.columns([2, 1, 6], vertical_alignment="center")

        with r1c1:
            user_inn = hp.create_inn_filter(display_df, mode="player")
            # Drop players below Inn threshold
            display_df = display_df.drop(
                display_df[display_df.Inn < user_inn].index
            )
        with r1c2:
            user_league = hp.create_league_filter(mode="npb")
        with r1c3:
            user_pos = hp.create_pos_filter(display_df, mode="player_field")
        user_team = hp.create_team_filter(mode="npb")
        user_cols = hp.create_stat_cols_filter(display_df, "player_field")

    # Apply filters
    display_df = display_df[display_df["Pos"].isin(user_pos)]
    display_df = display_df[display_df["League"].isin(user_league)]
    display_df = display_df[display_df["Team"].isin(user_team)]

    # Convert to best matched type and use column_config for trailing zeroes
    display_df = hp.convert_pct_cols_to_float(display_df)
    display_df = display_df.convert_dtypes()

    # Display dataframe
    st.dataframe(
        display_df[user_cols],
        use_container_width=True,
        row_height=25,
        hide_index=True,
        column_config=hp.get_column_config("RF"),
    )


if __name__ == "__main__":
    main()
