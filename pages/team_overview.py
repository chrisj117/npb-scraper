"""Displays lineup, rotation, and bullpen data with Streamlit"""

import streamlit as st
import pandas as pd
import pages.helper as hp


def main():
    """
    Main entry point for the Streamlit NPB team overview.

    Displays dropdowns for year and team selection with an advanced stats toggle,
    then generates team-specific dashboards showing the projected starting lineup,
    reserve batters, starting rotation, bullpen, and team statistics.

    Functions called:
        - create_lineup(team, user_year, advanced_view): Shows the team's starting lineup and reserve batters.
        - create_rotation_bullpen(team, user_year, advanced_view): Shows the team's starting rotation and bullpen.
        - create_team_stats(team, user_year): Shows team batting and pitching stats compared to League Average.

    Returns:
        None
    """
    st.set_page_config(layout="centered")

    # User selections
    user_year = hp.create_year_filter()
    user_team = hp.create_team_filter(mode="overview")
    advanced_view = st.toggle("Advanced Stats")

    # Streamlit dataframe displays
    create_lineup(user_team, user_year, advanced_view)
    create_rotation_bullpen(user_team, user_year, advanced_view)
    create_team_stats(user_team, user_year)


def create_lineup(team, user_year, advanced_view):
    """
    Displays the projected starting lineup and reserve batter for the selected
    team.

    Loads batting and fielding data from remote CSV files, merges them, and
    filters for the specified team. Identifies the top player at each position
    (excluding UTL and, for CL teams, DH), and selects the player with the
    highest plate appearances not already in the starting lineup as the
    reserve. Formats and renames columns for display, then shows the lineup
    and reserve in a Streamlit dataframe.

    Parameters:
        team (str): The name of the team to display the lineup for.
        user_year (str): The season year to load data for.
        advanced_view (bool): Whether to display additional stats columns.

    Returns:
        None
    """
    bat_df = hp.load_csv(st.secrets[user_year + "StatsFinalBR_link"])
    field_df = hp.load_csv(st.secrets[user_year + "FieldingFinalR_link"])
    # Drop all sub-10 PA players to help alleviate merging errors
    bat_df = bat_df.drop(bat_df[bat_df.PA < 10].index)
    try:
        cumulative_df = pd.merge(bat_df, field_df, how="left")
    except ValueError:
        st.error(
            "Error: Batting and fielding dataframes failed to merge. "
            "Check Age columns and update name translation + roster data if "
            "necessary!"
        )
        cumulative_df = pd.DataFrame()

    # Drop everyone not in team
    cumulative_df = cumulative_df.drop(cumulative_df[cumulative_df.Team != team].index)

    lineup_df = pd.DataFrame()
    # Find top players in each position (minus UTL and 1)
    if "CL" in cumulative_df["League"].values:
        # CL league does not have DH players
        filter_pos_rows = ["UTL", "9", "8", "7", "6", "5", "4", "3", "2"]
    else:
        filter_pos_rows = ["UTL", "DH", "9", "8", "7", "6", "5", "4", "3", "2"]
    for pos in filter_pos_rows:
        pos_df = cumulative_df.drop(cumulative_df[cumulative_df.Pos != pos].index)
        starter = pos_df[pos_df["Inn"] == pos_df["Inn"].max()]
        lineup_df = pd.concat([starter, lineup_df])

    # Reserves = top 4 guys with most PA but not in top 9
    starter_list = lineup_df["Player"].tolist()
    reserve = (
        cumulative_df[~cumulative_df["Player"].isin(starter_list)]
        .sort_values("PA", ascending=False)
        .head(4)
    )
    lineup_df = pd.concat([lineup_df, reserve])

    # Convert Tablepress number position representation to abbreviations
    pos_map = {
        "2": "C",
        "3": "1B",
        "4": "2B",
        "5": "3B",
        "6": "SS",
        "7": "LF",
        "8": "CF",
        "9": "RF",
        "DH": "DH",
        "UTL": "UTL",
    }
    lineup_df["Pos"] = lineup_df["Pos"].map(pos_map)

    # Column reordering
    chosen_lineup_cols = [
        "Pos",
        "Player",
        "Age",
        "B",
        "PA",
    ]
    if advanced_view:
        chosen_lineup_cols = chosen_lineup_cols + [
            "OBP",
            "SLG",
            "ISO",
            "K%",
            "BB%",
            "sSeager",
            "OPS+",
        ]
    else:
        chosen_lineup_cols = chosen_lineup_cols + [
            "H",
            "HR",
            "RBI",
            "SB",
            "SO",
            "BB",
            "AVG",
        ]
    lineup_df = lineup_df[chosen_lineup_cols]
    lineup_df = hp.convert_pct_cols_to_float(lineup_df)

    # Declare columns to be colored percentiles
    pct_cols = [
        "OBP",
        "SLG",
        "ISO",
        "K%",
        "BB%",
        "sSeager",
        "OPS+",
        "AVG",
        "PA",
    ]
    invert_pct_cols = []

    # Display data
    st.write("Lineup")
    st.dataframe(
        lineup_df.style.apply(
            hp.color_by_percentile, axis=0, args=(pct_cols, invert_pct_cols)
        ),
        width="stretch",
        hide_index=True,
        row_height=25,
        column_config=hp.get_column_config("BR"),
    )


def create_rotation_bullpen(team, user_year, advanced_view):
    """
    Displays the projected starting rotation and bullpen for the selected team.

    Loads pitching data from a remote CSV file, cleans and filters it for the
    specified team, and separates pitchers into starting rotation and bullpen
    roles based on saves, holds, and usage ratios. Formats and renames columns
    for display, then shows the rotation and bullpen in Streamlit dataframes.

    Parameters:
        team (str): The name of the team to display the pitching staff for.
        user_year (str): The season year to load data for.
        advanced_view (bool): Whether to display additional stats columns.

    Returns:
        None
    """
    pitch_df = hp.load_csv(st.secrets[user_year + "StatsFinalPR_link"])
    # Only look at one team
    pitch_df = pitch_df.drop(pitch_df[pitch_df.Team != team].index)

    # Rotation (starting pitchers)
    # Determine starters
    pitch_df["HLDSV"] = pitch_df["HLD"] + pitch_df["SV"]
    sp_df = pitch_df.drop(pitch_df[pitch_df.HLDSV >= 7].index)
    sp_df["GIP"] = sp_df["G"] / sp_df["IP"]
    sp_df = sp_df.drop(sp_df[sp_df.GIP > 0.66].index)
    sp_df = sp_df.sort_values("IP", ascending=False).head(7)

    # Conditionally fill RP depending on length of reliever
    sp_entries = []
    i = 1
    while i <= len(sp_df):
        sp_entries.append("SP" + str(i))
        i += 1
    sp_df["Role"] = sp_entries

    # Column reordering
    chosen_sp_cols = [
        "Role",
        "Pitcher",
        "Age",
        "T",
        "IP",
    ]
    if advanced_view:
        chosen_sp_cols = chosen_sp_cols + [
            "FB Velo",
            "CSW%",
            "GB%",
            "K%",
            "BB%",
            "FIP-",
            "ERA+",
        ]
    else:
        chosen_sp_cols = chosen_sp_cols + ["W", "CG", "HR", "SO", "BB", "WHIP", "ERA"]
    sp_df = sp_df[chosen_sp_cols]
    sp_df = hp.convert_pct_cols_to_float(sp_df)

    # Bullpen
    closer = pitch_df.sort_values("SV", ascending=False).head(1)
    # Drop closer from potential relievers
    pitch_df = pitch_df.drop(closer.index)
    # Drop anybody with 0 HLD
    pitch_df = pitch_df.drop(pitch_df[pitch_df["HLD"] == 0].index)
    reliever = pitch_df.sort_values("HLD", ascending=False).head(6)
    bp_df = pd.concat([closer, reliever])

    # Conditionally fill RP depending on length of reliever
    roles = ["CL", "SU"]
    i = 1
    while i < len(reliever):
        roles.append("RP")
        i += 1
    bp_df["Role"] = roles

    # Column reordering
    chosen_bp_cols = [
        "Role",
        "Pitcher",
        "Age",
        "T",
        "IP",
    ]
    if advanced_view:
        chosen_bp_cols = chosen_bp_cols + [
            "FB Velo",
            "CSW%",
            "GB%",
            "K%",
            "BB%",
            "FIP-",
            "ERA+",
        ]
    else:
        chosen_bp_cols = chosen_bp_cols + ["SV", "HLD", "HR", "SO", "BB", "WHIP", "ERA"]
    bp_df = bp_df[chosen_bp_cols]
    bp_df = hp.convert_pct_cols_to_float(bp_df)

    # Declare columns to be colored percentiles
    pct_cols = ["IP", "FB Velo", "CSW%", "GB%", "K%", "BB%", "FIP-", "ERA+"]
    invert_pct_cols = ["ERA", "FIP-"]

    st.write("Rotation")
    st.dataframe(
        sp_df.style.apply(
            hp.color_by_percentile, axis=0, args=(pct_cols, invert_pct_cols)
        ),
        width="stretch",
        hide_index=True,
        row_height=25,
        column_config=hp.get_column_config("PR"),
    )

    st.write("Bullpen")
    st.dataframe(
        bp_df.style.apply(
            hp.color_by_percentile, axis=0, args=(pct_cols, invert_pct_cols)
        ),
        width="stretch",
        hide_index=True,
        row_height=25,
        column_config=hp.get_column_config("PR"),
    )


def create_team_stats(team, user_year):
    """
    Displays team batting and pitching stats compared to League Average.

    Loads team batting and pitching data from remote CSV files, filters for
    the specified team and League Average, and displays both sets of stats
    in Streamlit dataframes.

    Parameters:
        team (str): The name of the team to display stats for.
        user_year (str): The season year to load data for.

    Returns:
        None
    """
    npb_team_bat_df = hp.load_csv(st.secrets[user_year + "TeamBR_link"])
    npb_team_pitch_df = hp.load_csv(st.secrets[user_year + "TeamPR_link"])

    # Get only filtered team + League Average
    team_bat = npb_team_bat_df.drop(npb_team_bat_df[npb_team_bat_df.Team != team].index)
    lg_avg = npb_team_bat_df.drop(
        npb_team_bat_df[npb_team_bat_df.Team != "League Average"].index
    )
    bat_final_df = pd.concat([team_bat, lg_avg]).reset_index(drop=True)
    # Filter batting stats
    bat_final_df = bat_final_df[["Team", "HR", "SB", "K%", "BB%", "AVG", "ISO", "OPS+"]]
    bat_final_df = hp.convert_pct_cols_to_float(bat_final_df)
    bat_final_df = bat_final_df.astype(str)

    team_pitch = npb_team_pitch_df.drop(
        npb_team_pitch_df[npb_team_pitch_df.Team != team].index
    )
    lg_avg = npb_team_pitch_df.drop(
        npb_team_pitch_df[npb_team_pitch_df.Team != "League Average"].index
    )
    pitch_final_df = pd.concat([team_pitch, lg_avg]).reset_index(drop=True)
    # Filter pitch stats
    pitch_final_df = pitch_final_df[
        ["Team", "W", "CG", "K%", "BB%", "ERA", "FIP-", "ERA+"]
    ]
    pitch_final_df = hp.convert_pct_cols_to_float(pitch_final_df)
    pitch_final_df = pitch_final_df.astype(str)

    st.write("Team Statistics")
    st.dataframe(
        bat_final_df,
        width="stretch",
        hide_index=True,
        row_height=25,
        column_config=hp.get_column_config("BR"),
    )
    st.dataframe(
        pitch_final_df,
        width="stretch",
        hide_index=True,
        row_height=25,
        column_config=hp.get_column_config("PR"),
    )


if __name__ == "__main__":
    main()
