"""Helper functions for Streamlit pages"""

from io import StringIO
import altair as alt
import streamlit as st
import pandas as pd
import requests


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
            subtitle_str + " · " + df[df[name_col] == name]["PA"].astype(str) + " PA" + " · " + pos + " · Age " + age + " · Bats " + tb_hand
        )
    elif suffix in ("PF", "PR"):
        tb_hand = df[df[name_col] == name]["T"]
        subtitle_str = subtitle_str + " · " + df[df[name_col] == name]["IP"].astype(str) + " IP" + " · Age " + age + " · Throws " + tb_hand
    else:
        subtitle_str = subtitle_str + " · Age " + age

    # Extract from dataframe
    subtitle_str = subtitle_str.values[0]

    # Chart settings
    title_params = alt.TitleParams(
        text=title,
        subtitle=[subtitle_str, "Presented by Yakyu Cosmopolitan"],
        subtitleColor="grey",
        subtitleFontSize=13.5
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
        width="stretch",
        theme="streamlit",
        key=None,
        on_select="ignore",
        selection_mode=None,
    )

    # Transpose vertical df, grab stat names from first col + drop, reset index
    raw_data = raw_data.T
    raw_data.columns = raw_data.iloc[0]
    raw_data = raw_data.drop(index=raw_data.index[0], axis=0)
    raw_data.index = [0]

    # Prep cols and remove redundant cols for display on Streamlit
    raw_data = convert_pct_cols_to_float(raw_data)
    raw_data = raw_data.dropna()
    raw_data = raw_data.convert_dtypes()
    if suffix in ("BR", "BF"):
        raw_data = raw_data.drop("PA", axis=1)
    elif suffix in ("PR", "PF"):
        raw_data = raw_data.drop("IP", axis=1)
    
    # Display the actual stats the player has
    st.dataframe(
        raw_data,
        width='stretch',
        hide_index=True,
        row_height=25,
        column_config=get_column_config(suffix),
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
            "TTO%": "desc",
            "B": None,
            "Team": None,
            "League": None,
        }
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
            "GB%": "desc",
            "LD%": "desc",
            "FB Velo": "desc",
            "Team": None,
            "League": None,
        }
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
    else:
        default_sort = {
            "Team": None,
            "League": None,
        }

    user_sort_col = st.selectbox("Sort by", cols, index=0)
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


def create_stat_cols_filter(df, mode=None):
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
            "Team",
        ]
    elif mode == "player_pitch":
        filter_default = [
            "Pitcher",
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
    else:
        filter_default = df.columns.tolist()

    # Add "select all" and "select none" columns option (checkbox ver)
    filter_container = st.container()
    all_none_filter = st.segmented_control(
        "Select Stats", options=["All", "None"], selection_mode="single"
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


def create_team_filter(mode=None):
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
        team = st.selectbox(
            "Team",
            team_dict.values(),
        )
    else:
        team = st.multiselect(
            "Team",
            team_dict.keys(),
            default=team_dict.keys(),
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
    year = st.selectbox("Year", ["2025"])
    return year


def create_player_filter(df, player_col):
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
    player = st.selectbox(player_col, player_list)
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
            "GB%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Ground Ball Rate: The percentage of balls in play "
                + "against a pitcher that are hit on the ground.",
            ),
            "Chase%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Chase Rate: The percentage of pitches outside the "
                + "strike zone that batters swing at. Recognized by "
                + "PitcherList.com in 2018 as one of the “Big Three” plate "
                + "discipline metrics.",
            ),
            "Con%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Contact Rate: The percentage of swings against a "
                + "pitcher that result in contact, including both fair and "
                + "foul balls. Recognized by PitcherList.com in 2018 as one "
                + "of the “Big Three” plate discipline metrics.",
            ),
            "SwStr%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Swinging Strike Rate: The percentage of a pitcher's "
                + "total pitches that result in swinging strikes. Recognized "
                + "by PitcherList.com in 2018 as one of the “Big Three” plate "
                + "discipline metrics.",
            ),
            "CSW%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Called Strike plus Whiff Rate: The percentage of a "
                + "pitcher's pitches that result in either a called strike or "
                "a swinging strike.",
            ),
            "FB Velo": st.column_config.NumberColumn(
                format="%.1f",
                help="Average Fastball Velocity: The average speed of a "
                + "pitcher's fastball, measured in miles per hour (mph). The "
                "NPB league average in 2025 is about 91.5 mph.",
            ),
            "G": st.column_config.NumberColumn(
                help="Games Played: The number of games in which a pitcher "
                + "appears.",
            ),
            "W": st.column_config.NumberColumn(
                help="Wins: The number of games a pitcher is credited with "
                + "a winning decision.",
            ),
            "L": st.column_config.NumberColumn(
                help="Losses: The number of games a pitcher is credited "
                + "with a losing decision.",
            ),
            "IP": st.column_config.NumberColumn(
                format="%.1f",
                help="Innings Pitched: The total number of innings a "
                + "pitcher completes, recorded in one-third increments.",
            ),
            "BF": st.column_config.NumberColumn(
                help="Batters Faced: The total number of hitters a pitcher "
                + "faces.",
            ),
            "R": st.column_config.NumberColumn(
                help="Runs: The total number of runs a pitcher allows.",
            ),
            "ER": st.column_config.NumberColumn(
                help="Earned Runs: The number of runs scored against the "
                + "pitcher that are not the result of errors or passed balls.",
            ),
            "H": st.column_config.NumberColumn(
                help="Hits: The number of hits a pitcher allows.",
            ),
            "HR": st.column_config.NumberColumn(
                help="Home Runs: The number of home runs a pitcher allows.",
            ),
            "HR%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Home Run Rate: The percentage of batters faced by a "
                + "pitcher that results in home runs.",
            ),
            "BB": st.column_config.NumberColumn(
                help="Walks: The number of times a pitcher allows a batter "
                + "to reach first base by throwing four balls.",
            ),
            "BB%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Walk Rate: The percentage of batters faced by a "
                + "pitcher that result in walks.",
            ),
            "IBB": st.column_config.NumberColumn(
                help="Intentional Walks: The number of walks a pitcher "
                + "intentionally issues.",
            ),
            "HB": st.column_config.NumberColumn(
                help="Hit By Pitches: The number of batters a pitcher hits "
                + "with a pitch.",
            ),
            "SO": st.column_config.NumberColumn(
                help="Strikeouts: The number of batters a pitcher retires "
                + "on strikes.",
            ),
            "K%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Strikeout Rate: The percentage of batters faced by "
                + "a pitcher that result in strikeouts.",
            ),
            "K-BB%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Strikeout Rate minus Walk Rate: The difference "
                + "between a pitcher's strikeout rate and walk rate.",
            ),
            "WHIP": st.column_config.NumberColumn(
                format="%.2f",
                help="Walks plus Hits per Inning Pitched: The average "
                + "number of walks and hits allowed by a pitcher per inning.",
            ),
            "ERA+": st.column_config.NumberColumn(
                help="Earned Run Average Plus: A normalized version of ERA "
                + "that adjusts for park factors, with 100 always being the "
                + "league average. Higher values are better.",
            ),
            "FIP": st.column_config.NumberColumn(
                format="%.2f",
                help="Fielding Independent Pitching: A measure of a "
                + "pitcher's effectiveness based on strikeouts, walks, and "
                + "home runs, independent of defensive performance.",
            ),
            "FIP-": st.column_config.NumberColumn(
                help="Fielding Independent Pitching Minus: A normalized "
                + "version of FIP that adjusts for park factors, with 100 "
                + "always being the league average. Lower values are better.",
            ),
            "Diff": st.column_config.NumberColumn(
                format="%.2f",
                help="ERA-FIP Differential: The differential of a pitcher's "
                + "ERA and FIP. Higher values indicate underperformance and "
                + "lower values indicate overperformance relative to "
                + "expectations.",
            ),
            "kwERA": st.column_config.NumberColumn(
                format="%.2f",
                help="Strikeout-Walk based Earned Run Average: An estimate "
                + "of a pitcher's ERA based on strikeout and walk rates.",
            ),
            "kwERA-": st.column_config.NumberColumn(
                help="Strikeout-Walk based Earned Run Average Minus: A "
                + "normalized version of kwERA with 100 always being the "
                + "league average. Lower values are better.",
            ),
            "SV": st.column_config.NumberColumn(
                help="Saves: The number of games a pitcher finishes while "
                + "preserving a lead of three runs or fewer.",
            ),
            "HLD": st.column_config.NumberColumn(
                help="Holds: The number of games a relief pitcher enters in "
                + "a save situation, maintains the lead, but does not finish.",
            ),
            "CG": st.column_config.NumberColumn(
                help="Complete Games: The number of games where a pitcher "
                + "pitches the entire game.",
            ),
            "SHO": st.column_config.NumberColumn(
                help="Shutouts: The number of complete games a pitcher "
                + "finishes without allowing any runs.",
            ),
            "WP": st.column_config.NumberColumn(
                help="Wild Pitches: The number of pitches a pitcher throws "
                + "that are too wild for the catcher to handle, allowing "
                + "baserunners to advance.",
            ),
            "Qualifier": st.column_config.TextColumn(
                help="Qualified Pitcher: A pitcher is qualified for titles "
                + "with 1.0 IP per team game played (NPB) or 0.8 IP per team "
                + "game played (Farm).",
            ),
            "ERA": st.column_config.NumberColumn(
                format="%.2f",
                help="Earned Run Average: The average number of earned "
                + "runs a pitcher allows per nine innings pitched.",
            ),
            "Age": st.column_config.TextColumn(
                help="Age: How old a pitcher is on June 30th of that year.",
            ),
            "T": st.column_config.TextColumn(
                help="Throws: A pitcher's throwing hand.",
            ),
        }
    elif suffix in ("B", "BR", "BF"):
        column_config = {
            "PullAIR%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Pull Air Rate: The percentage of balls in play that are pulled and not "
                + "hit on the ground.",
            ),
            "Chase%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Chase Rate: The percentage of pitches outside the "
                + "strike zone that batters swing at.",
            ),
            "Z-Con%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="In-Zone Contact Rate: The percentage of swings on pitches in the strike zone "
                + "that result in contact, including both fair and "
                + "foul balls.",
            ),
            "SwStr%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Swinging Strike Rate: The percentage of a player's "
                + "total pitches that result in swinging strikes.",
            ),
            "Swing%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Swing Rate: The percentage of total pitches a player "
                + "swings at.",
            ),
            "AB": st.column_config.NumberColumn(
                help="At-bats: The number of times a player bats, excluding "
                + "walks, hit-by-pitches, sacrifices, errors, fielder's "
                + "choices, and catcher's interferences.",
            ),
            "K%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Strikeout Rate: The percentage of a player's plate "
                + "appearances that end in a strikeout.",
            ),
            "BB%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Walk Rate: The percentage of a player's plate "
                + "appearances that result in a walk.",
            ),
            "TTO%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Three True Outcomes Rate: The percentage of a player's "
                + "plate appearances that result in one of the three true "
                + "outcomes: a home run, a strikeout, or a walk.",
            ),
            "AVG": st.column_config.NumberColumn(
                format="%.3f",
                help="Batting Average: The ratio of a player's hits to "
                + "their at-bats.",
            ),
            "OBP": st.column_config.NumberColumn(
                format="%.3f",
                help="On Base Percentage: The percentage of plate "
                + "appearances in which a player reaches base.",
            ),
            "SLG": st.column_config.NumberColumn(
                format="%.3f",
                help="Slugging Percentage: The total number of bases a "
                + "player records per at-bat.",
            ),
            "OPS": st.column_config.NumberColumn(
                format="%.3f",
                help="On Base plus Slugging: The sum of a player's on-base "
                + "percentage and slugging percentage.",
            ),
            "ISO": st.column_config.NumberColumn(
                format="%.3f",
                help="Isolated Power: A measure of a hitter's raw power, "
                + "calculated as SLG - AVG.",
            ),
            "BABIP": st.column_config.NumberColumn(
                format="%.3f",
                help="Batting Average on Balls in Play: The batting average "
                + "for balls hit into play, excluding home runs.",
            ),
            "BB/K": st.column_config.NumberColumn(
                format="%.2f",
                help="Walk to Strikeout Ratio: A comparison of how often "
                + "a player walks versus how often they strike out.",
            ),
            "wSB": st.column_config.NumberColumn(
                format="%.1f",
                help="Weighted Stolen Base Runs: An estimate of the number "
                + "of runs a player contributes to his team by stealing "
                + "bases, with 0.0 being league-average.",
            ),
            "G": st.column_config.NumberColumn(
                help="Games Played: The number of games in which a player "
                + "appears.",
            ),
            "PA": st.column_config.NumberColumn(
                help="Plate Appearances: The total number of times a "
                + "player comes to bat.",
            ),
            "R": st.column_config.NumberColumn(
                help="Runs: The number of times a player crosses home plate "
                + "to score.",
            ),
            "RBI": st.column_config.NumberColumn(
                help="Runs Batted In: The number of runs a player drives "
                + "in with their at-bats, except when grounding into a double "
                + "play or reaching on an error.",
            ),
            "1B": st.column_config.NumberColumn(
                help="Singles: The number of hits where a player safely "
                + "reaches first base without an error or fielder's choice.",
            ),
            "2B": st.column_config.NumberColumn(
                help="Doubles: The number of hits where a player safely "
                + "reaches second base without an error or fielder's choice.",
            ),
            "3B": st.column_config.NumberColumn(
                help="Triples: The number of hits where a player safely "
                + "reaches third base without an error or fielder's choice.",
            ),
            "HR": st.column_config.NumberColumn(
                help="Home Runs: The number of hits where a player safely "
                + "reaches home plate without an error or fielder's choice.",
            ),
            "TB": st.column_config.NumberColumn(
                help="Total Bases: The total number of bases a player "
                + "records from hits.",
            ),
            "BB": st.column_config.NumberColumn(
                help="Walks: The number of times a player is awarded first "
                + "base after receiving four balls outside the strike zone.",
            ),
            "IBB": st.column_config.NumberColumn(
                help="Intentional Walks: The number of times a player is "
                + "intentionally awarded first base by the opposing team.",
            ),
            "SO": st.column_config.NumberColumn(
                help="Strikeouts: The number of times a player is put out "
                + "on three strikes.",
            ),
            "HP": st.column_config.NumberColumn(
                help="Hit By Pitches: The number of times a player reaches "
                + "first base after being hit by a pitched ball.",
            ),
            "SB": st.column_config.NumberColumn(
                help="Stolen Bases: The number of times a player "
                + "successfully steals a base.",
            ),
            "CS": st.column_config.NumberColumn(
                help="Caught Stealing: The number of times a player is "
                + "tagged out while attempting to steal a base.",
            ),
            "SF": st.column_config.NumberColumn(
                help="Sacrifice Flies: A fly ball that results in a run "
                + "being scored, but the batter is out.",
            ),
            "SH": st.column_config.NumberColumn(
                help="Sacrifice Hits: A bunt that allows a runner to "
                + "advance to the next base, but the batter is out.",
            ),
            "GDP": st.column_config.NumberColumn(
                help="Grounded into Double Plays: The number of times a "
                + "player hits a ground ball that results in two outs.",
            ),
            "OPS+": st.column_config.NumberColumn(
                help="On Base plus Slugging Plus: A normalized version of "
                + "OPS that adjusts for park factors, with 100 always being "
                + "the league average. Higher values are better.",
            ),
            "Qualifier": st.column_config.TextColumn(
                help="Qualified Hitter: A player is qualified for titles "
                + "with 3.1 PA per team game played (NPB) or 2.7 PA per team "
                + "game played (Farm).",
            ),
            "H": st.column_config.TextColumn(
                help="Hits: The number of times a player reaches safely on "
                + "a ball put in play without an error or fielder's choice.",
            ),
            "Age": st.column_config.TextColumn(
                help="Age: How old a player is on June 30th of that year.",
            ),
            "B": st.column_config.TextColumn(
                help="Bats: A player's batting hand.",
            ),
            "Pos": st.column_config.TextColumn(
                help="Position: A player's position on the field.",
            ),
            "Range": st.column_config.NumberColumn(
                format="%.1f",
                help="Range Runs: Defensive runs through fielding batted "
                + "balls.",
            ),
            "Def Value": st.column_config.NumberColumn(
                format="%.1f",
                help="Position-Adjusted Total Zone Runs: A player's "
                + "position-adjusted fielding value per 143 games or 1287 "
                + "innings (a full NPB season).",
            ),
            "Arm": st.column_config.NumberColumn(
                format="%.1f",
                help="Arm Runs: Defensive runs through throwing. For "
                + "outfielders, this includes throwing out and preventing "
                + "runners from advancing bases. For catchers, this includes "
                + "preventing stolen bases.",
            ),
            "Framing": st.column_config.NumberColumn(
                format="%.1f",
                help="Framing: A catcher's framing value.",
            ),
            "DPR": st.column_config.NumberColumn(
                format="%.1f",
                help="Double Play Runs: Defensive runs through fielding "
                + "ground ball double plays.",
            ),
        }
    elif suffix in ("fielding"):
        column_config = {
            "ARM": st.column_config.NumberColumn(
                format="%.1f",
                help="Arm Runs: Defensive runs through throwing. For "
                + "outfielders, this includes throwing out and preventing "
                + "runners from advancing bases. For catchers, this includes "
                + "preventing stolen bases.",
            ),
            "Blocking": st.column_config.NumberColumn(
                format="%.1f",
                help="Blocking: A catcher's blocking value.",
            ),
            "DPR": st.column_config.NumberColumn(
                format="%.1f",
                help="Double Play Runs: Defensive runs through fielding "
                + "ground ball double plays.",
            ),
            "ErrR": st.column_config.NumberColumn(
                format="%.1f",
                help="Error Runs: Defensive runs through preventing errors.",
            ),
            "Framing": st.column_config.NumberColumn(
                format="%.1f",
                help="Framing: A catcher's framing value.",
            ),
            "Inn": st.column_config.NumberColumn(
                format="%.1f",
                help="Innings Played: Total innings played at the position, "
                + "recorded in one-third increments.",
            ),
            "Pos": st.column_config.TextColumn(
                help="Position: A player's position on the field.",
            ),
            "Pos Adj": st.column_config.NumberColumn(
                format="%.1f",
                help="Positional Adjustment: Adjustment to value premium "
                + "positions higher. Hierarchy: Catcher > Shortstop > Center "
                + "Field > Second Base > Third Base > Right Field > Left "
                + "Field > Designated Hitter.",
            ),
            "RngR": st.column_config.NumberColumn(
                format="%.1f",
                help="Range Runs: Defensive runs through fielding batted "
                + "balls.",
            ),
            "TZR": st.column_config.NumberColumn(
                format="%.1f",
                help="Total Zone Runs: Combined fielding value of defensive "
                + "metrics. Infield/Outfield = RngR + DPR + ARM + ErrR; "
                + "Catchers = ARM + ErrR. Does not include framing or "
                + "blocking.",
            ),
            "TZR/143": st.column_config.NumberColumn(
                format="%.1f",
                help="Total Zone Runs per 143 games: Approximate TZR per "
                + "143 games or 1287 innings (a full NPB season).",
            ),
            "Age": st.column_config.TextColumn(
                help="Age: How old a player is on June 30th of that year.",
            ),
        }
    elif suffix in ("standings"):
        column_config = {
            "G": st.column_config.NumberColumn(
                help="Games",
            ),
            "W": st.column_config.NumberColumn(
                help="Wins",
            ),
            "L": st.column_config.NumberColumn(
                help="Losses",
            ),
            "T": st.column_config.NumberColumn(
                help="Ties",
            ),
            "PCT": st.column_config.NumberColumn(
                format="%.3f",
                help="Winning Percentage",
            ),
            "GB": st.column_config.TextColumn(
                help="Games Behind",
            ),
            "RS": st.column_config.TextColumn(
                help="Runs Scored",
            ),
            "RA": st.column_config.NumberColumn(
                help="Runs Against",
            ),
            "Diff": st.column_config.NumberColumn(
                format="%.0f",
                help="Run Differential",
            ),
            "XPCT": st.column_config.NumberColumn(
                format="%.3f",
                help="Pythagorean Winning Percentage",
            ),
            "Home": st.column_config.TextColumn(
                help="Home Record",
            ),
            "Road": st.column_config.TextColumn(
                help="Road Record",
            ),
            "vs T": st.column_config.TextColumn(
                help="Record vs. Hanshin Tigers",
            ),
            "vs DB": st.column_config.TextColumn(
                help="Record vs. DeNA BayStars",
            ),
            "vs G": st.column_config.TextColumn(
                help="Record vs. Yomiuri Giants",
            ),
            "vs C": st.column_config.TextColumn(
                help="Record vs. Hiroshima Carp",
            ),
            "vs D": st.column_config.TextColumn(
                help="Record vs. Chunichi Dragons",
            ),
            "vs S": st.column_config.TextColumn(
                help="Record vs. Yakult Swallows",
            ),
            "Inter": st.column_config.TextColumn(
                help="Interleague Record",
            ),
            "vs H": st.column_config.TextColumn(
                help="Record vs. SoftBank Hawks",
            ),
            "vs F": st.column_config.TextColumn(
                help="Record vs. Nipponham Fighters",
            ),
            "vs B": st.column_config.TextColumn(
                help="Record vs. ORIX Buffaloes",
            ),
            "vs E": st.column_config.TextColumn(
                help="Record vs. Rakuten Eagles",
            ),
            "vs L": st.column_config.TextColumn(
                help="Record vs. Seibu Lions",
            ),
            "vs M": st.column_config.TextColumn(
                help="Record vs. Lotte Marines",
            ),
        }
    elif suffix in ("team_summary"):
        column_config = {
            "W": st.column_config.NumberColumn(
                help="Wins",
            ),
            "L": st.column_config.NumberColumn(
                help="Losses",
            ),
            "PCT": st.column_config.NumberColumn(
                format="%.3f",
                help="Winning Percentage",
            ),
            "Diff": st.column_config.NumberColumn(
                format="%.0f",
                help="Run Differential",
            ),
            "HR": st.column_config.NumberColumn(
                help="Home Runs",
            ),
            "SB": st.column_config.NumberColumn(
                help="Stolen Bases",
            ),
            "OPS+": st.column_config.NumberColumn(
                help="On Base plus Slugging Plus",
            ),
            "ERA+": st.column_config.NumberColumn(
                help="Earned Run Average Plus",
            ),
            "FIP-": st.column_config.NumberColumn(
                help="Fielding Independent Pitching Minus",
            ),
            "K-BB%": st.column_config.NumberColumn(
                format="%.1f%%",
                help="Strikeout Rate minus Walk Rate",
            ),
            "wSB": st.column_config.NumberColumn(
                format="%.1f",
                help="Weighted Stolen Base Runs",
            ),
            "TZR": st.column_config.NumberColumn(
                format="%.1f",
                help="Total Zone Runs",
            ),
        }
    else:
        column_config = {}
    return column_config
