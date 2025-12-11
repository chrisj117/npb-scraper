"""Displays subsets of leaders in key statistics using Streamlit"""

import streamlit as st
import pandas as pd
import pages.helper as hp


def main():
    """
    Main entry point for the Streamlit NPB leader overview.

    Displays league and statistic type filters. Generates league-wide
    dashboards. Depending on what league(s) are selected, players are ranked
    relative to others within that current selection (for example, a player
    might be #1 when only filtered for Central, but #5 with both leagues
    enabled).

    Returns:
        None
    """
    st.set_page_config(layout="wide")
    lead_bat_df = hp.load_csv(st.secrets["2025LeadersBR_link"])
    player_bat_df = hp.load_csv(st.secrets["2025StatsFinalBR_link"])
    lead_pitch_df = hp.load_csv(st.secrets["2025LeadersPR_link"])
    player_pitch_df = hp.load_csv(st.secrets["2025StatsFinalPR_link"])
    st.title("NPB Leaders")

    # Dict of stats and what dataframes they come from
    # Ordered from left to right, first to last in desired appearance
    bat_stat_dict = {
        "AVG": lead_bat_df,
        "OBP": lead_bat_df,
        "SLG": lead_bat_df,
        "OPS": lead_bat_df,
        "HR": player_bat_df,
        "RBI": player_bat_df,
        "H": player_bat_df,
        "R": player_bat_df,
        "SB": player_bat_df,
        "SO": player_bat_df,
        "BB": player_bat_df,
        "BB/K": lead_bat_df,
    }
    pitch_stat_dict = {
        "ERA": lead_pitch_df,
        "FIP": lead_pitch_df,
        "WHIP": lead_pitch_df,
        "IP": player_pitch_df,
        "W": player_pitch_df,
        "SHO": player_pitch_df,
        "G": player_pitch_df,
        "HLD": player_pitch_df,
        "SV": player_pitch_df,
        "SO": player_pitch_df,
        "BB": player_pitch_df,
        "K-BB%": lead_pitch_df,
        "GB%": lead_pitch_df,
        "CSW%": lead_pitch_df,
        "FB Velo": player_pitch_df,
    }
    flip_rank_stats = ["ERA", "FIP", "WHIP"]

    # User filters
    stat_col1, stat_col2 = st.columns([1.5, 8.5], vertical_alignment="center")
    with stat_col1:
        stat_dicts = []
        user_bat_pitch = st.pills(
            "Statistics",
            ["Batting", "Pitching"],
            selection_mode="multi",
            default=["Batting", "Pitching"],
        )
        if "Batting" in user_bat_pitch:
            stat_dicts.append(bat_stat_dict)
        if "Pitching" in user_bat_pitch:
            stat_dicts.append(pitch_stat_dict)
    with stat_col2:
        user_league = hp.create_league_filter("npb")

    # Print mini dataframes in 3 columns
    r1c1, r1c2, r1c3 = st.columns([1, 1, 1], vertical_alignment="center")
    for stat_dict in stat_dicts:
        i = 0
        for key, value in stat_dict.items():
            # Distribute dataframes into each column
            if i % 3 == 0:
                chosen_col = r1c1
            elif i % 3 == 1:
                chosen_col = r1c2
            else:
                chosen_col = r1c3

            with chosen_col:
                # Display stat name and determine stat display/hover configs
                st.header(key)
                if value.equals(player_bat_df) or value.equals(lead_bat_df):
                    config = "BR"
                    name_col = "Player"
                elif value.equals(player_pitch_df) or value.equals(
                    lead_pitch_df
                ):
                    config = "PR"
                    name_col = "Pitcher"
                else:
                    config = ""
                    name_col = "Player"

                # Filter by league
                display_df = value[value["League"].isin(user_league)].copy()
                # Convert to correct notation for Streamlit
                display_df = hp.convert_pct_cols_to_float(display_df)
                # Rank by given column
                if key in flip_rank_stats:
                    display_df["Rank"] = display_df[key].rank(method="min")
                else:
                    display_df["Rank"] = display_df[key].rank(
                        method="min", ascending=False
                    )
                # Extract needed columns
                display_df = display_df[
                    ["Rank", name_col, key, "Team"]
                ].sort_values("Rank")

                chosen_col.dataframe(
                    display_df,
                    width='stretch',
                    hide_index=True,
                    row_height=25,
                    height=160,
                    column_config=hp.get_column_config(config),
                )
            i = i + 1


if __name__ == "__main__":
    main()
