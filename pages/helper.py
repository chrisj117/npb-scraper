"""Helper functions for Streamlit pages"""

from io import StringIO
import altair as alt
import streamlit as st
import pandas as pd
import requests


def load_csv(url=None):
    """
    Loads a csv from a Github link and returns it as a dataframe.

    Parameters:
        url (str): The Github raw csv link to load.

    Returns:
        (dataframe/None): Returns none if link is unable to be loaded, or a
        dataframe if the link is valid.
    """
    # returns dataframe if good link, otherwise None
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        return pd.read_csv(StringIO(response.text))
    st.error("Failed to load data from GitHub.")
    return None


def display_player_percentile(df, name, year, suffix):
    """
    Displays a percentile bar chart and raw statistics for a selected player.

    Parameters:
        df (pandas.DataFrame): DataFrame containing player statistics.
        name (str): The name of the player to display.
        year (str): The season year for labeling the chart.
        suffix (str): Indicates stat type and determines which columns to plot
        (e.g., 'PR', 'PF', 'BR', 'BF').

    Functionality:
        - Selects relevant statistics and inverts percentile ranks for metrics
        where lower is better.
        - Calculates percentiles for each stat and prepares data for
        visualization.
        - Generates an Altair horizontal bar chart showing the player's
        percentile ranks.
        - Displays the player's raw statistics in a Streamlit dataframe
        below the chart.

    Returns:
        None
    """
    # Suffix determines stats to be put into percentiles
    plot_cols = []
    invert_cols = []
    name_col = ""
    if suffix in ("PR", "PF"):
        name_col = "Pitcher"
        plot_cols = [
            "K-BB%",
            "BB%",
            "K%",
            "HR%",
            "WHIP",
            "FIP-",
            "ERA+",
            "IP",
        ]
        invert_cols = ["HR%", "WHIP", "FIP-", "BB%"]
    elif suffix in ("BR", "BF"):
        # Rename positions
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
        df["Pos"] = df["Pos"].map(pos_map)
        name_col = "Player"
        plot_cols = [
            "Def Value",
            "wSB",
            "BB/K",
            "BB%",
            "K%",
            "BABIP",
            "ISO",
            "OPS+",
            "PA",
        ]
        # Position specific stats
        if df[df[name_col] == name]["Pos"].values[0] == "C":
            plot_cols.insert(0, "Framing")
            plot_cols.insert(0, "Arm")
        elif df[df[name_col] == name]["Pos"].values[0] in (
            "1B",
            "2B",
            "3B",
            "SS",
            "UTL",
        ):
            plot_cols.insert(0, "Range")
            plot_cols.insert(0, "DPR")
        elif df[df[name_col] == name]["Pos"].values[0] in ("LF", "CF", "RF"):
            plot_cols.insert(0, "Range")
            plot_cols.insert(0, "Arm")
        invert_cols = ["K%"]

    # Get player's team, age
    team = df[df[name_col] == name]["Team"]
    age = df[df[name_col] == name]["Age"].astype(str)
    # Save raw numbers
    raw_data = df[df[name_col] == name][plot_cols].T
    raw_data = raw_data.reset_index()
    raw_data.columns = ["Stat", "Value"]
    raw_data = raw_data.iloc[::-1]
    if suffix in ("BR", "BF"):
        plot_cols.remove("PA")
    elif suffix in ("PR", "PF"):
        plot_cols.remove("IP")

    # Generate percentiles for given cols
    for col in plot_cols:
        # Standardize all stat cols as floats
        if "%" in col:
            df[col] = df[col].str.rstrip("%").astype("float") / 100.0
        else:
            df[col] = df[col].astype("float")
        df[col] = df[col].rank(pct=True)
        # Percentile adjustment (I.E. 0th percentile = lowest)
        df[col] = (df[col] - df[col].min()) / (df[col].max() - df[col].min())
        # invert_cols are stats where lower = better
        if col in invert_cols:
            df[col] = 1.0 - df[col]
        df[col] = df[col] * 100
        df[col] = df[col].fillna("0")
        # Convert to whole numbers for display on bar
        df[col] = df[col].astype("int")

    # Generate percentile graphs for desired player
    chart_data = df[df[name_col] == name][plot_cols].T
    chart_data = chart_data.reset_index()
    chart_data.columns = ["Stats", "Percentile Rank"]
    chart_data = chart_data.iloc[::-1]

    # Determine title/subtitle contents
    emoji_dict = {
        "ORIX Buffaloes": "🦬",
        "Hiroshima Carp": "🎏",
        "Chunichi Dragons": "🐉",
        "DeNA BayStars": "🌟",
        "Rakuten Eagles": "🦅",
        "Nipponham Fighters": "🦊",
        "Yomiuri Giants": "🐰",
        "SoftBank Hawks": "🪶",
        "Seibu Lions": "🦁",
        "Lotte Marines": "⚓",
        "Yakult Swallows": "🐧",
        "Hanshin Tigers": "🐯",
    }
    title = name + " " + emoji_dict[team.values[0]]
    if suffix in ("BR", "PR"):
        subtitle_str = team + " · " + year + " NPB"
    elif suffix in ("BF", "PF"):
        subtitle_str = team + " · " + year + " Farm"
    else:
        subtitle_str = team + " · " + year
    if suffix in ("BF", "BR"):
        tb_hand = df[df[name_col] == name]["B"]
        pos = df[df[name_col] == name]["Pos"]
        subtitle_str = (
            subtitle_str + " · " + pos + " · Age " + age + " · Bats " + tb_hand
        )
    elif suffix in ("PF", "PR"):
        tb_hand = df[df[name_col] == name]["T"]
        subtitle_str = subtitle_str + " · Age " + age + " · Throws " + tb_hand
    else:
        subtitle_str = subtitle_str + " · Age " + age

    # Chart settings
    title_params = alt.TitleParams(
        text=title,
        subtitle=subtitle_str,
        subtitleColor="grey",
    )
    chart = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X(
                "Percentile Rank",
                scale=alt.Scale(type="linear", domain=[0, 100]),
                title="",
                axis=alt.Axis(
                    values=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
                ),
            ),
            y=alt.Y("Stats", title="", sort=None),
            text="Percentile Rank",
            tooltip=alt.value(None),
            color=alt.Color("Percentile Rank")
            .scale(domain=[0, 100], range=["#3366cc", "#b3b3b3", "#e60000"])
            .legend(None),
        )
        .properties(
            width="container",
            height=alt.Step(25),
            title=title_params,
        )
    )

    # Display percentile number after bar
    chart = chart.mark_bar() + chart.mark_text(align="left", dx=2, fontSize=14)
    # Adjust font sizes
    chart = chart.configure_title(fontSize=20, subtitleFontSize=14)
    chart = chart.configure_axis(labelFontSize=14)

    # Display data on Streamlit
    st.altair_chart(
        chart,
        use_container_width=True,
        theme="streamlit",
        key=None,
        on_select="ignore",
        selection_mode=None,
    )

    # Display the actual stats the player has + league averages
    raw_data = add_league_average(df, raw_data, name, plot_cols, suffix)
    # Convert all of dataframe to string to avoid pyarrow.lib.ArrowInvalid
    raw_data = raw_data.astype(str)
    st.dataframe(
        raw_data, use_container_width=True, hide_index=True, row_height=25
    )


def add_league_average(df, player_df, name, stat_cols, suffix):
    """
    Adds league average statistics to a player's raw data DataFrame for
    comparison.

    Parameters:
        df (pandas.DataFrame): The full DataFrame containing all player
        statistics.
        player_df (pandas.DataFrame): DataFrame containing the selected
        player's raw statistics.
        name (str): The name of the player.
        stat_cols (list): List of statistic column names to include.
        suffix (str): Indicates stat type and determines which team stats to
        use ('BR', 'PR', etc.).

    Functionality:
        - Loads league average stats from the appropriate team CSV file based
        on suffix.
        - Appends league average values to the player's stats for side-by-side
        comparison.
        - Ensures relevant columns (including PA or IP) are included for
        display.
        - Inserts a "Player" column to label rows as either the player or
        "League Average".

    Returns:
        pandas.DataFrame: DataFrame containing both the player's and league
        average statistics.
    """
    # Transpose vertical df, reset index, and drop
    player_df = player_df.T
    player_df.columns = player_df.iloc[0]
    player_df = player_df.drop(index=player_df.index[0], axis=0)
    player_df.index = [0]

    # Append League Average stats
    if suffix in ("BR"):
        # Extract only league average row from Team stats
        team_df = load_csv(
            "https://raw.githubusercontent.com/chrisj117/npb-scraper/refs/heads/"
            + "master/stats/2025/streamlit_src/2025TeamBR.csv"
        )
        lg_avg = team_df[team_df["Team"] == "League Average"]
        lg_avg.index = [0]
        # Get PA from player df
        lg_avg.at[0, "PA"] = round(df.loc[:, 'PA'].mean(), 0)
        player_df = pd.concat([player_df, lg_avg])
        player_df = player_df.astype(str).replace("nan","0.0")
        # Drop extra concatenated columns
        stat_cols.append("PA")
        player_df = player_df[player_df.columns.intersection(stat_cols)]
    elif suffix in ("PR"):
        # Extract only league average row from Team stats
        team_df = load_csv(
            "https://raw.githubusercontent.com/chrisj117/npb-scraper/refs/heads/"
            + "master/stats/2025/streamlit_src/2025TeamPR.csv"
        )
        lg_avg = team_df[team_df["Team"] == "League Average"]
        lg_avg.index = [0]
        # Get PA from player df
        lg_avg.at[0, "IP"] = round(df.loc[:, 'IP'].mean(), 0)
        player_df = pd.concat([player_df, lg_avg])
        # Drop extra concatenated columns
        stat_cols.append("IP")
        player_df = player_df[player_df.columns.intersection(stat_cols)]

    player_df.insert(0, "Player", [name, "League Average"])
    return player_df
