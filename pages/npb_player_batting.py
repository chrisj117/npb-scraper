"""Displays NPB batting data with Streamlit"""

import pages.helper as hp
import streamlit as st


def main():
    """
    Main entry point for the Streamlit NPB batting dashboard.

    Loads player batting statistics (including leaders/qualifiers) from GitHub,
    then provides interactive filters for qualifiers, plate appearances,
    league, batting hand, position, team, and statistic columns. Applies
    user-selected filters to the data and formats key statistics for display.
    Shows the resulting batting data in a Streamlit dataframe.

    Returns:
        None
    """
    st.set_page_config(layout="wide")
    lead_bat_df = hp.load_csv(
        "https://raw.githubusercontent.com/chrisj117/npb-scraper/refs/heads/"
        + "master/stats/2025/streamlit_src/2025LeadersBR.csv"
    )
    player_bat_df = hp.load_csv(
        "https://raw.githubusercontent.com/chrisj117/npb-scraper/refs/heads/"
        + "master/stats/2025/streamlit_src/2025StatsFinalBR.csv"
    )

    # Split filters away from dataframe
    with st.container(border=True):
        # Smaller filters split by cols, larger filters receive exclusive cols
        r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(
            [1, 2, 1, 1.2, 7], vertical_alignment="center"
        )

        with r1c1:
            leader_view = st.toggle("Qualifiers")
            if leader_view is True:
                display_df = lead_bat_df.drop("Rank", axis=1)
            else:
                display_df = player_bat_df
        with r1c2:
            display_df = display_df.fillna(value={"Pos": "N/A"})
            user_pa = hp.create_pa_num_input(display_df, "player")
            # Drop players below PA threshold
            display_df = display_df.drop(
                display_df[display_df.PA < user_pa].index
            )
        with r1c3:
            user_league = hp.create_league_filter(mode="npb")
        with r1c4:
            user_batting_hand = hp.create_hand_filter("player_bat")
        with r1c5:
            user_pos = hp.create_pos_filter(display_df, mode="player_bat")

        user_team = hp.create_team_filter(mode="npb")
        user_cols = hp.create_stat_cols_filter(display_df, mode="player_bat")

    # Apply filters
    display_df = display_df[display_df["Pos"].isin(user_pos)]
    display_df = display_df[display_df["B"].isin(user_batting_hand)]
    display_df = display_df[display_df["League"].isin(user_league)]
    display_df = display_df[display_df["Team"].isin(user_team)]

    # Number formatting
    format_maps = {
        "OPS+": "{:.0f}",
        "AVG": "{:.3f}",
        "OBP": "{:.3f}",
        "SLG": "{:.3f}",
        "OPS": "{:.3f}",
        "ISO": "{:.3f}",
        "BABIP": "{:.3f}",
        "BB/K": "{:.2f}",
        "wSB": "{:.1f}",
    }
    for key, value in format_maps.items():
        display_df[key] = display_df[key].apply(value.format)

    nan_cols = ["BB/K", "BABIP"]
    for col in nan_cols:
        if col in display_df:
            display_df[col] = (
                display_df[col].astype(str).str.replace("nan", "")
            )

    # Display dataframe
    st.dataframe(
        display_df[user_cols],
        use_container_width=True,
        hide_index=True,
        row_height=25,
        column_order=user_cols,
    )


if __name__ == "__main__":
    main()
