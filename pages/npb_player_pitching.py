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
        r1c1, r1c2 = st.columns([2, 7], vertical_alignment="center")

        with r1c1:
            leader_view = st.toggle("Qualifiers")
            if leader_view is True:
                display_df = lead_pitch_df.drop("Rank", axis=1)
            else:
                display_df = player_pitch_df
            user_ip = hp.create_ip_num_input(display_df, mode="player")
            # Drop players below IP threshold
            display_df = display_df.drop(
                display_df[display_df.IP < user_ip].index
            )
        with r1c2:
            user_league = hp.create_league_filter(mode="npb")
            user_pitching_hand = hp.create_hand_filter(mode="player_pitch")
        user_team = hp.create_team_filter(mode="npb")
        user_cols = hp.create_stat_cols_filter(display_df, mode="player_pitch")

    # Apply filters
    display_df = display_df[display_df["T"].isin(user_pitching_hand)]
    display_df = display_df[display_df["League"].isin(user_league)]
    display_df = display_df[display_df["Team"].isin(user_team)]

    # Convert to best matched type and use column_config for trailing zeroes
    display_df = hp.convert_pct_cols_to_float(display_df)
    display_df = display_df.convert_dtypes()

    # Display dataframe
    st.dataframe(
        display_df[user_cols],
        use_container_width=True,
        hide_index=True,
        row_height=25,
        column_config={
            "K%": st.column_config.NumberColumn(
                format="%.1f%%",
                # help="potential stat explanation",
            ),
            "HR%": st.column_config.NumberColumn(
                format="%.1f%%",
            ),
            "BB%": st.column_config.NumberColumn(
                format="%.1f%%",
            ),
            "K-BB%": st.column_config.NumberColumn(
                format="%.1f%%",
            ),
            "IP": st.column_config.NumberColumn(
                format="%.1f",
            ),
            "ERA": st.column_config.NumberColumn(
                format="%.2f",
            ),
            "FIP": st.column_config.NumberColumn(
                format="%.2f",
            ),
            "kwERA": st.column_config.NumberColumn(
                format="%.2f",
            ),
            "WHIP": st.column_config.NumberColumn(
                format="%.2f",
            ),
            "Diff": st.column_config.NumberColumn(
                format="%.2f",
            ),
        },
    )


if __name__ == "__main__":
    main()
