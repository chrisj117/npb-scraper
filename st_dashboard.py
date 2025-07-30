"""Sets up Streamlit dashboard pages"""

import streamlit as st


def main():
    """Main navigational driver for the Streamlit app"""

    st.set_page_config(page_title="YC Dashboard", page_icon="⚾")

    dashboard = [
        st.Page("pages/home.py", title="Home"),
        st.Page("pages/team_overview.py", title="Team Overview"),
        st.Page("pages/batter_percentiles.py", title="Batter Percentiles"),
        st.Page("pages/pitcher_percentiles.py", title="Pitcher Percentiles"),
    ]

    pg = st.navigation(
        {
            "⭐ Main Pages": dashboard,
        }
    )
    pg.run()

    # Footer
    st.caption("[Yakyu Cosmopolitan](https://www.yakyucosmo.com/)")


if __name__ == "__main__":
    main()
