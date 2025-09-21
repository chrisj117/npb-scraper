"""Home page for multiple dashboards in Streamlit"""

import streamlit as st


def main():
    """Home page that provides descriptions of stats offered"""

    st.set_page_config(layout="centered")
    st.title("Yakyu Cosmopolitan Dashboard")

    st.write(
        "Welcome to the Yakyu Cosmopolitan Dashboard, your hub for up-to-date Nippon Professional Baseball stats. Batting and pitching stats are updated daily while fielding stats refresh about twice a month."
    )
    st.header("Team Overview")
    st.write(
        "Each team's primary lineup, rotation, and bullpen, plus top bench players. Starting position players are selected by defensive innings, bench players by plate appearances, starting pitchers by innings pitched, and relievers by saves and holds."
    )
    st.header("Player Percentiles")
    st.write(
        "Interactive bar graphs to compare players across key stats to the rest of the league, with filters for plate appearance and innings pitched minimums. Higher percentiles indicate stronger performance."
    )
    st.header("Sortable Stats")
    st.write(
        "Complete stat tables with filters make it easy to sort, compare, and explore players across batting, pitching, and fielding."
    )
    st.write("Thank you for visiting!")


if __name__ == "__main__":
    main()
