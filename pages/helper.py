"""Helper functions for Streamlit pages"""

import re
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


def display_player_percentile(df, name, team, year, suffix):
    """
    Displays a percentile bar chart and raw statistics for a selected player.

    Parameters:
        df (pandas.DataFrame): DataFrame containing player statistics.
        name (str): The name of the player to display.
        team (str): The team name of the player for data filtering.
        year (str): The season year for labeling the chart.
        suffix (str): Stat type indicator determining which columns to plot
            and chart formatting. Options: 'PR' (Pitcher Regular),
            'PF' (Pitcher Farm), 'BR' (Batter Regular), 'BF' (Batter Farm).

    Functionality:
        - Selects relevant statistics and inverts percentile ranks for metrics
        where lower is better.
        - Calculates percentiles for each stat and prepares data for
        visualization.
        - Generates an Altair horizontal bar chart showing the player's
        percentile ranks with team emoji, stat values, and context subtitles.
        - Displays the chart in the Streamlit app.

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
            "F-Str%",
            "GB%",
            "K-BB%",
            "BB%",
            "K%",
            "HR%",
            "HR/FB",
            "WHIP",
            "pERA-",
            "FIP-",
            "ERA+",
            "IP",
        ]
        invert_cols = ["HR%", "HR/FB", "WHIP", "FIP-", "BB%", "pERA-"]
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
            "sSeager",
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
        if df[(df[name_col] == name) & (df["Team"] == team)]["Pos"].values[0] == "C":
            plot_cols.insert(0, "Framing")
            plot_cols.insert(0, "Arm")
        elif df[(df[name_col] == name) & (df["Team"] == team)]["Pos"].values[0] in (
            "1B",
            "2B",
            "3B",
            "SS",
            "UTL",
        ):
            plot_cols.insert(0, "Range")
            plot_cols.insert(0, "DPR")
        elif df[(df[name_col] == name) & (df["Team"] == team)]["Pos"].values[0] in (
            "LF",
            "CF",
            "RF",
        ):
            plot_cols.insert(0, "Range")
            plot_cols.insert(0, "Arm")
        invert_cols = ["K%", "SwStr%", "Chase%"]

    # Get player's age
    age = df[(df[name_col] == name) & (df["Team"] == team)]["Age"].astype(str)
    # Save raw numbers
    raw_data = prepare_streamlit_types(
        df[(df[name_col] == name) & (df["Team"] == team)][plot_cols]
    )
    if suffix == "P":
        raw_data = format_cols_as_strs(raw_data, "player_pitch")
    else:
        raw_data = format_cols_as_strs(raw_data)
    raw_data = raw_data.T
    raw_data = raw_data.reset_index()
    raw_data.columns = ["Stat", "Value"]
    raw_data = raw_data.iloc[::-1]

    # Store original values before converting to percentiles
    original_values = raw_data["Value"].copy().astype(str)

    if suffix in ("BR", "BF"):
        plot_cols.remove("PA")
    elif suffix in ("PR", "PF"):
        plot_cols.remove("IP")

    # Ensure chosen percentile cols have correct types before creating percentiles
    df = prepare_streamlit_types(df)
    df[plot_cols] = df[plot_cols].apply(pd.to_numeric, errors="coerce")

    # Generate percentiles for given cols
    for col in plot_cols:
        df[col] = df[col].rank(pct=True)
        # Percentile adjustment (I.E. 0th percentile = lowest)
        df[col] = (df[col] - df[col].min()) / (df[col].max() - df[col].min())
        # invert_cols are stats where lower = better
        if col in invert_cols:
            df[col] = 1.0 - df[col]
        df[col] = df[col] * 100
        df[col] = df[col].fillna(0)
        # Convert to whole numbers for display on bar
        df[col] = df[col].astype("int")

    # Generate percentile df for desired player
    chart_data = df[(df[name_col] == name) & (df["Team"] == team)][plot_cols].T
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
        "ORIX Buffaloes": "🐃",
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
    title = name + " " + emoji_dict[team]
    if suffix in ("BR", "PR"):
        subtitle_str1 = team + " · " + year + " NPB"
    elif suffix in ("BF", "PF"):
        subtitle_str1 = team + " · " + year + " Farm"
    else:
        subtitle_str1 = team + " · " + year
    if suffix in ("BF", "BR"):
        subtitle_str2 = (
            df[(df[name_col] == name) & (df["Team"] == team)]["Pos"].astype(str)
            + " · Age "
            + age
            + " · Bats "
            + df[(df[name_col] == name) & (df["Team"] == team)]["B"].astype(str)
        )
    elif suffix in ("PF", "PR"):
        subtitle_str2 = (
            "Age "
            + age
            + " · Throws "
            + df[(df[name_col] == name) & (df["Team"] == team)]["T"].astype(str)
        )
    else:
        subtitle_str2 = "Age " + age

    # Chart settings
    title_params = alt.TitleParams(
        text=title,
        subtitle=[
            subtitle_str1,
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

    # Combine base layers
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

    # Add metrics below chart
    if suffix in ("BR", "BF"):
        value_text_df = pd.DataFrame(
            {
                "PA": [
                    df[(df[name_col] == name) & (df["Team"] == team)]["PA"].values[0]
                ],
                "HR": [
                    df[(df[name_col] == name) & (df["Team"] == team)]["HR"].values[0]
                ],
                "RBI": [
                    df[(df[name_col] == name) & (df["Team"] == team)]["RBI"].values[0]
                ],
                "AVG": [
                    df[(df[name_col] == name) & (df["Team"] == team)]["AVG"].values[0]
                ],
                "OBP": [
                    df[(df[name_col] == name) & (df["Team"] == team)]["OBP"].values[0]
                ],
                "SLG": [
                    df[(df[name_col] == name) & (df["Team"] == team)]["SLG"].values[0]
                ],
                "OPS": [
                    df[(df[name_col] == name) & (df["Team"] == team)]["OPS"].values[0]
                ],
            }
        )
        # Set trailing zeroes for select stats
        value_text_df = value_text_df.style.format(
            {
                "AVG": "{:.3f}",
                "OBP": "{:.3f}",
                "SLG": "{:.3f}",
                "OPS": "{:.3f}",
            }
        )
        st.table(value_text_df, border="horizontal")
    elif suffix in ("PR", "PF"):
        value_text_df = pd.DataFrame(
            {
                "G": [df[(df[name_col] == name) & (df["Team"] == team)]["G"].values[0]],
                "IP": [
                    df[(df[name_col] == name) & (df["Team"] == team)]["IP"].values[0]
                ],
                "SO": [
                    df[(df[name_col] == name) & (df["Team"] == team)]["SO"].values[0]
                ],
                "ERA": [
                    df[(df[name_col] == name) & (df["Team"] == team)]["ERA"].values[0]
                ],
                "W": [df[(df[name_col] == name) & (df["Team"] == team)]["W"].values[0]],
                "L": [df[(df[name_col] == name) & (df["Team"] == team)]["L"].values[0]],
                "SV": [
                    df[(df[name_col] == name) & (df["Team"] == team)]["SV"].values[0]
                ],
                "HLD": [
                    df[(df[name_col] == name) & (df["Team"] == team)]["HLD"].values[0]
                ],
            }
        )
        # Set trailing zeroes for select stats
        value_text_df = value_text_df.style.format(
            {
                "IP": "{:.1f}",
                "ERA": "{:.2f}",
            }
        )
        st.table(value_text_df, border="horizontal")


def create_sort_filter(cols, mode):
    """
    Creates Streamlit widgets for sorting and filtering data columns.

    Parameters:
        cols (list): List of column names available for sorting.
        mode (str): Mode determining which default sort order to use. If no mode is
                    explicitly set, the sort will be descending.
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
            "G": "desc",
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
            "HR/FB": "desc",
            "PullAIR%": "desc",
            "Chase%": "asc",
            "Z-Con%": "desc",
            "Swing%": "desc",
            "SwStr%": "asc",
            "sSeager": "desc",
            "TTO%": "desc",
            "K-BB%": "asc",
            "Whiff%": "asc",
            "CSW%": "asc",
            "sHPT": "asc",
            "GB%": "asc",
            "IFFB%": "asc",
            "B": None,
            "Pos": None,
            "Team": None,
            "League": None,
        }
        # Set index of default sort column for individual stat pages
        try:
            if "Player" in cols:
                default_sort_col_index = cols.index("PA")
            # Set index of default sort column for team stat pages
            else:
                default_sort_col_index = cols.index("OPS+")
        except:
            default_sort_col_index = 0
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
            "Z-Con%": "asc",
            "SwStr%": "desc",
            "Chase%": "desc",
            "GB%": "desc",
            "LD%": "asc",
            "FB Velo": "desc",
            "HR/FB": "asc",
            "Sec%": "desc",
            "Z-Swing%": "asc",
            "Z-O Swing%": "asc",
            "Swing%": "asc",
            "O-Con%": "asc",
            "Contact%": "asc",
            "sSeager": "asc",
            "Ball%": "asc",
            "FB%": "asc",
            "OFFB%": "asc",
            "AIR%": "asc",
            "PullAIR%": "asc",
            "MM%": "asc",
            "Behind%": "asc",
            "pERA-": "asc",
            "kwERA-": "asc",
            "Team": None,
            "League": None,
        }
        try:
            # Set index of default sort column for individual stat pages
            if "Pitcher" in cols:
                default_sort_col_index = cols.index("IP")
            # Set index of default sort column for team stat pages
            else:
                default_sort_col_index = cols.index("ERA+")
        except:
            default_sort_col_index = 0
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
        try:
            # Set index of default sort column for individual stat pages
            if "Inn" in cols:
                default_sort_col_index = cols.index("Inn")
            # Set index of default sort column for team stat pages
            else:
                default_sort_col_index = cols.index("TZR")
        except:
            default_sort_col_index = 0
    elif mode == "team_summary":
        default_sort = {
            "W": "desc",
            "L": "desc",
            "TZR": "desc",
            "wSB": "desc",
            "K-BB%": "desc",
            "FIP-": "asc",
            "ERA+": "desc",
            "HR": "desc",
            "Diff": "desc",
            "OPS+": "desc",
            "SB": "desc",
            "PCT": "desc",
            "Team": None,
        }
        default_sort_col_index = cols.index("PCT")
    else:
        default_sort = {
            "Team": None,
            "League": None,
        }
        default_sort_col_index = 0

    user_sort_col = st.selectbox("Sort by", cols, index=default_sort_col_index)
    if user_sort_col not in default_sort or default_sort[user_sort_col] == "desc":
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
    Creates Streamlit widgets for selecting which statistic columns to display.

    Parameters:
        df (pandas.DataFrame): DataFrame containing the available statistic
            columns.
        mode (str, optional): Determines both the default column selection and
            the available quick-view presets. Options:
            - "player_bat": Default batting stats; "Plate Discipline" and
              "Batted Ball" quick views (plus "All"/"None").
            - "team_bat": Team batting stats; same batting quick views.
            - "player_pitch": Default pitching stats; "Plate Discipline",
              "Batted Ball", and "Approach" quick views.
            - "team_pitch": Team pitching stats; same pitching quick views.
            - "player_field": Default fielding stats.
            - "team_field": Team fielding stats.
            - "career_bat_cols": Default career batting stats.
            - "career_pitch_cols": Default career pitching stats.
            - None (default): Defaults to every column in df.
        key (str, optional): Prefix used for Streamlit widget keys, so multiple
            instances of the filter can coexist on one page without key
            collisions. If provided, the "All/None" control uses
            f"{key}_all_none".

    Functionality:
        - Displays a primary "Select Stats" segmented control offering "All",
          "None", and any applicable quick-view presets for the given mode.
        - Displays a secondary multi-select "Statistics" segmented control whose
          default selection is driven by the chosen preset (or the mode default).
        - Reorders the selected columns to match the order they appear in df.

    Returns:
        list: List of selected statistic column names, ordered as they appear in
            df.
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
            "Chase%",
            "SwStr%",
            "AIR%",
            "R",
            "BB/K",
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
            "kwERA-",
            "pERA-",
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
            "Chase%",
            "SwStr%",
            "AIR%",
            "R",
            "BB/K",
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
            "kwERA-",
            "pERA-",
            "K-BB%",
            "CSW%",
            "GB%",
            "FB Velo",
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

    # Check all default cols are in dataframe
    for col in filter_default[:]:
        if col not in df.columns:
            filter_default.remove(col)

    # Add "select all" and "select none" columns option
    filter_container = st.container()
    if key is not None:
        all_none_key = key + "_all_none"
    else:
        all_none_key = key

    # Add views based on columns in dataframe
    options_list = ["All", "None"]
    # Batter mode views
    if mode in ["player_bat", "team_bat"]:
        batter_plate_discipline_cols = [
            "Player",
            "G",
            "PA",
            "K%",
            "BB%",
            "BB/K",
            "Z-Swing%",
            "Chase%",
            "Z-O Swing%",
            "Swing%",
            "Z-Con%",
            "O-Con%",
            "Contact%",
            "Whiff%",
            "SwStr%",
            "CSW%",
            "sHPT",
            "sST",
            "sSeager",
            "TTO%",
            "Age",
            "Pos",
            "B",
            "Team",
            "League",
            "OBP",
        ]
        batter_batted_balls_cols = [
            "Player",
            "G",
            "PA",
            "AVG",
            "SLG",
            "OPS+",
            "ISO",
            "BABIP",
            "HR",
            "HR%",
            "HR/FB",
            "GB%",
            "LD%",
            "FB%",
            "OFFB%",
            "IFFB%",
            "AIR%",
            "PullAIR%",
            "Pull%",
            "Cent%",
            "Oppo%",
            "Age",
            "Pos",
            "B",
            "Team",
            "League",
        ]

        if mode == "team_bat":
            for col in ["Player", "Age", "G", "Pos", "B"]:
                batter_plate_discipline_cols.remove(col)
                batter_batted_balls_cols.remove(col)

        if set(batter_plate_discipline_cols).issubset(df.columns.to_list()):
            options_list.append("Plate Discipline")
        if set(batter_batted_balls_cols).issubset(df.columns.to_list()):
            options_list.append("Batted Ball")
    # Pitcher mode views
    if mode in ["player_pitch", "team_pitch"]:
        pitcher_plate_discipline_cols = [
            "Pitcher",
            "G",
            "IP",
            "K%",
            "BB%",
            "K-BB%",
            "Z-Swing%",
            "Chase%",
            "Z-O Swing%",
            "Swing%",
            "Z-Con%",
            "O-Con%",
            "Contact%",
            "Whiff%",
            "SwStr%",
            "CSW%",
            "sSeager",
            "Strike%",
            "Ball%",
            "F-Str%",
            "Putaway%",
            "Age",
            "T",
            "Team",
            "League",
        ]
        pitcher_batted_ball_cols = [
            "Pitcher",
            "G",
            "IP",
            "HR%",
            "HR/FB",
            "GB%",
            "LD%",
            "FB%",
            "OFFB%",
            "IFFB%",
            "AIR%",
            "PullAIR%",
            "Pull%",
            "Cent%",
            "Oppo%",
            "Age",
            "T",
            "Team",
            "League",
        ]
        pitcher_approach_cols = [
            "Pitcher",
            "G",
            "IP",
            "Zone%",
            "High%",
            "Low%",
            "MM%",
            "Arm%",
            "Glove%",
            "Behind%",
            "Sec%",
            "Age",
            "T",
            "Team",
            "League",
        ]

        if mode == "team_pitch":
            for col in ["Pitcher", "G", "Age", "T"]:
                pitcher_plate_discipline_cols.remove(col)
                pitcher_batted_ball_cols.remove(col)
                pitcher_approach_cols.remove(col)

        if set(pitcher_plate_discipline_cols).issubset(df.columns.to_list()):
            options_list.append("Plate Discipline")
        if set(pitcher_batted_ball_cols).issubset(df.columns.to_list()):
            options_list.append("Batted Ball")
        if set(pitcher_approach_cols).issubset(df.columns.to_list()):
            options_list.append("Approach")
    # Create "Select Stats" buttons
    all_none_filter = st.segmented_control(
        "Select Stats",
        options=options_list,
        selection_mode="single",
        key=all_none_key,
    )

    # Change highlighted "Statistics" cols buttons
    if all_none_filter == "All":
        cols = filter_container.segmented_control(
            "Statistics",
            df.columns.to_list(),
            default=df.columns.to_list(),
            selection_mode="multi",
        )
    elif all_none_filter == "None":
        cols = filter_container.segmented_control(
            "Statistics",
            df.columns.to_list(),
            default=df.columns.to_list()[0],
            selection_mode="multi",
        )
    # Alternative batter quick views
    elif all_none_filter == "Plate Discipline" and mode in ["player_bat", "team_bat"]:
        cols = filter_container.segmented_control(
            "Statistics",
            df.columns.to_list(),
            default=batter_plate_discipline_cols,
            selection_mode="multi",
        )
    elif all_none_filter == "Batted Ball" and mode in ["player_bat", "team_bat"]:
        cols = filter_container.segmented_control(
            "Statistics",
            df.columns.to_list(),
            default=batter_batted_balls_cols,
            selection_mode="multi",
        )
    # Alternative pitcher quick views
    elif all_none_filter == "Plate Discipline" and mode in ["player_pitch", "team_pitch"]:
        cols = filter_container.segmented_control(
            "Statistics",
            df.columns.to_list(),
            default=pitcher_plate_discipline_cols,
            selection_mode="multi",
        )
    elif all_none_filter == "Batted Ball" and mode in ["player_pitch", "team_pitch"]:
        cols = filter_container.segmented_control(
            "Statistics",
            df.columns.to_list(),
            default=pitcher_batted_ball_cols,
            selection_mode="multi",
        )
    elif all_none_filter == "Approach" and mode in ["player_pitch", "team_pitch"]:
        cols = filter_container.segmented_control(
            "Statistics",
            df.columns.to_list(),
            default=pitcher_approach_cols,
            selection_mode="multi",
        )
    # Default stats
    else:
        cols = filter_container.segmented_control(
            "Statistics",
            df.columns.to_list(),
            default=filter_default,
            selection_mode="multi",
        )

    # Sort cols as dataframe
    cols = [c for c in df.columns.to_list() if c in cols]
    return cols


def create_team_filter(mode=None, team_col=None, key=None):
    """
    Creates a Streamlit multiselect filter for NPB team selection.

    Parameters:
        mode (str, optional): Controls the filter behavior:
            - "farm": Includes farm league teams (HAYATE Ventures, Oisix Albirex).
            - "overview": Returns a single team (selectbox), returns full name.
            - "career": Returns abbreviations (multiselect), defaults to all.
            - None (default): Returns full team names (multiselect).
        team_col (str, optional): Unused parameter, kept for compatibility.
        key (str, optional): Streamlit widget key for state management.

    Functionality:
        - Maps team abbreviations to full team names.
        - Optionally adds farm league teams if mode is "farm".
        - Returns team names (full or abbreviated) based on mode.

    Returns:
        list/str: List of selected full team names, single team name (overview),
            or list of team abbreviations (career).
    """
    team_dict = {
        "Hanshin": "Hanshin Tigers",
        "Chunichi": "Chunichi Dragons",
        "DeNA": "DeNA BayStars",
        "Hiroshima": "Hiroshima Carp",
        "Yakult": "Yakult Swallows",
        "Yomiuri": "Yomiuri Giants",
        "Lotte": "Lotte Marines",
        "Nipponham": "Nipponham Fighters",
        "ORIX": "ORIX Buffaloes",
        "Rakuten": "Rakuten Eagles",
        "Seibu": "Seibu Lions",
        "SoftBank": "SoftBank Hawks",
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


def convert_team_names(df, team_col, mode):
    """
    Converts team names between abbreviated and full formats in a DataFrame.

    Parameters:
        df (pandas.DataFrame): DataFrame containing a column with team names.
        team_col (str): The name of the column containing team names to convert.
        mode (str): Conversion direction. Options: "long" (abbreviated to full
            name) or "short" (full name to abbreviated).

    Functionality:
        - Maps NPB team abbreviations to their full official names.
        - Includes legacy and farm team names in the conversion dictionary.
        - Modifies the specified column in place based on the mode.

    Returns:
        None
    """
    team_dict = {
        "Hanshin": "Hanshin Tigers",
        "Chunichi": "Chunichi Dragons",
        "DeNA": "DeNA BayStars",
        "Yokohama": "Yokohama BayStars",
        "Hiroshima": "Hiroshima Carp",
        "Yakult": "Yakult Swallows",
        "Yomiuri": "Yomiuri Giants",
        "Lotte": "Lotte Marines",
        "Nipponham": "Nipponham Fighters",
        "ORIX": "ORIX Buffaloes",
        "Rakuten": "Rakuten Eagles",
        "Seibu": "Seibu Lions",
        "SoftBank": "SoftBank Hawks",
        "HAYATE": "HAYATE Ventures",
        "Oisix": "Oisix Albirex",
        "Kintetsu": "Kintetsu Buffaloes",
        "Daiei": "Daiei Hawks",
        "Taiyo": "Taiyo Whales",
        "Hankyu": "Hankyu Braves",
        "BlueWave": "ORIX BlueWave",
    }

    # Shorten/abbreviate teams
    if mode == "long":
        df[team_col] = df[team_col].replace(team_dict)
    # Lengthen teams
    elif mode == "short":
        df[team_col] = df[team_col].replace({v: k for k, v in team_dict.items()})


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


def prepare_streamlit_types(df):
    """
    Converts DataFrame columns to appropriate numeric types for Streamlit
    display and downstream calculations.

    Parameters:
        df (pandas.DataFrame): DataFrame with columns that may contain
            percentage strings or incorrect numeric types.

    Functionality:
        - Calls convert_dtypes() to infer better dtypes.
        - Strips '%' signs from string-based percentage columns and converts
          them to float for proper sorting and calculations.
        - Removes instances of "inf" (except in Player, League, and Team).
        - Converts known count/rate columns to integer type where appropriate.

    Returns:
        pandas.DataFrame: The DataFrame with cleaned numeric types.
    """
    # Format data that may cause invalid cast warnings on Streamlit
    for col in df.columns.tolist():
        # Remove percent signs
        if df[col].astype(str).str.contains("%").any():
            df[col] = df[col].str.rstrip("%").astype(float)
        # If "inf" values appear, make them NA (appears as None on Streamlit)
        if df[col].astype(str).str.contains("inf").any() and col not in [
            "Player",
            "Team",
            "League",
        ]:
            df[col] = df[col].astype(str).replace("inf", "")

    df = df.convert_dtypes()

    # Check and convert columns that should be whole numbers
    int_cols = [
        "AB",
        "R",
        "H",
        "2B",
        "3B",
        "HR",
        "BB",
        "SO",
        "PA",
        "TB",
        "RBI",
        "SB",
        "CS",
        "SH",
        "SF",
        "SO",
        "BB",
        "IBB",
        "HP",
        "GDP",
        "W",
        "L",
        "SV",
        "HLD",
        "CG",
        "SHO",
        "BF",
        "HB",
        "WP",
        "ER",
    ]
    for col in int_cols:
        if col in df.columns.to_list() and df[col].dtype != int:
            df[col] = df[col].astype(int)

    return df


def prepare_streamlit_col_order(df, mode=None):
    """
    Prepares a DataFrame for display in Streamlit by dropping unwanted columns,
    renaming columns for consistency, and reordering columns according to the
    specified mode.

    Parameters:
        df (pandas.DataFrame): DataFrame containing statistic data to prepare.
        mode (str, optional): Determines column drop and ordering rules.
            Options: "team_bat", "player_bat", "team_pitch", "player_pitch",
            or None (no specific ordering applied).

    Functionality:
        - Drops internal/extraneous columns not meant for display ("#", "ParkF",
          "keys", etc).
        - Renames columns to standardized names (e.g., "Pull AIR%" -> "PullAIR%",
          "YpERA-" -> "pERA-").
        - Optionally drops mode-specific columns not relevant to the view.
        - Reorders columns based on a predefined display order for the given
          mode, with any remaining columns appended at the end.

    Returns:
        pandas.DataFrame: The prepared DataFrame with cleaned and ordered columns.
    """
    # These are columns that should never appear on any Streamlit page
    bad_cols = ["#", "ParkF", "keys", "NBBG"]
    if mode in ["team_pitch", "player_pitch"]:
        bad_cols.append("HP")
    df = df.drop(columns=bad_cols, errors="ignore")

    # Rename, drop extraneous columns, set order
    df = df.rename(
        columns={
            "Pull AIR%": "PullAIR%",
            "PAR%": "Putaway%",
            "YpERA Grade": "Grade",
            "YpERA-": "pERA-",
        },
        errors="ignore",
    )
    if mode == "team_bat":
        df = df.drop(columns="PLUS%", errors="ignore")
        col_order = [
            "Team",
            "G",
            "PA",
            "AB",
            "R",
            "H",
            "2B",
            "3B",
            "HR",
            "TB",
            "RBI",
            "SB",
            "CS",
            "SH",
            "SF",
            "SO",
            "BB",
            "IBB",
            "HP",
            "GDP",
            "AVG",
            "OBP",
            "SLG",
            "OPS",
            "OPS+",
            "ISO",
            "BABIP",
            "K%",
            "BB%",
            "K-BB%",
            "BB/K",
            "wSB",
            "Z-Swing%",
            "Chase%",
            "Z-O Swing%",
            "Swing%",
            "Z-Con%",
            "O-Con%",
            "Contact%",
            "Whiff%",
            "SwStr%",
            "CSW%",
            "sHPT",
            "sST",
            "sSeager",
            "TTO%",
            "HR%",
            "HR/FB",
            "GB%",
            "LD%",
            "FB%",
            "OFFB%",
            "IFFB%",
            "AIR%",
            "PullAIR%",
            "Pull%",
            "Cent%",
            "Oppo%",
            "League",
        ]
    elif mode == "player_bat":
        df = df.drop(columns="PLUS%", errors="ignore")
        col_order = [
            "Player",
            "G",
            "PA",
            "AB",
            "R",
            "H",
            "2B",
            "3B",
            "HR",
            "TB",
            "RBI",
            "SB",
            "CS",
            "SH",
            "SF",
            "SO",
            "BB",
            "IBB",
            "HP",
            "GDP",
            "AVG",
            "OBP",
            "SLG",
            "OPS",
            "OPS+",
            "ISO",
            "BABIP",
            "K%",
            "BB%",
            "BB/K",
            "wSB",
            "Z-Swing%",
            "Chase%",
            "Z-O Swing%",
            "Swing%",
            "Z-Con%",
            "O-Con%",
            "Contact%",
            "Whiff%",
            "SwStr%",
            "CSW%",
            "sHPT",
            "sST",
            "sSeager",
            "TTO%",
            "HR%",
            "HR/FB",
            "GB%",
            "LD%",
            "FB%",
            "OFFB%",
            "IFFB%",
            "AIR%",
            "PullAIR%",
            "Pull%",
            "Cent%",
            "Oppo%",
            "Age",
            "Pos",
            "B",
            "Team",
            "League",
        ]
    elif mode == "team_pitch":
        df = df.drop(columns=["sST", "sHPT", "TBF"], errors="ignore")
        col_order = [
            "Team",
            "G",
            "W",
            "L",
            "SV",
            "HLD",
            "CG",
            "SHO",
            "BF",
            "IP",
            "H",
            "HR",
            "SO",
            "BB",
            "IBB",
            "HB",
            "WP",
            "R",
            "ER",
            "ERA",
            "FIP",
            "kwERA",
            "WHIP",
            "ERA+",
            "FIP-",
            "kwERA-",
            "pERA-",
            "Diff",
            "HR%",
            "K%",
            "BB%",
            "K-BB%",
            "Z-Swing%",
            "Chase%",
            "Z-O Swing%",
            "Swing%",
            "Z-Con%",
            "O-Con%",
            "Contact%",
            "Whiff%",
            "SwStr%",
            "CSW%",
            "sSeager",
            "Strike%",
            "Ball%",
            "F-Str%",
            "Putaway%",
            "PLUS%",
            "HR/FB",
            "GB%",
            "LD%",
            "FB%",
            "OFFB%",
            "IFFB%",
            "AIR%",
            "PullAIR%",
            "Pull%",
            "Cent%",
            "Oppo%",
            "Zone%",
            "Arm%",
            "Glove%",
            "High%",
            "Low%",
            "MM%",
            "Behind%",
            "Sec%",
            "FB Velo",
            "Grade",
            "League",
        ]
    elif mode == "player_pitch":
        df = df.drop(columns=["sST", "sHPT", "TBF", "PCT", "BK"], errors="ignore")
        col_order = [
            "Pitcher",
            "G",
            "W",
            "L",
            "SV",
            "HLD",
            "CG",
            "SHO",
            "BF",
            "IP",
            "H",
            "HR",
            "SO",
            "BB",
            "IBB",
            "HB",
            "WP",
            "R",
            "ER",
            "ERA",
            "FIP",
            "kwERA",
            "WHIP",
            "ERA+",
            "FIP-",
            "kwERA-",
            "pERA-",
            "Diff",
            "HR%",
            "K%",
            "BB%",
            "K-BB%",
            "Z-Swing%",
            "Chase%",
            "Z-O Swing%",
            "Swing%",
            "Z-Con%",
            "O-Con%",
            "Contact%",
            "Whiff%",
            "SwStr%",
            "CSW%",
            "sSeager",
            "Strike%",
            "Ball%",
            "F-Str%",
            "Putaway%",
            "PLUS%",
            "HR/FB",
            "GB%",
            "LD%",
            "FB%",
            "OFFB%",
            "IFFB%",
            "AIR%",
            "PullAIR%",
            "Pull%",
            "Cent%",
            "Oppo%",
            "Zone%",
            "Arm%",
            "Glove%",
            "High%",
            "Low%",
            "MM%",
            "Behind%",
            "Sec%",
            "FB Velo",
            "Grade",
            "Age",
            "T",
            "Team",
            "League",
        ]
    elif mode == "team_summary":
        df = df.drop(columns=["RS", "RA"], errors="ignore")
        col_order = [
            "Team",
            "W",
            "L",
            "PCT",
            "Diff",
            "HR",
            "SB",
            "OPS+",
            "ERA+",
            "FIP-",
            "K-BB%",
            "wSB",
            "TZR",
        ]
    else:
        col_order = []

    # Reorder columns so any not in col_order go at the end
    df = df[
        [c for c in col_order if c in df.columns]
        + [c for c in df.columns if c not in col_order]
    ]

    return df


def format_cols_as_strs(df, mode=None):
    """
    Formats DataFrame columns as strings with appropriate display formatting.
    This is mainly for Altair chart text displaying raw stats. Use after running
    calculations using the numeric representation.

    Parameters:
        df (pandas.DataFrame): DataFrame with columns to format.
        mode (str, optional): Determines what format to use with stats that share
            names. Options: "player_pitch", "team_pitch", "standings", or None.

    Functionality:
        - Applies custom format strings to statistic columns based on type.
        - Handles both regular stats and percentage stats (rescaling percentages).
        - For specific modes, adds additional format mappings (e.g., "Diff", "kwERA-").

    Returns:
        pandas.DataFrame: The DataFrame with formatted string values.
    """
    # This dict and the updates below should contain stats that require specific formats
    format_maps = {
        "OBP": "{:.3f}",
        "PA": "{:.0f}",
        "AB": "{:.0f}",
        "2B": "{:.0f}",
        "3B": "{:.0f}",
        "TB": "{:.0f}",
        "RBI": "{:.0f}",
        "SB": "{:.0f}",
        "CS": "{:.0f}",
        "SH": "{:.0f}",
        "SF": "{:.0f}",
        "HP": "{:.0f}",
        "GDP": "{:.0f}",
        "HR": "{:.0f}",
        "BB": "{:.0f}",
        "IBB": "{:.0f}",
        "R": "{:.0f}",
        "W": "{:.0f}",
        "L": "{:.0f}",
        "SV": "{:.0f}",
        "CG": "{:.0f}",
        "SHO": "{:.0f}",
        "BF": "{:.0f}",
        "H": "{:.0f}",
        "SO": "{:.0f}",
        "HB": "{:.0f}",
        "WP": "{:.0f}",
        "ER": "{:.0f}",
        "GB%": "{:.1%}",
        "HLD": "{:.0f}",
        "FB Velo": "{:.1f}",
        "XPCT": "{:.3f}",
        "RS": "{:.0f}",
        "RA": "{:.0f}",
        "TZR": "{:.1f}",
        "TZR/143": "{:.1f}",
        "RngR": "{:.1f}",
        "ARM": "{:.1f}",
        "Arm": "{:.1f}",
        "DPR": "{:.1f}",
        "ErrR": "{:.1f}",
        "Framing": "{:.1f}",
        "Blocking": "{:.1f}",
        "PCT": "{:.3f}",
        "OPS+": "{:.0f}",
        "AVG": "{:.3f}",
        "SLG": "{:.3f}",
        "OPS": "{:.3f}",
        "ISO": "{:.3f}",
        "BABIP": "{:.3f}",
        "BB/K": "{:.2f}",
        "PullAIR%": "{:.1%}",
        "Chase%": "{:.1%}",
        "Swing%": "{:.1%}",
        "sSeager": "{:.1f}",
        "HR/FB": "{:.1%}",
        "TTO%": "{:.1%}",
        "wSB": "{:.1f}",
        "BB%": "{:.1%}",
        "K%": "{:.1%}",
        "K-BB%": "{:.1%}",
        "HR%": "{:.1%}",
        "FIP": "{:.2f}",
        "WHIP": "{:.2f}",
        "kwERA": "{:.2f}",
        "ERA": "{:.2f}",
        "ERA+": "{:.0f}",
        "FIP-": "{:.0f}",
        "Z-Con%": "{:.1%}",
        "Sec%": "{:.1%}",
        "SwStr%": "{:.1%}",
        "CSW%": "{:.1%}",
        "Total Zone Runs": "{:.1f}",
        "Steal Tendency": "{:.1f}",
        "Bunt Tendency": "{:.1f}",
        "Def Value": "{:.1f}",
        "Range": "{:.1f}",
        "F-Str%": "{:.1%}",
    }
    # Stats that have different appearance depending on what page they'll be displayed
    if mode == "player_pitch":
        new_format_maps = {
            "kwERA-": "{:.0f}",
            "Diff": "{:.2f}",
        }
        format_maps.update(new_format_maps)
    elif mode == "team_pitch":
        new_format_maps = {
            "kwERA-": "{:.1f}",
            "Diff": "{:.2f}",
        }
        format_maps.update(new_format_maps)
    elif mode == "standings":
        new_format_maps = {
            "Diff": "{:.0f}",
        }
        format_maps.update(new_format_maps)

    for key, value in format_maps.items():
        if key in df.columns.to_list():
            df[key] = pd.to_numeric(df[key], errors="coerce")
            # Rescale percentage stats
            if "%" in key or key == "HR/FB":
                df[key] = df[key] / 100
            df[key] = df[key].apply(value.format)
    return df


def ordinal(n):
    """
    Converts an integer to its ordinal string representation.

    Applies standard English ordinal suffixes (st, nd, rd, th) to the input
    integer, with special handling for the teen numbers 11-13 which always
    use the 'th' suffix.

    Parameters:
        n (int): The integer to convert to an ordinal string.

    Returns:
        str: The ordinal string representation of the input integer
            (e.g., 1 -> '1st', 2 -> '2nd', 11 -> '11th').
    """
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    suffixes = {1: "st", 2: "nd", 3: "rd"}
    return f"{n}{suffixes.get(n % 10, 'th')}"


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
    year = st.selectbox("Year", ["2026", "2025"])
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
        string: The user's chosen player.
    """
    df = df.sort_values(player_col)
    player_list = df[player_col]
    player = st.selectbox(player_col, player_list, key=key)
    return player


def create_team_plus_player_filter(df, player_col, key=None):
    """
    Creates a Streamlit select box filter for selecting players with team names.

    Parameters:
        df (pandas.DataFrame): DataFrame with a player column and a "Team" column.
        player_col (string): The column containing player names.
        key (string, optional): Streamlit widget key for state management.

    Functionality:
        - Sorts the DataFrame by player name for consistent display.
        - Appends team names in parentheses to player names for disambiguation.
        - Displays a select box with combined "Player (Team)" options.
        - Extracts and returns both the selected player name and team name.

    Returns:
        tuple: (player, team) where:
            - player (string): The selected player name without the team suffix.
            - team (string): The extracted team name from the selection.
    """
    df = df.sort_values(player_col)
    df[player_col] = df[player_col] + " (" + df["Team"] + ")"
    player_list = df[player_col]
    player_team = st.selectbox(player_col, player_list, key=key)
    # Remove team and parentheses from player name
    player = player_team.replace(
        " (" + re.search("\\(([^)]+)", player_team).group(1) + ")", ""
    )
    # Extract team name between parentheses
    team = re.search("\\(([^)]+)", player_team).group(1)
    return player, team


def wavg_ignore_missing(df, value_col, weight_col):
    """Calculate weighted average while ignoring missing values.

    Args:
        df (pandas.DataFrame): The DataFrame containing the data.
        value_col (str): The name of the column containing values to average.
        weight_col (str): The name of the column containing weights.

    Returns:
        float: The weighted average of the valid values, or np.nan if no
            valid rows exist.
    """
    # Keep only rows where BOTH value and weight exist (and weight > 0)
    valid_rows = df[value_col].notna() & df[weight_col].notna() & (df[weight_col] > 0)
    if not valid_rows.any():
        return np.nan
    return np.average(
        df.loc[valid_rows, value_col], weights=df.loc[valid_rows, weight_col]
    )


def hex_to_rgb(hex_color):
    """
    Converts a hexadecimal color string to an RGB tuple.

    Parameters:
        hex_color (str): A hex color string in the format "#RRGGBB" or "RRGGBB".

    Returns:
        tuple: A tuple of three integers (R, G, B) representing the RGB values.
    """
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def interpolate_color(percentile, color_range):
    """
    Interpolates between three colors based on a percentile value.

    Parameters:
        percentile (float): A value between 0 and 1 representing the position
            in the color gradient.
        color_range (list): A list of three hex color strings [low, mid, high]
            defining the gradient endpoints.

    Returns:
        str: A CSS background-color string in the format "rgb(r, g, b)".
    """
    low, mid, high = map(hex_to_rgb, color_range)
    if percentile <= 0.5:
        t = percentile * 2
        r = int(low[0] + (mid[0] - low[0]) * t)
        g = int(low[1] + (mid[1] - low[1]) * t)
        b = int(low[2] + (mid[2] - low[2]) * t)
    else:
        t = (percentile - 0.5) * 2
        r = int(mid[0] + (high[0] - mid[0]) * t)
        g = int(mid[1] + (high[1] - mid[1]) * t)
        b = int(mid[2] + (high[2] - mid[2]) * t)
    return f"background-color: rgb({r}, {g}, {b})"


def color_by_percentile(col, pct_cols, invert_pct_cols):
    """
    Apply background color based on percentile rank within the column.

    Parameters:
        col (pandas.Series): A column from a DataFrame to apply coloring to.
        pct_cols (list): List of column names to apply percentile coloring to.
        invert_pct_cols (list): List of column names where lower values are better.

    Functionality:
        - Calculates the percentile rank of each value within the column.
        - For normal stats, applies blue→gray→red gradient based on percentile
          (lower values get blue, middle get gray, higher get red).
        - For inverted stats where lower is better, reverses the percentile calculation.
        - Skips columns not in pct_cols or invert_pct_cols.

    Returns:
        list: List of CSS background-color strings for each cell in the column.
    """
    col_data = pd.to_numeric(col, errors="coerce")
    valid_data = col_data.dropna()
    if len(valid_data) == 0:
        return [""] * len(col)

    colors = []
    color_range = ["#4d79d1", "#c2c2c2", "#e04d4d"]
    for val in col_data:
        if pd.isna(val) or col.name not in (pct_cols + invert_pct_cols):
            colors.append("")
        # "Inverse" percentile stats
        elif col.name in invert_pct_cols:
            pct = (valid_data > val).sum() / len(valid_data)
            colors.append(interpolate_color(pct, color_range))
        else:
            pct = (valid_data < val).sum() / len(valid_data)
            colors.append(interpolate_color(pct, color_range))
    return colors


def color_by_team(col):
    """
    Apply background color based on team colors.

    Parameters:
        col (pandas.Series): A column from a DataFrame with team names.

    Functionality:
        - Maps team names to their official colors and "League Average" to white.
        - Returns CSS background-color strings for each cell.

    Returns:
        list: List of CSS background-color strings for each cell in the column.
    """
    valid_data = col.dropna()
    if len(valid_data) == 0 or col.name != "Team":
        return [""] * len(col)

    team_colors = {
        "Rakuten": "#b63a52",
        "Nipponham": "#4f8cb2",
        "ORIX": "#bbaa31",
        "SoftBank": "#fcc800",
        "Seibu": "#6b7fcf",
        "Lotte": "#9a9a9a",
        "Hiroshima": "#f9271a",
        "Chunichi": "#4a68c2",
        "Yomiuri": "#f69822",
        "Hanshin": "#ffe200",
        "DeNA": "#9b8cf2",
        "Yakult": "#4dba84",
        "League Average": "#ffffff",
    }

    colors = []
    for team_str in col:
        if pd.isna(team_str):
            colors.append("")
        else:
            for key, color_code in team_colors.items():
                if key in team_str:
                    r, g, b = hex_to_rgb(color_code)
                    colors.append(f"background-color: rgb({r}, {g}, {b})")
    return colors


def get_column_config(mode=None):
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
    column_config = {
        "HR/FB": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Home Run to Fly Ball Ratio: The rate of fly balls that end up as home runs.",
            alignment="left",
        ),
        "Z-Swing%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="In-Zone Swing Rate: The percentage of pitches inside the strike zone that are swung at.",
            alignment="left",
        ),
        "Z-O Swing%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Zone-minus-Chase Swing Rate: The difference between in-zone swing rate and chase rate.",
            alignment="left",
        ),
        "Contact%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Contact Rate: The percentage of swings that result in contact, including both fair and foul balls.",
            alignment="left",
        ),
        "O-Con%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Out-of-Zone Contact Rate: The percentage of swings on pitches outside the strike zone that result in contact.",
            alignment="left",
        ),
        "Whiff%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Whiff Rate: The percentage of swings that result in swinging strikes.",
            alignment="left",
        ),
        "CSW%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Called Strike plus Whiff Rate: The percentage of pitches that result in either a called strike or a swinging strike. For pitchers, higher is generally better. For hitters, lower is generally better.",
            alignment="left",
        ),
        "GB%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Ground Ball Rate: The percentage of batted balls that are hit on the ground.",
            alignment="left",
        ),
        "FB%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Fly Ball Rate: The percentage of batted balls that are fly balls.",
            alignment="left",
        ),
        "LD%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Line Drive Rate: The percentage of batted balls that are line drives.",
            alignment="left",
        ),
        "OFFB%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Outfield Fly Ball Rate: The percentage of batted balls that are hit as outfield fly balls.",
            alignment="left",
        ),
        "IFFB%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Infield Fly Ball Rate: The percentage of fly balls that are hit as infield pop-ups.",
            alignment="left",
        ),
        "AIR%": st.column_config.NumberColumn(
            format="%.1f%%",
            help=" Air Ball Rate: The percentage of batted balls that are not hit on the ground, including line drives, fly balls, and pop-ups.",
            alignment="left",
        ),
        "HR%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Home Run Rate: The percentage of plate appearances that result in home runs.",
            alignment="left",
        ),
        "Pull%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Pull Rate: The percentage of batted balls hit to the pull side of the field.",
            alignment="left",
        ),
        "Cent%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Center Rate: The percentage of batted balls hit to the middle of the field.",
            alignment="left",
        ),
        "Oppo%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Opposite Field Rate: The percentage of batted balls hit to the opposite field.",
            alignment="left",
        ),
        "PullAIR%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Pulled Air Ball Rate: The percentage of balls in play that are pulled and not hit on the ground.",
            alignment="left",
        ),
        "Pitcher": st.column_config.TextColumn(pinned=True),
        "Player": st.column_config.TextColumn(pinned=True),
        "Year": st.column_config.TextColumn(
            width=45,
            alignment="left",
        ),
        "Age": st.column_config.TextColumn(
            width=40,
            help="Age: How old a player is on June 30th of that year.",
            alignment="left",
        ),
        "Pos": st.column_config.TextColumn(
            width=40,
            help="Position: A player's position on the field.",
            alignment="left",
        ),
        "SwStr%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Swinging Strike Rate: The percentage of total pitches that result in swinging strikes.",
            alignment="left",
        ),
        "Sec%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Secondary Pitch Rate: The percentage of a pitcher's pitches that are NOT fastballs (4-Seam, Sinker, Cutter).",
            alignment="left",
        ),
        "Strike%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Strike Rate: The percentage of total pitches that are recorded as strikes, including called strikes, swinging strikes, foul balls, and balls put in play.",
            alignment="left",
        ),
        "Ball%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Ball Rate: The percentage of total pitches that are recorded as balls.",
            alignment="left",
        ),
        "F-Str%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="First-Pitch Strike Rate: The percentage of plate appearances that begin with a first-pitch strike.",
            alignment="left",
        ),
        "Putaway%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Putaway Rate: The percentage of two-strike pitches that result in a strikeout. It measures how often a pitcher finishes off hitters once they are in a putaway count.",
            alignment="left",
        ),
        "PLUS%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Plus Rate: The percentage of pitches that result in a positive outcome for the pitcher, including called strikes, swinging strikes, foul balls, and batted-ball outs.",
            alignment="left",
        ),
        "Zone%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Zone Rate: The percentage of pitches that are located inside the strike zone.",
            alignment="left",
        ),
        "Arm%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Arm-Side Pitch Rate: The percentage of pitches thrown to the pitcher's arm side of the strike zone.",
            alignment="left",
        ),
        "Glove%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Glove-Side Pitch Rate: The percentage of pitches thrown to the pitcher's glove side of the strike zone.",
            alignment="left",
        ),
        "High%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="High Pitch Rate: The percentage of pitches thrown in the upper half of the strike zone or above it.",
            alignment="left",
        ),
        "Low%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Low Pitch Rate: The percentage of pitches thrown in the lower half of the strike zone or below it.",
            alignment="left",
        ),
        "MM%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Middle-Middle Pitch Rate: The percentage of pitches thrown in the middle-middle quadrant of the strike zone. Lower is generally better because middle-middle pitches are usually the easiest locations for hitters to damage.",
            alignment="left",
        ),
        "Behind%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Behind-in-the-Count Pitch Rate: The percentage of pitches thrown when the pitcher is behind in the count. Lower is generally better because it indicates that a pitcher is working ahead more often.",
            alignment="left",
        ),
        "Grade": st.column_config.NumberColumn(
            format="%.0f",
            help="Pitch ERA Grade: A 20-80 scale grade for pERA, inspired by Jeff Zimmerman's model for per pitch valuations. A grade of 50 is league average, and every 10 points represents one standard deviation from average.",
            alignment="left",
        ),
        "pERA-": st.column_config.NumberColumn(
            format="%.0f",
            help="Pitch ERA Minus: A normalized version of pERA, inspired by Jeff Zimmerman's model for per pitch valuations, with 100 always being the league average. Lower values are better.",
            alignment="left",
        ),
        "Z-Con%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="In-Zone Contact Rate: The percentage of swings on pitches in the strike zone that result in contact, including both fair and foul balls.",
            alignment="left",
        ),
        "Con%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Contact Rate: The percentage of swings against a pitcher that result in contact, including both fair and foul balls. Recognized by PitcherList.com in 2018 as one of the “Big Three” plate discipline metrics.",
            alignment="left",
        ),
        "FB Velo": st.column_config.NumberColumn(
            format="%.1f",
            help="Average Fastball Velocity: The average speed of a pitcher's fastball, measured in miles per hour (mph).",
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
        "ER": st.column_config.NumberColumn(
            help="Earned Runs: The number of runs scored against the pitcher that are not the result of errors or passed balls.",
            alignment="left",
        ),
        "HB": st.column_config.NumberColumn(
            help="Hit By Pitches: The number of batters a pitcher hits with a pitch.",
            alignment="left",
        ),
        "K%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Strikeout Rate: The percentage of plate appearances that end in a strikeout.",
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
        "ERA": st.column_config.NumberColumn(
            format="%.2f",
            help="Earned Run Average: The average number of earned runs a pitcher allows per nine innings pitched.",
            alignment="left",
        ),
        "sHPT": st.column_config.NumberColumn(
            format="%.1f",
            help="Simple Hittable Pitches Taken: The percentage of taken pitches that are hittable pitches, calculated as C/(C+D). Lower is generally better because it means a player is taking fewer hittable pitches among all pitches they let go.",
            alignment="left",
        ),
        "sST": st.column_config.NumberColumn(
            format="%.1f",
            help="Simple Selection Tendency: The percentage of good decisions that come from taking bad pitches, calculated as D/(A+D). Higher generally points to a more selective approach, while lower scores generally point to a more aggressive approach.",
            alignment="left",
        ),
        "Chase%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Chase Rate: The percentage of pitches outside the strike zone that are swung at.",
            alignment="left",
        ),
        "Swing%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Swing Rate: The percentage of total pitches swung at.",
            alignment="left",
        ),
        "AB": st.column_config.NumberColumn(
            help="At-bats: The number of times a player bats, excluding walks, hit-by-pitches, sacrifices, errors, fielder's choices, and catcher's interferences.",
            alignment="left",
        ),
        "BB%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Walk Rate: The percentage of plate appearances that result in a walk.",
            alignment="left",
        ),
        "TTO%": st.column_config.NumberColumn(
            format="%.1f%%",
            help="Three True Outcomes Rate: The percentage of plate appearances that result in one of the three true outcomes: a home run, a strikeout, or a walk.",
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
            help="Isolated Power: A measure of a player's raw power, calculated as SLG - AVG.",
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
        "PA": st.column_config.NumberColumn(
            format="%.0f",
            help="Plate Appearances: The total number of times a player comes to bat.",
            alignment="left",
        ),
        "RBI": st.column_config.NumberColumn(
            format="%.0f",
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
        "TB": st.column_config.NumberColumn(
            help="Total Bases: The total number of bases a player records from hits.",
            alignment="left",
        ),
        "HP": st.column_config.NumberColumn(
            help="Hit By Pitches: The number of times a player reaches first base after being hit by a pitched ball.",
            alignment="left",
        ),
        "SB": st.column_config.NumberColumn(
            format="%.0f",
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
        "B": st.column_config.TextColumn(
            help="Bats: A hitter's batting hand.",
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
        "ErrR": st.column_config.NumberColumn(
            format="%.1f",
            help="Error Runs: Defensive runs through preventing errors.",
            alignment="left",
        ),
        "Inn": st.column_config.NumberColumn(
            format="%.1f",
            help="Innings Played: Total innings played at the position, recorded in one-third increments.",
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
        "G": st.column_config.NumberColumn(
            help="Games Played",
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
    # Pin and widen team columns on according pages, keep unpinned elsewhere
    if "team" in mode:
        column_config.update(
            {
                "Team": st.column_config.TextColumn(
                    pinned=True,
                    width=140,
                    alignment="left",
                )
            }
        )
    else:
        column_config.update(
            {
                "Team": st.column_config.TextColumn(
                    width=85,
                    alignment="left",
                )
            }
        )
    # Page specific definitions
    if mode == "team_standings":
        column_config.update(
            {
                "T": st.column_config.NumberColumn(
                    help="Ties",
                    alignment="left",
                ),
                "Diff": st.column_config.NumberColumn(
                    format="%.0f",
                    help="Run Differential",
                    alignment="left",
                ),
            }
        )
    if mode == "player_bat":
        column_config.update(
            {
                "sSeager": st.column_config.NumberColumn(
                    format="%.1f",
                    help="Simple Seager: A simplified version of SEAGER (named after Corey Seager) that measures swing choices using zone vs. out-of-zone pitches instead of more complex pitch-level models. For hitters, it rewards swinging at strikes and taking balls, and it can be calculated as D/(A+D) - C/(C+D) using four pitch-decision buckets.",
                    alignment="left",
                ),
                "R": st.column_config.NumberColumn(
                    help="Runs: The number of times a player crosses home plate to score.",
                    alignment="left",
                ),
                "HR": st.column_config.NumberColumn(
                    format="%.0f",
                    help="Home Runs: The number of hits where a player safely reaches home plate without an error or fielder's choice.",
                    alignment="left",
                ),
                "BB": st.column_config.NumberColumn(
                    format="%.0f",
                    help="Walks: The number of times a player is awarded first base after receiving four balls outside the strike zone.",
                    alignment="left",
                ),
                "IBB": st.column_config.NumberColumn(
                    help="Intentional Walks: The number of times a player is intentionally awarded first base by the opposing team.",
                    alignment="left",
                ),
                "SO": st.column_config.NumberColumn(
                    format="%.0f",
                    help="Strikeouts: The number of times a player is put out on three strikes.",
                    alignment="left",
                ),
                "Qualifier": st.column_config.TextColumn(
                    help="Qualified Hitter: A player is qualified for titles with 3.1 PA per team game played (NPB) or 2.7 PA per team game played (Farm).",
                    alignment="left",
                ),
                "H": st.column_config.NumberColumn(
                    format="%.0f",
                    help="Hits: The number of times a player reaches safely on a ball put in play without an error or fielder's choice.",
                    alignment="left",
                ),
            }
        )
    if mode == "player_pitch":
        column_config.update(
            {
                "sSeager": st.column_config.NumberColumn(
                    format="%.1f",
                    help="Simple Seager: A simplified version of SEAGER that measures swing choices against a pitcher using zone vs. out-of-zone pitches instead of more complex pitch-level models. For pitchers, it rewards getting hitters to take strikes and swing at balls, and it can be calculated as C/(A+C) - B/(B+D) using four pitch-decision buckets.",
                    alignment="left",
                ),
                "R": st.column_config.NumberColumn(
                    help="Runs: The total number of runs a pitcher allows.",
                    alignment="left",
                ),
                "HR": st.column_config.NumberColumn(
                    format="%.0f",
                    help="Home Runs: The number of home runs a pitcher allows.",
                    alignment="left",
                ),
                "BB": st.column_config.NumberColumn(
                    help="Walks: The number of times a pitcher allows a batter to reach first base by throwing four balls.",
                    alignment="left",
                ),
                "IBB": st.column_config.NumberColumn(
                    help="Intentional Walks: The number of walks a pitcher intentionally issues.",
                    alignment="left",
                ),
                "SO": st.column_config.NumberColumn(
                    help="Strikeouts: The number of batters a pitcher retires on strikes.",
                    alignment="left",
                ),
                "Qualifier": st.column_config.TextColumn(
                    help="Qualified Pitcher: A pitcher is qualified for titles with 1.0 IP per team game played (NPB) or 0.8 IP per team game played (Farm).",
                    alignment="left",
                ),
                "H": st.column_config.NumberColumn(
                    help="Hits: The number of hits a pitcher allows.",
                    alignment="left",
                ),
                "T": st.column_config.TextColumn(
                    help="Throws: A pitcher's throwing hand.",
                    alignment="left",
                ),
                "Diff": st.column_config.NumberColumn(
                    format="%.2f",
                    help="ERA-FIP Differential: The differential of a pitcher's ERA and FIP. Higher values indicate underperformance and lower values indicate overperformance relative to expectations.",
                    alignment="left",
                ),
            }
        )

    return column_config
