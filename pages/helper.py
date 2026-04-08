"""Helper functions for Streamlit pages"""

from io import StringIO
import altair as alt
import streamlit as st
import pandas as pd
import requests
import numpy as np


@st.cache_data(ttl=600, show_spinner=False)
def load_csv(url=None):
    """
    Loads a csv from a link and returns it as a dataframe.

    Parameters:
        url (str): The raw csv link to load.

    Returns:
        (dataframe/None): Returns none if link is unable to be loaded, or a
        dataframe if the link is valid.
    """
    # Returns dataframe if good link, otherwise None
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        return pd.read_csv(StringIO(response.text))
    st.error("Failed to load raw data.")
    return None

def convert_ip_column_in(df, inn_col="IP"):
    """Converts the decimals in the IP column TO thirds (.1 -> .33, .2 -> .66)
    for stat calculations

    Parameters:
    df (pandas dataframe): A pitching stat dataframe with the traditional
    .1/.2 IP representation
    inn_col (string): The name of the column to convert (default is "IP")

    Returns:
    temp_df[inn_col] (pandas dataframe column): An IP column converted for stat
    calculations"""
    temp_df = pd.DataFrame(df[inn_col])
    # Get the ".0 .1 .2" in the 'IP' column
    ip_decimals = temp_df[inn_col] % 1
    # Make the original 'IP' column whole numbers
    temp_df[inn_col] = temp_df[inn_col] - ip_decimals
    # Multiply IP decimals by .3333333333 and readd them to the whole numbers
    ip_decimals = (ip_decimals * 10) * 0.3333333333
    temp_df[inn_col] = temp_df[inn_col] + ip_decimals
    return temp_df[inn_col]

def convert_ip_column_out(df, inn_col="IP"):
    """In baseball, innings are traditionally represented using .1 (single
    inning pitched), .2 (2 innings pitched), and whole numbers. This function
    converts the decimals FROM thirds (.33 -> .1, .66 -> .2) for sake of
    presentation

    Parameters:
    df (pandas dataframe): A pitching stat dataframe with the "thirds"
    representation
    inn_col (string): The name of the column to convert (default is "IP")

    Returns:
    temp_df[inn_col] (pandas dataframe column): An innings column
    converted back to the informal innings representation"""
    # Innings ".0 .1 .2" fix
    temp_df = pd.DataFrame(df[inn_col])
    # Get the ".0 .3 .7" in the innings column
    ip_decimals = temp_df[inn_col] % 1
    # Make the original innings column whole numbers
    temp_df[inn_col] = temp_df[inn_col] - ip_decimals
    # Convert IP decimals to thirds and re-add them to the whole numbers
    ip_decimals = (ip_decimals / 0.3333333333) / 10
    df[inn_col] = temp_df[inn_col] + ip_decimals
    # Entries with .3 are invalid: add 1 and remove the decimals
    x = temp_df[inn_col] + ip_decimals
    condlist = [((x % 1) < 0.29), ((x % 1) >= 0.29)]
    choicelist = [x, (x - (x % 1)) + 1]
    temp_df[inn_col] = np.select(condlist, choicelist)
    temp_df[inn_col] = temp_df[inn_col].apply(lambda x: f"{x:.1f}")
    temp_df[inn_col] = temp_df[inn_col].astype(float)
    return temp_df[inn_col]


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
            "FB Velo",
            "CSW%",
            "SwStr%",
            "Chase%",
            "GB%",
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
        pos_dict = {
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
        df["Pos"] = df["Pos"].map(pos_dict)
        name_col = "Player"
        plot_cols = [
            "Def Value",
            "SwStr%",
            "Z-Con%",
            "Chase%",
            "PullAIR%",
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
        invert_cols = ["K%", "SwStr%", "Chase%"]

    # Get player's team, age
    team = df[df[name_col] == name]["Team"]
    age = df[df[name_col] == name]["Age"].astype(str)
    # Save raw numbers
    raw_data = df[df[name_col] == name][plot_cols].T
    raw_data = raw_data.reset_index()
    raw_data.columns = ["Stat", "Value"]
    raw_data = raw_data.iloc[::-1]

    # Store original values before converting to percentiles
    original_values = raw_data["Value"].copy().astype(str)

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

    # Keep in original plot_cols order (transpose reverses, so we reverse back)
    chart_data = chart_data.iloc[::-1]
    # Add original values to chart_data
    chart_data["Value"] = original_values
    # Add an explicit order column to lock y ordering across layers
    chart_data["order"] = range(len(chart_data))
    # Reuse a single Y encoding with explicit sort to maintain stat order between layers
    y_enc = alt.Y(
        "Stats:N",
        title="",
        sort=alt.SortField(field="order", order="ascending"),
        axis=alt.Axis(labelFontSize=14),
    )

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
        subtitle_str1 = team + " · " + year + " NPB"
    elif suffix in ("BF", "PF"):
        subtitle_str1 = team + " · " + year + " Farm"
    else:
        subtitle_str1 = team + " · " + year
    if suffix in ("BF", "BR"):
        subtitle_str2 = (
            df[df[name_col] == name]["PA"].astype(str)
            + " PA"
            + " · "
            + df[df[name_col] == name]["Pos"].astype(str)
            + " · Age "
            + age
            + " · Bats "
            + df[df[name_col] == name]["B"].astype(str)
        )
    elif suffix in ("PF", "PR"):
        subtitle_str2 = (
            df[df[name_col] == name]["IP"].astype(str)
            + " IP"
            + " · "
            + "Age "
            + age
            + " · Throws "
            + df[df[name_col] == name]["T"].astype(str)
        )
    else:
        subtitle_str2 = "Age " + age

    # Chart settings
    title_params = alt.TitleParams(
        text=title,
        subtitle=[
            subtitle_str1.values[0],
            subtitle_str2.values[0],
            "@YakyuCosmo",
        ],
        subtitleColor="grey",
        subtitleFontSize=13.5,
    )
    # Create base bar graph that charts the data
    chart = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X(
                "Percentile Rank",
                scale=alt.Scale(
                    type="linear", domain=[0, 105]
                ),  # Extended to 105 to add padding for stats on right
                title="",
                axis=alt.Axis(values=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]),
            ),
            y=y_enc,
            text="Percentile Rank",
            tooltip=alt.value(None),
            color=alt.Color("Percentile Rank")
            .scale(domain=[0, 100], range=["#3366cc", "#b3b3b3", "#e60000"])
            .legend(None),
        )
        .properties(
            height=alt.Step(25),
            title=title_params,
        )
    )

    # Create circle layer for background behind percentile numbers
    circle_layer = (
        alt.Chart(chart_data)
        .mark_circle(size=400, opacity=1, stroke="white", strokeWidth=2)
        .encode(
            x="Percentile Rank",
            y=y_enc,
            # Match circle color with bar color based on percentile rank
            color=alt.Color("Percentile Rank")
            .scale(domain=[0, 100], range=["#3366cc", "#b3b3b3", "#e60000"])
            .legend(None),
            tooltip=alt.value(None),
        )
    )

    # Create a text layer with percentile values aligned with end of bar
    percentile_layer = (
        alt.Chart(chart_data)
        .mark_text(align="center", dx=0, fontSize=12, color="white")
        .encode(
            x="Percentile Rank",
            y=y_enc,
            text="Percentile Rank",
            tooltip=alt.value(None),
        )
    )

    # Create a text layer with original values along right edge of chart
    raw_stat_layer = (
        alt.Chart(chart_data)
        .mark_text(
            align="left",
            baseline="middle",
            dx=5,  # Position to the right of the bar
            fontSize=14,
            color="grey",
        )
        .encode(
            # Fixed position outside the chart
            x=alt.datum(105),
            y=y_enc,
            # Show original value (already formatted)
            text="Value",
            tooltip=alt.value(None),
        )
    )

    # Combine all layers
    chart = alt.layer(chart, circle_layer, percentile_layer, raw_stat_layer)

    # Configure the chart
    chart = chart.configure_title(fontSize=20, subtitleFontSize=14)
    chart = chart.configure_axis(labelFontSize=14)

    # Display data on Streamlit
    st.altair_chart(
        chart,
        width="stretch",
        theme="streamlit",
        key=None,
        on_select="ignore",
        selection_mode=None,
    )


def create_sort_filter(cols, mode):
    """
    Creates Streamlit widgets for sorting and filtering data columns.

    Parameters:
        cols (list): List of column names available for sorting.
        mode (str): Mode determining which default sort order to use.
                    Options: "bat" (batting stats), "pitch" (pitching stats),
                    "field" (fielding stats), or other (generic).

    Functionality:
        - Provides mode-specific default sort orders for batting, pitching,
          and fielding statistics.
        - Displays a select box for users to choose the column to sort by.
        - Displays a toggle for users to choose ascending or descending sort
          order, with default based on the column's typical interpretation
          (e.g., ERA defaults to ascending, HR defaults to descending).
        - Returns the selected column and sort direction.

    Returns:
        tuple: (user_sort_col, user_sort_asc) where:
            - user_sort_col (str): The column name selected for sorting
            - user_sort_asc (bool): True for ascending, False for descending
    """
    if mode == "bat":
        default_sort = {
            "Player": None,
            "Age": "asc",
            "PA": "desc",
            "AB": "desc",
            "R": "desc",
            "H": "desc",
            "2B": "desc",
            "3B": "desc",
            "HR": "desc",
            "TB": "desc",
            "RBI": "desc",
            "SB": "desc",
            "CS": "desc",
            "SH": "desc",
            "SF": "desc",
            "SO": "desc",
            "BB": "desc",
            "IBB": "desc",
            "HP": "desc",
            "GDP": "desc",
            "AVG": "desc",
            "OBP": "desc",
            "SLG": "desc",
            "OPS": "desc",
            "OPS+": "desc",
            "ISO": "desc",
            "BABIP": "desc",
            "K%": "asc",
            "BB%": "desc",
            "BB/K": "desc",
            "wSB": "desc",
            "PullAIR%": "desc",
            "Chase%": "asc",
            "Z-Con%": "desc",
            "Swing%": "desc",
            "SwStr%": "asc",
            "TTO%": "desc",
            "B": None,
            "Pos": None,
            "Team": None,
            "League": None,
        }
        # Set index of default sort column for individual stat pages
        if "Player" in cols:
            default_sort_col_index = cols.index("PA")
        # Set index of default sort column for team stat pages
        else:
            default_sort_col_index = cols.index("OPS+")
    elif mode == "pitch":
        default_sort = {
            "Pitcher": None,
            "Age": "asc",
            "G": "desc",
            "W": "desc",
            "L": "desc",
            "SV": "desc",
            "HLD": "desc",
            "CG": "desc",
            "SHO": "desc",
            "WP": "desc",
            "R": "desc",
            "ER": "desc",
            "ERA": "asc",
            "FIP": "asc",
            "kwERA": "asc",
            "WHIP": "asc",
            "FIP-": "asc",
            "ERA+": "desc",
            "Diff": "desc",
            "IP": "desc",
            "H": "desc",
            "HR": "desc",
            "SO": "desc",
            "BB": "desc",
            "IBB": "desc",
            "HB": "desc",
            "BF": "desc",
            "K%": "desc",
            "BB%": "asc",
            "K-BB%": "desc",
            "CSW%": "desc",
            "HR%": "asc",
            "Con%": "desc",
            "SwStr%": "desc",
            "Chase%": "desc",
            "GB%": "desc",
            "LD%": "desc",
            "FB Velo": "desc",
            "Team": None,
            "League": None,
        }
        # Set index of default sort column for individual stat pages
        if "Pitcher" in cols:
            default_sort_col_index = cols.index("IP")
        # Set index of default sort column for team stat pages
        else:
            default_sort_col_index = cols.index("ERA+")
    elif mode == "field":
        default_sort = {
            # Fielding
            "Player": None,
            "Age": "asc",
            "Pos": None,
            "Inn": "desc",
            "TZR": "desc",
            "TZR/143": "desc",
            "RngR": "desc",
            "ARM": "desc",
            "DPR": "desc",
            "ErrR": "desc",
            "Pos Adj": "desc",
            "Framing": "desc",
            "Blocking": "desc",
            "Team": None,
            "League": None,
        }
        # Set index of default sort column for individual stat pages
        if "Inn" in cols:
            default_sort_col_index = cols.index("Inn")
        # Set index of default sort column for team stat pages
        else:
            default_sort_col_index = cols.index("TZR")
    else:
        default_sort = {
            "Team": None,
            "League": None,
        }
        default_sort_col_index = 0

    user_sort_col = st.selectbox("Sort by", cols, index=default_sort_col_index)
    if default_sort[user_sort_col] == "desc":
        user_sort_asc = st.toggle("Ascending", value=False)
    else:
        user_sort_asc = st.toggle("Ascending", value=True)

    return user_sort_col, user_sort_asc


def create_pos_filter(df, mode=None):
    """
    Creates a Streamlit segmented control filter for player positions.

    Parameters:
        df (pandas.DataFrame): DataFrame containing a "Pos" column with
            position codes.
        mode (str, optional): If set to "player_field", removes pitcher, N/A,
            and UTL positions from the filter.

    Functionality:
        - Maps numeric and string position codes to their abbreviations.
        - Optionally removes certain positions for field player filtering.
        - Displays a multi-select segmented control for users to choose
        positions.
        - Returns the list of selected position abbreviations.

    Returns:
        list: List of selected position abbreviations.
    """
    # Change original data to have abbreviation rather than pos numbers
    pos_dict = {
        "1": "P",
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
        "N/A": "N/A",
    }
    if mode == "player_field":
        del pos_dict["1"]
        del pos_dict["N/A"]
        del pos_dict["UTL"]
    df["Pos"] = df["Pos"].map(pos_dict)

    pos_list = st.multiselect(
        "Positions",
        pos_dict.values(),
        default=pos_dict.values(),
    )
    return pos_list


def create_stat_cols_filter(df, mode=None, key=None):
    """
    Creates a Streamlit segmented control filter for selecting statistic
    columns to display.

    Parameters:
        df (pandas.DataFrame): DataFrame containing available statistic
            columns.
        mode (str, optional): If set to "player_bat" or "player_pitch",
            provides a default selection of common batting or pitching stats.
            Otherwise, defaults to all columns.

    Functionality:
        - Displays a multi-select segmented control for users to choose which
        statistic columns to show.
        - Sorts the selected columns in the order they appear in the DataFrame.

    Returns:
        list: List of selected statistic column names.
    """
    if mode == "player_bat":
        filter_default = [
            "Player",
            "PA",
            "HR",
            "RBI",
            "SB",
            "AVG",
            "OBP",
            "SLG",
            "OPS",
            "OPS+",
            "ISO",
            "K%",
            "BB%",
            "Team",
        ]
    elif mode == "player_pitch":
        filter_default = [
            "Pitcher",
            "IP",
            "W",
            "L",
            "SV",
            "ERA",
            "FIP",
            "WHIP",
            "ERA+",
            "FIP-",
            "K%",
            "BB%",
            "K-BB%",
            "Team",
            "GB%",
            "CSW%",
            "FB Velo",
        ]
    elif mode == "player_field":
        filter_default = [
            "Player",
            "Pos",
            "Inn",
            "TZR",
            "TZR/143",
            "RngR",
            "ARM",
            "DPR",
            "ErrR",
            "Pos Adj",
            "Framing",
            "Blocking",
            "Team",
        ]
    elif mode == "team_bat":
        filter_default = [
            "Team",
            "PA",
            "HR",
            "R",
            "RBI",
            "SB",
            "AVG",
            "OBP",
            "SLG",
            "OPS",
            "OPS+",
            "ISO",
            "K%",
            "BB%",
        ]
    elif mode == "team_pitch":
        filter_default = [
            "Team",
            "IP",
            "W",
            "L",
            "SV",
            "HLD",
            "ERA",
            "FIP",
            "WHIP",
            "ERA+",
            "FIP-",
            "K%",
            "BB%",
            "K-BB%",
        ]
    elif mode == "team_field":
        filter_default = [
            "TZR",
            "TZR/143",
            "RngR",
            "ARM",
            "DPR",
            "ErrR",
            "Framing",
            "Blocking",
            "Team",
        ]
    elif mode == "career_bat_cols":
        filter_default = [
            "Year",
            "Age",
            "G",
            "PA",
            "HR",
            "H",
            "RBI",
            "SB",
            "AVG",
            "OBP",
            "SLG",
            "OPS",
            "OPS+",
            "ISO",
            "K%",
            "BB%",
            "Team",
        ]
    elif mode == "career_pitch_cols":
        filter_default = [
            "Year",
            "Age",
            "G",
            "IP",
            "W",
            "L",
            "SV",
            "HLD",
            "ERA",
            "FIP",
            "WHIP",
            "HR%",
            "ERA+",
            "FIP-",
            "K%",
            "BB%",
            "K-BB%",
            "Team",
        ]
    else:
        filter_default = df.columns.tolist()

    # Add "select all" and "select none" columns option
    filter_container = st.container()
    if key is not None:
        all_none_key = key + "_all_none"
    else:
        all_none_key = key
    all_none_filter = st.segmented_control(
        "Select Stats", options=["All", "None"], selection_mode="single", key=all_none_key
    )
    if all_none_filter == "All":
        cols = filter_container.segmented_control(
            "Statistics",
            df.columns.tolist(),
            default=df.columns.tolist(),
            selection_mode="multi",
        )
    elif all_none_filter == "None":
        cols = filter_container.segmented_control(
            "Statistics",
            df.columns.tolist(),
            default=df.columns.tolist()[0],
            selection_mode="multi",
        )
    else:
        cols = filter_container.segmented_control(
            "Statistics",
            df.columns.tolist(),
            default=filter_default,
            selection_mode="multi",
        )

    # Sort cols as dataframe
    cols = [c for c in df.columns.tolist() if c in cols]
    return cols


def create_team_filter(mode=None, team_col=None, key=None):
    # TODO: docs
    """
    Creates a Streamlit multiselect filter for NPB team selection.

    Parameters:
        mode (str, optional): If set to "farm", includes farm league teams in
            the filter.

    Functionality:
        - Maps team abbreviations to full team names.
        - Optionally adds farm league teams if mode is "farm".
        - Displays a multiselect widget for users to choose teams.
        - Returns a list of selected full team names.

    Returns:
        list/str: List/string of selected full team name(s).
    """
    team_dict = {
        "Hanshin": "Hanshin Tigers",
        "Chunichi": "Chunichi Dragons",
        "DeNA": "DeNA BayStars",
        "Hiroshima": "Hiroshima Carp",
        "Lotte": "Lotte Marines",
        "Nipponham": "Nipponham Fighters",
        "ORIX": "ORIX Buffaloes",
        "Rakuten": "Rakuten Eagles",
        "Seibu": "Seibu Lions",
        "SoftBank": "SoftBank Hawks",
        "Yakult": "Yakult Swallows",
        "Yomiuri": "Yomiuri Giants",
    }
    if mode == "farm":
        team_dict.update(
            {
                "HAYATE": "HAYATE Ventures",
                "Oisix": "Oisix Albirex",
            }
        )

    if mode == "overview":
        team = st.selectbox("Team", team_dict.values(), key=key)
    elif mode == "career":
        team = st.multiselect(
            "Team", team_dict.keys(), default=team_dict.keys(), key=key
        )
    else:
        team = st.multiselect(
            "Team", team_dict.keys(), default=team_dict.keys(), key=key
        )
        team = [team_dict[k] for k in team]
    return team


def create_pa_filter(df, mode=None):
    """
    Creates a Streamlit number input widget for filtering by minimum plate
    appearances (PA).

    Parameters:
        df (pandas.DataFrame): DataFrame containing a "PA" column with plate
            appearance values.
        mode (str, optional): If set to "player", allows any PA value.
            If set to "percentile", sets a higher minimum and default value.
            Otherwise, uses the minimum PA in the DataFrame.

    Functionality:
        - Determines the minimum and default PA values based on mode.
        - Displays a number input widget for users to select the minimum PA.
        - Returns the selected minimum PA value.

    Returns:
        int: The user-selected minimum plate appearances value.
    """
    if mode == "player":
        filter_min = 0
        filter_default = 0
    elif mode == "percentile":
        filter_min = 25
        if df["PA"].max() >= 25 and df["PA"].max() <= 50:
            filter_default = 25
        else:
            filter_default = 50
    else:
        filter_min = 0
        filter_default = df["PA"].min()

    pa = st.number_input(
        "Min. PA",
        value=filter_default,
        min_value=filter_min,
        step=50,
        max_value=df["PA"].max(),
    )
    return pa


def create_ip_filter(df, mode=None):
    """
    Creates a Streamlit number input widget for filtering by minimum innings
    pitched (IP).

    Parameters:
        df (pandas.DataFrame): DataFrame containing an "IP" column with innings
            pitched values.
        mode (str, optional): If set to "player", allows any IP value.
            If set to "percentile", sets a higher minimum and default value.
            Otherwise, uses the minimum IP in the DataFrame.

    Functionality:
        - Determines the minimum and default IP values based on mode.
        - Displays a number input widget for users to select the minimum IP.
        - Returns the selected minimum IP value.

    Returns:
        float: The user-selected minimum innings pitched value.
    """
    if mode == "player":
        filter_min = 0.0
        filter_default = 0.0
    elif mode == "percentile":
        filter_min = 10.0
        if df["IP"].max() >= 10.0 and df["IP"].max() <= 25.0:
            filter_default = 10.0
        else:
            filter_default = 25.0
    else:
        filter_min = 0.0
        filter_default = df["IP"].min()

    ip = st.number_input(
        "Min. IP",
        value=filter_default,
        min_value=filter_min,
        step=25.0,
        max_value=df["IP"].max(),
        format="%0.1f",
    )
    return ip


def create_inn_filter(df, mode=None):
    """
    Creates a Streamlit number input widget for filtering by minimum innings
    fielded.

    Parameters:
        df (pandas.DataFrame): DataFrame containing an "Inn" column with
            innings fielded values.
        mode (str, optional): If set to "player", allows any innings value.
            Otherwise, uses the minimum innings in the DataFrame.

    Functionality:
        - Determines the minimum and default innings values based on mode.
        - Displays a number input widget for users to select the minimum
            innings fielded.
        - Returns the selected minimum innings value.

    Returns:
        float: The user-selected minimum innings fielded value.
    """
    if mode == "player":
        filter_min = 0.0
        filter_default = 0.0
    else:
        filter_min = 0.0
        filter_default = df["Inn"].min()

    inn = st.number_input(
        "Min. Inn",
        value=filter_default,
        min_value=filter_min,
        step=250.0,
        max_value=df["Inn"].max(),
        format="%0.1f",
    )
    return inn


def create_hand_filter(mode=None):
    """
    Creates a Streamlit segmented control filter for selecting batting or
    pitching hand.

    Parameters:
        mode (str, optional): If set to "player_pitch", displays pitching hand
            options ("L", "R"). If set to "player_bat", displays batting hand
            options ("L", "S", "R"). Otherwise, displays all hand options.

    Functionality:
        - Sets the filter label and available hand options based on mode.
        - Displays a multi-select segmented control for users to choose
            hand(s).
        - Returns the list of selected hand options.

    Returns:
        list: List of selected hand options.
    """
    if mode == "player_pitch":
        filter_label = "Pitching Hand"
        filter_hands = ["L", "R"]
        filter_default = ["L", "R"]
    elif mode == "player_bat":
        filter_label = "Batting Hand"
        filter_hands = ["L", "S", "R"]
        filter_default = ["L", "S", "R"]
    else:
        filter_label = "Hand"
        filter_hands = ["L", "S", "R"]
        filter_default = ["L", "S", "R"]

    hand = st.pills(
        filter_label,
        filter_hands,
        default=filter_default,
        selection_mode="multi",
    )
    return hand


def create_league_filter(mode=None):
    """
    Creates a Streamlit segmented control filter for selecting NPB or farm
    league(s).

    Parameters:
        mode (str, optional): If set to "npb", displays only NPB leagues
            ("CL", "PL"). If set to "farm", displays only farm leagues
            ("EL", "WL"). Otherwise, displays all league options.

    Functionality:
        - Sets available league options and defaults based on mode.
        - Displays a multi-select segmented control for users to choose
            league(s).
        - Returns the list of selected league abbreviations.

    Returns:
        list: List of selected league abbreviations.
    """
    if mode == "npb":
        filter_leagues = ["CL", "PL"]
        filter_default = ["CL", "PL"]
    elif mode == "farm":
        filter_leagues = ["EL", "WL"]
        filter_default = ["EL", "WL"]
    else:
        filter_leagues = ["CL", "PL", "EL", "WL"]
        filter_default = ["CL", "PL", "EL", "WL"]

    league = st.pills(
        "League",
        filter_leagues,
        default=filter_default,
        selection_mode="multi",
    )
    return league


def convert_pct_cols_to_float(df):
    """
    Converts columns containing percentage values (with '%' sign) in a
    DataFrame to float type.

    Parameters:
        df (pandas.DataFrame): DataFrame with columns that may contain
            percentage strings.

    Functionality:
        - Identifies columns with percentage values.
        - Removes the '%' sign and converts the values to float type.
        - Ensures proper numeric sorting and calculations in downstream usage.

    Returns:
        pandas.DataFrame: The DataFrame with percentage columns converted to
        float.
    """
    # Format data that has percent format since it breaks sorting
    df = df.copy()
    for col in df.columns.tolist():
        if df[col].astype(str).str.contains("%").any():
            df[col] = df[col].str.rstrip("%").astype("float")
    return df


def create_year_filter():
    """
    Creates a Streamlit select box filter for selecting statistic years.

    Parameters:
        N/A

    Functionality:
        - Streamlines controlling what years users can request.

    Returns:
        string: The user's chosen year.
    """
    # Always place newest year first
    year = st.selectbox("Year", ["2026","2025"])
    return year


def create_player_filter(df, player_col, key=None):
    """
    Creates a Streamlit select box filter for selecting players.

    Parameters:
        df (pandas.DataFrame): DataFrame with a "Pitcher" or "Player" column.
        player_col (string): The column containing player names.

    Functionality:
        - Sorts name columns for consistent display across pages.

    Returns:
        string: The user's chosen year.
    """
    df = df.sort_values(player_col)
    player_list = df[player_col]
    player = st.selectbox(player_col, player_list, key=key)
    return player


def get_column_config(suffix=None):
    """
    Provides statistic hover labels and trailing zeroes for DataFrames on
    Streamlit.

    Parameters:
        suffix (str, optional): If set to "None", no trailing zeroes or labels
            are enforced. Otherwise, provides the appropriate column config for
            the DataFrame.

    Functionality:
        - Ensures statistics displayed on one page appear the same across the
        whole site.

    Returns:
        set: The appropriate column_config arguments.
    """
    if suffix in ("P", "PR", "PF"):
        column_config = {
            "#": st.column_config.NumberColumn(
                width=15,
                alignment="left",
            ),
            "Team": st.column_config.TextColumn(
                width=90,
                alignment="left",
            ),
            "Year": st.column_config.TextColumn(
                width=45,
                alignment="left",
            ),
            "GB%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Ground Ball Rate: The percentage of balls in play against a pitcher that are hit on the ground.",
                alignment="left",
            ),
            "Chase%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Chase Rate: The percentage of pitches outside the strike zone that batters swing at. Recognized by PitcherList.com in 2018 as one of the “Big Three” plate discipline metrics.",
                alignment="left",
            ),
            "Con%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Contact Rate: The percentage of swings against a pitcher that result in contact, including both fair and foul balls. Recognized by PitcherList.com in 2018 as one of the “Big Three” plate discipline metrics.",
                alignment="left",
            ),
            "SwStr%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Swinging Strike Rate: The percentage of a pitcher's total pitches that result in swinging strikes. Recognized by PitcherList.com in 2018 as one of the “Big Three” plate discipline metrics.",
                alignment="left",
            ),
            "CSW%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Called Strike plus Whiff Rate: The percentage of a pitcher's pitches that result in either a called strike or a swinging strike.",
                alignment="left",
            ),
            "FB Velo": st.column_config.NumberColumn(
                format="%.1f",
                help="Average Fastball Velocity: The average speed of a pitcher's fastball, measured in miles per hour (mph).",
                alignment="left",
            ),
            "G": st.column_config.NumberColumn(
                help="Games Played: The number of games in which a pitcher appears.",
                alignment="left",
            ),
            "W": st.column_config.NumberColumn(
                help="Wins: The number of games a pitcher is credited with a winning decision.",
                alignment="left",
            ),
            "L": st.column_config.NumberColumn(
                help="Losses: The number of games a pitcher is credited with a losing decision.",
                alignment="left",
            ),
            "IP": st.column_config.NumberColumn(
                format="%.1f",
                help="Innings Pitched: The total number of innings a pitcher completes, recorded in one-third increments.",
                alignment="left",
            ),
            "BF": st.column_config.NumberColumn(
                help="Batters Faced: The total number of hitters a pitcher faces.",
                alignment="left",
            ),
            "R": st.column_config.NumberColumn(
                help="Runs: The total number of runs a pitcher allows.",
                alignment="left",
            ),
            "ER": st.column_config.NumberColumn(
                help="Earned Runs: The number of runs scored against the pitcher that are not the result of errors or passed balls.",
                alignment="left",
            ),
            "H": st.column_config.NumberColumn(
                help="Hits: The number of hits a pitcher allows.",
                alignment="left",
            ),
            "HR": st.column_config.NumberColumn(
                help="Home Runs: The number of home runs a pitcher allows.",
                alignment="left",
            ),
            "HR%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Home Run Rate: The percentage of batters faced by a pitcher that results in home runs.",
                alignment="left",
            ),
            "BB": st.column_config.NumberColumn(
                help="Walks: The number of times a pitcher allows a batter to reach first base by throwing four balls.",
                alignment="left",
            ),
            "BB%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Walk Rate: The percentage of batters faced by a pitcher that result in walks.",
                alignment="left",
            ),
            "IBB": st.column_config.NumberColumn(
                help="Intentional Walks: The number of walks a pitcher intentionally issues.",
                alignment="left",
            ),
            "HB": st.column_config.NumberColumn(
                help="Hit By Pitches: The number of batters a pitcher hits with a pitch.",
                alignment="left",
            ),
            "SO": st.column_config.NumberColumn(
                help="Strikeouts: The number of batters a pitcher retires on strikes.",
                alignment="left",
            ),
            "K%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Strikeout Rate: The percentage of batters faced by a pitcher that result in strikeouts.",
                alignment="left",
            ),
            "K-BB%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Strikeout Rate minus Walk Rate: The difference between a pitcher's strikeout rate and walk rate.",
                alignment="left",
            ),
            "WHIP": st.column_config.NumberColumn(
                format="%.2f",
                help="Walks plus Hits per Inning Pitched: The average number of walks and hits allowed by a pitcher per inning.",
                alignment="left",
            ),
            "ERA+": st.column_config.NumberColumn(
                format="%.0f",
                help="Earned Run Average Plus: A normalized version of ERA that adjusts for park factors, with 100 always being the league average. Higher values are better.",
                alignment="left",
            ),
            "FIP": st.column_config.NumberColumn(
                format="%.2f",
                help="Fielding Independent Pitching: A measure of a pitcher's effectiveness based on strikeouts, walks, and home runs, independent of defensive performance.",
                alignment="left",
            ),
            "FIP-": st.column_config.NumberColumn(
                format="%.0f",
                help="Fielding Independent Pitching Minus: A normalized version of FIP that adjusts for park factors, with 100 always being the league average. Lower values are better.",
                alignment="left",
            ),
            "Diff": st.column_config.NumberColumn(
                format="%.2f",
                help="ERA-FIP Differential: The differential of a pitcher's ERA and FIP. Higher values indicate underperformance and lower values indicate overperformance relative to expectations.",
                alignment="left",
            ),
            "kwERA": st.column_config.NumberColumn(
                format="%.2f",
                help="Strikeout-Walk based Earned Run Average: An estimate of a pitcher's ERA based on strikeout and walk rates.",
                alignment="left",
            ),
            "kwERA-": st.column_config.NumberColumn(
                format="%.0f",
                help="Strikeout-Walk based Earned Run Average Minus: A normalized version of kwERA with 100 always being the league average. Lower values are better.",
                alignment="left",
            ),
            "SV": st.column_config.NumberColumn(
                help="Saves: The number of games a pitcher finishes while preserving a lead of three runs or fewer.",
                alignment="left",
            ),
            "HLD": st.column_config.NumberColumn(
                help="Holds: The number of games a relief pitcher enters in a save situation, maintains the lead, but does not finish.",
                alignment="left",
            ),
            "CG": st.column_config.NumberColumn(
                help="Complete Games: The number of games where a pitcher pitches the entire game.",
                alignment="left",
            ),
            "SHO": st.column_config.NumberColumn(
                help="Shutouts: The number of complete games a pitcher finishes without allowing any runs.",
                alignment="left",
            ),
            "WP": st.column_config.NumberColumn(
                help="Wild Pitches: The number of pitches a pitcher throws that are too wild for the catcher to handle, allowing baserunners to advance.",
                alignment="left",
            ),
            "Qualifier": st.column_config.TextColumn(
                help="Qualified Pitcher: A pitcher is qualified for titles with 1.0 IP per team game played (NPB) or 0.8 IP per team game played (Farm).",
                alignment="left",
            ),
            "ERA": st.column_config.NumberColumn(
                format="%.2f",
                help="Earned Run Average: The average number of earned runs a pitcher allows per nine innings pitched.",
                alignment="left",
            ),
            "Age": st.column_config.TextColumn(
                width=40,
                help="Age: How old a pitcher is on June 30th of that year.",
                alignment="left",
            ),
            "T": st.column_config.TextColumn(
                help="Throws: A pitcher's throwing hand.",
                alignment="left",
            ),
        }
    elif suffix in ("B", "BR", "BF"):
        column_config = {
            "#": st.column_config.NumberColumn(
                width=15,
                alignment="left",
            ),
            "Team": st.column_config.TextColumn(
                width=90,
                alignment="left",
            ),
            "Year": st.column_config.TextColumn(
                width=45,
                alignment="left",
            ),
            "PullAIR%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Pull Air Rate: The percentage of balls in play that are pulled and not hit on the ground.",
                alignment="left",
            ),
            "Chase%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Chase Rate: The percentage of pitches outside the strike zone that batters swing at.",
                alignment="left",
            ),
            "Z-Con%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="In-Zone Contact Rate: The percentage of swings on pitches in the strike zone that result in contact, including both fair and foul balls.",
                alignment="left",
            ),
            "SwStr%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Swinging Strike Rate: The percentage of a player's total pitches that result in swinging strikes.",
                alignment="left",
            ),
            "Swing%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Swing Rate: The percentage of total pitches a player swings at.",
                alignment="left",
            ),
            "AB": st.column_config.NumberColumn(
                help="At-bats: The number of times a player bats, excluding walks, hit-by-pitches, sacrifices, errors, fielder's choices, and catcher's interferences.",
                alignment="left",
            ),
            "K%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Strikeout Rate: The percentage of a player's plate appearances that end in a strikeout.",
                alignment="left",
            ),
            "BB%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Walk Rate: The percentage of a player's plate appearances that result in a walk.",
                alignment="left",
            ),
            "TTO%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Three True Outcomes Rate: The percentage of a player's plate appearances that result in one of the three true outcomes: a home run, a strikeout, or a walk.",
                alignment="left",
            ),
            "AVG": st.column_config.NumberColumn(
                format="%.3f",
                help="Batting Average: The ratio of a player's hits to their at-bats.",
                alignment="left",
            ),
            "OBP": st.column_config.NumberColumn(
                format="%.3f",
                help="On Base Percentage: The percentage of plate appearances in which a player reaches base.",
                alignment="left",
            ),
            "SLG": st.column_config.NumberColumn(
                format="%.3f",
                help="Slugging Percentage: The total number of bases a player records per at-bat.",
                alignment="left",
            ),
            "OPS": st.column_config.NumberColumn(
                format="%.3f",
                help="On Base plus Slugging: The sum of a player's on-base percentage and slugging percentage.",
                alignment="left",
            ),
            "ISO": st.column_config.NumberColumn(
                format="%.3f",
                help="Isolated Power: A measure of a hitter's raw power, calculated as SLG - AVG.",
                alignment="left",
            ),
            "BABIP": st.column_config.NumberColumn(
                format="%.3f",
                help="Batting Average on Balls in Play: The batting average for balls hit into play, excluding home runs.",
                alignment="left",
            ),
            "BB/K": st.column_config.NumberColumn(
                format="%.2f",
                help="Walk to Strikeout Ratio: A comparison of how often a player walks versus how often they strike out.",
                alignment="left",
            ),
            "wSB": st.column_config.NumberColumn(
                format="%.1f",
                help="Weighted Stolen Base Runs: An estimate of the number of runs a player contributes to his team by stealing bases, with 0.0 being league-average.",
                alignment="left",
            ),
            "G": st.column_config.NumberColumn(
                help="Games Played: The number of games in which a player appears.",
                alignment="left",
            ),
            "PA": st.column_config.NumberColumn(
                help="Plate Appearances: The total number of times a player comes to bat.",
                alignment="left",
            ),
            "R": st.column_config.NumberColumn(
                help="Runs: The number of times a player crosses home plate to score.",
                alignment="left",
            ),
            "RBI": st.column_config.NumberColumn(
                help="Runs Batted In: The number of runs a player drives in with their at-bats, except when grounding into a double play or reaching on an error.",
                alignment="left",
            ),
            "1B": st.column_config.NumberColumn(
                help="Singles: The number of hits where a player safely reaches first base without an error or fielder's choice.",
                alignment="left",
            ),
            "2B": st.column_config.NumberColumn(
                help="Doubles: The number of hits where a player safely reaches second base without an error or fielder's choice.",
                alignment="left",
            ),
            "3B": st.column_config.NumberColumn(
                help="Triples: The number of hits where a player safely reaches third base without an error or fielder's choice.",
                alignment="left",
            ),
            "HR": st.column_config.NumberColumn(
                help="Home Runs: The number of hits where a player safely reaches home plate without an error or fielder's choice.",
                alignment="left",
            ),
            "TB": st.column_config.NumberColumn(
                help="Total Bases: The total number of bases a player records from hits.",
                alignment="left",
            ),
            "BB": st.column_config.NumberColumn(
                help="Walks: The number of times a player is awarded first base after receiving four balls outside the strike zone.",
                alignment="left",
            ),
            "IBB": st.column_config.NumberColumn(
                help="Intentional Walks: The number of times a player is intentionally awarded first base by the opposing team.",
                alignment="left",
            ),
            "SO": st.column_config.NumberColumn(
                help="Strikeouts: The number of times a player is put out on three strikes.",
                alignment="left",
            ),
            "HP": st.column_config.NumberColumn(
                help="Hit By Pitches: The number of times a player reaches first base after being hit by a pitched ball.",
                alignment="left",
            ),
            "SB": st.column_config.NumberColumn(
                help="Stolen Bases: The number of times a player successfully steals a base.",
                alignment="left",
            ),
            "CS": st.column_config.NumberColumn(
                help="Caught Stealing: The number of times a player is tagged out while attempting to steal a base.",
                alignment="left",
            ),
            "SF": st.column_config.NumberColumn(
                help="Sacrifice Flies: A fly ball that results in a run being scored, but the batter is out.",
                alignment="left",
            ),
            "SH": st.column_config.NumberColumn(
                help="Sacrifice Hits: A bunt that allows a runner to advance to the next base, but the batter is out.",
                alignment="left",
            ),
            "GDP": st.column_config.NumberColumn(
                help="Grounded into Double Plays: The number of times a player hits a ground ball that results in two outs.",
                alignment="left",
            ),
            "OPS+": st.column_config.NumberColumn(
                format="%.0f",
                help="On Base plus Slugging Plus: A normalized version of OPS that adjusts for park factors, with 100 always being the league average. Higher values are better.",
                alignment="left",
            ),
            "Qualifier": st.column_config.TextColumn(
                help="Qualified Hitter: A player is qualified for titles with 3.1 PA per team game played (NPB) or 2.7 PA per team game played (Farm).",
                alignment="left",
            ),
            "H": st.column_config.NumberColumn(
                help="Hits: The number of times a player reaches safely on a ball put in play without an error or fielder's choice.",
                alignment="left",
            ),
            "Age": st.column_config.TextColumn(
                width=40,
                help="Age: How old a player is on June 30th of that year.",
                alignment="left",
            ),
            "B": st.column_config.TextColumn(
                help="Bats: A player's batting hand.",
                alignment="left",
            ),
            "Pos": st.column_config.TextColumn(
                width=40,
                help="Position: A player's position on the field.",
                alignment="left",
            ),
            "Range": st.column_config.NumberColumn(
                format="%.1f",
                help="Range Runs: Defensive runs through fielding batted balls.",
                alignment="left",
            ),
            "Def Value": st.column_config.NumberColumn(
                format="%.1f",
                help="Position-Adjusted Total Zone Runs: A player's position-adjusted fielding value per 143 games or 1287 innings (a full NPB season).",
                alignment="left",
            ),
            "Arm": st.column_config.NumberColumn(
                format="%.1f",
                help="Arm Runs: Defensive runs through throwing. For outfielders, this includes throwing out and preventing runners from advancing bases. For catchers, this includes preventing stolen bases.",
                alignment="left",
            ),
            "Framing": st.column_config.NumberColumn(
                format="%.1f",
                help="Framing: A catcher's framing value.",
                alignment="left",
            ),
            "DPR": st.column_config.NumberColumn(
                format="%.1f",
                help="Double Play Runs: Defensive runs through fielding ground ball double plays.",
                alignment="left",
            ),
        }
    elif suffix in ("fielding"):
        column_config = {
            "ARM": st.column_config.NumberColumn(
                format="%.1f",
                help="Arm Runs: Defensive runs through throwing. For outfielders, this includes throwing out and preventing runners from advancing bases. For catchers, this includes preventing stolen bases.",
                alignment="left",
            ),
            "Blocking": st.column_config.NumberColumn(
                format="%.1f",
                help="Blocking: A catcher's blocking value.",
                alignment="left",
            ),
            "DPR": st.column_config.NumberColumn(
                format="%.1f",
                help="Double Play Runs: Defensive runs through fielding ground ball double plays.",
                alignment="left",
            ),
            "ErrR": st.column_config.NumberColumn(
                format="%.1f",
                help="Error Runs: Defensive runs through preventing errors.",
                alignment="left",
            ),
            "Framing": st.column_config.NumberColumn(
                format="%.1f",
                help="Framing: A catcher's framing value.",
                alignment="left",
            ),
            "Inn": st.column_config.NumberColumn(
                format="%.1f",
                help="Innings Played: Total innings played at the position, recorded in one-third increments.",
                alignment="left",
            ),
            "Pos": st.column_config.TextColumn(
                width=40,
                help="Position: A player's position on the field.",
                alignment="left",
            ),
            "Pos Adj": st.column_config.NumberColumn(
                format="%.1f",
                help="Positional Adjustment: Adjustment to value premium positions higher. Hierarchy: Catcher > Shortstop > Center Field > Second Base > Third Base > Right Field > Left Field > Designated Hitter.",
                alignment="left",
            ),
            "RngR": st.column_config.NumberColumn(
                format="%.1f",
                help="Range Runs: Defensive runs through fielding batted balls.",
                alignment="left",
            ),
            "TZR": st.column_config.NumberColumn(
                format="%.1f",
                help="Total Zone Runs: Combined fielding value of defensive metrics. Infield/Outfield = RngR + DPR + ARM + ErrR; Catchers = ARM + ErrR. Does not include framing or blocking.",
                alignment="left",
            ),
            "TZR/143": st.column_config.NumberColumn(
                format="%.1f",
                help="Total Zone Runs per 143 games: Approximate TZR per 143 games or 1287 innings (a full NPB season).",
                alignment="left",
            ),
            "Age": st.column_config.TextColumn(
                width=40,
                help="Age: How old a player is on June 30th of that year.",
                alignment="left",
            ),
        }
    elif suffix in ("standings"):
        column_config = {
            "G": st.column_config.NumberColumn(
                help="Games",
                alignment="left",
            ),
            "W": st.column_config.NumberColumn(
                help="Wins",
                alignment="left",
            ),
            "L": st.column_config.NumberColumn(
                help="Losses",
                alignment="left",
            ),
            "T": st.column_config.NumberColumn(
                help="Ties",
                alignment="left",
            ),
            "PCT": st.column_config.NumberColumn(
                format="%.3f",
                help="Winning Percentage",
                alignment="left",
            ),
            "GB": st.column_config.TextColumn(
                help="Games Behind",
                alignment="left",
            ),
            "RS": st.column_config.TextColumn(
                help="Runs Scored",
                alignment="left",
            ),
            "RA": st.column_config.NumberColumn(
                help="Runs Against",
                alignment="left",
            ),
            "Diff": st.column_config.NumberColumn(
                format="%.0f",
                help="Run Differential",
                alignment="left",
            ),
            "XPCT": st.column_config.NumberColumn(
                format="%.3f",
                help="Pythagorean Winning Percentage",
                alignment="left",
            ),
            "Home": st.column_config.TextColumn(
                help="Home Record",
                alignment="left",
            ),
            "Road": st.column_config.TextColumn(
                help="Road Record",
                alignment="left",
            ),
            "vs T": st.column_config.TextColumn(
                help="Record vs. Hanshin Tigers",
                alignment="left",
            ),
            "vs DB": st.column_config.TextColumn(
                help="Record vs. DeNA BayStars",
                alignment="left",
            ),
            "vs G": st.column_config.TextColumn(
                help="Record vs. Yomiuri Giants",
                alignment="left",
            ),
            "vs C": st.column_config.TextColumn(
                help="Record vs. Hiroshima Carp",
                alignment="left",
            ),
            "vs D": st.column_config.TextColumn(
                help="Record vs. Chunichi Dragons",
                alignment="left",
            ),
            "vs S": st.column_config.TextColumn(
                help="Record vs. Yakult Swallows",
                alignment="left",
            ),
            "Inter": st.column_config.TextColumn(
                help="Interleague Record",
                alignment="left",
            ),
            "vs H": st.column_config.TextColumn(
                help="Record vs. SoftBank Hawks",
                alignment="left",
            ),
            "vs F": st.column_config.TextColumn(
                help="Record vs. Nipponham Fighters",
                alignment="left",
            ),
            "vs B": st.column_config.TextColumn(
                help="Record vs. ORIX Buffaloes",
                alignment="left",
            ),
            "vs E": st.column_config.TextColumn(
                help="Record vs. Rakuten Eagles",
                alignment="left",
            ),
            "vs L": st.column_config.TextColumn(
                help="Record vs. Seibu Lions",
                alignment="left",
            ),
            "vs M": st.column_config.TextColumn(
                help="Record vs. Lotte Marines",
                alignment="left",
            ),
        }
    elif suffix in ("team_summary"):
        column_config = {
            "W": st.column_config.NumberColumn(
                help="Wins",
                alignment="left",
            ),
            "L": st.column_config.NumberColumn(
                help="Losses",
                alignment="left",
            ),
            "PCT": st.column_config.NumberColumn(
                format="%.3f",
                help="Winning Percentage",
                alignment="left",
            ),
            "Diff": st.column_config.NumberColumn(
                format="%.0f",
                help="Run Differential",
                alignment="left",
            ),
            "HR": st.column_config.NumberColumn(
                help="Home Runs",
                alignment="left",
            ),
            "SB": st.column_config.NumberColumn(
                help="Stolen Bases",
                alignment="left",
            ),
            "OPS+": st.column_config.NumberColumn(
                help="On Base plus Slugging Plus",
                alignment="left",
            ),
            "ERA+": st.column_config.NumberColumn(
                help="Earned Run Average Plus",
                alignment="left",
            ),
            "FIP-": st.column_config.NumberColumn(
                help="Fielding Independent Pitching Minus",
                alignment="left",
            ),
            "K-BB%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Strikeout Rate minus Walk Rate",
                alignment="left",
            ),
            "wSB": st.column_config.NumberColumn(
                format="%.1f",
                help="Weighted Stolen Base Runs",
                alignment="left",
            ),
            "TZR": st.column_config.NumberColumn(
                format="%.1f",
                help="Total Zone Runs",
                alignment="left",
            ),
        }
    else:
        column_config = {}
    return column_config
