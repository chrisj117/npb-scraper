"""Sets up Streamlit dashboard pages"""

import streamlit as st


def main():
    """Main navigational driver for the Streamlit app"""

    st.set_page_config(page_title="YC Dashboard", page_icon="⚾")
    st.logo(st.secrets["logo_link"])

    dashboard = [
        st.Page("pages/home.py", title="Home"),
        st.Page("pages/team_overview.py", title="Team Overview"),
        st.Page("pages/batter_percentiles.py", title="Batter Percentiles"),
        st.Page("pages/pitcher_percentiles.py", title="Pitcher Percentiles"),
        st.Page("pages/npb_standings_scores.py", title="Standings & Scores"),
    ]

    npb_pages = [
        st.Page("pages/npb_player_batting.py", title="Player Batting"),
        st.Page("pages/npb_player_pitching.py", title="Player Pitching"),
        st.Page("pages/npb_player_fielding.py", title="Player Fielding"),
        st.Page("pages/npb_team_bat_stats.py", title="Team Batting"),
        st.Page("pages/npb_team_pitch_stats.py", title="Team Pitching"),
        st.Page("pages/npb_team_fielding.py", title="Team Fielding"),
        st.Page("pages/npb_team_summary.py", title="Team Summary"),
    ]

    pg = st.navigation(
        {
            "⭐ Main Pages": dashboard,
            "⚾ NPB Statistics": npb_pages,
        }
    )
    pg.run()

    # Footer
    st.caption("[Yakyu Cosmopolitan](https://www.yakyucosmo.com/)")


if __name__ == "__main__":
    main()
