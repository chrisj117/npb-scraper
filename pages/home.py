"""Home page for multiple dashboards in Streamlit"""

import streamlit as st


def main():
    """Home page that provides descriptions of stats offered"""

    st.set_page_config(layout="centered", initial_sidebar_state=200)

    st.title("Yakyu Cosmopolitan's NPB Dashboard 🇯🇵⚾", text_alignment="center")
    st.write(
        "Welcome to the Yakyu Cosmopolitan Dashboard, your home for up-to-date Nippon Professional Baseball statistics. Data is updated daily throughout the season."
    )
    st.header("Team Overview 📋")
    st.write(
        "View each team's primary lineup, starting rotation, bullpen, and top bench players. Starting position players are selected by defensive innings, bench players by plate appearances, starting pitchers by innings pitched, and relievers by saves and holds. Percentile colors are calculated separately within each section."
    )
    st.header("Career Overview 👤")
    st.write(
        "Explore biographical information and career statistics for NPB players across a wide range of categories. Select different metrics to track performance trends over time. The database includes players who appeared in NPB from 2016-2025, though some career totals may be incomplete."
    )
    st.header("Player Percentiles 📊")
    st.write(
        "Compare players with the rest of the league through interactive percentile charts covering key batting and pitching metrics. Plate appearance and innings pitched filters allow you to set your own qualification thresholds. Higher percentiles generally represent stronger performance."
    )
    st.header("Standings & Scores 🔢")
    st.write(
        "View the latest Central and Pacific standings, latest scores from around NPB, home/road splits, and head-to-head records."
    )
    st.header("Leaders 👑")
    st.write(
        "View NPB’s top performers across key batting, pitching, and fielding categories. Quickly compare league leaders and see which players stand out in both traditional and advanced statistics."
    )
    st.header("Sortable Stats 🔎")
    st.write(
        "Sort, filter, and compare comprehensive batting, pitching, and fielding tables with percentile-based coloring that makes standout performances easy to identify. Customize the minimum playing-time requirements to quickly find league leaders and explore statistical trends."
    )
    st.info(
        "Thank you for visiting! For exclusive data and development updates, please consider supporting Yakyu Cosmopolitan on [Patreon](https://www.patreon.com/c/baseballcosmo) for as little as $1 per month! Your contribution helps keep this app free."
    )

    st.iframe(
        "https://www.google.com/maps/d/embed?mid=1ZHEgyoTb730mB6rCF9lueotXFzUXFaU&ehbc=2E312F",
        height=500,
    )


if __name__ == "__main__":
    main()
