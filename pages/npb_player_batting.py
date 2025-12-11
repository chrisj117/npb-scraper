"""Displays NPB batting data with Streamlit"""

import streamlit as st
import pages.helper as hp


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
    lead_bat_df = hp.load_csv(st.secrets["2025LeadersBR_link"])
    player_bat_df = hp.load_csv(st.secrets["2025StatsFinalBR_link"])

    # Split filters away from dataframe
    with st.container(border=True):
        # Smaller filters split by cols, larger filters receive exclusive cols
        r1c1, r1c2, r1c3 = st.columns([2, 1, 6], vertical_alignment="center")

        with r1c1:
            leader_view = st.toggle("Qualifiers")
            if leader_view is True:
                display_df = lead_bat_df.drop("#", axis=1)
            else:
                display_df = player_bat_df
            display_df = display_df.fillna(value={"Pos": "N/A"})
            user_pa = hp.create_pa_filter(display_df, "player")
            # Drop players below PA threshold
            display_df = display_df.drop(
                display_df[display_df.PA < user_pa].index
            )
        with r1c2:
            user_league = hp.create_league_filter(mode="npb")
            user_batting_hand = hp.create_hand_filter("player_bat")
        with r1c3:
            user_pos = hp.create_pos_filter(display_df, mode="player_bat")

        user_team = hp.create_team_filter(mode="npb")
        user_cols = hp.create_stat_cols_filter(display_df, mode="player_bat")

    # Apply filters
    display_df = display_df[display_df["Pos"].isin(user_pos)]
    display_df = display_df[display_df["B"].isin(user_batting_hand)]
    display_df = display_df[display_df["League"].isin(user_league)]
    display_df = display_df[display_df["Team"].isin(user_team)]

    # Convert to best matched type and use column_config for trailing zeroes
    display_df = hp.convert_pct_cols_to_float(display_df)
    display_df = display_df.convert_dtypes()

    # Display dataframe
    st.dataframe(
        display_df[user_cols],
        width='stretch',
        hide_index=True,
        row_height=25,
        column_order=user_cols,
        column_config=hp.get_column_config("BR"),
    )


if __name__ == "__main__":
    main()
