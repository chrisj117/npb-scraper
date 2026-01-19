"""Displays lineup, rotation, and bullpen data with Streamlit"""

import streamlit as st
import pandas as pd
import pages.helper as hp


def main():
    """
    Main entry point for the Streamlit NPB team overview.

    Displays a dropdown for team selection and generates team-specific
    dashboards. When a team is selected, displays the projected starting
    lineup, reserve, starting rotation, and bullpen for that team using data
    loaded from GitHub.

    Functions called:
        - create_lineup(team): Shows the team's starting lineup and reserve
        batter.
        - create_rotation_bullpen(team): Shows the team's starting rotation and
        bullpen.

    Returns:
        None
    """

    st.set_page_config(layout="centered")
    # User dropdown box
    user_team = hp.create_team_filter(mode="overview")

    # Streamlit dataframe displays
    create_lineup(user_team)
    create_rotation_bullpen(user_team)
    create_team_stats(user_team)


def create_lineup(team):
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

    Returns:
        None
    """
    bat_df = hp.load_csv(st.secrets["2025StatsFinalBR_link"])
    field_df = hp.load_csv(st.secrets["2025FieldingFinalR_link"])
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

    # Column reordering
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
    lineup_df = lineup_df[
        [
            "Pos",
            "Player",
            "Age",
            "B",
            "PA",
            "HR",
            "SB",
            "K%",
            "BB%",
            "AVG",
            "OPS+",
        ]
    ]
    lineup_df = hp.convert_pct_cols_to_float(lineup_df)

    # Display data
    st.write("Lineup")
    st.dataframe(
        lineup_df,
        width="stretch",
        hide_index=True,
        row_height=25,
        column_config=hp.get_column_config("BR"),
    )


def create_rotation_bullpen(team):
    """
    Displays the projected starting rotation and bullpen for the selected team.

    Loads pitching data from a remote CSV file, cleans and filters it for the
    specified team, and separates pitchers into starting rotation and bullpen
    roles based on saves, holds, and usage ratios. Formats and renames columns
    for display, then shows the rotation and bullpen in Streamlit dataframes.

    Parameters:
        team (str): The name of the team to display the pitching staff for.

    Returns:
        None
    """
    pitch_df = hp.load_csv(st.secrets["2025StatsFinalPR_link"])
    # Only look at one team
    pitch_df = pitch_df.drop(pitch_df[pitch_df.Team != team].index)

    # Rotation (starting pitchers)
    # Determine starters
    pitch_df["HLDSV"] = pitch_df["HLD"] + pitch_df["SV"]
    sp_df = pitch_df.drop(pitch_df[pitch_df.HLDSV >= 7].index)
    sp_df["GIP"] = sp_df["G"] / sp_df["IP"]
    sp_df = sp_df.drop(sp_df[sp_df.GIP > 0.66].index)
    sp_df = sp_df.sort_values("IP", ascending=False).head(7)

    # Column reordering
    sp_df["Role"] = [
        "SP1",
        "SP2",
        "SP3",
        "SP4",
        "SP5",
        "SP6",
        "SP7",
    ]
    sp_df = sp_df[
        [
            "Role",
            "Pitcher",
            "Age",
            "T",
            "IP",
            "W",
            "CG",
            "K%",
            "BB%",
            "ERA",
            "FIP-",
        ]
    ]
    sp_df = hp.convert_pct_cols_to_float(sp_df)

    # Bullpen
    closer = pitch_df.sort_values("SV", ascending=False).head(1)
    # Drop closer from potential relievers
    pitch_df = pitch_df.drop(closer.index)
    reliever = pitch_df.sort_values("HLD", ascending=False).head(6)
    bp_df = pd.concat([closer, reliever])

    # Column reordering
    bp_df["Role"] = [
        "CL",
        "SU",
        "RP",
        "RP",
        "RP",
        "RP",
        "RP",
    ]
    bp_df = bp_df[
        [
            "Role",
            "Pitcher",
            "Age",
            "T",
            "IP",
            "SV",
            "HLD",
            "K%",
            "BB%",
            "ERA",
            "FIP-",
        ]
    ]
    bp_df = hp.convert_pct_cols_to_float(bp_df)

    # Display data
    st.write("Rotation")
    st.dataframe(
        sp_df,
        width="stretch",
        hide_index=True,
        row_height=25,
        column_config=hp.get_column_config("PR"),
    )
    st.write("Bullpen")
    st.dataframe(
        bp_df,
        width="stretch",
        hide_index=True,
        row_height=25,
        column_config=hp.get_column_config("PR"),
    )


def create_team_stats(team):
    """Displays the related stats for the selected team.

    Loads team batting/pitching data from a remote CSV file, cleans and filters
    it for the specified team and League Average.

    Parameters:
        team (str): The name of the team to display the pitching/batting stats
        for.

    Returns:
        None
    """
    npb_team_bat_df = hp.load_csv(st.secrets["2025TeamBR_link"])
    npb_team_pitch_df = hp.load_csv(st.secrets["2025TeamPR_link"])

    # Get only filtered team + League Average
    team_bat = npb_team_bat_df.drop(npb_team_bat_df[npb_team_bat_df.Team != team].index)
    lg_avg = npb_team_bat_df.drop(
        npb_team_bat_df[npb_team_bat_df.Team != "League Average"].index
    )
    bat_final_df = pd.concat([team_bat, lg_avg]).reset_index(drop=True)
    # Filter batting stats
    bat_final_df = bat_final_df[["Team", "HR", "SB", "K%", "BB%", "AVG", "OPS+"]]
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
    pitch_final_df = pitch_final_df[["Team", "W", "CG", "K%", "BB%", "ERA", "FIP-"]]
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
