"""Displays top players, lineup, rotation, and bullpen data with Streamlit"""

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
        - create_top_pos_players(cumulative_df, pos_map): Shows the team's top 5 position players by WAR.
        - create_lineup(cumulative_df, pos_map, advanced_view): Shows the team's starting lineup and reserve batters.
        - create_top_pitchers(pitch_df): Shows the team's top 5 pitchers by WAR.
        - create_rotation(pitch_df, advanced_view): Shows the team's starting rotation.
        - create_bullpen(pitch_df, advanced_view): Shows the team's bullpen.
        - create_team_stats(team, year): Shows team batting and pitching stats compared to League Average.

    Returns:
        None
    """
    st.set_page_config(layout="wide")

    # User selections
    user_year = hp.create_year_filter()
    user_team = hp.create_team_filter(mode="overview")
    advanced_view = st.toggle("Advanced Stats")

    bat_df = hp.load_csv(st.secrets[user_year + "StatsFinalBR_link"])
    field_df = hp.load_csv(st.secrets[user_year + "FieldingFinalR_link"])
    pitch_df = hp.load_csv(st.secrets[user_year + "StatsFinalPR_link"])
    team_bat_df = hp.load_csv(st.secrets[user_year + "TeamBR_link"])
    team_pitch_df = hp.load_csv(st.secrets[user_year + "TeamPR_link"])

    # Check min league avg PA and IP for appropriate sample sizes before continuing
    if (
        team_bat_df.loc[team_bat_df["Team"] == "League Average", "PA"].iloc[0] < 900
    ) or (
        team_pitch_df.loc[team_pitch_df["Team"] == "League Average", "IP"].iloc[0]
        < 225
    ):
        st.warning(
            "League average minimum IP or PA is not met. This year's team overview "
            "is unavailable until a larger sample is obtained. Choose a previous year or "
            "check back later!"
        )
        st.stop()

    # Aggregate all of a player's fielding into 1 row
    field_df = field_df.groupby(["Player", "Team"], as_index=False).agg(
        {
            "Inn": "sum",
            "TZR": "sum",
            "Pos Adj": "sum",
            "Framing": "sum",
            "Blocking": "sum",
        }
    )
    # Recalculate [key_stat]/143 after aggregating players into 1 row in fielding
    field_df["TZR/143"] = (field_df["TZR"] / field_df["Inn"]) * 1287
    field_df["Framing/143"] = (field_df["Framing"] / field_df["Inn"]) * 1287
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
        st.stop()

    # Drop everyone not in team
    cumulative_df = cumulative_df.drop(
        cumulative_df[cumulative_df.Team != user_team].index
    )
    pitch_df = pitch_df.drop(pitch_df[pitch_df.Team != user_team].index)
    cumulative_df = hp.convert_pct_cols_to_float(cumulative_df)

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
    # Remap from Tablepress number representation
    cumulative_df["Pos"] = cumulative_df["Pos"].map(pos_map)

    c1, c2 = st.columns(2)

    # Streamlit dataframe displays
    with c1:
        create_top_pos_players(cumulative_df)
        create_lineup(cumulative_df, advanced_view)
    with c2:
        create_top_pitchers(pitch_df)
        create_rotation(pitch_df, advanced_view)
        create_bullpen(pitch_df, advanced_view)
    create_team_stats(team_bat_df, team_pitch_df, user_team)


def create_lineup(cumulative_df, advanced_view):
    """
    Displays the projected starting lineup and reserve batters for the selected
    team.

    Uses the cumulative batting and fielding dataframe to identify the highest-inning
    player at each position, excluding UTL and DH for CL teams. Selects the four
    highest-PA players not already in the starting lineup as reserves. Formats
    the lineup and reserve tables for display, optionally including advanced
    statistics.

    Parameters:
        cumulative_df (DataFrame): Merged batting and fielding data for the selected team.
        advanced_view (bool): Whether to display advanced statistics columns.

    Returns:
        None
    """
    lineup_df = pd.DataFrame()
    # Find top players in each position (minus UTL and 1)
    if "CL" in cumulative_df["League"].values:
        # CL league does not have DH players
        filter_pos_rows = ["UTL", "RF", "CF", "LF", "SS", "3B", "2B", "1B", "C"]
    else:
        filter_pos_rows = ["UTL", "DH", "RF", "CF", "LF", "SS", "3B", "2B", "1B", "C"]
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
        "BB%",
        "sSeager",
        "OPS+",
        "AVG",
        "PA",
    ]
    invert_pct_cols = ["K%"]

    # Display data
    st.write("Lineup")
    styler = lineup_df.style
    styler.apply(hp.color_by_percentile, axis=0, args=(pct_cols, invert_pct_cols))
    styler = styler.set_properties(subset=["Player"], **{"font-weight": "bold"})
    st.dataframe(
        styler,
        width="stretch",
        hide_index=True,
        row_height=25,
        column_config=hp.get_column_config("BR"),
    )


def create_top_pos_players(cumulative_df):
    """
    Displays the top 5 position players by an approximation of WAR for the selected team.

    Calculates a WAR metric based on OPS+, wSB, defensive metrics (TZR, Pos Adj,
    Framing, Blocking), and playing time (PA). Sorts players by WAR, ranks the
    top five, assigns player archetypes from offensive, baserunning, and defensive
    thresholds, and displays the results in a Streamlit table.

    Parameters:
        cumulative_df (DataFrame): Merged batting and fielding data for the selected team.

    Returns:
        None
    """
    # Calculate best players on team
    cumulative_df["IMPACT"] = (
        (((cumulative_df["OPS+"] - 100) / 100) * 0.094656 * cumulative_df["PA"]) * 1.15
        + cumulative_df["wSB"]
        + cumulative_df["TZR"]
        + cumulative_df["Pos Adj"]
        + cumulative_df["Framing"]
        + cumulative_df["Blocking"]
        + (cumulative_df["PA"] / 30)
    ) / 10
    top_pos_player_df = cumulative_df.sort_values(by="IMPACT", ascending=False).head(10)

    # Create archetypes for players
    archetypes = []
    for _, row in top_pos_player_df.iterrows():
        player_archetypes = []
        if (
            row["OPS+"] > 130
            and row["K%"] < 20
            and row["TZR/143"] > 5
            and row["Pos"] not in ["DH"]
        ):
            player_archetypes.append(":yellow-badge[All-Rounder ⭐]")
        if row["ISO"] > 0.150 and row["HR/FB"] > 9:
            player_archetypes.append(":red-badge[Slugger 💥]")
        if row["K%"] < 17.5 and row["SwStr%"] < 9:
            player_archetypes.append(":blue-badge[Contact Hitter 🏓]")
        if row["OBP"] > 0.33 and row["Chase%"] < 27.5 and row["BB%"] > 7.5:
            player_archetypes.append(":violet-badge[Disciplined 👁️]")
        if row["Swing%"] > 47.5 and row["Chase%"] > 27.5:
            player_archetypes.append(":orange-badge[Aggressive 🗡️]")
        if (row["TZR/143"] > 8 or row["Framing/143"] > 8) and row["Pos"] not in [
            "1B",
            "DH",
        ]:
            player_archetypes.append(":grey-badge[Defensive Specialist 🛡️]")
        if (row["SB"] > 10 and row["wSB"] > 1.0) or (
            ((row["SB"] + row["CS"]) / row["G"]) > 0.17
        ):
            player_archetypes.append(":green-badge[Run Threat 💨]")
        archetypes.append("".join(player_archetypes) if player_archetypes else "")
    top_pos_player_df["Archetype"] = archetypes

    # Reset index to rank players from 1-5
    top_pos_player_df = top_pos_player_df.reset_index(drop=True)
    top_pos_player_df.index += 1

    # Declare visible columns in top pos player table
    top_pos_player_df = top_pos_player_df[["Player", "Pos", "Age", "Archetype"]]

    with st.expander("Top Position Players"):
        st.write("Players are ranked using a simplified value metric that measures impact through park-adjusted offensive production, base stealing efficiency, defense, positional difficulty, catcher framing and blocking, and playing time, with a small multiplier that rewards strong batting performance.")
        st.write(":yellow-badge[All-Rounder ⭐]")
        st.write(
            "A star position player with an OPS+ above 130, a K% below 20.0%, and a TZR/143 above 5.0."
        )
        st.write(":red-badge[Slugger 💥]")
        st.write("A power hitter with an ISO above .150 and an HR/FB% above 9.0%.")
        st.write(":blue-badge[Contact Hitter 🏓]")
        st.write("A high-contact hitter with a K% below 17.5% and a SwStr% below 9.0%")
        st.write(":violet-badge[Disciplined 👁️]")
        st.write(
            "A selective hitter with an OBP above .330, a BB% above 7.5%, and a Chase% below 27.5%."
        )
        st.write(":orange-badge[Aggressive 🗡️]")
        st.write(
            "A proactive hitter with a Swing% above 47.5% and a Chase% above 27.5%."
        )
        st.write(":grey-badge[Defensive Specialist 🛡️]")
        st.write(
            "A fielder with a TZR/143 above 8.0, or a catcher with a Framing/143 above 8.0. Primary first basemen and designated hitters are excluded."
        )
        st.write(":green-badge[Run Threat 💨]")
        st.write(
            "A dangerous base stealer with either more than 10 stolen bases and a wSB above 1.0, or is on pace for more than 25 stolen base attempts over a full season."
        )
    st.table(
        top_pos_player_df,
        width="stretch",
        hide_index=False,
        border="horizontal",
        height=250,
    )


def create_top_pitchers(pitch_df):
    """
    Displays the top 5 pitchers by an approximation of WAR for the selected team.

    Calculates a WAR metric based on innings pitched and earned runs, sorts
    pitchers by WAR, and ranks the top five. Converts inning totals to display
    format, derives pitcher position labels, assigns player archetypes from
    performance and role thresholds, and displays the results in a Streamlit
    table.

    Parameters:
        pitch_df (DataFrame): Pitching data for all players on the selected team.

    Returns:
        None
    """
    pitch_df["IP"] = hp.convert_ip_column_in(pitch_df, "IP")

    pitch_df["IMPACT"] = ((pitch_df["IP"] / 20) - (pitch_df["ER"] / 9)) * (
        1 + ((100 - pitch_df["kwERA-"]) / 100)
    )
    top_pitcher_df = pitch_df.sort_values(by="IMPACT", ascending=False).head(10)
    top_pitcher_df = hp.convert_pct_cols_to_float(top_pitcher_df)
    top_pitcher_df["Pos"] = top_pitcher_df["T"] + "HP"

    # Create archetypes for players
    archetypes = []
    for _, row in top_pitcher_df.iterrows():
        player_archetypes = []
        if row["ERA+"] > 120 and row["K-BB%"] > 15 and (row["IP"] / row["G"]) > 6:
            player_archetypes.append(":yellow-badge[Ace ♠️]")
        if (row["IP"] / row["G"]) > 7 or row["CG"] > 2:
            player_archetypes.append(":green-badge[Workhorse 🐎]")
        if row["FB Velo"] > 93:
            player_archetypes.append(":red-badge[Power Pitcher 🔥]")
        if row["FB Velo"] < 90:
            player_archetypes.append(":violet-badge[Finesse Pitcher 🧠]")
        if row["GB%"] > 51:
            player_archetypes.append(":grey-badge[Groundballer ⬇️]")
        if row["BB%"] < 5.5:
            player_archetypes.append(":blue-badge[Control Specialist 🎯]")
        if row["ERA+"] > 140 and (row["IP"] / row["G"]) < 1.5 and row["SwStr%"] > 12:
            player_archetypes.append(":orange-badge[Fireman 🧯]")
        archetypes.append("".join(player_archetypes) if player_archetypes else "")
    top_pitcher_df["Archetype"] = archetypes

    pitch_df["IP"] = hp.convert_ip_column_out(pitch_df, "IP")

    # Reset index to rank players from 1-5
    top_pitcher_df = top_pitcher_df.reset_index(drop=True)
    top_pitcher_df.index += 1

    # Declare visible columns in top pos pitcher table
    top_pitcher_df = top_pitcher_df[
        [
            "Pitcher",
            "Pos",
            "Age",
            "Archetype",
        ]
    ]

    with st.expander("Top Pitchers"):
        st.write("Pitchers are ranked using a simplified value metric that measures impact through innings pitched and earned-run prevention, with a small multiplier that rewards strong strikeout-to-walk ratios.")
        st.write(":yellow-badge[Ace ♠️]")
        st.write(
            "A frontline starter with an ERA+ above 120, a K-BB% above 15.0%, and more than 6.0 innings per game."
        )
        st.write(":green-badge[Workhorse 🐎]")
        st.write(
            "A durable starter who averages more than 7.0 innings per game or has thrown more than two complete games."
        )
        st.write(":red-badge[Power Pitcher 🔥]")
        st.write(
            "A hard-throwing pitcher with an average fastball velocity above 93.0 mph."
        )
        st.write(":violet-badge[Finesse Pitcher 🧠]")
        st.write(
            " A soft-throwing pitcher with an average fastball velocity below 90.0 mph."
        )
        st.write(":grey-badge[Groundballer ⬇️]")
        st.write("A pitcher who limits fly balls with a GB% above 51.0%.")
        st.write(":blue-badge[Control Specialist 🎯]")
        st.write("A strike-thrower who limits free passes with a BB% below 5.5%.")
        st.write(":orange-badge[Fireman 🧯]")
        st.write("A dominant reliever with an ERA+ above 140 and a SwStr% above 12.0%.")
    st.table(
        top_pitcher_df,
        width="stretch",
        hide_index=False,
        border="horizontal",
        height=250,
    )


def create_rotation(pitch_df, advanced_view):
    """
    Displays the projected starting rotation for the selected team.

    Filters pitching data for starting pitchers by dropping those with high save/hold
    totals (HLDSV >= 7) and high game-to-IP ratio (GIP > 0.66), indicating relievers.
    Sorts by innings pitched and takes top 7, assigning roles SP1-SP7. Formats and renames
    columns for display, then shows the rotation in a Streamlit dataframe.

    Parameters:
        pitch_df (DataFrame): Pitching data for all players on the team.
        advanced_view (bool): Whether to display additional stats columns.

    Returns:
        None
    """
    # Rotation (starting pitchers)
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

    # Declare columns to be colored percentiles
    pct_cols = ["IP", "FB Velo", "CSW%", "GB%", "K%", "FIP-", "ERA+"]
    invert_pct_cols = ["ERA", "FIP-", "BB%"]

    st.write("Rotation")
    styler_sp = sp_df.style
    styler_sp.apply(hp.color_by_percentile, axis=0, args=(pct_cols, invert_pct_cols))
    styler_sp = styler_sp.set_properties(subset=["Pitcher"], **{"font-weight": "bold"})
    st.dataframe(
        styler_sp,
        width="stretch",
        hide_index=True,
        row_height=25,
        column_config=hp.get_column_config("PR"),
    )


def create_bullpen(pitch_df, advanced_view):
    """
    Displays the projected bullpen for the selected team.

    Identifies the closer (top by SV) and relievers (top 6 by HLD with non-zero holds).
    Assigns roles: CL (closer), SU (setup), and RP (relief pitcher) for remaining relievers.
    Formats and renames columns for display, then shows the bullpen in a Streamlit dataframe.

    Parameters:
        pitch_df (DataFrame): Pitching data for all players on the team.
        advanced_view (bool): Whether to display additional stats columns.

    Returns:
        None
    """
    closer: pd.DataFrame = pitch_df.sort_values("SV", ascending=False).head(1)
    # Drop closer from potential relievers
    pitch_df = pitch_df.drop(closer.index)
    # Drop anybody with 0 HLD
    pitch_df = pitch_df.drop(pitch_df[pitch_df["HLD"] == 0].index)
    reliever: pd.DataFrame = pitch_df.sort_values("HLD", ascending=False).head(6)
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
    pct_cols = ["IP", "FB Velo", "CSW%", "GB%", "K%", "FIP-", "ERA+"]
    invert_pct_cols = ["ERA", "FIP-", "BB%"]

    st.write("Bullpen")
    styler_bp = bp_df.style
    styler_bp.apply(hp.color_by_percentile, axis=0, args=(pct_cols, invert_pct_cols))
    styler_bp = styler_bp.set_properties(subset=["Pitcher"], **{"font-weight": "bold"})
    st.dataframe(
        styler_bp,
        width="stretch",
        hide_index=True,
        row_height=25,
        column_config=hp.get_column_config("PR"),
    )


def create_team_stats(team_bat_df, team_pitch_df, team):
    """
    Displays team batting and pitching stats compared to League Average.

    Filters for the specified team and League Average rows from the team-level
    batting and pitching dataframes, then displays both sets of stats in Streamlit
    dataframes for comparison.

    Parameters:
        team_bat_df (DataFrame): Team batting stats data for all teams.
        team_pitch_df (DataFrame): Team pitching stats data for all teams.
        team (str): The name of the team to display stats for.

    Returns:
        None
    """
    # Get only filtered team + League Average
    team_bat = team_bat_df.drop(team_bat_df[team_bat_df.Team != team].index)
    lg_avg: pd.DataFrame = team_bat_df.drop(
        team_bat_df[team_bat_df.Team != "League Average"].index
    )
    bat_final_df = pd.concat([team_bat, lg_avg]).reset_index(drop=True)
    # Filter batting stats
    bat_final_df = bat_final_df[["Team", "HR", "SB", "K%", "BB%", "AVG", "ISO", "OPS+"]]
    bat_final_df = hp.convert_pct_cols_to_float(bat_final_df)
    bat_final_df = bat_final_df.astype(str)

    team_pitch = team_pitch_df.drop(team_pitch_df[team_pitch_df.Team != team].index)
    lg_avg = team_pitch_df.drop(
        team_pitch_df[team_pitch_df.Team != "League Average"].index
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
