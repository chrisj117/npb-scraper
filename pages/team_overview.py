"""Displays top players, lineup, rotation, and bullpen data with Streamlit"""

import altair as alt
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
        - create_top_pos_players(cumulative_df): Shows the team's top 10 position players by IMPACT metric.
        - create_lineup(cumulative_df, advanced_view): Shows the team's starting lineup and reserve batters.
        - create_bench(cumulative_df, advanced_view): Shows the team's bench/reserve batters.
        - create_top_pitchers(pitch_df): Shows the team's top 10 pitchers by IMPACT metric.
        - create_rotation(pitch_df, advanced_view): Shows the team's starting rotation.
        - create_bullpen(pitch_df, advanced_view): Shows the team's bullpen.
        - create_team_bat_stats(team_bat_df, team_field_df, user_team, user_year): Shows team batting stats compared to League Average.
        - create_team_pitch_stats(team_pitch_df, user_team, user_year): Shows team pitching stats compared to League Average.

    Returns:
        None
    """
    st.set_page_config(layout="wide")

    # User selections
    user_year = hp.create_year_filter()
    user_team = hp.create_team_filter(mode="overview")
    advanced_view = st.toggle("Player Table Advanced Stats")

    bat_df = hp.load_csv(st.secrets[user_year + "StatsFinalBR_link"])
    field_df = hp.load_csv(st.secrets[user_year + "FieldingFinalR_link"])
    pitch_df = hp.load_csv(st.secrets[user_year + "StatsFinalPR_link"])
    team_bat_df = hp.load_csv(st.secrets[user_year + "TeamBR_link"])
    team_field_df = hp.load_csv(st.secrets[user_year + "TeamFieldingFinalR_link"])
    team_pitch_df = hp.load_csv(st.secrets[user_year + "TeamPR_link"])
    if int(user_year) >= 2026:
        central_df = hp.load_csv(st.secrets[user_year + "StandingsFinalC_npb_link"])
        pacific_df = hp.load_csv(st.secrets[user_year + "StandingsFinalP_npb_link"])
    else:
        central_df = hp.load_csv(st.secrets[user_year + "StandingsFinalC_link"])
        pacific_df = hp.load_csv(st.secrets[user_year + "StandingsFinalP_link"])

    # Check min league avg PA and IP for appropriate sample sizes before continuing
    if (
        team_bat_df.loc[team_bat_df["Team"] == "League Average", "PA"].iloc[0] < 900
    ) or (
        team_pitch_df.loc[team_pitch_df["Team"] == "League Average", "IP"].iloc[0] < 225
    ):
        st.warning(
            "League average minimum IP or PA is not met. This year's team overview "
            "is unavailable until a larger sample is obtained. Choose a previous year or "
            "check back later!"
        )
        st.stop()

    create_team_header(central_df, pacific_df, user_team)

    # Aggregate all of a player's fielding into 1 row
    agg_field_df = field_df.groupby(["Player", "Team"], as_index=False).agg(
        {
            "Inn": "sum",
            "TZR": "sum",
            "Pos Adj": "sum",
            "Framing": "sum",
            "Blocking": "sum",
        }
    )
    # Recalculate [key_stat]/143 after aggregating players into 1 row in fielding
    agg_field_df["TZR/143"] = (agg_field_df["TZR"] / agg_field_df["Inn"]) * 1287
    agg_field_df["Framing/143"] = (agg_field_df["Framing"] / agg_field_df["Inn"]) * 1287
    # Drop all sub-10 PA players to help alleviate merging errors
    bat_df = bat_df.drop(bat_df[bat_df.PA < 10].index)
    try:
        cumulative_df = pd.merge(bat_df, agg_field_df, how="left")
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
    field_df = field_df.drop(field_df[field_df.Team != user_team].index)
    cumulative_df = hp.prepare_streamlit_types(cumulative_df)
    pitch_df = hp.prepare_streamlit_types(pitch_df)
    team_field_df = hp.prepare_streamlit_types(team_field_df)
    team_bat_df = hp.prepare_streamlit_types(team_bat_df)
    team_pitch_df = hp.prepare_streamlit_types(team_pitch_df)

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
    field_df["Pos"] = field_df["Pos"].map(pos_map)

    c1, c2 = st.columns(2)

    # Streamlit dataframe displays
    with c1:
        create_top_pos_players(cumulative_df)
        create_lineup(cumulative_df, field_df, advanced_view)
        create_bench(cumulative_df, field_df, advanced_view)
        create_team_bat_stats(team_bat_df, team_field_df, user_team, user_year)
    with c2:
        create_top_pitchers(pitch_df)
        create_rotation(pitch_df, advanced_view)
        create_bullpen(pitch_df, advanced_view)
        create_team_pitch_stats(team_pitch_df, user_team, user_year)


def create_lineup(cumulative_df, field_df, advanced_view):
    """
    Displays the projected starting lineup for the selected team.

    Uses the cumulative batting and fielding dataframe to identify the highest-inning
    player at each position, excluding UTL and DH for CL teams. Formats the lineup
    table for display, optionally including advanced statistics.

    Parameters:
        cumulative_df (DataFrame): Merged batting and fielding data for the selected team.
        field_df (DataFrame): Fielding data for the selected team.
        advanced_view (bool): Whether to display advanced statistics columns.

    Returns:
        None
    """
    lineup_df = pd.DataFrame()
    # Find top players in each position (minus UTL and 1)
    if "CL" in cumulative_df["League"].values:
        # CL league does not have DH players
        filter_pos_rows = ["RF", "CF", "LF", "SS", "3B", "2B", "1B", "C"]
    else:
        filter_pos_rows = ["DH", "RF", "CF", "LF", "SS", "3B", "2B", "1B", "C"]
    for pos in filter_pos_rows:
        all_stats_pos_df = cumulative_df.drop(
            cumulative_df[cumulative_df["Pos"] != pos].index
        )
        field_pos_df = field_df.drop(field_df[field_df["Pos"] != pos].index)
        # Use field_df to get whoever has most innings at that position (cumulative_df has innings aggregated across all positions)
        starter_field = field_pos_df[field_pos_df["Inn"] == field_pos_df["Inn"].max()]
        starter_all_stats = all_stats_pos_df[
            all_stats_pos_df["Player"] == starter_field["Player"].iloc[0]
        ]
        lineup_df = pd.concat([starter_all_stats, lineup_df])

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
    st.write("***Lineup***")
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


def create_bench(cumulative_df, field_df, advanced_view):
    """
    Displays the bench/reserve batters for the selected team.

    Identifies the highest-inning player at each position to determine the starting
    lineup, then selects the top reserve players by PA not already in the starting
    lineup. Adjusts the number of reserves based on league (6 for CL, 5 for others)
    due to DH rules. Formats and displays the bench table in Streamlit.

    Parameters:
        cumulative_df (DataFrame): Merged batting and fielding data for the selected team.
        field_df (DataFrame): Fielding data for the selected team.
        advanced_view (bool): Whether to display advanced statistics columns.

    Returns:
        None
    """
    lineup_df = pd.DataFrame()
    # Find top players in each position (minus UTL and 1)
    if "CL" in cumulative_df["League"].values:
        # CL league does not have DH players
        filter_pos_rows = ["RF", "CF", "LF", "SS", "3B", "2B", "1B", "C"]
        bench_num = 6
    else:
        filter_pos_rows = ["DH", "RF", "CF", "LF", "SS", "3B", "2B", "1B", "C"]
        bench_num = 5
    for pos in filter_pos_rows:
        all_stats_pos_df = cumulative_df.drop(
            cumulative_df[cumulative_df["Pos"] != pos].index
        )
        field_pos_df = field_df.drop(field_df[field_df["Pos"] != pos].index)
        # Use field_df to get whoever has most innings at that position (cumulative_df has innings aggregated across all positions)
        starter_field = field_pos_df[field_pos_df["Inn"] == field_pos_df["Inn"].max()]
        starter_all_stats = all_stats_pos_df[
            all_stats_pos_df["Player"] == starter_field["Player"].iloc[0]
        ]
        lineup_df = pd.concat([starter_all_stats, lineup_df])

    # Reserves = top 4 guys with most PA but not in top 9
    starter_list = lineup_df["Player"].tolist()
    bench_df = (
        cumulative_df[~cumulative_df["Player"].isin(starter_list)]
        .sort_values("PA", ascending=False)
        .head(bench_num)
    )

    # Column reordering
    chosen_bench_cols = [
        "Pos",
        "Player",
        "Age",
        "B",
        "PA",
    ]
    if advanced_view:
        chosen_bench_cols = chosen_bench_cols + [
            "OBP",
            "SLG",
            "ISO",
            "K%",
            "BB%",
            "sSeager",
            "OPS+",
        ]
    else:
        chosen_bench_cols = chosen_bench_cols + [
            "H",
            "HR",
            "RBI",
            "SB",
            "SO",
            "BB",
            "AVG",
        ]
    bench_df = bench_df[chosen_bench_cols]

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
    st.write("***Bench***")
    styler = bench_df.style
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
    Displays the top 10 position players by an approximation of WAR for the selected team.

    Calculates a WAR metric based on OPS+, wSB, defensive metrics (TZR, Pos Adj,
    Framing, Blocking), and playing time (PA). Sorts players by WAR, ranks the
    top ten, assigns player archetypes from offensive, baserunning, and defensive
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

    with st.expander("***Top Position Players***"):
        st.write(
            "Players are ranked using a simplified value metric that measures impact through park-adjusted offensive production, base stealing efficiency, defense, positional difficulty, catcher framing and blocking, and playing time, with a small multiplier that rewards strong batting performance."
        )
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
    Displays the top 10 pitchers by an approximation of WAR for the selected team.

    Calculates a WAR metric based on innings pitched and earned runs, sorts
    pitchers by WAR, and ranks the top ten. Converts inning totals to display
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

    with st.expander("***Top Pitchers***"):
        st.write(
            "Pitchers are ranked using a simplified value metric that measures impact through innings pitched and earned-run prevention, with a small multiplier that rewards strong strikeout-to-walk ratios."
        )
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
    pitch_df["IP"] = hp.convert_ip_column_in(pitch_df, "IP")
    sp_df["GIP"] = sp_df["G"] / sp_df["IP"]
    pitch_df["IP"] = hp.convert_ip_column_out(pitch_df, "IP")
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

    # Declare columns to be colored percentiles
    pct_cols = ["IP", "FB Velo", "CSW%", "GB%", "K%", "FIP-", "ERA+"]
    invert_pct_cols = ["ERA", "FIP-", "BB%"]

    st.write("***Rotation***")
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

    # Declare columns to be colored percentiles
    pct_cols = ["IP", "FB Velo", "CSW%", "GB%", "K%", "FIP-", "ERA+"]
    invert_pct_cols = ["ERA", "FIP-", "BB%"]

    st.write("***Bullpen***")
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


def create_team_bat_stats(team_bat_df, team_field_df, team, year):
    """
    Displays team batting stats compared to League Average.

    Filters for the specified team from the team-level batting dataframe, calculates
    ranks for various batting metrics, and displays them in an Altair bar chart with
    raw statistics shown as text labels. Higher ranks (closer to 1) indicate better
    performance, shown with blue bars; lower ranks shown with red bars.

    Parameters:
        team_bat_df (DataFrame): Team batting stats data for all teams.
        team_field_df (DataFrame): Team fielding stats data for all teams.
        team (str): The name of the team to display stats for.
        year (str): The year of the season data.

    Returns:
        None
    """
    # Drop league averages before calculating ranks/normalizing
    team_bat_df = team_bat_df.drop(
        team_bat_df[team_bat_df.Team == "League Average"].index
    )
    team_field_df = team_field_df.drop(
        team_field_df[team_field_df.Team == "League Average"].index
    )

    # Calculate 1B and use it to normalize batting stats
    team_bat_df["1B"] = (
        team_bat_df["H"] - team_bat_df["HR"] - team_bat_df["3B"] - team_bat_df["2B"]
    )
    team_bat_df["Bunt Tendency"] = (
        team_bat_df["SH"]
        / (team_bat_df["1B"] + team_bat_df["BB"] + team_bat_df["HP"])
        * 100
    )
    team_bat_df["Steal Tendency"] = (
        (team_bat_df["SB"] + team_bat_df["CS"])
        / (team_bat_df["1B"] + team_bat_df["BB"] + team_bat_df["HP"])
        * 100
    )

    team_cumulative_df = pd.merge(team_bat_df, team_field_df, on=["Team", "League"])
    team_cumulative_df = team_cumulative_df.rename(
        columns={
            "TZR": "Total Zone Runs",
        }
    )

    # Determine type of stats to rank and order (top to bottom) in chart
    rank_cols = [
        "OPS+",
        "ISO",
        "HR",
        "SB",
        "K%",
        "BB%",
        "BB/K",
        "Chase%",
        "Swing%",
        "SwStr%",
        "Steal Tendency",
        "Bunt Tendency",
        "Total Zone Runs",
        "Framing",
    ]
    invert_rank_col = ["K%", "Chase%", "SwStr%"]
    rank_df = pd.DataFrame(team_cumulative_df["Team"])
    for col in rank_cols:
        if col in invert_rank_col:
            rank_df[col] = team_cumulative_df[col].rank(method="max", ascending=False)
        else:
            rank_df[col] = team_cumulative_df[col].rank(method="max", ascending=True)

    # Get only filtered team in raw stat and rank chart
    team_cumulative_df = team_cumulative_df.drop(
        team_cumulative_df[team_cumulative_df.Team != team].index
    )
    rank_df = rank_df.drop(rank_df[rank_df.Team != team].index)
    team_cumulative_df = hp.format_cols_as_strs(team_cumulative_df)

    # Melt ranks and raw stats, then merge them
    rank_melted = rank_df.melt(id_vars=["Team"], value_name="Rank", var_name="Stat")
    raw_stat_melted = team_cumulative_df.melt(
        id_vars=["Team"], value_name="Raw_Stat", var_name="Stat"
    )
    rank_melted = rank_melted.merge(
        raw_stat_melted[["Team", "Stat", "Raw_Stat"]], on=["Team", "Stat"]
    )

    # Chart settings
    title_params = alt.TitleParams(
        text=team + " - Team Batting & Fielding",
        subtitle=[year + " NPB", "@YakyuCosmo"],
        subtitleColor="grey",
        subtitleFontSize=13.5,
    )

    chart = (
        alt.Chart(rank_melted)
        .mark_bar()
        .encode(
            x=alt.X(
                "Rank:Q",
                title="NPB Rank",
                scale=alt.Scale(domain=[0, 12]),
                axis=alt.Axis(values=list(range(1, 13)), labelExpr="13 - datum.value"),
            ),
            y=alt.Y("Stat:N", sort=rank_cols, title=None),
            tooltip=alt.value(None),
            color=alt.Color("Rank")
            .scale(domain=[0, 12], range=["#3366cc", "#b3b3b3", "#e60000"])
            .legend(None),
        )
        .properties(
            height=alt.Step(25),
            title=title_params,
        )
    )

    # Create a text layer with original values along right edge of chart
    raw_stat_layer = (
        alt.Chart(rank_melted)
        .mark_text(
            align="left",
            baseline="middle",
            dx=5,
            fontSize=14,
            color="grey",
        )
        .encode(
            x=alt.datum(12.5),
            y=alt.Y("Stat:N", sort=rank_cols, title=None),
            text="Raw_Stat:N",
            tooltip=alt.value(None),
        )
    )

    # Combine base layers
    chart = alt.layer(chart, raw_stat_layer)
    # Configure the chart
    chart = chart.configure_title(fontSize=20, subtitleFontSize=14)
    chart = chart.configure_axis(labelFontSize=14)

    st.altair_chart(chart)


def create_team_pitch_stats(team_pitch_df, team, year):
    """
    Displays team pitching stats compared to League Average.

    Filters for the specified team from the team-level pitching dataframe, calculates
    ranks for various pitching metrics, and displays them in an Altair bar chart with
    raw statistics shown as text labels. Higher ranks (closer to 1) indicate better
    performance, shown with blue bars; lower ranks shown with red bars.

    Parameters:
        team_pitch_df (DataFrame): Team pitching stats data for all teams.
        team (str): The name of the team to display stats for.
        year (str): The year of the season data.

    Returns:
        None
    """
    # Drop league average before calculating ranks
    team_pitch_df = team_pitch_df.drop(
        team_pitch_df[team_pitch_df.Team == "League Average"].index
    )

    rank_cols = [
        "ERA+",
        "FIP-",
        "WHIP",
        "HR/FB",
        "HR%",
        "K%",
        "BB%",
        "K-BB%",
        "GB%",
        "Chase%",
        "SwStr%",
        "CSW%",
        "Sec%",
        "FB Velo",
    ]
    invert_rank_col = ["FIP-", "WHIP", "BB%", "HR%", "HR/FB"]
    rank_df = pd.DataFrame(team_pitch_df["Team"])
    for col in rank_cols:
        if col in invert_rank_col:
            rank_df[col] = team_pitch_df[col].rank(method="max", ascending=False)
        else:
            rank_df[col] = team_pitch_df[col].rank(method="max", ascending=True)

    # Get only filtered team in raw stat and rank chart
    pitch_final_df = team_pitch_df.drop(team_pitch_df[team_pitch_df.Team != team].index)
    rank_df = rank_df.drop(rank_df[rank_df.Team != team].index)
    pitch_final_df = hp.format_cols_as_strs(pitch_final_df, "team_pitch")

    # Melt ranks and raw stats, then merge them
    rank_melted = rank_df.melt(id_vars=["Team"], value_name="Rank", var_name="Stat")
    raw_stat_melted = pitch_final_df.melt(
        id_vars=["Team"], value_name="Raw_Stat", var_name="Stat"
    )
    rank_melted = rank_melted.merge(
        raw_stat_melted[["Team", "Stat", "Raw_Stat"]], on=["Team", "Stat"]
    )

    # Chart settings
    title_params = alt.TitleParams(
        text=team + " - Team Pitching",
        subtitle=[year + " NPB", "@YakyuCosmo"],
        subtitleColor="grey",
        subtitleFontSize=13.5,
    )

    chart = (
        alt.Chart(rank_melted)
        .mark_bar()
        .encode(
            x=alt.X(
                "Rank:Q",
                title="NPB Rank",
                scale=alt.Scale(domain=[0, 12]),
                axis=alt.Axis(values=list(range(1, 13)), labelExpr="13 - datum.value"),
            ),
            y=alt.Y("Stat:N", sort=rank_cols, title=None),
            tooltip=alt.value(None),
            color=alt.Color("Rank")
            .scale(domain=[0, 12], range=["#3366cc", "#b3b3b3", "#e60000"])
            .legend(None),
        )
        .properties(
            height=alt.Step(25),
            title=title_params,
        )
    )

    # Create a text layer with original values along right edge of chart
    raw_stat_layer = (
        alt.Chart(rank_melted)
        .mark_text(
            align="left",
            baseline="middle",
            dx=5,
            fontSize=14,
            color="grey",
        )
        .encode(
            x=alt.datum(12.5),
            y=alt.Y("Stat:N", sort=rank_cols, title=None),
            text="Raw_Stat:N",
            tooltip=alt.value(None),
        )
    )

    # Combine base layers
    chart = alt.layer(chart, raw_stat_layer)
    # Configure the chart
    chart = chart.configure_title(fontSize=20, subtitleFontSize=14)
    chart = chart.configure_axis(labelFontSize=14)

    st.altair_chart(chart)


def create_team_header(central_df: pd.DataFrame, pacific_df: pd.DataFrame, team):
    """
    Displays a team header with record, run differential, league, and standings placement.

    Concatenates Central and Pacific league standings to determine the selected
    team's rank within its league, then displays a formatted subheader showing
    the team's win-loss-tie record, winning percentage, run differential, league
    affiliation, and ordinal league placement.

    Parameters:
        central_df (DataFrame): Central league standings data.
        pacific_df (DataFrame): Pacific league standings data.
        team (str): The name of the team to display the header for.

    Returns:
        None
    """
    all_standings_df = pd.concat([central_df, pacific_df])
    # Preserve index team is at before reindexing (index contains placement in their league)
    all_standings_df.index += 1
    league_rank = all_standings_df[all_standings_df.Team == team].index
    all_standings_df = all_standings_df.reset_index(drop=True)

    # Look at only 1 team
    all_standings_df = all_standings_df.drop(
        all_standings_df[all_standings_df.Team != team].index
    )

    if team in central_df["Team"].values:
        league = "Central"
    elif team in pacific_df["Team"].values:
        league = "Pacific"
    else:
        league = "Unknown"

    # Display W, L, T, PCT, Diff from standings
    st.subheader(
        team
        + " · "
        + all_standings_df["W"].astype(str).values[0]
        + "-"
        + all_standings_df["L"].astype(str).values[0]
        + "-"
        + all_standings_df["T"].astype(str).values[0]
        + " ("
        + f"{all_standings_df["PCT"].values[0]:.3f}"
        + ")"
        + " · Run Diff: "
        + all_standings_df["Diff"].astype(str).values[0]
        + " · "
        + league
        + " League: "
        + hp.ordinal(league_rank.astype(int).values[0])
        + " Place",
        anchor=False,
        divider="grey",
    )


if __name__ == "__main__":
    main()
