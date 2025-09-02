# **NPB Scraper**

This project scrapes and organizes NPB (Nippon Professional Baseball) and Farm League baseball statistics, then facilitates viewing the statistics via Streamlit.

Rather than running this locally, it is highly suggested to visit the following links to view the latest statistics as intended:
- https://www.yakyucosmo.com/ provides most stats
- https://yakyucosmo.streamlit.app/ provides a supplementary dashboard

## **Introduction**

There are two main parts to the project:
- **npb_scrape.py and the .csv files in /input/**
  - This component scrapes from various sources, then organizes the statistics into .csv files that are uploaded to https://www.yakyucosmo.com/
  - Input files are persistent and separated by year to utilize the most accurate FIP constants, park factors, roster data, name translations, fielding data sources, and team URLs
    - As of now, input files must be periodically updated manually
  - Files in /stats/ are overwritten every run
    - A basic text view of the statistics are provided by the files in /stats/$YEAR/alt/ to assist in local debugging
    - Final .csv files *without* HTML formatting are in /stats/$YEAR/streamlit_src/
  - When running locally, users can request a .zip archive of /stats/$YEAR/, but the .zip files in the repository are <ins>not</ins> updated daily
- **st_dashboard.py and the Python files in /pages/**
  - This component supplies more statistics and a convenient view of the generated statistics from files in /stats/$YEAR/streamlit_src/
  - Alongside linting and unit testing, GitHub Actions are responsible for daily updates of the statistics utilized on the Streamlit dashboard
    - **Consequently, the Streamlit dashboard loads the statistics from _this repository_ rather than any files generated locally**
   
To summarize, npb_scrape.py *generates* all statistics used by https://www.yakyucosmo.com/ and the Streamlit dashboard, while the Streamlit dashboard *reorganizes* the outputted statistics.

## **Authors and Acknowledgment**

This project was developed by **[Christian Johnson](https://github.com/chrisj117)**.

Additional contributors include:
- **[Yuri Karasawa](https://www.yakyucosmo.com/)** - Main co-contributor and maintainer of https://www.yakyucosmo.com/
- **[ぼーの (Bouno)](https://bo-no05.hatenadiary.org/)** - Source for all fielding statistics
- **[Ramos & Ramos](https://ramos-ramos.github.io/)** - Source for advanced pitching data
