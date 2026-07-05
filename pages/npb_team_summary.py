"""Displays NPB team summary data with Streamlit"""

import streamlit as st
import altair as alt
import pages.helper as hp


def main():
    """
    Main entry point for the Streamlit NPB team summary dashboard.

    Loads team summary statistics from GitHub. Formats team summary statistics
    for display. Shows the resulting team data in a Streamlit dataframe.

    Returns:
        None
    """
    st.set_page_config(layout="wide")

    with st.container(border=True):
        # Sorting options
        user_year = hp.create_year_filter()
        display_df = hp.load_csv(st.secrets[user_year + "TeamSummaryFinalR_link"])
        user_sort_col, user_sort_asc = hp.create_sort_filter(
            display_df.columns.to_list(), mode="team_summary"
        )

    display_df = hp.prepare_streamlit_types(display_df)
    display_df = hp.prepare_streamlit_col_order(display_df, mode="team_summary")

    # Apply sorting and reset index (must be after prepare_streamlit_types())
    display_df = display_df.sort_values(
        user_sort_col, ascending=user_sort_asc
    ).reset_index(drop=True)
    display_df.index += 1

    # Declare columns to be colored percentiles
    pct_cols = [
        "W",
        "PCT",
        "Diff",
        "HR",
        "SB",
        "OPS+",
        "ERA+",
        "K-BB%",
        "wSB",
        "TZR",
    ]
    invert_pct_cols = ["L", "FIP-"]
    styler = display_df.style
    styler.apply(hp.color_by_percentile, axis=0, args=(pct_cols, invert_pct_cols))
    styler.apply(hp.color_by_team, axis=0)
    styler = styler.set_properties(
        subset=["Team"],
        **{"font-weight": "bold"}
    )
    st.dataframe(
        styler,
        width="stretch",
        hide_index=True,
        row_height=25,
        column_config=hp.get_column_config("team_summary"),
    )

    # Convert abbreviated names to full team names
    abbr_dict = {
        "Hanshin Tigers": "T",
        "Hiroshima Carp": "C",
        "DeNA BayStars": "DB",
        "Yomiuri Giants": "G",
        "Yakult Swallows": "S",
        "Chunichi Dragons": "D",
        "ORIX Buffaloes": "B",
        "Lotte Marines": "M",
        "SoftBank Hawks": "H",
        "Rakuten Eagles": "E",
        "Seibu Lions": "L",
        "Nipponham Fighters": "F",
        "Oisix Albirex": "A",
        "HAYATE Ventures": "V",
    }
    display_df["short_Team"] = (
        display_df["Team"]
        .map(abbr_dict)
        .infer_objects()
        .fillna(display_df["Team"])
        .astype(str)
    )

    team_colors = {
        "E": "#b63a52",
        "F": "#4f8cb2",
        "B": "#bbaa31",
        "H": "#fcc800",
        "L": "#6b7fcf",
        "M": "#9a9a9a",
        "C": "#f9271a",
        "D": "#4a68c2",
        "G": "#f69822",
        "T": "#ffe200",
        "DB": "#9b8cf2",
        "S": "#4dba84",
    }

    # Create scatter plot with colored points and team name labels
    display_df = hp.format_cols_as_strs(display_df)
    points = (
        alt.Chart(display_df)
        .mark_point(size=250, opacity=0.8, filled=True)
        .encode(
             x=alt.X(
                 "ERA+:Q",
                 title="ERA+",
                 scale=alt.Scale(type="linear", domain=[65, 135]),
                 axis=alt.Axis(values=[100]),
             ),
             y=alt.Y(
                 "OPS+:Q",
                 title="OPS+",
                 scale=alt.Scale(type="linear", domain=[65, 135]),
                 axis=alt.Axis(values=[100]),
             ),
            color=alt.Color("short_Team:N", legend=None).scale(
                domain=list(team_colors.keys()), range=list(team_colors.values())
            ),
            tooltip=alt.value(None),
        )
    )

    text = (
        alt.Chart(display_df)
        .mark_text(size=10)
        .encode(
            x=alt.X("ERA+:Q"),
            y=alt.Y("OPS+:Q"),
            text="short_Team",
            tooltip=[
                "Team",
                alt.Tooltip("ERA+", format=".0f"),
                alt.Tooltip("OPS+", format=".0f"),
            ],
        )
    )

    title_params = alt.TitleParams(
        text=user_year + " NPB - Team ERA+ vs OPS+",
        subtitle="@YakyuCosmo",
        subtitleColor="grey",
        subtitleFontSize=13.5,
    )
    chart = (points + text).properties(title=title_params)

    st.altair_chart(
        chart,
        width="content",
        height="content",
        on_select="ignore",
        selection_mode=None,
    )


if __name__ == "__main__":
    main()
