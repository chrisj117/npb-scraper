"""Displays NPB team batting data with Streamlit"""

import streamlit as st
import pages.helper as hp


def main():
    """
    Main entry point for the Streamlit NPB team pitching dashboard.

    Loads team pitching statistics from GitHub. Provides interactive filters
    for league, team, and statistic columns. Applies user-selected filters and
    formats key pitching statistics for display. Shows the resulting pitching
    data in a Streamlit dataframe.

    Returns:
        None
    """
    st.set_page_config(layout="wide")

    # Split filters away from dataframe
    with st.container(border=True):
        # Smaller filters split by cols, larger filters receive exclusive cols
        r1c1, r1c2 = st.columns([1, 9], vertical_alignment="center")

        with r1c1:
            user_year = hp.create_year_filter()
            display_df = hp.load_csv(st.secrets[user_year + "TeamPR_link"])
            user_league = hp.create_league_filter(mode="npb")
        with r1c2:
            user_team = hp.create_team_filter(mode="npb")
        user_cols = hp.create_stat_cols_filter(display_df, "team_pitch")

        # Sorting options
        user_sort_col, user_sort_asc = hp.create_sort_filter(user_cols, mode="pitch")

    # Exclude "League Average" from filters
    display_df = display_df.fillna(value={"League": "N/A"})
    user_team.append("League Average")
    user_league.append("N/A")

    # Apply filters
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

    # Display df
    st.dataframe(
        display_df[user_cols]
        .style.apply(hp.color_by_percentile, axis=0, args=(pct_cols, invert_pct_cols))
        .apply(hp.color_by_team, axis=0),
        hide_index=False,
        row_height=25,
        column_order=user_cols,
        column_config=hp.get_column_config("PR"),
    )


if __name__ == "__main__":
    main()
