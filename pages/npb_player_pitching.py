"""Displays NPB pitching data with Streamlit"""

import pages.helper as hp
import streamlit as st


def main():
    """
    Main entry point for the Streamlit NPB pitching dashboard.

    Loads player pitching statistics (including leaders/qualifiers) from
    GitHub. Provides interactive filters for qualifiers, minimum innings
    pitched (IP), league, pitching hand, team, and statistic columns. Applies
    user-selected filters and formats key pitching statistics for display.
    Shows the resulting pitching data in a Streamlit dataframe.

    Returns:
        None
    """
    st.set_page_config(layout="wide")
    lead_pitch_df = hp.load_csv(
        "https://raw.githubusercontent.com/chrisj117/npb-scraper/refs/heads/"
        + "master/stats/2025/streamlit_src/2025LeadersPR.csv"
    )
    player_pitch_df = hp.load_csv(
        "https://raw.githubusercontent.com/chrisj117/npb-scraper/refs/heads/"
        + "master/stats/2025/streamlit_src/2025StatsFinalPR.csv"
    )

    # Split filters away from dataframe
    with st.container(border=True):
        # Smaller filters split by cols, larger filters receive exclusive cols
        r1c1, r1c2, r1c3, r1c4 = st.columns(
            [1, 2, 1, 8.2], vertical_alignment="center"
        )

        leader_view = r1c1.toggle("Qualifiers")
        if leader_view is True:
            display_df = lead_pitch_df.drop("Rank", axis=1)
        else:
            display_df = player_pitch_df

        with r1c2:
            user_ip = hp.create_ip_num_input(display_df, mode="player")
            # Drop players below IP threshold
            display_df = display_df.drop(
                display_df[display_df.IP < user_ip].index
            )
        with r1c3:
            user_league = hp.create_league_filter(mode="npb")
        with r1c4:
            user_pitching_hand = hp.create_hand_filter(mode="player_pitch")
        user_team = hp.create_team_filter(mode="npb")
        user_cols = hp.create_stat_cols_filter(display_df, mode="player_pitch")

    # Apply filters
    display_df = display_df[display_df["T"].isin(user_pitching_hand)]
    display_df = display_df[display_df["League"].isin(user_league)]
    display_df = display_df[display_df["Team"].isin(user_team)]

    # Number formatting
    format_maps = {
        "IP": "{:.1f}",
        "Diff": "{:.2f}",
        "FIP": "{:.2f}",
        "WHIP": "{:.2f}",
        "kwERA": "{:.2f}",
        "ERA": "{:.2f}",
        "kwERA-": "{:.0f}",
        "ERA+": "{:.0f}",
        "FIP-": "{:.0f}",
    }
    for key, value in format_maps.items():
        display_df[key] = display_df[key].apply(value.format)

    # Display dataframe
    st.dataframe(
        display_df[user_cols],
        use_container_width=True,
        hide_index=True,
        row_height=25,
    )


if __name__ == "__main__":
    main()
