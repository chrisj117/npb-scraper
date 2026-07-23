"""Displays subsets of leaders in key statistics using Streamlit"""

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
    st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
    st.title("NPB Leaders")

    # User filters
    stat_col1, stat_col2 = st.columns(
        [2, 8],
        vertical_alignment="center",
    )
    with stat_col1:
        user_year = hp.create_year_filter()
    with stat_col2:
        with st.container(horizontal=True):
            user_league = hp.create_league_filter("npb")
            user_bat_pitch = st.pills(
                "Statistics",
                ["Batting", "Pitching"],
                selection_mode="multi",
                default=["Batting", "Pitching"],
            )

    # Generate list of dataframe to show
    if len(user_league) == 0 or len(user_bat_pitch) == 0:
        st.error("Error: No players to rank - check your filters above.", icon="🚨")
        return
    leader_tables = build_leader_tables(user_year, user_bat_pitch, user_league)

    # Print dataframes in 4 columns
    r1c1, r1c2, r1c3, r1c4 = st.columns([1, 1, 1, 1], gap="xxsmall")
    i = 0
    for table in leader_tables:
        # Distribute dataframes into each column
        if i % 4 == 0:
            chosen_col = r1c1
        elif i % 4 == 1:
            chosen_col = r1c2
        elif i % 4 == 2:
            chosen_col = r1c3
        else:
            chosen_col = r1c4
        with chosen_col:
            # 2nd column from data will always be stat name
            st.write("***" + table.columns.to_list()[1] + "***")
            # Determine stat display/hover configs
            if "Player" in table.columns.to_list():
                config = "player_bat"
            elif "Pitcher" in table.columns.to_list():
                config = "player_pitch"
            else:
                config = ""

            # Shorten team names
            hp.convert_team_names(table, "Team", mode="short")

            styler = table.style
            styler.apply(hp.color_by_team, axis=0)
            if "Player" in table.columns:
                bolded = ["Player", "Team"]
            else:
                bolded = ["Pitcher", "Team"]
            styler = styler.set_properties(subset=bolded, **{"font-weight": "bold"})
            chosen_col.dataframe(
                styler,
                width="stretch",
                hide_index=False,
                row_height=25,
                height=160,
                column_config=hp.get_column_config(config),
            )
        i = i + 1


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
    lead_bat_df = hp.prepare_streamlit_col_order(lead_bat_df)
    player_bat_df = hp.prepare_streamlit_col_order(player_bat_df)
    lead_pitch_df = hp.prepare_streamlit_col_order(lead_pitch_df)
    player_pitch_df = hp.prepare_streamlit_col_order(player_pitch_df)

    stat_dicts = []
    # Dict of stats and what dataframes they come from
    # Ordered from left to right, first to last in desired appearance
    bat_stat_dict = {
        "AVG": lead_bat_df,
        "OBP": lead_bat_df,
        "SLG": lead_bat_df,
        "OPS": lead_bat_df,
        "HR": player_bat_df,
        "ISO": lead_bat_df,
        "BABIP": lead_bat_df,
        "OPS+": lead_bat_df,
        "RBI": player_bat_df,
        "H": player_bat_df,
        "R": player_bat_df,
        "SH": player_bat_df,
        "SB": player_bat_df,
        "SO": player_bat_df,
        "BB": player_bat_df,
        "BB/K": lead_bat_df,
    }
    if "Batting" in user_bat_pitch:
        stat_dicts.append(bat_stat_dict)
    pitch_stat_dict = {
        "IP": player_pitch_df,
        "ERA": lead_pitch_df,
        "FIP": lead_pitch_df,
        "WHIP": lead_pitch_df,
        "W": player_pitch_df,
        "L": player_pitch_df,
        "CG": player_pitch_df,
        "SHO": player_pitch_df,
        "G": player_pitch_df,
        "HLD": player_pitch_df,
        "SV": player_pitch_df,
        "HR": player_pitch_df,
        "SO": player_pitch_df,
        "BB": player_pitch_df,
        "K-BB%": lead_pitch_df,
        "GB%": lead_pitch_df,
        "SwStr%": lead_pitch_df,
        "CSW%": lead_pitch_df,
        "FB Velo": player_pitch_df,
        "Grade": lead_pitch_df,
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
            display_df = hp.prepare_streamlit_types(display_df)

            # Sort by given column and use index as rank
            if key in flip_rank_stats:
                display_df = display_df.sort_values(key)
            else:
                display_df = display_df.sort_values(key, ascending=False)

            display_df = display_df.reset_index(drop=True)
            display_df.index = display_df.index + 1

            # Extract needed columns
            display_df = display_df[[name_col, key, "Team"]]
            leader_tables.append(display_df)

    return leader_tables


if __name__ == "__main__":
    main()
