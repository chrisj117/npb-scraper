"""Displays subsets of leaders in key statistics using Streamlit"""

import time
import streamlit as st
import pages.helper as hp


def main():
    """
    Main entry point for the Streamlit NPB leader overview.

    Displays league and statistic type filters. Generates league-wide dashboards.
    Depending on what league(s) are selected, players are ranked relative to others
    within that current selection (for example, a player might be #1 when only filtered
    for Central, but #5 with both leagues enabled).

    Returns:
        None
    """
    st.set_page_config(layout="wide")
    st.title("NPB Leaders")

    # User filters
    stat_col1, stat_col2, stat_col3 = st.columns(
        [2, 1.1, 5.9], vertical_alignment="center"
    )
    with stat_col1:
        user_year = hp.create_year_filter()
    with stat_col2:
        user_league = hp.create_league_filter("npb")
    with stat_col3:
        user_bat_pitch = st.pills(
            "Statistics",
            ["Batting", "Pitching"],
            selection_mode="multi",
            default=["Batting", "Pitching"],
        )

    # Generate list of dataframe to show
    leader_tables = build_leader_tables(user_year, user_bat_pitch, user_league)

    # Print dataframes in 3 columns
    r1c1, r1c2, r1c3 = st.columns([1, 1, 1])
    i = 0
    for table in leader_tables:
        # Distribute dataframes into each column
        if i % 3 == 0:
            chosen_col = r1c1
        elif i % 3 == 1:
            chosen_col = r1c2
        else:
            chosen_col = r1c3

        with chosen_col:
            # 3rd column will always be stat name
            st.header(table.columns.to_list()[2])
            # Determine stat display/hover configs
            if "Player" in table.columns.to_list():
                config = "BR"
            elif "Pitcher" in table.columns.to_list():
                config = "PR"
            else:
                config = ""

            chosen_col.dataframe(
                table,
                width="stretch",
                hide_index=True,
                row_height=25,
                height=160,
                column_config=hp.get_column_config(config),
            )
        i = i + 1


@st.cache_data
def build_leader_tables(user_year, user_bat_pitch, user_league):
    """
    Build ranked leader tables for selected batting and pitching statistics.

    Loads batting and pitching leader data from CSV based on the selected year.
    For each enabled statistic (batting or pitching), filters by league, ranks
    players, and returns a sorted DataFrame with Rank, Player/Pitcher name,
    stat value, and Team columns.

    Args:
        user_year: Year string to load data for (e.g., "2024").
        user_bat_pitch: List containing "Batting" and/or "Pitching" to include.
        user_league: List of league abbreviations to filter by (e.g., ["C", "P"]).

    Returns:
        List of DataFrames, one per enabled statistic, sorted by rank.
    """
    lead_bat_df = hp.load_csv(st.secrets[user_year + "LeadersBR_link"])
    player_bat_df = hp.load_csv(st.secrets[user_year + "StatsFinalBR_link"])
    lead_pitch_df = hp.load_csv(st.secrets[user_year + "LeadersPR_link"])
    player_pitch_df = hp.load_csv(st.secrets[user_year + "StatsFinalPR_link"])

    stat_dicts = []
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
    if "Batting" in user_bat_pitch:
        stat_dicts.append(bat_stat_dict)
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
    if "Pitching" in user_bat_pitch:
        stat_dicts.append(pitch_stat_dict)

    leader_tables = []
    flip_rank_stats = ["ERA", "FIP", "WHIP"]
    for stat_dict in stat_dicts:
        for key, value in stat_dict.items():
            if "Player" in value.columns.to_list():
                name_col = "Player"
            elif "Pitcher" in value.columns.to_list():
                name_col = "Pitcher"
            else:
                name_col = "Player"

            # Filter by league
            display_df = value[value["League"].isin(user_league)].copy()
            # Convert to correct notation for Streamlit
            display_df = hp.convert_pct_cols_to_float(display_df)

            # Rank by given column
            if key in flip_rank_stats:
                display_df["#"] = display_df[key].rank(method="min")
            else:
                display_df["#"] = display_df[key].rank(method="min", ascending=False)

            # Extract needed columns
            display_df = display_df[["#", name_col, key, "Team"]].sort_values("#")
            leader_tables.append(display_df)

    return leader_tables


if __name__ == "__main__":
    main()
