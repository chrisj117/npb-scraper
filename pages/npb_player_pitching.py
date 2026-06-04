"""Displays NPB pitching data with Streamlit"""

import streamlit as st
import altair as alt
import pages.helper as hp


def main():
    """
    Main entry point for the Streamlit NPB pitching dashboard.

    Loads player pitching statistics (including leaders/qualifiers) from
    GitHub. Provides interactive filters for qualifiers, minimum innings
    pitched (IP), league, pitching hand, team, and statistic columns. Applies
    user-selected filters and formats key pitching statistics for display.
    Shows the resulting pitching data in a Streamlit dataframe.

    Returns:
        None
    """
    st.set_page_config(layout="wide")

    # Split filters away from dataframe
    with st.container(border=True):
        # Smaller filters split by cols, larger filters receive exclusive cols
        r1c1, r1c2, r1c3 = st.columns([2, 1, 6])

        with r1c1:
            user_year = hp.create_year_filter()
            lead_pitch_df = hp.load_csv(st.secrets[user_year + "LeadersPR_link"])
            player_pitch_df = hp.load_csv(st.secrets[user_year + "StatsFinalPR_link"])
            leader_view = st.toggle("Qualifiers")
            if leader_view is True:
                display_df = lead_pitch_df.drop("#", axis=1)
            else:
                display_df = player_pitch_df
            user_ip = hp.create_ip_filter(display_df, mode="player")
            # Drop players below IP threshold
            display_df = display_df.drop(display_df[display_df.IP < user_ip].index)
        with r1c2:
            user_league = hp.create_league_filter(mode="npb")
            user_pitching_hand = hp.create_hand_filter(mode="player_pitch")
        with r1c3:
            user_team = hp.create_team_filter(mode="npb")

        user_cols = hp.create_stat_cols_filter(display_df, mode="player_pitch")
        # Sorting options
        user_sort_col, user_sort_asc = hp.create_sort_filter(user_cols, mode="pitch")

    # Apply filters
    display_df = display_df[display_df["T"].isin(user_pitching_hand)]
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
        "ERA+",
        "Diff",
        "K%",
        "K-BB%",
        "GB%",
        "Chase%",
        "SwStr%",
        "CSW%",
        "Sec%",
        "FB Velo",
    ]
    invert_pct_cols = [
        "ERA",
        "FIP",
        "kwERA",
        "WHIP",
        "FIP-",
        "kwERA-",
        "HR%",
        "BB%",
        "HR/FB",
        "Z-Con%",
    ]

    # Display stats
    st.dataframe(
        display_df[user_cols]
        .style.apply(hp.color_by_percentile, axis=0, args=(pct_cols, invert_pct_cols))
        .apply(hp.color_by_team, axis=0),
        width="stretch",
        hide_index=False,
        row_height=25,
        column_order=user_cols,
        column_config=hp.get_column_config("PR"),
    )
    generate_player_pitching_plots(player_pitch_df, display_df, user_year)


def generate_player_pitching_plots(original_df, display_df, user_year):
    """
    Generates interactive scatter plots for NPB pitching statistics using Altair.

    Creates four tabs with comparative visualizations:
    - BB% vs K% with league average reference lines
    - CSW% vs GB% with league average reference lines
    - SwStr% vs Chase% with league average reference lines
    - FB Velo vs Sec% with league average reference lines

    Each plot displays player data points colored by team with player name labels
    and interactive tooltips showing relevant statistics.

    Args:
        original_df (pandas.DataFrame): Unfiltered pitching statistics dataframe
        display_df (pandas.DataFrame): Filtered pitching statistics dataframe based on user selections
        user_year (str): The selected NPB season year for chart titles

    Returns:
        None: Displays plots directly in Streamlit interface
    """
    if display_df.empty:
        st.error("Error: No players to graph - check your filters above.", icon="🚨")
        return

    tab1, tab2, tab3, tab4 = st.tabs(
        ["BB% vs K%", "CSW% vs. GB%", "SwStr% vs. Chase%", "FB Velo vs. Sec%"]
    )

    # Convert cols to best matched type and get weighted league average approximations
    converted_src_df = hp.convert_pct_cols_to_float(original_df)
    converted_src_df = converted_src_df.convert_dtypes()
    league_gb = hp.wavg_ignore_missing(converted_src_df, "GB%", "IP")
    league_chase = hp.wavg_ignore_missing(converted_src_df, "Chase%", "IP")
    league_swstr = hp.wavg_ignore_missing(converted_src_df, "SwStr%", "IP")
    league_csw = hp.wavg_ignore_missing(converted_src_df, "CSW%", "IP")
    league_sec = hp.wavg_ignore_missing(converted_src_df, "Sec%", "IP")
    league_fb_velo = hp.wavg_ignore_missing(converted_src_df, "FB Velo", "IP")
    league_k = (converted_src_df["SO"].sum() / converted_src_df["BF"].sum()) * 100
    league_bb = (converted_src_df["BB"].sum() / converted_src_df["BF"].sum()) * 100

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
            .mark_point(size=100, opacity=0.8, filled=True)
            .encode(
                x=alt.X(
                    "BB%:Q",
                    title="BB%",
                    scale=alt.Scale(
                        type="linear",
                        nice=True,
                        domain=[display_df["BB%"].min(), display_df["BB%"].max()],
                    ),
                    axis=alt.Axis(values=[league_bb]),
                ),
                y=alt.Y(
                    "K%:Q",
                    title="K%",
                    scale=alt.Scale(
                        type="linear",
                        nice=True,
                        domain=[display_df["K%"].min(), display_df["K%"].max()],
                    ),
                    axis=alt.Axis(values=[league_k]),
                ),
                color=alt.Color("Team:N", legend=None).scale(
                    domain=list(team_colors.keys()), range=list(team_colors.values())
                ),
                tooltip=["Pitcher", "K%", "BB%", "K-BB%", "Team"],
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
                        nice=True,
                        domain=[display_df["BB%"].min(), display_df["BB%"].max()],
                    ),
                    axis=alt.Axis(values=[league_bb], format=".1f"),
                ),
                y=alt.Y(
                    "K%:Q",
                    title="K%",
                    scale=alt.Scale(
                        type="linear",
                        nice=True,
                        domain=[display_df["K%"].min(), display_df["K%"].max()],
                    ),
                    axis=alt.Axis(values=[league_k], format=".1f"),
                ),
                text="Pitcher",
                tooltip=alt.value(None),
            )
        )
        title_params = alt.TitleParams(
            text=user_year + " NPB - Pitching BB% vs K%",
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
            .mark_point(size=100, opacity=0.8, filled=True)
            .encode(
                x=alt.X(
                    "GB%:Q",
                    title="GB%",
                    scale=alt.Scale(
                        type="linear",
                        nice=True,
                        domain=[display_df["GB%"].min(), display_df["GB%"].max()],
                    ),
                    axis=alt.Axis(values=[league_gb], format=".1f"),
                ),
                y=alt.Y(
                    "CSW%:Q",
                    title="CSW%",
                    scale=alt.Scale(
                        type="linear",
                        nice=True,
                        domain=[display_df["CSW%"].min(), display_df["CSW%"].max()],
                    ),
                    axis=alt.Axis(values=[league_csw], format=".1f"),
                ),
                color=alt.Color("Team:N", legend=None).scale(
                    domain=list(team_colors.keys()), range=list(team_colors.values())
                ),
                tooltip=["Pitcher", "CSW%", "GB%", "ERA+", "Team"],
            )
        )

        text = (
            alt.Chart(display_df)
            .mark_text(size=10, dy=-10)
            .encode(
                x=alt.X(
                    "GB%:Q",
                    title="GB%",
                    scale=alt.Scale(
                        type="linear",
                        nice=True,
                        domain=[display_df["GB%"].min(), display_df["GB%"].max()],
                    ),
                    axis=alt.Axis(values=[league_gb], format=".1f"),
                ),
                y=alt.Y(
                    "CSW%:Q",
                    title="CSW%",
                    scale=alt.Scale(
                        type="linear",
                        nice=True,
                        domain=[display_df["CSW%"].min(), display_df["CSW%"].max()],
                    ),
                    axis=alt.Axis(values=[league_csw], format=".1f"),
                ),
                text="Pitcher",
                tooltip=alt.value(None),
            )
        )
        title_params = alt.TitleParams(
            text=user_year + " NPB - Pitching CSW% vs GB%",
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
            .mark_point(size=100, opacity=0.8, filled=True)
            .encode(
                x=alt.X(
                    "Chase%:Q",
                    title="Chase%",
                    scale=alt.Scale(
                        type="linear",
                        nice=True,
                        domain=[display_df["Chase%"].min(), display_df["Chase%"].max()],
                    ),
                    axis=alt.Axis(values=[league_chase], format=".1f"),
                ),
                y=alt.Y(
                    "SwStr%:Q",
                    title="SwStr%",
                    scale=alt.Scale(
                        type="linear",
                        nice=True,
                        domain=[display_df["SwStr%"].min(), display_df["SwStr%"].max()],
                    ),
                    axis=alt.Axis(values=[league_swstr], format=".1f"),
                ),
                color=alt.Color("Team:N", legend=None).scale(
                    domain=list(team_colors.keys()), range=list(team_colors.values())
                ),
                tooltip=["Pitcher", "SwStr%", "Chase%", "ERA+", "Team"],
            )
        )

        text = (
            alt.Chart(display_df)
            .mark_text(size=10, dy=-10)
            .encode(
                x=alt.X(
                    "Chase%:Q",
                    title="Chase%",
                    scale=alt.Scale(
                        type="linear",
                        nice=True,
                        domain=[display_df["Chase%"].min(), display_df["Chase%"].max()],
                    ),
                    axis=alt.Axis(values=[league_chase], format=".1f"),
                ),
                y=alt.Y(
                    "SwStr%:Q",
                    title="SwStr%",
                    scale=alt.Scale(
                        type="linear",
                        nice=True,
                        domain=[display_df["SwStr%"].min(), display_df["SwStr%"].max()],
                    ),
                    axis=alt.Axis(values=[league_swstr], format=".1f"),
                ),
                text="Pitcher",
                tooltip=alt.value(None),
            )
        )
        title_params = alt.TitleParams(
            text=user_year + " NPB - Pitching SwStr% vs Chase%",
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
            .mark_point(size=100, opacity=0.8, filled=True)
            .encode(
                x=alt.X(
                    "FB Velo:Q",
                    title="FB Velo",
                    scale=alt.Scale(
                        type="linear",
                        nice=True,
                        domain=[
                            display_df["FB Velo"].min(),
                            display_df["FB Velo"].max(),
                        ],
                    ),
                    axis=alt.Axis(values=[league_fb_velo], format=".1f"),
                ),
                y=alt.Y(
                    "Sec%:Q",
                    title="Sec%",
                    scale=alt.Scale(
                        type="linear",
                        nice=True,
                        domain=[display_df["Sec%"].min(), display_df["Sec%"].max()],
                    ),
                    axis=alt.Axis(values=[league_sec], format=".1f"),
                ),
                color=alt.Color("Team:N", legend=None).scale(
                    domain=list(team_colors.keys()), range=list(team_colors.values())
                ),
                tooltip=["Pitcher", "FB Velo", "Sec%", "ERA+", "Team"],
            )
        )

        text = (
            alt.Chart(display_df)
            .mark_text(size=10, dy=-10)
            .encode(
                x=alt.X(
                    "FB Velo:Q",
                    title="FB Velo",
                    scale=alt.Scale(
                        type="linear",
                        nice=True,
                        domain=[
                            display_df["FB Velo"].min(),
                            display_df["FB Velo"].max(),
                        ],
                    ),
                    axis=alt.Axis(values=[league_fb_velo], format=".1f"),
                ),
                y=alt.Y(
                    "Sec%:Q",
                    title="Sec%",
                    scale=alt.Scale(
                        type="linear",
                        nice=True,
                        domain=[display_df["Sec%"].min(), display_df["Sec%"].max()],
                    ),
                    axis=alt.Axis(values=[league_sec], format=".1f"),
                ),
                text="Pitcher",
                tooltip=alt.value(None),
            )
        )
        title_params = alt.TitleParams(
            text=user_year + " NPB - Pitching FB Velo vs Sec%",
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
