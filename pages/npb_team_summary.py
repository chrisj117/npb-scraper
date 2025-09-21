"""Displays NPB team summary data with Streamlit"""

import pages.helper as hp
import streamlit as st


def main():
    """
    Main entry point for the Streamlit NPB team summary dashboard.

    Loads team summary statistics from GitHub. Formats team summary statistics
    for display. Shows the resulting team data in a Streamlit dataframe.

    Returns:
        None
    """
    st.set_page_config(layout="wide")
    display_df = hp.load_csv(
        "https://raw.githubusercontent.com/chrisj117/npb-scraper/refs/heads/"
        + "master/stats/2025/streamlit_src/2025TeamSummaryFinalR.csv"
    )
    display_df = hp.convert_pct_cols_to_float(display_df)
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        row_height=25,
        column_config=hp.get_column_config("team_summary"),
    )


if __name__ == "__main__":
    main()
