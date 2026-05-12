"""Displays NPB batting data with Streamlit"""

import streamlit as st
import altair as alt
import pages.helper as hp


def main():
    """
    Main entry point for the Streamlit NPB batting dashboard.

    Loads player batting statistics (including leaders/qualifiers) from GitHub,
    then provides interactive filters for qualifiers, plate appearances,
    league, batting hand, position, team, and statistic columns. Applies
    user-selected filters to the data and formats key statistics for display.
    Shows the resulting batting data in a Streamlit dataframe.

    Returns:
        None
    """
    st.set_page_config(layout="wide")

    # Split filters away from dataframe
    with st.container(border=True):
        # Smaller filters split by cols, larger filters receive exclusive cols
        r1c1, r1c2, r1c3 = st.columns([2, 1, 6], vertical_alignment="center")

        with r1c1:
            user_year = hp.create_year_filter()
            lead_bat_df = hp.load_csv(st.secrets[user_year + "LeadersBR_link"])
            player_bat_df = hp.load_csv(st.secrets[user_year + "StatsFinalBR_link"])
            leader_view = st.toggle("Qualifiers")
            if leader_view is True:
                display_df = lead_bat_df.drop("#", axis=1)
            else:
                display_df = player_bat_df
            display_df = display_df.fillna(value={"Pos": "N/A"})
            user_pa = hp.create_pa_filter(display_df, "player")
            # Drop players below PA threshold
            display_df = display_df.drop(display_df[display_df.PA < user_pa].index)
        with r1c2:
            user_league = hp.create_league_filter(mode="npb")
            user_batting_hand = hp.create_hand_filter("player_bat")
        with r1c3:
            user_pos = hp.create_pos_filter(display_df, mode="player_bat")

        user_team = hp.create_team_filter(mode="npb")
        user_cols = hp.create_stat_cols_filter(display_df, mode="player_bat")

        # Sorting options
        user_sort_col, user_sort_asc = hp.create_sort_filter(user_cols, mode="bat")

    # Apply filters
    display_df = display_df[display_df["Pos"].isin(user_pos)]
    display_df = display_df[display_df["B"].isin(user_batting_hand)]
    display_df = display_df[display_df["League"].isin(user_league)]
    display_df = display_df[display_df["Team"].isin(user_team)]

    # Convert to best matched type and use column_config for trailing zeroes
    display_df = hp.convert_pct_cols_to_float(display_df)
    display_df = display_df.convert_dtypes()

    # Apply sorting and reset index (must be after convert_pct_cols_to_float())
    display_df = display_df.sort_values(
        user_sort_col, ascending=user_sort_asc
    ).reset_index(drop=True)
    display_df.index += 1

    # Declare columns to be colored percentiles
    pct_cols = [
        "AVG",
        "OBP",
        "SLG",
        "OPS",
        "OPS+",
        "ISO",
        "BABIP",
        "BB%",
        "BB/K",
        "wSB",
        "HR/FB",
        "wSB",
        "PullAIR%",
        "Z-Con%",
        "Swing%",
        "sSeager",
        "TTO%",
    ]
    invert_pct_cols = ["K%", "Chase%", "SwStr%"]

    # Display dataframe
    st.dataframe(
        display_df[user_cols]
        .style.apply(hp.color_by_percentile, axis=0, args=(pct_cols, invert_pct_cols))
        .apply(hp.color_by_team, axis=0),
        width="stretch",
        hide_index=False,
        row_height=25,
        column_order=user_cols,
        column_config=hp.get_column_config("BR"),
    )
    generate_player_batting_plots(player_bat_df, display_df, user_year)

    

def generate_player_batting_plots(original_df, display_df, user_year):
    """TODO docs"""
    if display_df.empty:
        st.error("Error: No players to graph - check your filters above.", icon="🚨")
        return

    tab1, tab2, tab3, tab4 = st.tabs(
        ["SLG vs OBP", "BB% vs. K%", "ISO vs. Chase%", "PullAIR% vs. sSeager"]
    )

    # Convert cols to best matched type and get weighted league average approximations
    converted_src_df = hp.convert_pct_cols_to_float(original_df)
    converted_src_df = converted_src_df.convert_dtypes()
    league_obp = (
        converted_src_df["H"].sum() + converted_src_df["BB"].sum() + converted_src_df["HP"].sum()
    ) / (
        converted_src_df["AB"].sum()
        + converted_src_df["BB"].sum()
        + converted_src_df["HP"].sum()
        + converted_src_df["SF"].sum()
    )
    league_slg = (
        (
            converted_src_df["H"].sum()
            - converted_src_df["2B"].sum()
            - converted_src_df["3B"].sum()
            - converted_src_df["HR"].sum()
        )
        + (2 * converted_src_df["2B"].sum())
        + (3 * converted_src_df["3B"].sum())
        + (4 * converted_src_df["HR"].sum())
    ) / converted_src_df["AB"].sum()
    league_chase = hp.wavg_ignore_missing(converted_src_df, "Chase%", "PA")
    league_pullair = hp.wavg_ignore_missing(converted_src_df, "PullAIR%", "PA")
    league_sseager = hp.wavg_ignore_missing(converted_src_df, "sSeager", "PA")
    league_avg = converted_src_df["H"].sum() / converted_src_df["AB"].sum()
    league_iso = league_slg - league_avg
    league_k = (converted_src_df["SO"].sum() / converted_src_df["PA"].sum()) * 100
    league_bb = (converted_src_df["BB"].sum() / converted_src_df["PA"].sum()) * 100

    team_colors = {
        "Hanshin Tigers": "#ffe200",
        "Hiroshima Carp": "#f9271a",
        "DeNA BayStars": "#9b8cf2",
        "Yomiuri Giants": "#f69822",
        "Yakult Swallows": "#4dba84",
        "Chunichi Dragons": "#4a68c2",
        "ORIX Buffaloes": "#bbaa31",
        "Lotte Marines": "#9a9a9a",
        "SoftBank Hawks": "#fcc800",
        "Rakuten Eagles": "#b63a52",
        "Seibu Lions": "#6b7fcf",
        "Nipponham Fighters": "#4f8cb2",
    }

    with tab1:
        # Create scatter plot with colored points and team name labels
        points = (
            alt.Chart(display_df)
            .mark_point(size=100, filled=True)
            .encode(
                x=alt.X(
                    "OBP:Q",
                    title="OBP",
                    scale=alt.Scale(
                        type="linear",
                        domain=[display_df["OBP"].min(), display_df["OBP"].max()],
                    ),
                    axis=alt.Axis(values=[league_obp]),
                ),
                y=alt.Y(
                    "SLG:Q",
                    title="SLG",
                    scale=alt.Scale(
                        type="linear",
                        domain=[display_df["SLG"].min(), display_df["SLG"].max()],
                    ),
                    axis=alt.Axis(values=[league_slg]),
                ),
                color=alt.Color("Team:N", legend=None).scale(
                    domain=list(team_colors.keys()), range=list(team_colors.values())
                ),
                tooltip=["Player", "OBP", "SLG", "OPS", "Team"],
            )
        )

        text = (
            alt.Chart(display_df)
            .mark_text(size=10, dy=-10)
            .encode(
                x=alt.X(
                    "OBP:Q",
                    title="OBP",
                    scale=alt.Scale(
                        type="linear",
                        domain=[display_df["OBP"].min(), display_df["OBP"].max()],
                    ),
                    axis=alt.Axis(values=[league_obp], format=".3f"),
                ),
                y=alt.Y(
                    "SLG:Q",
                    title="SLG",
                    scale=alt.Scale(
                        type="linear",
                        domain=[display_df["SLG"].min(), display_df["SLG"].max()],
                    ),
                    axis=alt.Axis(values=[league_slg], format=".3f"),
                ),
                text="Player",
                tooltip=alt.value(None),
            )
        )
        title_params = alt.TitleParams(
            text=user_year + " NPB - Batting SLG vs OBP",
            subtitle="@YakyuCosmo",
            subtitleColor="grey",
            subtitleFontSize=13.5,
        )
        chart = (text + points).properties(title=title_params).interactive()

        st.info("Adjust graph using the filters above", icon="ℹ️")
        st.altair_chart(
            chart,
            width="stretch",
            height=750,
            on_select="ignore",
            selection_mode=None,
        )

    with tab2:
        # Create scatter plot with colored points and team name labels
        points = (
            alt.Chart(display_df)
            .mark_point(size=100, filled=True)
            .encode(
                x=alt.X(
                    "BB%:Q",
                    title="BB%",
                    scale=alt.Scale(
                        type="linear",
                        domain=[display_df["BB%"].min(), display_df["BB%"].max()],
                    ),
                    axis=alt.Axis(values=[league_bb], format=".1f"),
                ),
                y=alt.Y(
                    "K%:Q",
                    title="K%",
                    scale=alt.Scale(
                        type="linear",
                        domain=[display_df["K%"].min(), display_df["K%"].max()],
                    ),
                    axis=alt.Axis(values=[league_k], format=".1f"),
                ),
                color=alt.Color("Team:N", legend=None).scale(
                    domain=list(team_colors.keys()), range=list(team_colors.values())
                ),
                tooltip=["Player", "BB%", "K%", "BB/K", "Team"],
            )
        )

        text = (
            alt.Chart(display_df)
            .mark_text(size=10, dy=-10)
            .encode(
                x=alt.X(
                    "BB%:Q",
                    title="BB%",
                    scale=alt.Scale(
                        type="linear",
                        domain=[display_df["BB%"].min(), display_df["BB%"].max()],
                    ),
                    axis=alt.Axis(values=[league_bb]),
                ),
                y=alt.Y(
                    "K%:Q",
                    title="K%",
                    scale=alt.Scale(
                        type="linear",
                        domain=[display_df["K%"].min(), display_df["K%"].max()],
                    ),
                    axis=alt.Axis(values=[league_k]),
                ),
                text="Player",
                tooltip=alt.value(None),
            )
        )
        title_params = alt.TitleParams(
            text=user_year + " NPB - Batting BB% vs K%",
            subtitle="@YakyuCosmo",
            subtitleColor="grey",
            subtitleFontSize=13.5,
        )
        chart = (text + points).properties(title=title_params).interactive()

        st.info("Adjust graph using the filters above", icon="ℹ️")
        st.altair_chart(
            chart,
            width="stretch",
            height=750,
            on_select="ignore",
            selection_mode=None,
        )

    with tab3:
        # Create scatter plot with colored points and team name labels
        points = (
            alt.Chart(display_df)
            .mark_point(size=100, filled=True)
            .encode(
                x=alt.X(
                    "ISO:Q",
                    title="ISO",
                    scale=alt.Scale(
                        type="linear",
                        domain=[display_df["ISO"].min(), display_df["ISO"].max()],
                    ),
                    axis=alt.Axis(values=[league_iso], format=".1f"),
                ),
                y=alt.Y(
                    "Chase%:Q",
                    title="Chase%",
                    scale=alt.Scale(
                        type="linear",
                        domain=[display_df["Chase%"].min(), display_df["Chase%"].max()],
                    ),
                    axis=alt.Axis(values=[league_chase], format=".3f"),
                ),
                color=alt.Color("Team:N", legend=None).scale(
                    domain=list(team_colors.keys()), range=list(team_colors.values())
                ),
                tooltip=["Player", "ISO", "Chase%", "OPS+", "Team"],
            )
        )

        text = (
            alt.Chart(display_df)
            .mark_text(size=10, dy=-10)
            .encode(
                x=alt.X(
                    "ISO:Q",
                    title="ISO",
                    scale=alt.Scale(
                        type="linear",
                        domain=[display_df["ISO"].min(), display_df["ISO"].max()],
                    ),
                    axis=alt.Axis(values=[league_iso], format=".3f"),
                ),
                y=alt.Y(
                    "Chase%:Q",
                    title="Chase%",
                    scale=alt.Scale(
                        type="linear",
                        domain=[display_df["Chase%"].min(), display_df["Chase%"].max()],
                    ),
                    axis=alt.Axis(values=[league_chase], format=".1f"),
                ),
                text="Player",
                tooltip=alt.value(None),
            )
        )
        title_params = alt.TitleParams(
            text=user_year + " NPB - Batting ISO vs Chase%",
            subtitle="@YakyuCosmo",
            subtitleColor="grey",
            subtitleFontSize=13.5,
        )
        chart = (text + points).properties(title=title_params).interactive()

        st.info("Adjust graph using the filters above", icon="ℹ️")
        st.altair_chart(
            chart,
            width="stretch",
            height=750,
            on_select="ignore",
            selection_mode=None,
        )

    with tab4:
        # Create scatter plot with colored points and team name labels
        points = (
            alt.Chart(display_df)
            .mark_point(size=100, filled=True)
            .encode(
                x=alt.X(
                    "PullAIR%:Q",
                    title="PullAIR%",
                    scale=alt.Scale(
                        type="linear",
                        domain=[display_df["PullAIR%"].min(), display_df["PullAIR%"].max()],
                    ),
                    axis=alt.Axis(values=[league_pullair], format=".1f"),
                ),
                y=alt.Y(
                    "sSeager:Q",
                    title="sSeager",
                    scale=alt.Scale(
                        type="linear",
                        domain=[display_df["sSeager"].min(), display_df["sSeager"].max()],
                    ),
                    axis=alt.Axis(values=[league_sseager], format=".1f"),
                ),
                color=alt.Color("Team:N", legend=None).scale(
                    domain=list(team_colors.keys()), range=list(team_colors.values())
                ),
                tooltip=["Player", "PullAIR%", "sSeager", "OPS+", "Team"],
            )
        )

        text = (
            alt.Chart(display_df)
            .mark_text(size=10, dy=-10)
            .encode(
                x=alt.X(
                    "PullAIR%:Q",
                    title="PullAIR%",
                    scale=alt.Scale(
                        type="linear",
                        domain=[display_df["PullAIR%"].min(), display_df["PullAIR%"].max()],
                    ),
                    axis=alt.Axis(values=[league_pullair], format=".1f"),
                ),
                y=alt.Y(
                    "sSeager:Q",
                    title="sSeager",
                    scale=alt.Scale(
                        type="linear",
                        domain=[display_df["sSeager"].min(), display_df["sSeager"].max()],
                    ),
                    axis=alt.Axis(values=[league_sseager], format=".1f"),
                ),
                text="Player",
                tooltip=alt.value(None),
            )
        )
        title_params = alt.TitleParams(
            text=user_year + " NPB - Batting PullAIR% vs sSeager",
            subtitle="@YakyuCosmo",
            subtitleColor="grey",
            subtitleFontSize=13.5,
        )
        chart = (text + points).properties(title=title_params).interactive()

        st.info("Adjust graph using the filters above", icon="ℹ️")
        st.altair_chart(
            chart,
            width="stretch",
            height=750,
            on_select="ignore",
            selection_mode=None,
        )

if __name__ == "__main__":
    main()
