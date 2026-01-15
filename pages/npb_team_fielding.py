"""Displays NPB team fielding data with Streamlit"""

import pages.helper as hp
import streamlit as st


def main():
    """
    Main entry point for the Streamlit NPB team fielding dashboard.

    Loads team fielding statistics from GitHub. Provides interactive filters
    for league, team, and statistic columns. Applies user-selected filters and
    formats key fielding statistics for display. Shows the resulting fielding
    data in a Streamlit dataframe.

    Returns:
        None
    """
    st.set_page_config(layout="wide")
    display_df = hp.load_csv(st.secrets["2025TeamFieldingFinalR_link"])

    # Split filters away from dataframe
    with st.container(border=True):
        # Smaller filters split by cols, larger filters receive exclusive cols
        r1c1, r1c2 = st.columns([1, 9], vertical_alignment="center")

        with r1c1:
            user_league = hp.create_league_filter(mode="npb")
        with r1c2:
            user_team = hp.create_team_filter(mode="npb")
        user_cols = hp.create_stat_cols_filter(display_df, "team_field")

        # Sorting options
        user_sort_col, user_sort_asc = hp.create_sort_filter(
            user_cols, mode="field"
        )

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

    # Display dataframe
    st.dataframe(
        display_df[user_cols].style.highlight_between(
            color="#F8F9FB", subset=user_sort_col, axis="columns"
        ),
        width='stretch',
        row_height=25,
        hide_index=False,
        column_config=hp.get_column_config("fielding"),
    )


if __name__ == "__main__":
    main()
