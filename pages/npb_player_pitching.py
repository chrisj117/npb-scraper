"""Displays NPB pitching data with Streamlit"""

import streamlit as st
import pages.helper as hp


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
    lead_pitch_df = hp.load_csv(st.secrets["2025LeadersPR_link"])
    player_pitch_df = hp.load_csv(st.secrets["2025StatsFinalPR_link"])

    # Split filters away from dataframe
    with st.container(border=True):
        # Smaller filters split by cols, larger filters receive exclusive cols
        r1c1, r1c2 = st.columns([2, 7], vertical_alignment="center")

        with r1c1:
            leader_view = st.toggle("Qualifiers")
            if leader_view is True:
                display_df = lead_pitch_df.drop("#", axis=1)
            else:
                display_df = player_pitch_df
            user_ip = hp.create_ip_filter(display_df, mode="player")
            # Drop players below IP threshold
            display_df = display_df.drop(
                display_df[display_df.IP < user_ip].index
            )
        with r1c2:
            user_league = hp.create_league_filter(mode="npb")
            user_pitching_hand = hp.create_hand_filter(mode="player_pitch")
        user_team = hp.create_team_filter(mode="npb")
        user_cols = hp.create_stat_cols_filter(display_df, mode="player_pitch")

        # Sorting options
        user_sort_col, user_sort_asc = hp.create_sort_filter(
            user_cols, mode="pitch"
        )

    # Apply filters
    display_df = display_df[display_df["T"].isin(user_pitching_hand)]
    display_df = display_df[display_df["League"].isin(user_league)]
    display_df = display_df[display_df["Team"].isin(user_team)]

    # Convert to best matched type and use column_config for trailing zeroes
    display_df = hp.convert_pct_cols_to_float(display_df)
    display_df = display_df.convert_dtypes()

    # Apply sorting and reset index (must be after convert_pct_cols_to_float())
    display_df = display_df.sort_values(
        user_sort_col, ascending=user_sort_asc
    ).reset_index(drop=True)
    display_df.index += 1

    # Display dataframe
    st.dataframe(
        display_df[user_cols].style.highlight_between(
            color="#F8F9FB", subset=user_sort_col, axis="columns"
        ),
        width="stretch",
        hide_index=False,
        row_height=25,
        column_order=user_cols,
        column_config=hp.get_column_config("PR"),
    )


if __name__ == "__main__":
    main()
