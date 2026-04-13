"""Displays NPB team summary data with Streamlit"""

from datetime import datetime
import streamlit as st
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

    display_df = hp.convert_pct_cols_to_float(display_df)

    # Apply sorting and reset index (must be after convert_pct_cols_to_float())
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
    st.dataframe(
        display_df.style.apply(
            hp.color_by_percentile, axis=0, args=(pct_cols, invert_pct_cols)
        ).apply(hp.color_by_team, axis=0),
        width="stretch",
        hide_index=True,
        row_height=25,
        column_config=hp.get_column_config("team_summary"),
    )


if __name__ == "__main__":
    main()
