"""Sets up Streamlit dashboard pages"""

import streamlit as st


def main():
    """Main navigational driver for the Streamlit app"""

    st.set_page_config(page_title="YC Dashboard", page_icon="⚾")

    pages = [
        st.Page("pages/home.py", title="Home"),
        st.Page("pages/team_dashboard.py", title="Team Dashboard"),
        st.Page("pages/batter_percentiles.py", title="Batter Percentiles"),
        st.Page("pages/pitcher_percentiles.py", title="Pitcher Percentiles"),
    ]

    pg = st.navigation(pages)
    pg.run()


if __name__ == "__main__":
    main()
