"""Scrapes NPB and Farm League statistics from npb.jp"""

from time import sleep
from random import randint
from datetime import datetime
from urllib.error import HTTPError, URLError
import os
import sys
import shutil
import tempfile
import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup


def main():
    """The main function for the NPB/Farm League Statistic Scraper.

    This function orchestrates the scraping, processing, and output of baseball
    statistics from the NPB (Nippon Professional Baseball) and Farm League
    websites. It handles user input, directory setup, file checks, and the
    execution of various scraping and data organization tasks.

    Workflow:
    1. Initializes the directory structure for storing scraped data.
    2. Validates the presence of required input files.
    3. Processes command-line arguments to determine the year to scrape
       and bypasses user input if arguments are provided.
    4. Prompts the user for input if no command-line arguments are given,
       allowing for manual control over scraping and data organization.
    5. Scrapes and organizes statistics for regular season and farm league
       games, including batting, pitching, fielding, standings, and daily
       scores.
    6. Optionally zips the output files for easier distribution.

    Returns:
        int:
            - -1 if an error occurs.
            - 0 if the program completes successfully.
            - 1 if the program completes successfully with user input."""
    print("NPB/Farm League Statistic Scraper")
    # Open the directory to store the scraped stat csv files
    rel_dir = os.path.dirname(__file__)
    stats_dir = os.path.join(rel_dir, "stats")
    if not os.path.exists(stats_dir):
        os.mkdir(stats_dir)

    # Check for scrape_year command line arg
    if len(sys.argv) == 2:
        print("ARGUMENTS DETECTED: " + str(sys.argv))
        # "A" scrapes current year, else scrape for given year
        if sys.argv[1] == "A":
            print("Setting year to: " + str(datetime.now().year))
            scrape_year = get_scrape_year(str(datetime.now().year))
        else:
            print("Setting year to: " + str(sys.argv[1]))
            scrape_year = get_scrape_year(sys.argv[1])
        print("\nProgram will scrape and create upload zip for given year.")
        # Bypass all user input functions and set flags for scraping
        arg_bypass = True
        npb_scrape_yn = "Y"
        farm_scrape_yn = "Y"
        stat_zip_yn = "Y"
    elif len(sys.argv) > 2:
        print("Too many arguments. Try passing in the desired stat year.")
        sys.exit("Exiting...")
    else:
        # Give user control if a year argument isn't passed in
        arg_bypass = False
        scrape_year = get_scrape_year()
        npb_scrape_yn = get_user_choice("R")
        farm_scrape_yn = get_user_choice("F")
        stat_zip_yn = get_user_choice("Z")

    # Check for input files (all except player_urls_fix.csv are required)
    if check_input_files(rel_dir, scrape_year) is True:
        input("Press Enter to exit. ")
        return -1

    # Create year directory
    year_dir = os.path.join(stats_dir, scrape_year)
    if not os.path.exists(year_dir):
        os.mkdir(year_dir)

    if npb_scrape_yn == "Y":
        # Scrape regular season batting and pitching URLs
        get_stats(year_dir, "BR", scrape_year)
        get_stats(year_dir, "PR", scrape_year)
        get_standings(year_dir, "C", scrape_year)
        get_standings(year_dir, "P", scrape_year)
        get_fielding(year_dir, "R", scrape_year)
    # NPB Daily Scores (only executes on current year)
    if scrape_year == str(datetime.now().year):
        if npb_scrape_yn == "Y":
            get_daily_scores(year_dir, "R", scrape_year)
        npb_daily_scores = DailyScoresData(
            stats_dir, year_dir, "R", scrape_year
        )
        npb_daily_scores.output_final()
    # NPB Individual Fielding
    # NOTE: fielding must be organized before any player stats to obtain player
    # positions
    npb_fielding = FieldingData(stats_dir, year_dir, "R", scrape_year)
    # NPB Team Fielding
    npb_team_fielding = TeamFieldingData(
        npb_fielding.df, stats_dir, year_dir, "R", scrape_year
    )
    # NPB Standings
    # NOTE: standings must be organized before any player stats to calculate
    # correct IP/PA drop consts
    central_standings = StandingsData(stats_dir, year_dir, "C", scrape_year)
    pacific_standings = StandingsData(stats_dir, year_dir, "P", scrape_year)
    # NPB Player stats
    npb_bat_player_stats = PlayerData(stats_dir, year_dir, "BR", scrape_year)
    npb_pitch_player_stats = PlayerData(stats_dir, year_dir, "PR", scrape_year)
    # Adding positions to batting stats
    npb_bat_player_stats.append_positions(
        npb_fielding.df, npb_pitch_player_stats.df
    )
    # NPB Team stats
    npb_bat_team_stats = TeamData(
        npb_bat_player_stats.df, stats_dir, year_dir, "BR", scrape_year
    )
    npb_pitch_team_stats = TeamData(
        npb_pitch_player_stats.df, stats_dir, year_dir, "PR", scrape_year
    )
    # NPB team summary
    npb_team_summary = TeamSummaryData(
        npb_team_fielding.df,
        central_standings.df,
        pacific_standings.df,
        npb_bat_team_stats.df,
        npb_pitch_team_stats.df,
        stats_dir,
        year_dir,
        "R",
        scrape_year,
    )
    # NPB output
    npb_bat_player_stats.output_final()
    npb_pitch_player_stats.output_final()
    npb_bat_team_stats.output_final()
    npb_pitch_team_stats.output_final()
    central_standings.output_final(
        npb_bat_team_stats.df, npb_pitch_team_stats.df
    )
    pacific_standings.output_final(
        npb_bat_team_stats.df, npb_pitch_team_stats.df
    )
    npb_fielding.output_final()
    npb_team_fielding.output_final()
    npb_team_summary.output_final()
    print("Regular season statistics finished!\n")

    if farm_scrape_yn == "Y":
        get_stats(year_dir, "BF", scrape_year)
        get_stats(year_dir, "PF", scrape_year)
        get_standings(year_dir, "E", scrape_year)
        get_standings(year_dir, "W", scrape_year)
        get_fielding(year_dir, "F", scrape_year)
    # Farm Fielding
    farm_fielding = FieldingData(stats_dir, year_dir, "F", scrape_year)
    # NPB Team Fielding
    farm_team_fielding = TeamFieldingData(
        farm_fielding.df, stats_dir, year_dir, "F", scrape_year
    )
    # Farm Standings
    eastern_standings = StandingsData(stats_dir, year_dir, "E", scrape_year)
    western_standings = StandingsData(stats_dir, year_dir, "W", scrape_year)
    # Farm Player stats
    farm_bat_player_stats = PlayerData(stats_dir, year_dir, "BF", scrape_year)
    farm_pitch_player_stats = PlayerData(
        stats_dir, year_dir, "PF", scrape_year
    )
    # Adding positions to batting stats
    farm_bat_player_stats.append_positions(
        farm_fielding.df, farm_pitch_player_stats.df
    )
    # Farm Team stats
    farm_bat_team_stats = TeamData(
        farm_bat_player_stats.df, stats_dir, year_dir, "BF", scrape_year
    )
    farm_pitch_team_stats = TeamData(
        farm_pitch_player_stats.df, stats_dir, year_dir, "PF", scrape_year
    )
    # Farm output
    farm_bat_player_stats.output_final()
    farm_pitch_player_stats.output_final()
    farm_bat_team_stats.output_final()
    farm_pitch_team_stats.output_final()
    eastern_standings.output_final(
        farm_bat_team_stats.df, farm_pitch_team_stats.df
    )
    western_standings.output_final(
        farm_bat_team_stats.df, farm_pitch_team_stats.df
    )
    farm_fielding.output_final()
    farm_team_fielding.output_final()
    print("Farm statistics finished!\n")

    # Make upload zips for manual uploads
    if stat_zip_yn == "Y":
        make_zip(year_dir, "S", scrape_year)

    if arg_bypass is False:
        input("Press Enter to exit. ")
        return 1
    return 0


class Stats:
    """Parent class Stats variables:
    stats_dir (string): The dir that holds all year stats and player URL file
    suffix (string): Indicates league or farm/NPB reg season stats
    year (string): The year that the stats will cover
    year_dir (string):The directory to store relevant year statistics

    OOP hierarchy:
    stats (stats_dir, year_dir, suffix, year)
        - individual stats (stats_dir, suffix, year)
        - team stats (player_df, stats_dir, suffix, year)
        - standings stats (stats_dir, suffix, year)

    Purpose: keeps dataframes in memory to pass around for other functions
    (I.E. IP/PA drop const calculations and standingsNewStats()), stat
    organization for Final and Alt files"""

    def __init__(self, stats_dir, year_dir, suffix, year):
        self.stats_dir = stats_dir
        self.suffix = suffix
        self.year = year
        self.year_dir = year_dir
        self.df = pd.DataFrame()

    def __str__(self):
        """Outputs the Alt view of the associated dataframe (no HTML team or
        player names, no csv formatting, shows entire df instead of only
        Leaders if applicable)"""
        return self.df.to_string()

    def get_csv(self):
        """Outputs the csv of the associated dataframe (no HTML team or
        player names shows entire df instead of only Leaders if applicable)"""
        return self.df.to_csv()


class PlayerData(Stats):
    """A class to handle individual player statistics for NPB and Farm League.

    This class extends the `Stats` class and is responsible for organizing,
    processing, and outputting individual player statistics for batting and
    pitching. It reads raw CSV files, calculates additional statistics, and
    formats the data for final output.

    Attributes:
        df (pandas.DataFrame): Holds an entire league's individual batting or
            pitching statistics.
        stats_dir (str): The directory that holds all year stats and player
            URL files.
        year_dir (str): The directory to store relevant year statistics.
        suffix (str): Indicates the type of statistics (e.g., "BR" for regular
            season batting, "PR" for regular season pitching).
        year (str): The year that the statistics cover.

    Methods:
        output_final():
            Outputs the final organized statistics to CSV files for upload.
        org_pitch():
            Organizes raw pitching statistics and calculates additional
            metrics.
        org_bat():
            Organizes raw batting statistics and calculates additional metrics.
        get_team_games():
            Combines team games played into a single DataFrame for IP/PA
            calculations.
        append_positions(field_df, pitch_df):
            Adds the primary position of a player to the player DataFrame."""

    def __init__(self, stats_dir, year_dir, suffix, year):
        super().__init__(stats_dir, year_dir, suffix, year)
        # Initialize data frame to store stats
        self.df = pd.read_csv(
            self.year_dir + "/raw/" + year + "StatsRaw" + suffix + ".csv"
        )
        # Modify df for correct stats
        if self.suffix in ("BF", "BR"):
            self.org_bat()
        elif self.suffix in ("PF", "PR"):
            self.org_pitch()

    def output_final(self):
        """Outputs final files for upload using the filtered and organized
        stat dataframes (NOTE: IP and PA drop constants are determined in this
        function)"""
        # Make dir that will store alt views of the dataframes
        alt_dir = os.path.join(self.year_dir, "alt")
        # Make dirs that will store files uploaded to yakyucosmo.com
        upload_dir = self.year_dir
        if self.suffix in ("PR", "BR"):
            upload_dir = os.path.join(self.year_dir, "npb")
        elif self.suffix in ("PF", "BF"):
            upload_dir = os.path.join(self.year_dir, "farm")

        # For batting, remove all players with PA <= 0
        if self.suffix in ("BF", "BR"):
            self.df = self.df.drop(self.df[self.df.PA == 0].index)
        # Print organized dataframe to file
        alt_filename = self.year + "AltView" + self.suffix + ".csv"
        alt_filename = store_dataframe(self.df, alt_dir, alt_filename, "alt")

        # Store df without HTML for streamlit
        st_dir = os.path.join(self.year_dir, "streamlit_src")
        st_filename = self.year + "StatsFinal" + self.suffix + ".csv"
        st_filename = store_dataframe(self.df, st_dir, st_filename, "csv")

        # Add blank Rank column for Wordpress table counter
        self.df["Rank"] = ""
        move_col = self.df.pop("Rank")
        self.df.insert(0, "Rank", move_col)
        # Make deep copy of original df to avoid HTML in df's team/player names
        final_df = self.df.copy()
        # Convert player/team names to HTML that contains appropriate URLs
        if int(self.year) == datetime.now().year:
            final_df = convert_player_to_html(final_df, self.suffix, self.year)
        final_df = convert_team_to_html(final_df, self.year, "Abb")
        # Print final file with all players
        final_filename = self.year + "StatsFinal" + self.suffix + ".csv"
        final_filename = store_dataframe(
            final_df, upload_dir, final_filename, "csv"
        )

        # Make deep copy again for leader's file
        leader_df = self.df.copy()
        # Get df with number of games played by each team for IP/PA drop consts
        game_df = self.get_team_games()
        # Add new column (called 'GTeam') for team's games played
        leader_df = leader_df.merge(
            game_df, on="Team", suffixes=(None, "Team")
        )

        # Leader file output
        if self.suffix in ("PR", "PF"):
            # Drop all players below the IP/PA threshold
            if self.suffix == "PF":
                leader_df = leader_df.drop(
                    leader_df[leader_df.IP < (leader_df["GTeam"] * 0.8)].index
                )
            else:
                leader_df = leader_df.drop(
                    leader_df[leader_df.IP < leader_df["GTeam"]].index
                )
            # Drop temp GTeamIP column
            leader_df.drop(["GTeam"], axis=1, inplace=True)

            # Convert player/team names to HTML that contains appropriate URLs
            if int(self.year) == datetime.now().year:
                leader_df = convert_player_to_html(
                    leader_df, self.suffix, self.year
                )
            leader_df = convert_team_to_html(leader_df, self.year, "Abb")
            # Output leader file as a csv
            leader_filename = self.year + "Leaders" + self.suffix + ".csv"
            leader_filename = store_dataframe(
                leader_df, upload_dir, leader_filename, "csv"
            )
            # Store df without HTML for streamlit
            st_filename = self.year + "Leaders" + self.suffix + ".csv"
            st_filename = store_dataframe(self.df, st_dir, st_filename, "csv")

            print(
                "The pitching leaders file will be stored in: "
                + leader_filename
            )
            print(
                "An alternative view of the pitching results will be stored "
                "in: " + alt_filename
            )
            print(
                "The final organized pitching results will be stored in: "
                + final_filename
            )

        # Leader file is calculated differently for batters
        elif self.suffix in ("BR", "BF"):
            # Drop all players below the IP/PA threshold (PA gets rounded down)
            if self.suffix == "BF":
                leader_df = leader_df.drop(
                    leader_df[
                        leader_df.PA < np.floor((leader_df["GTeam"] * 2.7))
                    ].index
                )
            else:
                leader_df = leader_df.drop(
                    leader_df[
                        leader_df.PA < np.floor((leader_df["GTeam"] * 3.1))
                    ].index
                )
            # Drop temp GTeamIP column
            leader_df.drop(["GTeam"], axis=1, inplace=True)

            # Convert player/team names to HTML that contains appropriate URLs
            if int(self.year) == datetime.now().year:
                leader_df = convert_player_to_html(
                    leader_df, self.suffix, self.year
                )
            leader_df = convert_team_to_html(leader_df, self.year, "Abb")
            # Output leader file as a csv
            leader_filename = self.year + "Leaders" + self.suffix + ".csv"
            leader_filename = store_dataframe(
                leader_df, upload_dir, leader_filename, "csv"
            )
            # Store df without HTML for streamlit
            st_filename = self.year + "Leaders" + self.suffix + ".csv"
            st_filename = store_dataframe(self.df, st_dir, st_filename, "csv")

            print(
                "The batting leaders file will be stored in: "
                + leader_filename
            )
            print(
                "An alternative view of the batting results will be stored "
                "in: " + alt_filename
            )
            print(
                "The final organized batting results will be stored in: "
                + final_filename
            )

    def org_pitch(self):
        """Organize the raw pitching stat csv and add new stats"""
        # Some IP entries can be '+', replace with 0 for conversions and
        # calculations
        self.df["IP"] = self.df["IP"].astype(str).replace("+", "0")
        # Some ERA entries can be '----', replace with 0 and convert to float
        # for calculations
        self.df["ERA"] = self.df["ERA"].astype(str).replace("----", "inf")
        self.df["ERA"] = self.df["ERA"].astype(float)
        # Convert all NaN to 0 (as floats)
        if self.suffix == "PR":
            self.df.iloc[:, 11] = self.df.iloc[:, 11].fillna(0)
            self.df.iloc[:, 11] = self.df.iloc[:, 11].astype(float)
            # Combine the incorrectly split IP stat columns
            self.df["IP"] = self.df["IP"].astype(float)
            self.df["IP"] = self.df["IP"] + self.df.iloc[:, 11]
            # Drop unnamed column that held IP column decimals
            self.df.drop(self.df.columns[11], axis=1, inplace=True)
        # Farm stats are missing HLD column, so bad format column is #10
        elif self.suffix == "PF":
            self.df.iloc[:, 10] = self.df.iloc[:, 10].fillna(0)
            self.df.iloc[:, 10] = self.df.iloc[:, 10].astype(float)
            self.df["IP"] = self.df["IP"].astype(float)
            self.df["IP"] = self.df["IP"] + self.df.iloc[:, 10]
            self.df.drop(self.df.columns[10], axis=1, inplace=True)
        # Drop last, BK, and PCT columns
        self.df.drop(
            self.df.columns[len(self.df.columns) - 1], axis=1, inplace=True
        )
        self.df.drop(["BK", "PCT"], axis=1, inplace=True)
        # IP ".0 .1 .2" fix
        self.df["IP"] = convert_ip_column_in(self.df, "IP")

        # Counting stat column totals
        total_era = 9 * (self.df["ER"].sum() / self.df["IP"].sum())
        total_fip = (
            (
                13 * self.df["HR"].sum()
                + 3 * (self.df["BB"].sum() + self.df["HB"].sum())
                - 2 * self.df["SO"].sum()
            )
            / self.df["IP"].sum()
        ) + select_fip_const(self.suffix, self.year)
        total_kwera = 4.80 - (
            10
            * (
                (self.df["SO"].sum() - self.df["BB"].sum())
                / self.df["BF"].sum()
            )
        )

        # Individual statistic calculations
        self.df["kwERA"] = 4.80 - (
            10 * ((self.df["SO"] - self.df["BB"]) / self.df["BF"])
        )
        self.df = select_park_factor(self.df, self.suffix, self.year)
        self.df["ERA+"] = 100 * (
            (total_era * self.df["ParkF"]) / self.df["ERA"]
        )
        self.df["ERA+"] = self.df["ERA+"].astype(str).replace("inf", "999")
        self.df["ERA+"] = self.df["ERA+"].astype(float)
        self.df["K%"] = self.df["SO"] / self.df["BF"]
        self.df["BB%"] = self.df["BB"] / self.df["BF"]
        self.df["K-BB%"] = self.df["K%"] - self.df["BB%"]
        self.df["FIP"] = (
            (
                13 * self.df["HR"]
                + 3 * (self.df["BB"] + self.df["HB"])
                - 2 * self.df["SO"]
            )
            / self.df["IP"]
        ) + select_fip_const(self.suffix, self.year)
        self.df["FIP-"] = 100 * (
            self.df["FIP"] / (total_fip * self.df["ParkF"])
        )
        self.df["WHIP"] = (self.df["BB"] + self.df["H"]) / self.df["IP"]
        self.df["HR%"] = self.df["HR"] / self.df["BF"]
        self.df["kwERA-"] = 100 * (self.df["kwERA"] / (total_kwera))
        self.df["Diff"] = self.df["ERA"] - self.df["FIP"]

        # Data cleaning/reformatting
        # Remove temp Park Factor column
        self.df.drop("ParkF", axis=1, inplace=True)
        # "Mercedes Cristopher Crisostomo" name shortening to "Mercedes CC"
        self.df["Pitcher"] = (
            self.df["Pitcher"]
            .astype(str)
            .replace("Mercedes Cristopher Crisostomo", "Mercedes CC")
        )
        # Number formatting
        format_maps = {
            "BB%": "{:.1%}",
            "K%": "{:.1%}",
            "K-BB%": "{:.1%}",
            "HR%": "{:.1%}",
            "Diff": "{:.2f}",
            "FIP": "{:.2f}",
            "WHIP": "{:.2f}",
            "kwERA": "{:.2f}",
            "ERA": "{:.2f}",
            "kwERA-": "{:.0f}",
            "ERA+": "{:.0f}",
            "FIP-": "{:.0f}",
        }
        for key, value in format_maps.items():
            self.df[key] = self.df[key].apply(value.format)

        # Replace infs/nans in select stat cols
        self.df["ERA"] = self.df["ERA"].astype(str).replace("inf", "")
        self.df["FIP"] = self.df["FIP"].astype(str).replace("inf", "")
        self.df["FIP-"] = self.df["FIP-"].astype(str).replace("inf", "")
        self.df["WHIP"] = self.df["WHIP"].astype(str).replace("inf", "")
        self.df["Diff"] = self.df["Diff"].astype(str).replace("nan", "")
        # Reordering columns
        col_order = [
            "Pitcher",
            "G",
            "W",
            "L",
            "SV",
            "HLD",
            "CG",
            "SHO",
            "BF",
            "IP",
            "H",
            "HR",
            "SO",
            "BB",
            "IBB",
            "HB",
            "WP",
            "R",
            "ER",
            "ERA",
            "FIP",
            "kwERA",
            "WHIP",
            "ERA+",
            "FIP-",
            "kwERA-",
            "Diff",
            "HR%",
            "K%",
            "BB%",
            "K-BB%",
            "Team",
        ]
        # Reordering for age and throwing arm if correct year
        if int(self.year) == datetime.now().year:
            self.df = add_roster_data(self.df, self.suffix, self.year)
            col_order.insert(-1, "Age")
            col_order.insert(-1, "T")
        if self.suffix == "PF":
            col_order.remove("HLD")
        self.df = self.df[col_order]
        # Changing .33 to .1 and .66 to .2 in the IP column
        self.df["IP"] = convert_ip_column_out(self.df, "IP")
        self.df = select_league(self.df, self.suffix)

    def org_bat(self):
        """Organize the raw batting stat csv and add additional stats"""
        # Drop last column
        self.df.drop(
            self.df.columns[len(self.df.columns) - 1], axis=1, inplace=True
        )

        # Counting stat column totals used in other calculations
        total_obp = (
            self.df["H"].sum() + self.df["BB"].sum() + self.df["HP"].sum()
        ) / (
            self.df["AB"].sum()
            + self.df["BB"].sum()
            + self.df["HP"].sum()
            + self.df["SF"].sum()
        )
        total_slg = (
            (
                self.df["H"].sum()
                - self.df["2B"].sum()
                - self.df["3B"].sum()
                - self.df["HR"].sum()
            )
            + (2 * self.df["2B"].sum())
            + (3 * self.df["3B"].sum())
            + (4 * self.df["HR"].sum())
        ) / self.df["AB"].sum()

        # Individual statistic calculations
        self.df["OPS"] = self.df["SLG"] + self.df["OBP"]
        self.df = select_park_factor(self.df, self.suffix, self.year)
        self.df["OPS+"] = 100 * (
            (self.df["OBP"] / total_obp) + (self.df["SLG"] / total_slg) - 1
        )
        self.df["OPS+"] = self.df["OPS+"] / self.df["ParkF"]
        self.df["ISO"] = self.df["SLG"] - self.df["AVG"]
        self.df["K%"] = self.df["SO"] / self.df["PA"]
        self.df["BB%"] = self.df["BB"] / self.df["PA"]
        self.df["BB/K"] = self.df["BB"] / self.df["SO"]
        self.df["TTO%"] = (
            self.df["BB"] + self.df["SO"] + self.df["HR"]
        ) / self.df["PA"]
        self.df["BABIP"] = (self.df["H"] - self.df["HR"]) / (
            self.df["AB"] - self.df["SO"] - self.df["HR"] + self.df["SF"]
        )

        lg_single = (
            self.df["H"].sum()
            - self.df["2B"].sum()
            - self.df["3B"].sum()
            - self.df["HR"].sum()
        )
        pl_single = (
            self.df["H"] - self.df["2B"] - self.df["3B"] - self.df["HR"]
        )
        wsb_a = 0.17 * self.df["SB"] - 0.33 * self.df["CS"]
        wsb_b = (self.df["SB"].sum() * 0.17 + self.df["CS"].sum() * -0.33) / (
            lg_single
            + self.df["BB"].sum()
            + self.df["HP"].sum()
            - self.df["IBB"].sum()
        )
        wsb_c = pl_single + self.df["BB"] + self.df["HP"] - self.df["IBB"]
        self.df["wSB"] = wsb_a - wsb_b * wsb_c

        # Remove temp Park Factor column
        self.df.drop("ParkF", axis=1, inplace=True)
        # "Mercedes Cristopher Crisostomo" name shortening to "Mercedes CC"
        self.df["Player"] = (
            self.df["Player"]
            .astype(str)
            .replace("Mercedes Cristopher Crisostomo", "Mercedes CC")
        )
        # "Davis Jonathan" name changing to "Davis JD"
        self.df["Player"] = (
            self.df["Player"].astype(str).replace("Davis Jonathan", "Davis JD")
        )
        # Number formatting
        format_maps = {
            "BB%": "{:.1%}",
            "K%": "{:.1%}",
            "OPS+": "{:.0f}",
            "AVG": "{:.3f}",
            "OBP": "{:.3f}",
            "SLG": "{:.3f}",
            "OPS": "{:.3f}",
            "ISO": "{:.3f}",
            "BABIP": "{:.3f}",
            "BB/K": "{:.2f}",
            "TTO%": "{:.1%}",
            "wSB": "{:.1f}",
        }
        for key, value in format_maps.items():
            self.df[key] = self.df[key].apply(value.format)
        # Replace all NaN in BB/K, wOBA and BABIP with ''
        self.df["BB/K"] = self.df["BB/K"].astype(str)
        self.df["BB/K"] = self.df["BB/K"].str.replace("nan", "")
        self.df["BABIP"] = self.df["BABIP"].astype(str)
        self.df["BABIP"] = self.df["BABIP"].str.replace("nan", "")
        # Replace BB/K infs with '1.00' (same format as MLB website)
        self.df["BB/K"] = self.df["BB/K"].str.replace("inf", "1.00")
        # Add age, (temp) position, and throwing/batting arm columns
        self.df["Pos"] = np.nan
        col_order = [
            "Player",
            "G",
            "PA",
            "AB",
            "R",
            "H",
            "2B",
            "3B",
            "HR",
            "TB",
            "RBI",
            "SB",
            "CS",
            "SH",
            "SF",
            "SO",
            "BB",
            "IBB",
            "HP",
            "GDP",
            "AVG",
            "OBP",
            "SLG",
            "OPS",
            "OPS+",
            "ISO",
            "BABIP",
            "TTO%",
            "K%",
            "BB%",
            "BB/K",
            "wSB",
            "Pos",
            "Team",
        ]
        if int(self.year) == datetime.now().year:
            self.df = add_roster_data(self.df, self.suffix, self.year)
            col_order.insert(-2, "Age")
            col_order.insert(-1, "B")
        self.df = self.df[col_order]
        self.df = select_league(self.df, self.suffix)

    def get_team_games(self):
        """Combines Central and Pacific (NPB) or Eastern and Western (farm)
        team games played into a single dataframe

        Returns:
        ip_pa_df (pandas dataframe): A dataframe with 2 columns: team name and
        # of games that team has played"""
        # Make new raw const file in write mode (made in writeStandingsStats())
        const_dir = os.path.join(self.year_dir, "drop_const")
        if not os.path.exists(const_dir):
            os.mkdir(const_dir)

        # Read in the correct raw const files for reg season or farm
        # Regular season team,game files
        standings_file1 = ""
        standings_file2 = ""
        if self.suffix in ("BR", "PR"):
            standings_file1 = const_dir + "/" + self.year + "const_rawC.csv"
            standings_file2 = const_dir + "/" + self.year + "const_rawP.csv"
        # Farm team,game files
        if self.suffix in ("BF", "PF"):
            standings_file1 = const_dir + "/" + self.year + "const_rawW.csv"
            standings_file2 = const_dir + "/" + self.year + "const_rawE.csv"

        # Combine into 1 raw const df/file
        standings_df1 = pd.read_csv(standings_file1)
        standings_df2 = pd.read_csv(standings_file2)
        ip_pa_df = pd.concat([standings_df1, standings_df2])

        # DEBUG: this file should have all combined teams and games
        # new_csv_name = (const_dir + "/" + self.year + "Const" + self.suffix +
        # ".csv")
        # constFile = ip_pa_df.to_string(new_csv_name)
        return ip_pa_df

    def append_positions(self, field_df, pitch_df):
        """Adds the primary position of a player to the player dataframe

        Parameters:
        field_df (pandas dataframe): Holds an entire NPB league's fielding stats
        pitch_df (pandas dataframe): Holds an entire NPB league's individual
        pitching stats"""
        # Create a temp df with players as rows and all pos they play as cols
        pivot_df = field_df.pivot_table(
            index="Player",
            columns="Pos",
            values="Inn",
            aggfunc="sum",
            fill_value=0,
        )
        # Append team names to help differentiate players after pitching merge
        pivot_df = pd.merge(
            pivot_df,
            field_df[["Player", "Team"]].drop_duplicates(),
            on="Player",
            how="outer",
        )
        # Append IP for position 1 (pitchers) as a new column "1"
        pivot_df = pd.merge(
            pivot_df,
            pitch_df[["Pitcher", "IP", "Team"]].rename(
                columns={"Pitcher": "Player", "IP": "1"}
            ),
            on=["Player", "Team"],
            how="outer",
        )
        # Fill NaN values in all colums with 0 (if needed)
        pivot_df = pivot_df.fillna(0)
        # Get primary positions
        pivot_df["Pos"] = pivot_df.apply(assign_primary_or_utl, axis=1)
        # Extract only the player name, team, and primary_position:
        temp_primary_df = pivot_df[["Player", "Pos", "Team"]]
        # Then merge if needed:
        self.df = pd.merge(
            self.df, temp_primary_df, on=["Player", "Team"], how="left"
        )
        # Swap temp Pos with updated Pos, drop placeholder Pos, rename
        self.df["Pos_x"], self.df["Pos_y"] = self.df["Pos_y"], self.df["Pos_x"]
        self.df = self.df.drop("Pos_y", axis=1)
        self.df = self.df.rename(columns={"Pos_x": "Pos"})
        # NaN means player wasn't on fielding df and pitching df (N/A data) OR
        # was a pinch hitter
        self.df["Pos"] = self.df["Pos"].fillna("")


class TeamData(Stats):
    """A class to handle team statistics for NPB and Farm League.

    This class extends the `Stats` class and is responsible for organizing,
    processing, and outputting team statistics for batting and pitching. It
    aggregates individual player statistics to calculate team-level metrics
    and formats the data for final output.

    Attributes:
        player_df (pandas.DataFrame): Holds an entire league's individual
            batting or pitching statistics used to calculate team stats.
        stats_dir (str): The directory that holds all year stats and player
            URL files.
        year_dir (str): The directory to store relevant year statistics.
        suffix (str): Indicates the type of statistics (e.g., "BR" for regular
            season batting, "PR" for regular season pitching).
        year (str): The year that the statistics cover.
        df (pandas.DataFrame): Holds the aggregated team statistics.

    Methods:
        output_final():
            Outputs the final organized team statistics to CSV files for upload.
        org_team_bat():
            Aggregates individual player batting statistics to calculate team
            batting metrics.
        org_team_pitch():
            Aggregates individual player pitching statistics to calculate team
            pitching metrics."""

    def __init__(self, player_df, stats_dir, year_dir, suffix, year):
        """TeamData new variables:
        player_df (pandas dataframe): Holds an entire NPB league's individual
        batting/pitching stats"""
        super().__init__(stats_dir, year_dir, suffix, year)
        self.player_df = player_df.copy()
        # Initialize df for teams stats
        if self.suffix in ("BF", "BR"):
            self.org_team_bat()
        elif self.suffix in ("PF", "PR"):
            self.org_team_pitch()

    def output_final(self):
        """Outputs final files for upload using the team stat dataframes"""
        # Make dir that will store alt views of the dataframes
        alt_dir = os.path.join(self.year_dir, "alt")
        # Make dirs that will store files uploaded to yakyucosmo.com
        upload_dir = self.year_dir
        if self.suffix in ("PR", "BR"):
            upload_dir = os.path.join(self.year_dir, "npb")
        elif self.suffix in ("PF", "BF"):
            upload_dir = os.path.join(self.year_dir, "farm")

        # Print organized dataframe to file
        alt_filename = self.year + "TeamAlt" + self.suffix + ".csv"
        alt_filename = store_dataframe(self.df, alt_dir, alt_filename, "alt")

        # Store df without HTML for streamlit
        st_dir = os.path.join(self.year_dir, "streamlit_src")
        st_filename = self.year + "Team" + self.suffix + ".csv"
        st_filename = store_dataframe(self.df, st_dir, st_filename, "csv")

        # Add blank counter (#) column for Wordpress table counter
        self.df["#"] = ""
        move_col = self.df.pop("#")
        self.df.insert(0, "#", move_col)
        # Make output copy to avoid modifying original df
        final_df = self.df.copy()
        # Insert HTML code for team names
        final_df = convert_team_to_html(final_df, self.year, "Full")
        # Print output file for upload
        final_filename = self.year + "Team" + self.suffix + ".csv"
        final_filename = store_dataframe(
            final_df, upload_dir, final_filename, "csv"
        )

        # Pitching TeamAlt and Team file location outputs
        if self.suffix in ("PR", "PF"):
            print(
                "The final organized team pitching results will be stored "
                "in: " + final_filename
            )
            print(
                "An alternative view of team pitching results will be stored"
                "in: " + alt_filename
            )

        elif self.suffix in ("BR", "BF"):
            print(
                "The final organized team batting results will be stored "
                "in: " + final_filename
            )
            print(
                "An alternative view of team batting results will be stored "
                "in: " + alt_filename
            )

    def org_team_bat(self):
        """Outputs batting team stat files using the organized player stat
        dataframes"""
        # Initialize new row list with all possible teams
        row_arr = [
            "Hanshin Tigers",
            "Hiroshima Carp",
            "DeNA BayStars",
            "Yomiuri Giants",
            "Yakult Swallows",
            "Chunichi Dragons",
            "ORIX Buffaloes",
            "Lotte Marines",
            "SoftBank Hawks",
            "Rakuten Eagles",
            "Seibu Lions",
            "Nipponham Fighters",
        ]
        # 2024 and beyond farm has 2 new teams
        if self.suffix == "BF" and int(self.year) >= 2024:
            row_arr.extend(["Oisix Albirex", "HAYATE Ventures"])

        # Initialize list to hold team stats
        team_bat_list = []
        # Form team stat rows
        for team in row_arr:
            temp_stat_df = self.player_df[self.player_df.Team == team]
            temp_stat_df = temp_stat_df.apply(pd.to_numeric, errors="coerce")
            new_team_stat = [
                team,
                temp_stat_df["PA"].sum(),
                temp_stat_df["AB"].sum(),
                temp_stat_df["R"].sum(),
                temp_stat_df["H"].sum(),
                temp_stat_df["2B"].sum(),
                temp_stat_df["3B"].sum(),
                temp_stat_df["HR"].sum(),
                temp_stat_df["TB"].sum(),
                temp_stat_df["RBI"].sum(),
                temp_stat_df["SB"].sum(),
                temp_stat_df["CS"].sum(),
                temp_stat_df["SH"].sum(),
                temp_stat_df["SF"].sum(),
                temp_stat_df["SO"].sum(),
                temp_stat_df["BB"].sum(),
                temp_stat_df["IBB"].sum(),
                temp_stat_df["HP"].sum(),
                temp_stat_df["GDP"].sum(),
                # AVG
                temp_stat_df["H"].sum() / temp_stat_df["AB"].sum(),
            ]
            # Calculate OBP, SLG (needs calcs/totals of other stats)
            total_obp = (
                temp_stat_df["H"].sum()
                + temp_stat_df["BB"].sum()
                + temp_stat_df["HP"].sum()
            ) / (
                temp_stat_df["AB"].sum()
                + temp_stat_df["BB"].sum()
                + temp_stat_df["HP"].sum()
                + temp_stat_df["SF"].sum()
            )
            total_slg = (
                (
                    temp_stat_df["H"].sum()
                    - temp_stat_df["2B"].sum()
                    - temp_stat_df["3B"].sum()
                    - temp_stat_df["HR"].sum()
                )
                + (2 * temp_stat_df["2B"].sum())
                + (3 * temp_stat_df["3B"].sum())
                + (4 * temp_stat_df["HR"].sum())
            ) / temp_stat_df["AB"].sum()
            # Append calculated stats
            new_team_stat.append(total_obp)
            new_team_stat.append(total_slg)
            # OPS
            new_team_stat.append(total_slg + total_obp)
            # Append as a new team row in team_bat_list
            team_bat_list.append(new_team_stat)

        # Initialize dataframe and ensure stats are in numeric format
        col_init_arr = [
            "Team",
            "PA",
            "AB",
            "R",
            "H",
            "2B",
            "3B",
            "HR",
            "TB",
            "RBI",
            "SB",
            "CS",
            "SH",
            "SF",
            "SO",
            "BB",
            "IBB",
            "HP",
            "GDP",
            "AVG",
            "OBP",
            "SLG",
            "OPS",
        ]
        self.df = pd.DataFrame(team_bat_list, columns=col_init_arr)
        cols = self.df.columns.drop(["Team"])
        self.df[cols] = self.df[cols].apply(pd.to_numeric, errors="coerce")
        # Retrieve park factors for any remaining team stats (EX: OPS+)
        self.df = select_park_factor(self.df, self.suffix, self.year)

        # Calculate OPS+, ISO, K%, BB%, BB/K, TTO%, BABIP, wSB
        league_obp = (
            self.df["H"].sum() + self.df["BB"].sum() + self.df["HP"].sum()
        ) / (
            self.df["AB"].sum()
            + self.df["BB"].sum()
            + self.df["HP"].sum()
            + self.df["SF"].sum()
        )
        league_slg = (
            (
                self.df["H"].sum()
                - self.df["2B"].sum()
                - self.df["3B"].sum()
                - self.df["HR"].sum()
            )
            + (2 * self.df["2B"].sum())
            + (3 * self.df["3B"].sum())
            + (4 * self.df["HR"].sum())
        ) / self.df["AB"].sum()
        self.df["OPS+"] = (
            100
            * (
                (self.df["OBP"] / league_obp)
                + (self.df["SLG"] / league_slg)
                - 1
            )
        ) / self.df["ParkF"]
        self.df["ISO"] = self.df["SLG"] - self.df["AVG"]
        self.df["K%"] = self.df["SO"] / self.df["PA"]
        self.df["BB%"] = self.df["BB"] / self.df["PA"]
        self.df["BB/K"] = self.df["BB"] / self.df["SO"]
        self.df["TTO%"] = (
            self.df["BB"] + self.df["SO"] + self.df["HR"]
        ) / self.df["PA"]
        self.df["BABIP"] = (self.df["H"] - self.df["HR"]) / (
            self.df["AB"] - self.df["SO"] - self.df["HR"] + self.df["SF"]
        )
        lg_single = (
            self.df["H"].sum()
            - self.df["2B"].sum()
            - self.df["3B"].sum()
            - self.df["HR"].sum()
        )
        team_single = (
            self.df["H"] - self.df["2B"] - self.df["3B"] - self.df["HR"]
        )
        wsb_a = 0.17 * self.df["SB"] - 0.33 * self.df["CS"]
        wsb_b = (self.df["SB"].sum() * 0.17 + self.df["CS"].sum() * -0.33) / (
            lg_single
            + self.df["BB"].sum()
            + self.df["HP"].sum()
            - self.df["IBB"].sum()
        )
        wsb_c = team_single + self.df["BB"] + self.df["HP"] - self.df["IBB"]
        self.df["wSB"] = wsb_a - wsb_b * wsb_c

        # Create "League Average" row after all stats have been calculated
        league_avg = self.df.mean(numeric_only=True)
        league_avg["Team"] = "League Average"
        # OPS+ league average should always be 100 regardless of actual avg
        league_avg["OPS+"] = 100
        # Recalculate stats that are based on league averages
        league_avg["OPS"] = league_slg + league_obp
        league_avg["AVG"] = self.df["H"].sum() / self.df["AB"].sum()
        league_avg["OBP"] = league_obp
        league_avg["SLG"] = league_slg
        league_avg["ISO"] = league_avg["SLG"] - league_avg["AVG"]
        league_avg["BABIP"] = (self.df["H"].sum() - self.df["HR"].sum()) / (
            self.df["AB"].sum()
            - self.df["SO"].sum()
            - self.df["HR"].sum()
            + self.df["SF"].sum()
        )
        league_avg["K%"] = self.df["SO"].sum() / self.df["PA"].sum()
        league_avg["BB%"] = self.df["BB"].sum() / self.df["PA"].sum()
        league_avg["BB/K"] = self.df["BB"].sum() / self.df["SO"].sum()
        self.df.loc[len(self.df)] = league_avg

        # Remove temp Park Factor column
        self.df.drop("ParkF", axis=1, inplace=True)
        # Number formatting
        format_maps = {
            "BB%": "{:.1%}",
            "K%": "{:.1%}",
            "AVG": "{:.3f}",
            "OBP": "{:.3f}",
            "SLG": "{:.3f}",
            "OPS": "{:.3f}",
            "ISO": "{:.3f}",
            "BB/K": "{:.2f}",
            "OPS+": "{:.0f}",
            "PA": "{:.0f}",
            "AB": "{:.0f}",
            "2B": "{:.0f}",
            "3B": "{:.0f}",
            "TB": "{:.0f}",
            "RBI": "{:.0f}",
            "SB": "{:.0f}",
            "CS": "{:.0f}",
            "SH": "{:.0f}",
            "SF": "{:.0f}",
            "HP": "{:.0f}",
            "GDP": "{:.0f}",
            "H": "{:.0f}",
            "HR": "{:.0f}",
            "SO": "{:.0f}",
            "BB": "{:.0f}",
            "IBB": "{:.0f}",
            "R": "{:.0f}",
            "TTO%": "{:.1%}",
            "BABIP": "{:.3f}",
            "wSB": "{:.1f}",
        }
        for key, value in format_maps.items():
            self.df[key] = self.df[key].apply(value.format)

        # Reorder columns
        col_order_arr = col_init_arr + [
            "OPS+",
            "ISO",
            "BABIP",
            "TTO%",
            "K%",
            "BB%",
            "BB/K",
            "wSB",
        ]
        self.df = self.df[col_order_arr]
        # Add "League" column
        self.df = select_league(self.df, self.suffix)

    def org_team_pitch(self):
        """Outputs pitching team stat files using the organized player stat
        dataframes"""
        # IP column ".1 .2 .3" calculation fix
        self.player_df["IP"] = convert_ip_column_in(self.player_df, "IP")
        # Initialize new row list with all possible teams
        row_arr = [
            "Hanshin Tigers",
            "Hiroshima Carp",
            "DeNA BayStars",
            "Yomiuri Giants",
            "Yakult Swallows",
            "Chunichi Dragons",
            "ORIX Buffaloes",
            "Lotte Marines",
            "SoftBank Hawks",
            "Rakuten Eagles",
            "Seibu Lions",
            "Nipponham Fighters",
        ]
        # 2024 and later farm has 2 new teams
        if self.suffix == "PF" and int(self.year) >= 2024:
            row_arr.extend(["Oisix Albirex", "HAYATE Ventures"])

        # Initialize list to hold team stats
        team_pitch_list = []
        # Form team stat rows and collect only COUNTING stats
        for team in row_arr:
            temp_stat_df = self.player_df[self.player_df.Team == team]
            temp_stat_df = temp_stat_df.apply(pd.to_numeric, errors="coerce")
            new_team_stat = [
                team,
                temp_stat_df["W"].sum(),
                temp_stat_df["L"].sum(),
                temp_stat_df["SV"].sum(),
                temp_stat_df["CG"].sum(),
                temp_stat_df["SHO"].sum(),
                temp_stat_df["BF"].sum(),
                temp_stat_df["IP"].sum(),
                temp_stat_df["H"].sum(),
                temp_stat_df["HR"].sum(),
                temp_stat_df["SO"].sum(),
                temp_stat_df["BB"].sum(),
                temp_stat_df["IBB"].sum(),
                temp_stat_df["HB"].sum(),
                temp_stat_df["WP"].sum(),
                temp_stat_df["R"].sum(),
                temp_stat_df["ER"].sum(),
            ]
            if self.suffix != "PF":
                new_team_stat.insert(4, temp_stat_df["HLD"].sum())
            team_pitch_list.append(new_team_stat)

        # Initialize new team stat dataframe
        col_init_arr = [
            "Team",
            "W",
            "L",
            "SV",
            "CG",
            "SHO",
            "BF",
            "IP",
            "H",
            "HR",
            "SO",
            "BB",
            "IBB",
            "HB",
            "WP",
            "R",
            "ER",
        ]
        # All other pitching stats have HLD column
        if self.suffix != "PF":
            col_init_arr.insert(4, "HLD")
        self.df = pd.DataFrame(team_pitch_list, columns=col_init_arr)
        # Create park factor col to use for any remaining team stats
        self.df = select_park_factor(self.df, self.suffix, self.year)

        # Required league totals not in team df
        total_ip = self.player_df["IP"].sum()
        total_hr = self.player_df["HR"].sum()
        total_so = self.player_df["SO"].sum()
        total_bb = self.player_df["BB"].sum()
        total_hb = self.player_df["HB"].sum()
        total_er = self.player_df["ER"].sum()
        total_bf = self.player_df["BF"].sum()
        total_era = 9 * (total_er / total_ip)
        total_kwera = 4.80 - (10 * ((total_so - total_bb) / total_bf))
        total_fip = (
            ((13 * total_hr) + (3 * (total_bb + total_hb)) - (2 * total_so))
            / total_ip
        ) + select_fip_const(self.suffix, self.year)

        # Calculations for RATE stats
        self.df["ERA"] = 9 * (self.df["ER"] / self.df["IP"])
        self.df["ERA+"] = 100 * (total_era * self.df["ParkF"]) / self.df["ERA"]
        self.df["kwERA"] = 4.80 - (
            10 * ((self.df["SO"] - self.df["BB"]) / self.df["BF"])
        )
        self.df["K%"] = self.df["SO"] / self.df["BF"]
        self.df["BB%"] = self.df["BB"] / self.df["BF"]
        self.df["K-BB%"] = self.df["K%"] - self.df["BB%"]
        self.df["FIP"] = (
            (
                (13 * self.df["HR"])
                + (3 * (self.df["BB"] + self.df["HB"]))
                - (2 * self.df["SO"])
            )
            / self.df["IP"]
        ) + select_fip_const(self.suffix, self.year)
        # NO PARK FACTOR TEST
        # self.df['FIP-'] = (100 * (self.df['FIP'] / (total_fip)))
        self.df["FIP-"] = 100 * (
            self.df["FIP"] / (total_fip * self.df["ParkF"])
        )
        self.df["WHIP"] = (self.df["BB"] + self.df["H"]) / self.df["IP"]
        self.df["Diff"] = self.df["ERA"] - self.df["FIP"]
        self.df["HR%"] = self.df["HR"] / self.df["BF"]
        self.df["kwERA-"] = 100 * (self.df["kwERA"] / total_kwera)

        # Calculate league averages
        league_avg = self.df.mean(numeric_only=True)
        league_avg["Team"] = "League Average"
        # Recalculate averages for stats that are based on league averages
        league_avg["ERA"] = total_era
        league_avg["K%"] = self.df["SO"].sum() / self.df["BF"].sum()
        league_avg["BB%"] = self.df["BB"].sum() / self.df["BF"].sum()
        league_avg["HR%"] = self.df["HR"].sum() / self.df["BF"].sum()
        league_avg["K-BB%"] = (self.df["SO"].sum() / self.df["BF"].sum()) - (
            self.df["BB"].sum() / self.df["BF"].sum()
        )
        self.df.loc[len(self.df)] = league_avg

        # Remove temp Park Factor column
        self.df.drop("ParkF", axis=1, inplace=True)
        # Number formatting
        format_maps = {
            "BB%": "{:.1%}",
            "K%": "{:.1%}",
            "K-BB%": "{:.1%}",
            "HR%": "{:.1%}",
            "Diff": "{:.2f}",
            "FIP": "{:.2f}",
            "WHIP": "{:.2f}",
            "kwERA": "{:.2f}",
            "ERA": "{:.2f}",
            "kwERA-": "{:.1f}",
            "ERA+": "{:.0f}",
            "FIP-": "{:.0f}",
            "W": "{:.0f}",
            "L": "{:.0f}",
            "SV": "{:.0f}",
            "CG": "{:.0f}",
            "SHO": "{:.0f}",
            "BF": "{:.0f}",
            "H": "{:.0f}",
            "HR": "{:.0f}",
            "SO": "{:.0f}",
            "BB": "{:.0f}",
            "IBB": "{:.0f}",
            "HB": "{:.0f}",
            "WP": "{:.0f}",
            "R": "{:.0f}",
            "ER": "{:.0f}",
        }
        # Readd HLD formatting if not farm
        if self.suffix != "PF":
            format_maps["HLD"] = "{:.0f}"
        for key, value in format_maps.items():
            self.df[key] = self.df[key].apply(value.format)

        # Reorder columns
        col_order_arr = col_init_arr + [
            "ERA",
            "FIP",
            "kwERA",
            "WHIP",
            "ERA+",
            "FIP-",
            "kwERA-",
            "Diff",
            "HR%",
            "K%",
            "BB%",
            "K-BB%",
        ]
        self.df = self.df[col_order_arr]
        # Changing .33 to .1 and .66 to .2 in the IP column
        self.df["IP"] = convert_ip_column_out(self.df, "IP")
        # Add "League" column
        self.df = select_league(self.df, self.suffix)


class StandingsData(Stats):
    """A class to handle league standings data for NPB and Farm League.

    This class extends the `Stats` class and is responsible for organizing,
    processing, and outputting league standings data. It also prepares data
    for calculating player qualification thresholds (e.g., IP/PA drop
    constants) and integrates team-level statistics.

    Attributes:
        df (pandas.DataFrame): Holds the league standings data.
        const_df (pandas.DataFrame): A two-column DataFrame containing team
            names and the number of games they have played.

    Methods:
        output_final(tb_df, tp_df):
            Outputs the final organized standings data to CSV files for upload.
        org_standings(tb_df, tp_df):
            Organizes the standings data and calculates additional metrics
            such as runs scored (RS), runs allowed (RA), run differential
            (Diff), and expected winning percentage (XPCT)."""

    def __init__(self, stats_dir, year_dir, suffix, year):
        """StandingsData new variables:
        df (pandas dataframe): Holds a league's standings stats
        const_df (pandas dataframe): 2 column df with team names and the games
        they've played"""
        super().__init__(stats_dir, year_dir, suffix, year)
        # Initialize dataframe and year dir to store stats
        self.df = pd.read_csv(
            self.year_dir + "/raw/" + year + "StandingsRaw" + suffix + ".csv"
        )

        # Do bare minimum to prepare IP/PA const file for PlayerData objects
        # Further organization of stats comes later in output_final()
        # Drop last unnamed column
        self.df.drop(
            self.df.columns[len(self.df.columns) - 1], axis=1, inplace=True
        )
        # Replace all team entries with correct names from dictionary
        team_dict = {
            "HanshinTigers": "Hanshin Tigers",
            "Hiroshima ToyoCarp": "Hiroshima Carp",
            "YOKOHAMA DeNABAYSTARS": "DeNA BayStars",
            "YomiuriGiants": "Yomiuri Giants",
            "Tokyo YakultSwallows": "Yakult Swallows",
            "ChunichiDragons": "Chunichi Dragons",
            "ORIXBuffaloes": "ORIX Buffaloes",
            "Chiba LotteMarines": "Lotte Marines",
            "Fukuoka SoftBankHawks": "SoftBank Hawks",
            "Tohoku RakutenGolden Eagles": "Rakuten Eagles",
            "Saitama SeibuLions": "Seibu Lions",
            "Hokkaido Nippon-HamFighters": "Nipponham Fighters",
            "Oisix NiigataAlbirex BC": "Oisix Albirex",
            "Kufu HAYATEVentures Shizuoka": "HAYATE Ventures",
        }
        for raw, corrected in team_dict.items():
            self.df.loc[self.df.Team == raw, "Team"] = corrected
        # Column renaming (Int = Inter, adding space between vs and team abbr.)
        self.df.rename(
            columns={
                "Int": "Inter",
                "vsD": "vs D",
                "vsH": "vs H",
                "vsB": "vs B",
                "vsT": "vs T",
                "vsC": "vs C",
                "vsV": "vs V",
                "vsF": "vs F",
                "vsM": "vs M",
                "vsE": "vs E",
                "vsL": "vs L",
                "vsG": "vs G",
                "vsDB": "vs DB",
                "vsS": "vs S",
                "vsA": "vs A",
            },
            inplace=True,
        )

        # Make Raw const df, file, and dir for IP/PA calculations
        self.const_df = self.df[["Team", "G"]]
        const_dir = os.path.join(self.year_dir, "drop_const")
        if not os.path.exists(const_dir):
            os.mkdir(const_dir)
        new_csv_const = (
            const_dir + "/" + self.year + "const_raw" + self.suffix + ".csv"
        )
        self.const_df.to_csv(new_csv_const, index=False)

    def output_final(self, tb_df, tp_df):
        """Outputs final files using the standings dataframes

        Parameters:
        tb_df (pandas dataframe): An organized NPB team batting stat dataframe
        tp_df (pandas dataframe): An organized NPB team pitching stat dataframe
        """
        # Organize standings
        self.org_standings(tb_df, tp_df)

        # Make dir that will store files uploaded to yakyucosmo.com
        if self.suffix in ("C", "P"):
            upload_dir = os.path.join(self.year_dir, "npb")
        elif self.suffix in ("W", "E"):
            upload_dir = os.path.join(self.year_dir, "farm")
        else:
            upload_dir = self.year_dir
        # Make dir that will store alt views of the dataframes
        alt_dir = os.path.join(self.year_dir, "alt")

        # Print organized dataframe to file
        alt_filename = self.year + "StandingsAlt" + self.suffix + ".csv"
        alt_filename = store_dataframe(self.df, alt_dir, alt_filename, "alt")

        # Store df without HTML for streamlit
        st_dir = os.path.join(self.year_dir, "streamlit_src")
        st_filename = self.year + "StandingsFinal" + self.suffix + ".csv"
        st_filename = store_dataframe(self.df, st_dir, st_filename, "csv")

        # Add blank counter (#) column for Wordpress table counter
        self.df["#"] = ""
        move_col = self.df.pop("#")
        self.df.insert(0, "#", move_col)
        # Insert HTML code for team names
        final_df = self.df.copy()
        final_df = convert_team_to_html(final_df, self.year, "Full")
        # Create Standings file name
        final_filename = self.year + "StandingsFinal" + self.suffix + ".csv"
        final_filename = store_dataframe(
            final_df, upload_dir, final_filename, "csv"
        )

        # Convert the standings to a string and output to user
        std_dict = {
            "C": "Central",
            "E": "Eastern",
            "W": "Western",
            "P": "Pacific",
        }

        print(
            "The final " + std_dict[self.suffix] + " standings will be stored"
            " in: " + final_filename
        )
        print(
            "An alternative view of the "
            + std_dict[self.suffix]
            + " standings will be stored in: "
            + alt_filename
        )

    def org_standings(self, tb_df, tp_df):
        """Organize the standings stat csv and adds new stats (RS, RA, and
        XPCT) that incorporate team data

        Parameters:
        tb_df (pandas dataframe): An organized NPB team batting stat dataframe
        tp_df (pandas dataframe): An organized NPB team pitching stat dataframe
        """
        # Merge team batting column to create 'RS'
        self.df = pd.merge(
            self.df, tb_df[["Team", "R"]], on="Team", how="left"
        )
        self.df.rename(columns={"R": "RS"}, inplace=True)
        self.df["RS"] = self.df["RS"].astype(float)
        # Merge team pitching column to create 'RA'
        self.df = pd.merge(
            self.df, tp_df[["Team", "R"]], on="Team", how="left"
        )
        self.df.rename(columns={"R": "RA"}, inplace=True)
        self.df["RA"] = self.df["RA"].astype(float)
        # Diff and XPCT calculations
        self.df["Diff"] = self.df["RS"] - self.df["RA"]
        self.df["XPCT"] = (self.df["RS"] ** 1.83) / (
            (self.df["RS"] ** 1.83) + (self.df["RA"] ** 1.83)
        )

        # Column reorder (reorganizes first "non-team vs" cols)
        cols = [
            "Team",
            "G",
            "W",
            "L",
            "T",
            "PCT",
            "GB",
            "RS",
            "RA",
            "Diff",
            "XPCT",
            "Home",
            "Road",
        ]
        self.df = self.df[cols + [c for c in self.df.columns if c not in cols]]
        # Number formatting
        format_maps = {
            "PCT": "{:.3f}",
            "XPCT": "{:.3f}",
            "RS": "{:.0f}",
            "RA": "{:.0f}",
            "Diff": "{:.0f}",
        }
        for key, value in format_maps.items():
            self.df[key] = self.df[key].apply(value.format)


class FieldingData(Stats):
    """A class to handle individual fielding statistics for NPB and Farm
    League.

    This class extends the `Stats` class and is responsible for organizing,
    processing, and outputting individual fielding statistics. It reads raw
    CSV files, calculates additional metrics, and formats the data for final
    output.

    Attributes:
        df (pandas.DataFrame): Holds the individual fielding statistics.

    Methods:
        output_final():
            Outputs the final organized fielding statistics to CSV files for
            upload.
        org_fielding():
            Organizes raw fielding statistics and calculates additional metrics
            such as Total Zone Rating (TZR) and TZR per 143 games (TZR/143)."""

    def __init__(self, stats_dir, year_dir, suffix, year):
        """FieldingData new variables:
        df (pandas dataframe): Holds the individual fielding stats"""
        super().__init__(stats_dir, year_dir, suffix, year)
        # Initialize data frame to store stats
        self.df = pd.read_csv(
            self.year_dir + "/raw/" + year + "FieldingRaw" + suffix + ".csv"
        )
        # Modify df for correct stats
        self.org_fielding()

    def output_final(self):
        """Outputs final files using the fielding dataframes"""
        # Make dir that will store alt views of the dataframes
        alt_dir = os.path.join(self.year_dir, "alt")
        # Make dirs that will store files uploaded to yakyucosmo.com
        upload_dir = self.year_dir
        if self.suffix == "R":
            upload_dir = os.path.join(self.year_dir, "npb")
        elif self.suffix == "F":
            upload_dir = os.path.join(self.year_dir, "farm")

        # Print organized dataframe to file
        alt_filename = self.year + "FieldingAlt" + self.suffix + ".csv"
        alt_filename = store_dataframe(self.df, alt_dir, alt_filename, "alt")

        # Store df without HTML for streamlit
        st_dir = os.path.join(self.year_dir, "streamlit_src")
        st_filename = self.year + "FieldingFinal" + self.suffix + ".csv"
        st_filename = store_dataframe(self.df, st_dir, st_filename, "csv")

        # Add blank Rank column for Wordpress table counter
        self.df["Rank"] = ""
        move_col = self.df.pop("Rank")
        self.df.insert(0, "Rank", move_col)
        # Make deep copy of original df to avoid HTML in df's team/player names
        final_df = self.df.copy()
        # Convert player/team names to HTML that contains appropriate URLs
        if int(self.year) == datetime.now().year:
            final_df = convert_player_to_html(final_df, self.suffix, self.year)
        final_df = convert_team_to_html(final_df, self.year, "Abb")
        # Print final file with all players
        final_filename = self.year + "FieldingFinal" + self.suffix + ".csv"
        final_filename = store_dataframe(
            final_df, upload_dir, final_filename, "csv"
        )

        if self.suffix == "R":
            print(
                "An alternative view of the regular season individual fielding"
                " results will be stored in: " + alt_filename
            )
            print(
                "The final organized regular season individual fielding "
                "results will be stored in: " + final_filename
            )
        elif self.suffix == "F":
            print(
                "An alternative view of the farm individual fielding results "
                "will be stored in: " + alt_filename
            )
            print(
                "The final organized farm individual fielding results will be "
                "stored in: " + final_filename
            )

    def org_fielding(self):
        """Organize the fielding stat csv and adds new stats (TZR, TZR/143)"""
        # Drop empty last column and convert column names
        self.df = self.df.drop(self.df.columns[-1], axis=1)
        if self.suffix == "R":
            self.df.rename(
                columns={
                    "Position": "Pos",
                    "Inning": "Inn",
                    "位置補正": "Pos Adj",
                },
                inplace=True,
            )
        if self.suffix == "F":
            self.df.rename(
                columns={
                    "Position": "Pos",
                    "Inning": "Inn",
                    "位置補正": "Pos Adj",
                    "Error": "ErrR",
                },
                inplace=True,
            )

        # '-' converted to nan
        self.df["RngR"] = self.df["RngR"].astype(str).replace("-", "")
        self.df["ARM"] = self.df["ARM"].astype(str).replace("-", "")
        self.df["DPR"] = self.df["DPR"].astype(str).replace("-", "")
        self.df["ErrR"] = self.df["ErrR"].astype(str).replace("-", "")
        self.df["Framing"] = self.df["Framing"].astype(str).replace("-", "")
        self.df["Blocking"] = self.df["Blocking"].astype(str).replace("-", "")
        # Convert Pos to numbers for WordPress sorting
        pos_dict = {
            "C": "2",
            "1B": "3",
            "2B": "4",
            "3B": "5",
            "SS": "6",
            "LF": "7",
            "CF": "8",
            "RF": "9",
        }
        self.df["Pos"] = (
            self.df["Pos"]
            .map(pos_dict)
            .infer_objects()
            .fillna(self.df["Pos"])
            .astype(str)
        )
        # Translate team and player names
        team_dict = {
            "巨": "Yomiuri Giants",
            "中": "Chunichi Dragons",
            "神": "Hanshin Tigers",
            "広": "Hiroshima Carp",
            "デ": "DeNA BayStars",
            "ヤ": "Yakult Swallows",
            "ソ": "SoftBank Hawks",
            "西": "Seibu Lions",
            "楽": "Rakuten Eagles",
            "ロ": "Lotte Marines",
            "日": "Nipponham Fighters",
            "オ": "ORIX Buffaloes",
            "ハ": "HAYATE Ventures",
            "O": "Oisix Albirex",
        }
        self.df["Team"] = (
            self.df["Team"]
            .map(team_dict)
            .infer_objects()
            .fillna(self.df["Team"])
            .astype(str)
        )
        self.df = translate_players(self.df, self.year)
        # TZR/143 calculation and cleaning
        self.df["TZR"] = self.df["TZR"].astype(str).replace("-", "inf")
        self.df["TZR"] = self.df["TZR"].astype(float)
        self.df["TZR/143"] = (self.df["TZR"] / self.df["Inn"]) * 1287
        self.df = self.df.round({"TZR/143": 1})
        self.df["TZR/143"] = self.df["TZR/143"].astype(str).replace("inf", "")
        self.df["TZR"] = self.df["TZR"].astype(str).replace("inf", "")
        # Innings conversion
        self.df["Inn"] = convert_ip_column_out(self.df, "Inn")
        # Add League and Age cols
        self.df = select_league(self.df, self.suffix)
        self.df = add_roster_data(self.df, self.suffix, self.year)
        # Column reordering
        self.df = self.df[
            [
                "Player",
                "Age",
                "Pos",
                "Inn",
                "TZR",
                "TZR/143",
                "RngR",
                "ARM",
                "DPR",
                "ErrR",
                "Pos Adj",
                "Framing",
                "Blocking",
                "Team",
                "League",
            ]
        ]


class TeamFieldingData(Stats):
    """A class to handle team fielding statistics for NPB and Farm League.

    This class extends the `Stats` class and is responsible for organizing,
    processing, and outputting team fielding statistics. It aggregates
    individual player fielding statistics to calculate team-level metrics
    and formats the data for final output.

    Attributes:
        fielding_df (pandas.DataFrame): Holds the individual fielding
        statistics.
        df (pandas.DataFrame): Holds the aggregated team fielding statistics.

    Methods:
        output_final():
            Outputs the final organized team fielding statistics to CSV files
            for upload.
        org_team_fielding():
            Aggregates individual fielding statistics to calculate team-level
            metrics such as Total Zone Rating (TZR) and TZR per 143 games
            (TZR/143)."""

    def __init__(self, fielding_df, stats_dir, year_dir, suffix, year):
        """TeamFieldingData new variables:
        fielding_df (pandas dataframe): Holds the individual fielding stats df
        df (pandas dataframe): Holds a team's fielding stats"""
        super().__init__(stats_dir, year_dir, suffix, year)
        # Initialize data frame to store individual stats
        self.fielding_df = fielding_df.copy()
        self.df = pd.DataFrame()
        # Modify df for correct stats
        self.org_team_fielding()

    def output_final(self):
        """Outputs final files using the team fielding dataframes"""
        # Make dir that will store alt views of the dataframes
        alt_dir = os.path.join(self.year_dir, "alt")
        # Make dirs that will store files uploaded to yakyucosmo.com
        upload_dir = self.year_dir
        if self.suffix == "R":
            upload_dir = os.path.join(self.year_dir, "npb")
        elif self.suffix == "F":
            upload_dir = os.path.join(self.year_dir, "farm")

        # Print organized dataframe to file
        alt_filename = self.year + "TeamFieldingAlt" + self.suffix + ".csv"
        alt_filename = store_dataframe(self.df, alt_dir, alt_filename, "alt")

        # Store df without HTML for streamlit
        st_dir = os.path.join(self.year_dir, "streamlit_src")
        st_filename = self.year + "TeamFieldingFinal" + self.suffix + ".csv"
        st_filename = store_dataframe(self.df, st_dir, st_filename, "csv")

        # Add blank # column for Wordpress table counter
        self.df["#"] = ""
        move_col = self.df.pop("#")
        self.df.insert(0, "#", move_col)
        # Make deep copy of original df to avoid HTML in df's team/player names
        final_df = self.df.copy()
        # Convert team names to HTML that contains appropriate URLs
        final_df = convert_team_to_html(final_df, self.year, "Full")
        # Print final file with all players
        final_filename = self.year + "TeamFieldingFinal" + self.suffix + ".csv"
        final_filename = store_dataframe(
            final_df, upload_dir, final_filename, "csv"
        )

        if self.suffix == "R":
            print(
                "An alternative view of the regular season team fielding "
                "results will be stored in: " + alt_filename
            )
            print(
                "The final organized regular season team fielding results "
                "will be stored in: " + final_filename
            )
        elif self.suffix == "F":
            print(
                "An alternative view of the farm team fielding results will "
                "be stored in: " + alt_filename
            )
            print(
                "The final organized farm team fielding results will be stored"
                " in: " + final_filename
            )

    def org_team_fielding(self):
        """Organize the team fielding stat csv using the individual fielding
        stats"""
        # Convert cols that are numeric to float
        cols = self.fielding_df.columns.drop(["Team", "League"])
        self.fielding_df[cols] = self.fielding_df[cols].apply(
            pd.to_numeric, errors="coerce"
        )
        # Group stats by team and append to team dataframe
        self.df["Team"] = self.fielding_df["Team"].unique()
        self.df = pd.merge(
            self.df,
            self.fielding_df.groupby("Team", as_index=False)["TZR"].sum(),
        )
        self.df = pd.merge(
            self.df,
            self.fielding_df.groupby("Team", as_index=False)["Inn"].sum(),
        )
        self.df["TZR/143"] = (self.df["TZR"] / self.df["Inn"]) * 1287
        self.df = pd.merge(
            self.df,
            self.fielding_df.groupby("Team", as_index=False)["RngR"].sum(),
        )
        self.df = pd.merge(
            self.df,
            self.fielding_df.groupby("Team", as_index=False)["ARM"].sum(),
        )
        self.df = pd.merge(
            self.df,
            self.fielding_df.groupby("Team", as_index=False)["DPR"].sum(),
        )
        self.df = pd.merge(
            self.df,
            self.fielding_df.groupby("Team", as_index=False)["ErrR"].sum(),
        )
        self.df = pd.merge(
            self.df,
            self.fielding_df.groupby("Team", as_index=False)["Framing"].sum(),
        )
        self.df = pd.merge(
            self.df,
            self.fielding_df.groupby("Team", as_index=False)["Blocking"].sum(),
        )
        self.df = select_league(self.df, self.suffix)

        # Column reordering
        self.df = self.df[
            [
                "Team",
                "TZR",
                "TZR/143",
                "RngR",
                "ARM",
                "DPR",
                "ErrR",
                "Framing",
                "Blocking",
                "League",
            ]
        ]
        # Number formatting
        format_maps = {
            "TZR": "{:.1f}",
            "TZR/143": "{:.1f}",
            "RngR": "{:.1f}",
            "ARM": "{:.1f}",
            "DPR": "{:.1f}",
            "ErrR": "{:.1f}",
            "Framing": "{:.1f}",
            "Blocking": "{:.1f}",
        }
        for key, value in format_maps.items():
            self.df[key] = self.df[key].apply(value.format)


class TeamSummaryData(Stats):
    """A class to handle team summary statistics for NPB and Farm League.

    This class extends the `Stats` class and is responsible for aggregating,
    organizing, and outputting team summary statistics. It combines data from
    team fielding, standings, batting, and pitching statistics to provide a
    comprehensive summary of team performance.

    Attributes:
        team_fielding_df (pandas.DataFrame): Holds the team fielding
        statistics.
        standings_df (pandas.DataFrame): Holds the combined league standings
            data from two halves (e.g., Central and Pacific leagues).
        team_bat_df (pandas.DataFrame): Holds the team batting statistics.
        team_pitch_df (pandas.DataFrame): Holds the team pitching statistics.
        df (pandas.DataFrame): Holds the aggregated team summary statistics.

    Methods:
        output_final():
            Outputs the final organized team summary statistics to CSV files
            for upload.
        org_team_summary():
            Aggregates and organizes team statistics from fielding, standings,
            batting, and pitching data to calculate metrics such as win-loss
            records, run differentials, and advanced metrics like OPS+ and
            ERA+."""

    def __init__(
        self,
        team_fielding_df,
        standings_df1,
        standings_df2,
        team_bat_df,
        team_pitch_df,
        stats_dir,
        year_dir,
        suffix,
        year,
    ):
        """TeamSummaryData new variables:
        team_fielding_df (pandas dataframe): Holds the team fielding stats df
        standings_df1 (pandas dataframe): Holds the first half of the standings
        standings_df2 (pandas dataframe): Holds the second half of the
        standings
        team_bat_df (pandas dataframe): Holds the team batting stats df
        team_pitch_df (pandas dataframe): Holds the team pitching stats df
        df (pandas dataframe): Holds a team's summarized stats"""
        super().__init__(stats_dir, year_dir, suffix, year)
        # Initialize data frames to store team stats
        self.team_fielding_df = team_fielding_df
        self.standings_df = pd.concat([standings_df1, standings_df2])
        self.team_bat_df = team_bat_df
        self.team_pitch_df = team_pitch_df
        self.df = pd.DataFrame()
        # Modify df for correct stats
        self.org_team_summary()

    def output_final(self):
        """Outputs final files using the team summary dataframes"""
        # Make dir that will store alt views of the dataframes
        alt_dir = os.path.join(self.year_dir, "alt")
        # Make dirs that will store files uploaded to yakyucosmo.com
        upload_dir = self.year_dir
        if self.suffix == "R":
            upload_dir = os.path.join(self.year_dir, "npb")
        elif self.suffix == "F":
            upload_dir = os.path.join(self.year_dir, "farm")

        # Print organized dataframe to file
        alt_filename = self.year + "TeamSummaryAlt" + self.suffix + ".csv"
        alt_filename = store_dataframe(self.df, alt_dir, alt_filename, "alt")

        # Store df without HTML for streamlit
        st_dir = os.path.join(self.year_dir, "streamlit_src")
        st_filename = self.year + "TeamSummaryFinal" + self.suffix + ".csv"
        st_filename = store_dataframe(self.df, st_dir, st_filename, "csv")

        # Add blank Rank column for Wordpress table counter
        self.df["#"] = ""
        move_col = self.df.pop("#")
        self.df.insert(0, "#", move_col)
        # Make deep copy of original df to avoid HTML in df's team/player names
        final_df = self.df.copy()
        # Convert team names to HTML that contains appropriate URLs
        final_df = convert_team_to_html(final_df, self.year, "Full")
        # Print final file with all players
        final_filename = self.year + "TeamSummaryFinal" + self.suffix + ".csv"
        final_filename = store_dataframe(
            final_df, upload_dir, final_filename, "csv"
        )

        if self.suffix == "R":
            print(
                "An alternative view of the regular season team summary "
                "results will be stored in: " + alt_filename
            )
            print(
                "The final organized regular season team summary results will "
                "be stored in: " + final_filename
            )
        elif self.suffix == "F":
            print(
                "An alternative view of the farm team summary results will "
                "be stored in: " + alt_filename
            )
            print(
                "The final organized farm team summary results will be stored "
                "in: " + final_filename
            )

    def org_team_summary(self):
        """Organize the team summary stat csv using the team stat dfs"""
        # Group stats by team and append to team dataframe
        self.df["Team"] = self.team_fielding_df["Team"].tolist()
        self.df = pd.merge(
            self.df,
            self.team_pitch_df[
                ["Team", "W", "L", "ERA+", "FIP-", "K-BB%", "R"]
            ],
            on="Team",
            how="left",
        )
        self.df.rename(columns={"R": "RA"}, inplace=True)
        self.df = pd.merge(
            self.df,
            self.team_bat_df[["Team", "HR", "SB", "OPS+", "R", "wSB"]],
            on="Team",
            how="left",
        )
        self.df.rename(columns={"R": "RS"}, inplace=True)
        self.df = pd.merge(
            self.df, self.standings_df[["Team", "PCT"]], on="Team", how="left"
        )
        self.df["Diff"] = self.df["RS"].astype(int) - self.df["RA"].astype(int)
        self.df = pd.merge(
            self.df,
            self.team_fielding_df[["Team", "TZR"]],
            on="Team",
            how="left",
        )
        self.df = select_league(self.df, self.suffix)

        # Column reordering
        self.df = self.df[
            [
                "Team",
                "W",
                "L",
                "PCT",
                "Diff",
                "HR",
                "SB",
                "OPS+",
                "ERA+",
                "FIP-",
                "K-BB%",
                "wSB",
                "TZR",
            ]
        ]
        # Number formatting
        format_maps = {"PCT": "{:.3f}"}
        for key, value in format_maps.items():
            self.df[key] = self.df[key].apply(value.format)


class DailyScoresData(Stats):
    """A class to handle daily game scores for NPB and Farm League.

    This class extends the `Stats` class and is responsible for organizing,
    processing, and outputting daily game scores. It reads raw CSV files,
    formats the data, and prepares it for final output.

    Attributes:
        df (pandas.DataFrame): Holds the daily game scores.

    Methods:
        output_final():
            Outputs the final organized daily game scores to CSV files for
            upload.
        org_daily_scores():
            Organizes raw daily game scores, converts team abbreviations to
            full names, and formats the data for presentation."""

    def __init__(self, stats_dir, year_dir, suffix, year):
        """DailyScores new variables:
        df (pandas dataframe): Holds the scores of the games"""
        super().__init__(stats_dir, year_dir, suffix, year)
        # Initialize dataframe to store scores
        self.df = pd.read_csv(
            self.year_dir + "/raw/" + year + "DailyScoresRaw" + suffix + ".csv"
        )
        # Modify df for correct stats
        self.org_daily_scores()

    def output_final(self):
        """Outputs final files using the daily score dataframes"""
        # Make dir that will store alt views of the dataframes
        alt_dir = os.path.join(self.year_dir, "alt")
        # Make dirs that will store files uploaded to yakyucosmo.com
        upload_dir = self.year_dir
        if self.suffix == "R":
            upload_dir = os.path.join(self.year_dir, "npb")
        elif self.suffix == "F":
            upload_dir = os.path.join(self.year_dir, "farm")

        alt_filename = self.year + "DailyScoresAlt" + self.suffix + ".csv"
        alt_filename = store_dataframe(self.df, alt_dir, alt_filename, "alt")

        # Store df without HTML for streamlit
        st_dir = os.path.join(self.year_dir, "streamlit_src")
        st_filename = self.year + "DailyScoresFinal" + self.suffix + ".csv"
        st_filename = store_dataframe(self.df, st_dir, st_filename, "csv")

        # Make deep copy of original df to avoid HTML in df's team/player names
        final_df = self.df.copy()
        # Convert team names to HTML that contains appropriate URLs
        final_df = convert_team_to_html(final_df, self.year, None)
        # Blank out score column names, rename team columns
        final_df.rename(
            columns={
                "HomeTeam": "Home",
                "RunsHome": "",
                "RunsAway": "",
                "AwayTeam": "Away",
            },
            inplace=True,
        )
        # Print final file with most recent game scores
        final_filename = self.year + "DailyScoresFinal" + self.suffix + ".csv"
        final_filename = store_dataframe(
            final_df, upload_dir, final_filename, "csv"
        )

        print(
            "An alternative view of the daily game scores will be stored "
            "in: " + alt_filename
        )
        print(
            "The final organized daily game scores will be stored in: "
            + final_filename
        )

    def org_daily_scores(self):
        """Organize the daily score csv"""
        # Convert abbreviated names to full team names
        abbr_dict = {
            "Hanshin": "Hanshin Tigers",
            "Hiroshima": "Hiroshima Carp",
            "DeNA": "DeNA BayStars",
            "Yomiuri": "Yomiuri Giants",
            "Yakult": "Yakult Swallows",
            "Chunichi": "Chunichi Dragons",
            "ORIX": "ORIX Buffaloes",
            "Lotte": "Lotte Marines",
            "SoftBank": "SoftBank Hawks",
            "Rakuten": "Rakuten Eagles",
            "Seibu": "Seibu Lions",
            "Nippon-Ham": "Nipponham Fighters",
            "Oisix": "Oisix Albirex",
            "HAYATE": "HAYATE Ventures",
        }
        team_cols = ["HomeTeam", "AwayTeam"]
        for col in team_cols:
            self.df[col] = (
                self.df[col]
                .map(abbr_dict)
                .infer_objects()
                .fillna(self.df[col])
                .astype(str)
            )
        # Remove trailing zeroes from scores
        runs_cols = ["RunsHome", "RunsAway"]
        for col in runs_cols:
            self.df[col] = self.df[col].astype(str)
            self.df[col] = self.df[col].str.replace(".0", "")
            self.df[col] = self.df[col].str.replace("nan", "*")


def get_url(try_url):
    """Attempts a GET request from the passed in URL

    Parameters:
    try_url (string): The URL to attempt opening

    Returns:
    response (Response): The URL's response"""
    try:
        print("Connecting to: " + try_url)
        response = requests.get(try_url, timeout=10)
        response.raise_for_status()
    # Page doesn't exist (404 not found, 403 not authorized, etc)
    except HTTPError as hp:
        print(hp)
    # Bad URL
    except URLError as ue:
        print(ue)
    return response


def get_daily_scores(year_dir, suffix, year):
    """The main daily scores scraping function that produces Raw daily scores
    files"""
    # Make output file
    output_file = make_raw_daily_scores_file(year_dir, suffix, year)
    output_file.write("HomeTeam,RunsHome,RunsAway,AwayTeam\n")
    # Grab URLs to scrape
    url = "https://npb.jp/bis/eng/" + year + "/games/"
    # Make GET request
    r = get_url(url)
    # Create the soup for parsing the html content
    soup = BeautifulSoup(r.content, "html.parser")
    game_divs = soup.find_all("div", class_="contentsgame")
    # Extract table rows from npb.jp daily game stats
    for result in game_divs:
        teams = result.find_all(class_="contentsTeam")
        runs = result.find_all(class_="contentsRuns")
        i = 0
        while i < len(teams):
            team1 = teams[i].get_text()
            team1_runs = runs[i].get_text()
            team2 = teams[i + 1].get_text()
            team2_runs = runs[i + 1].get_text()
            i += 2
            output_file.write(
                team1
                + ","
                + team1_runs
                + ","
                + team2_runs
                + ","
                + team2
                + "\n"
            )
    # After all URLs are scraped, close output file
    r.close()
    output_file.close()


def get_stats(year_dir, suffix, year):
    """The main stat scraping function that produces Raw stat files.
    Saving Raw stat files allows for scraping and stat organization to be
    independent of each other

    Parameters:
    year_dir (string): The directory that stores the raw, scraped NPB stats
    suffix (string): Determines header row of csv file and indicates the stats
    that the URLs point to:
    "BR" = reg season batting stat URLs passed in
    "PR" = reg season pitching stat URLs passed in
    "BF" = farm batting stat URLs passed in
    "PF" = farm pitching stat URLs passed in
    year (string): The desired npb year to scrape"""
    # Make output file
    output_file = make_raw_player_file(year_dir, suffix, year)
    # Grab URLs to scrape
    url_arr = get_stat_urls(suffix, year)
    # Create header row
    if suffix == "BR":
        output_file.write(
            "Player,G,PA,AB,R,H,2B,3B,HR,TB,RBI,SB,CS,SH,SF,BB,"
            "IBB,HP,SO,GDP,AVG,SLG,OBP,Team,\n"
        )
    elif suffix == "PR":
        output_file.write(
            "Pitcher,G,W,L,SV,HLD,CG,SHO,PCT,BF,IP,,H,HR,BB,IBB,"
            "HB,SO,WP,BK,R,ER,ERA,Team,\n"
        )
    elif suffix == "BF":
        output_file.write(
            "Player,G,PA,AB,R,H,2B,3B,HR,TB,RBI,SB,CS,SH,SF,BB,"
            "IBB,HP,SO,GDP,AVG,SLG,OBP,Team,\n"
        )
    elif suffix == "PF":
        output_file.write(
            "Pitcher,G,W,L,SV,CG,SHO,PCT,BF,IP,,H,HR,BB,IBB,HB,SO,WP,BK,R,ER,"
            "ERA,Team,\n"
        )

    # Loop through all team stat pages in url_arr
    for url in url_arr:
        # Make GET request
        r = get_url(url)
        # Create the soup for parsing the html content
        soup = BeautifulSoup(r.content, "html.parser")

        # Since header row was created, skip to stat rows
        iter_soup = iter(soup.table)
        # Left handed pitcher/batter and switch hitter row skip
        next(iter_soup)
        # npb.jp header row skip
        next(iter_soup)

        # Extract table rows from npb.jp team stats
        for table_row in iter_soup:
            # Skip first column for left handed batter/pitcher or switch hitter
            iter_table = iter(table_row)
            next(iter_table)
            # Write output in csv file format
            for entry in iter_table:
                # Remove commas in first and last names
                entry_text = entry.get_text()
                if entry_text.find(","):
                    entry_text = entry_text.replace(",", "")
                # Write output in csv file format
                output_file.write(entry_text + ",")

            # Get team
            title_div = soup.find(id="stdivtitle")
            year_title_str = title_div.h1.get_text()
            # Correct team name formatting
            year_title_str = year_title_str.replace(year, "")
            if year_title_str.find("Fukuoka"):
                year_title_str = year_title_str.replace("Fukuoka", "")
            if year_title_str.find("Chiba"):
                year_title_str = year_title_str.replace("Chiba", "")
            if year_title_str.find("Hokkaido Nippon-Ham Fighters"):
                year_title_str = year_title_str.replace(
                    "Hokkaido Nippon-Ham Fighters", "Nipponham Fighters"
                )
            if year_title_str.find("Toyo"):
                year_title_str = year_title_str.replace("Toyo ", "")
            if year_title_str.find("YOKOHAMA DeNA BAYSTARS"):
                year_title_str = year_title_str.replace(
                    "YOKOHAMA DeNA BAYSTARS", "DeNA BayStars"
                )
            if year_title_str.find("Saitama"):
                year_title_str = year_title_str.replace("Saitama", "")
            if year_title_str.find("Tokyo"):
                year_title_str = year_title_str.replace("Tokyo", "")
            if year_title_str.find("Tohoku Rakuten Golden Eagles"):
                year_title_str = year_title_str.replace(
                    "Tohoku Rakuten Golden Eagles", "Rakuten Eagles"
                )
            if year_title_str.find("Kufu HAYATE Ventures Shizuoka"):
                year_title_str = year_title_str.replace(
                    "Kufu HAYATE Ventures Shizuoka", "HAYATE Ventures"
                )
            if year_title_str.find("Oisix Niigata Albirex BC"):
                year_title_str = year_title_str.replace(
                    "Oisix Niigata Albirex BC", "Oisix Albirex"
                )
            year_title_str = year_title_str.lstrip()
            year_title_str = year_title_str.rstrip()
            # Append as last entry and move to next row
            output_file.write(year_title_str + ",\n")

        # Close request
        r.close()
        # Pace requests to npb.jp to avoid excessive requests
        sleep(randint(1, 3))
    # After all URLs are scraped, close output file
    output_file.close()


def get_standings(year_dir, suffix, year):
    """Scrape the games played table for relevant stats to calculate PA/IP
    qualifier drop stats and for reference

    Parameters:
    year_dir (string): The directory to store relevant year statistics
    suffix (string): Indicates URL being scraped:
    "C" = central league reg season standing URLs passed in
    "P" = pacific league reg season standing URLs passed in
    "E" = eastern league farm standing URLs passed in
    "W" = western league farm standing URLs passed in
    year (string):The desired standings stat year"""
    output_file = make_raw_standings_file(year_dir, suffix, year)
    # Get URL to scrape
    url_base = "https://npb.jp/bis/eng/{0}/stats/std_{1}.html"
    url = url_base.format(year, suffix.lower())
    r = get_url(url)
    # Create the soup for parsing the html content
    soup = BeautifulSoup(r.content, "html.parser")

    # Grab all rows in the first subtable on the page
    if len(soup.find_all("table")) >= 2:
        table = soup.find_all("table")[1].find_all("tr")
    # Stop running if no table is available
    else:
        # Close request and output file
        r.close()
        output_file.close()
        return

    # Create header row
    iter_table = iter(table)
    tr = next(iter_table)
    # Loop through each td in a table row
    for td in tr:
        entry_text = td.get_text()
        # Skip empty column
        if entry_text == "":
            continue
        # Insert each entry using csv format
        output_file.write(entry_text + ",")
    output_file.write("\n")

    # Since header row was created, skip to stat rows
    for tr in iter_table:
        # Loop through each td in a table row
        for td in tr:
            entry_text = td.get_text()
            # Standardize blank spots in the csv
            if entry_text == "***":
                entry_text = "--"
            # Skip empty columns
            if entry_text == "":
                continue
            # Insert each entry using csv format
            output_file.write(entry_text + ",")
        # Skip duplicate named table row
        next(iter_table)
        output_file.write("\n")

    # Close request and output file
    r.close()
    output_file.close()
    # Pace requests to npb.jp to avoid excessive requests
    sleep(randint(1, 3))


def get_fielding(year_dir, suffix, year):
    """Scrapes the fielding stats for the desired year and suffix

    Parameters:
    year_dir (string): The directory to store relevant year statistics
    suffix (string): Indicates URL being scraped:
    "R" = regular season fielding stats
    "F" = farm fielding stats
    year (string): The desired fielding stat year"""
    rel_dir = os.path.dirname(__file__)
    url_file = rel_dir + "/input/" + year + "/fielding_urls.csv"
    # Grab singular fielding URL from file
    df = pd.read_csv(url_file)
    df = df.drop(df[df.Year.astype(str) != year].index)
    if "R" in suffix:
        fielding_league = "NPB"
    else:
        fielding_league = "Farm"
    df = df.drop(df[df.League != fielding_league].index)
    fielding_url = df["Link"].iloc[0]

    output_file = make_raw_fielding_file(year_dir, suffix, year)
    r = get_url(fielding_url)
    soup = BeautifulSoup(r.content, "html.parser")
    # Grab all fielding table entries
    fielding_tr = soup.find_all("tr")
    for tr in fielding_tr:
        if tr.get_text() == "":
            continue
        for td in tr:
            entry_text = td.get_text()
            entry_text = entry_text.strip()
            if entry_text == "":
                continue
            output_file.write(entry_text + ",")
        output_file.write("\n")
    r.close()
    # Pace requests to npb.jp to avoid excessive requests
    sleep(randint(1, 3))
    # After all URLs are scraped, close output file
    output_file.close()


def get_stat_urls(suffix, year):
    """Creates arrays of the correct URLs for the individual stat scraping

    Parameters:
    suffix (string): The desired mode to run in (either farm or regular season)
    year (string): The desired npb year to scrape

    Returns:
    url_arrB (array - string): Contains URLs to the team batting/pitching
    stat pages"""
    if suffix == "BR":
        # Team regular season individual batting stats
        url_arr = [
            # Hanshin Tigers
            "https://npb.jp/bis/eng/2024/stats/idb1_t.html",
            # Hiroshima Toyo Carp
            "https://npb.jp/bis/eng/2024/stats/idb1_c.html",
            # YOKOHAMA DeNA BAYSTARS
            "https://npb.jp/bis/eng/2024/stats/idb1_db.html",
            # Yomiuri Giants
            "https://npb.jp/bis/eng/2024/stats/idb1_g.html",
            # Tokyo Yakult Swallows
            "https://npb.jp/bis/eng/2024/stats/idb1_s.html",
            # Chunichi Dragons
            "https://npb.jp/bis/eng/2024/stats/idb1_d.html",
            # ORIX Buffaloes
            "https://npb.jp/bis/eng/2024/stats/idb1_b.html",
            # Chiba Lotte Marines
            "https://npb.jp/bis/eng/2024/stats/idb1_m.html",
            # Fukuoka SoftBank Hawks
            "https://npb.jp/bis/eng/2024/stats/idb1_h.html",
            # Tohoku Rakuten Golden Eagles
            "https://npb.jp/bis/eng/2024/stats/idb1_e.html",
            # Saitama Seibu Lions
            "https://npb.jp/bis/eng/2024/stats/idb1_l.html",
            # Hokkaido Nippon-Ham Fighters
            "https://npb.jp/bis/eng/2024/stats/idb1_f.html",
        ]
    elif suffix == "PR":
        # Team regular season individual pitching stats
        url_arr = [
            # Hanshin Tigers
            "https://npb.jp/bis/eng/2024/stats/idp1_t.html",
            # Hiroshima Toyo Carp
            "https://npb.jp/bis/eng/2024/stats/idp1_c.html",
            # YOKOHAMA DeNA BAYSTARS
            "https://npb.jp/bis/eng/2024/stats/idp1_db.html",
            # Yomiuri Giants
            "https://npb.jp/bis/eng/2024/stats/idp1_g.html",
            # Tokyo Yakult Swallows
            "https://npb.jp/bis/eng/2024/stats/idp1_s.html",
            # Chunichi Dragons
            "https://npb.jp/bis/eng/2024/stats/idp1_d.html",
            # ORIX Buffaloes
            "https://npb.jp/bis/eng/2024/stats/idp1_b.html",
            # Chiba Lotte Marines
            "https://npb.jp/bis/eng/2024/stats/idp1_m.html",
            # Fukuoka SoftBank Hawks
            "https://npb.jp/bis/eng/2024/stats/idp1_h.html",
            # Tohoku Rakuten Golden Eagles
            "https://npb.jp/bis/eng/2024/stats/idp1_e.html",
            # Saitama Seibu Lions
            "https://npb.jp/bis/eng/2024/stats/idp1_l.html",
            # Hokkaido Nippon-Ham Fighters
            "https://npb.jp/bis/eng/2024/stats/idp1_f.html",
        ]
    elif suffix == "BF":
        # Team farm individual batting stats
        url_arr = [
            # Hanshin Tigers
            "https://npb.jp/bis/eng/2024/stats/idb2_t.html",
            # Hiroshima Toyo Carp
            "https://npb.jp/bis/eng/2024/stats/idb2_c.html",
            # YOKOHAMA DeNA BAYSTARS
            "https://npb.jp/bis/eng/2024/stats/idb2_db.html",
            # Yomiuri Giants
            "https://npb.jp/bis/eng/2024/stats/idb2_g.html",
            # Tokyo Yakult Swallows
            "https://npb.jp/bis/eng/2024/stats/idb2_s.html",
            # Chunichi Dragons
            "https://npb.jp/bis/eng/2024/stats/idb2_d.html",
            # ORIX Buffaloes
            "https://npb.jp/bis/eng/2024/stats/idb2_b.html",
            # Chiba Lotte Marines
            "https://npb.jp/bis/eng/2024/stats/idb2_m.html",
            # Fukuoka SoftBank Hawks
            "https://npb.jp/bis/eng/2024/stats/idb2_h.html",
            # Tohoku Rakuten Golden Eagles
            "https://npb.jp/bis/eng/2024/stats/idb2_e.html",
            # Saitama Seibu Lions
            "https://npb.jp/bis/eng/2024/stats/idb2_l.html",
            # Hokkaido Nippon-Ham Fighters
            "https://npb.jp/bis/eng/2024/stats/idb2_f.html",
        ]
        # Append new farm teams for 2024 and beyond
        if int(year) >= 2024:
            # Oisix Niigata Albirex BC
            url_arr.append("https://npb.jp/bis/eng/2024/stats/idb2_a.html")
            # Kufu HAYATE Ventures Shizuoka
            url_arr.append("https://npb.jp/bis/eng/2024/stats/idb2_v.html")
    elif suffix == "PF":
        # Team farm individual pitching stats
        url_arr = [
            # Hanshin Tigers
            "https://npb.jp/bis/eng/2024/stats/idp2_t.html",
            # Hiroshima Toyo Carp
            "https://npb.jp/bis/eng/2024/stats/idp2_c.html",
            # YOKOHAMA DeNA BAYSTARS
            "https://npb.jp/bis/eng/2024/stats/idp2_db.html",
            # Yomiuri Giants
            "https://npb.jp/bis/eng/2024/stats/idp2_g.html",
            # Tokyo Yakult Swallows
            "https://npb.jp/bis/eng/2024/stats/idp2_s.html",
            # Chunichi Dragons
            "https://npb.jp/bis/eng/2024/stats/idp2_d.html",
            # ORIX Buffaloes
            "https://npb.jp/bis/eng/2024/stats/idp2_b.html",
            # Chiba Lotte Marines
            "https://npb.jp/bis/eng/2024/stats/idp2_m.html",
            # Fukuoka SoftBank Hawks
            "https://npb.jp/bis/eng/2024/stats/idp2_h.html",
            # Tohoku Rakuten Golden Eagles
            "https://npb.jp/bis/eng/2024/stats/idp2_e.html",
            # Saitama Seibu Lions
            "https://npb.jp/bis/eng/2024/stats/idp2_l.html",
            # Hokkaido Nippon-Ham Fighters
            "https://npb.jp/bis/eng/2024/stats/idp2_f.html",
        ]
        # Append new farm teams for 2024 and beyond
        if int(year) >= 2024:
            # Oisix Niigata Albirex BC
            url_arr.append("https://npb.jp/bis/eng/2024/stats/idp2_a.html")
            # Kufu HAYATE Ventures Shizuoka
            url_arr.append("https://npb.jp/bis/eng/2024/stats/idp2_v.html")

    # Loop through each entry and change the year in the URL before returning
    for i, url in enumerate(url_arr):
        url_arr[i] = url.replace("2024", year)
    return url_arr


def make_raw_player_file(write_dir, suffix, year):
    """Opens a file to hold all player stats inside a relative /year/raw/
    directory that is created before calling this function

    Parameters:
    write_dir (string): The directory that stores the scraped NPB stats
    suffix (string): Indicates the raw stat file to create:
    "BR" = reg season batting stats
    "PR" = reg season pitching stats
    "BF" = farm batting stats
    "PF" = farm pitching stats
    year (string): The desired npb year to scrape

    Returns:
    new_file (file stream object): An opened file in /year/raw/ named
    "[Year][Stats][Suffix].csv"""
    # Open and return the file object in write mode
    raw_dir = os.path.join(write_dir, "raw")
    if not os.path.exists(raw_dir):
        os.mkdir(raw_dir)
    new_csv_name = raw_dir + "/" + year + "StatsRaw" + suffix + ".csv"
    if suffix == "BR":
        print(
            "Raw regular season batting results will be stored in: "
            + new_csv_name
        )
    if suffix == "PR":
        print(
            "Raw regular season pitching results will be stored in: "
            + new_csv_name
        )
    if suffix == "BF":
        print("Raw farm batting results will be stored in: " + new_csv_name)
    if suffix == "PF":
        print("Raw farm pitching results will be stored in: " + new_csv_name)
    new_file = open(new_csv_name, "w", encoding="utf-8")
    return new_file


def make_raw_daily_scores_file(write_dir, suffix, year):
    """Opens a file to hold all player stats inside a relative /year/raw/
    directory that is created before calling this function

    Parameters:
    write_dir (string): The directory that stores the scraped NPB stats
    year (string): The desired npb year to scrape

    Returns:
    new_file (file stream object): An opened file in /year/raw/ named
    "[Year]DailyScoresRaw[Suffix].csv"""
    # Open and return the file object in write mode
    raw_dir = os.path.join(write_dir, "raw")
    if not os.path.exists(raw_dir):
        os.mkdir(raw_dir)
    new_csv_name = raw_dir + "/" + year + "DailyScoresRaw" + suffix + ".csv"
    print("Raw daily scores will be stored in: " + new_csv_name)
    new_file = open(new_csv_name, "w", encoding="utf-8")
    return new_file


def make_raw_standings_file(write_dir, suffix, year):
    """Opens a file to hold all player stats inside a relative /year/raw
    directory that is created before calling this function

    Parameters:
    write_dir (string): The directory that stores the scraped NPB stats
    suffix (string): Indicates the league passed in:
    "C" = central league reg season
    "P" = pacific league reg season
    "E" = eastern league farm
    "W" = western league farm
    year (string): The desired npb year to scrape

    Returns:
    new_file (file stream object): An opened file in /year/raw/ formatted as
    "[Year][Standings][Suffix].csv"""
    # Open and return the file object in write mode
    raw_dir = os.path.join(write_dir, "raw")
    if not os.path.exists(raw_dir):
        os.mkdir(raw_dir)
    new_csv_name = raw_dir + "/" + year + "StandingsRaw" + suffix + ".csv"
    if suffix == "C":
        print(
            "Raw Central League regular season standings will be stored in: "
            + new_csv_name
        )
    elif suffix == "P":
        print(
            "Raw Pacific League regular season standings will be stored in: "
            + new_csv_name
        )
    elif suffix == "E":
        print(
            "Raw Eastern League farm standings will be stored in: "
            + new_csv_name
        )
    elif suffix == "W":
        print(
            "Raw Western League farm standings will be stored in: "
            + new_csv_name
        )
    new_file = open(new_csv_name, "w", encoding="utf-8")
    return new_file


def make_raw_fielding_file(write_dir, suffix, year):
    """Opens a file to hold all fielding stats inside a relative /year/raw/
    directory that is created before calling this function

    Parameters:
    write_dir (string): The directory that stores the scraped NPB stats
    suffix (string): Indicates the raw stat file to create:
    "R" = regular season fielding stats
    "F" = farm fielding stats
    year (string): The desired npb year to scrape

    Return:
    new_file (file stream object): An opened file in /year/raw/ named
    "[Year]FieldingRaw[Suffix].csv"
    """
    # Open and return the file object in write mode
    raw_dir = os.path.join(write_dir, "raw")
    if not os.path.exists(raw_dir):
        os.mkdir(raw_dir)
    new_csv_name = raw_dir + "/" + year + "FieldingRaw" + suffix + ".csv"
    if suffix == "R":
        print(
            "Raw regular season fielding results will be stored in: "
            + new_csv_name
        )
    if suffix == "F":
        print("Raw farm fielding results will be stored in: " + new_csv_name)
    new_file = open(new_csv_name, "w", encoding="utf-8")
    return new_file


def get_scrape_year(args_in=None):
    """Checks passed in arguments or gets user input for NPB stat year to
    scrape

    Parameters:
    args_in (string): If a command line argument is given, the year is checked
    for validity. Default (None) indicates to collect user input instead

    Returns:
    args_in (string): The desired npb stat year to scrape"""
    # User input check
    if args_in is None:
        # Infinite loop breaks when valid input obtained
        # Either valid year or exit signal entered
        while True:
            args_in = input(
                "Enter a NPB year between 2020-"
                + str(datetime.now().year)
                + " or Q to quit: "
            )
            if args_in == "Q":
                sys.exit("Exiting...")
            try:
                args_in = int(args_in)
            except ValueError:
                print("Input must be a number (Example: 2024)")
                continue
            # Bounds for scrapable years
            # Min year on npb.jp = 2008, but scraping is only tested until 2020
            if 2020 <= args_in <= datetime.now().year:
                print(str(args_in) + " entered. Continuing...")
                break
            print(
                "Please enter a valid year (2020-"
                + str(datetime.now().year)
                + ")."
            )
    # Argument check
    else:
        try:
            args_in = int(args_in)
        except ValueError:
            print("Year argument must be a number (Example: 2024)")
            sys.exit("Exiting...")
        # Bounds for scrapable years
        # Min year on npb.jp is 2008, but scraping is only tested until 2020
        if 2020 <= args_in <= datetime.now().year:
            pass
        else:
            print(
                "Please enter a valid year (2020-"
                + str(datetime.now().year)
                + ")."
            )
            sys.exit("Exiting...")

    # Return user input as a string
    return str(args_in)


def get_user_choice(suffix):
    """Gets user input for whether or not to undergo scraping and whether to
    place relevant files in a zip

    Parameters:
    suffix (string): Indicates the option being asked about (can be farm
    scraping "F", regular season scraping "R", stat zip file creation "Z"

    Returns:
    user_in (string): Returns "Y" or "N" (if "Q" is chosen, program terminates)
    """
    # Loop ends for valid choice/exit
    while True:
        if suffix == "F":
            print(
                "Choose whether to pull new farm stats from npb.jp or "
                "only reorganize existing stat files.\nWARNING: EXISTING "
                "RAW FILES MUST BE PRESENT TO SKIP SCRAPING."
            )
            user_in = input("Scrape farm stats? (Y/N): ")
        elif suffix == "R":
            print(
                "Choose whether to pull new regular season stats from "
                "npb.jp or only reorganize existing stat files.\nWARNING: "
                "EXISTING RAW STAT FILES MUST BE PRESENT TO SKIP SCRAPING."
            )
            user_in = input("Scrape regular season stats stats? (Y/N): ")
        elif suffix == "Z":
            user_in = input("Output stats in a zip file? (Y/N): ")
        else:
            user_in = "Q"

        if user_in == "Q":
            sys.exit("Exiting...")
        elif user_in == "Y":
            print("Continuing...")
            break
        elif user_in == "N":
            print("Skipping...")
            break
        else:
            print(
                "Invalid input - enter (Y/N) to determine whether to continue "
                "or (Q) to quit."
            )
            continue
    return user_in


def convert_team_to_html(df, year, mode=None):
    """Formats the team col to include links to their npb.jp pages and adds img
    tag col that represents the team (images from yakyucosmo.com)

    Parameters:
    df (pandas dataframe): A dataframe containing entries with NPB teams
    mode (string): Indicates whether to preserve full team names ("Full"),
    abbrieviate names in the <a> tags ("Abb"), or convert any team names
    found in the dataframe to linked names (None)

    Returns:
    df (pandas dataframe): The dataframe with correct links and abbreviations
    inserted in tags (if applicable) or normal text (if no tags can be made),
    plus an img tag column if mode is not None"""
    # Check for the team link file, if missing, tell user and return
    rel_dir = os.path.dirname(__file__)
    team_link_file = rel_dir + "/input/" + year + "/team_urls.csv"
    link_df = pd.read_csv(team_link_file)

    # Default mode links any team names it finds (assumes full team names are
    # present in the dataframe) and returns
    if mode is None:
        link_df["Link"] = link_df.apply(build_html, args=("Team",), axis=1)
        # Create dict of Team Name:<img> tag
        img_dict = dict(zip(link_df["Team"], link_df["ImgSrc"]))
        # Create dict of Team Name:Complete HTML tag
        team_dict = dict(zip(link_df["Team"], link_df["Link"]))
        for col in df.columns:
            # Insert img tag column before converting team names to <a> tags
            df.insert(
                df.columns.get_loc(col),
                "Logos",
                (df[col].map(img_dict).infer_objects().fillna("").astype(str)),
            )
            # Rename Logos column to blank ""
            df = df.rename(columns={"Logos": ""})
            # Convert normal team names to <a> tags
            df[col] = (
                df[col]
                .map(team_dict)
                .infer_objects()
                .fillna(df[col])
                .astype(str)
            )
        return df
    if mode == "Full":
        # Update Link col to have <a> tags
        link_df["Link"] = link_df.apply(build_html, args=("Team",), axis=1)
        # Create dict of Team Name:Complete HTML tag
        team_dict = dict(zip(link_df["Team"], link_df["Link"]))
    elif mode == "Abb":
        # Make HTML Link col using abbreviated names
        link_df["Link"] = link_df.apply(build_html, args=("Abbr",), axis=1)
        # Create dict of Team Name:Complete HTML tag
        team_dict = dict(zip(link_df["Team"], link_df["Link"]))
    # Add logo/color <img> tag column before converting team names to <a> tags
    img_dict = dict(zip(link_df["Team"], link_df["ImgSrc"]))
    df.insert(
        df.columns.get_loc("Team"),
        "Logos",
        (df["Team"].map(img_dict).infer_objects().fillna("").astype(str)),
    )
    # Convert and return dataframe
    df["Team"] = (
        df["Team"]
        .map(team_dict)
        .infer_objects()
        .fillna(df["Team"])
        .astype(str)
    )
    # Rename Logos column to blank ""
    df = df.rename(columns={"Logos": ""})
    return df


def add_roster_data(df, suffix, year):
    """Adds player age and throwing/batting arm data to the dataframe

    Parameters:
    df (pandas dataframe): A dataframe containing entries with player names
    suffix (string): Indicates the data to add:
    "BR" = regular season batting arm data
    "BF" = farm batting arm data
    "PR" = regular season throwing arm data
    "PF" = farm throwing arm data

    Returns:
    df (pandas dataframe): The inputted dataframe with the appended throwing
    arms and ages"""
    rel_dir = os.path.dirname(__file__)
    roster_data_file = rel_dir + "/input/" + year + "/roster_data.csv"

    # Player throwing/batting arms
    roster_df = pd.read_csv(roster_data_file)
    convert_col = df.iloc[:, 0].name
    tb_col = ""
    if suffix in ("BR", "BF", "PR", "PF"):
        if suffix in ("PR", "PF"):
            tb_col = "T"
        elif suffix in ("BR", "BF"):
            tb_col = "B"
        player_arm_dict = dict(zip(roster_df["Player"], roster_df[tb_col]))
        df[tb_col] = (
            df[convert_col]
            .map(player_arm_dict)
            .infer_objects()
            .fillna("")
            .astype(str)
        )

    # Player age
    roster_df["BirthDate"] = pd.to_datetime(
        roster_df["BirthDate"], format="mixed"
    )
    roster_df["Age"] = roster_df["BirthDate"].apply(calculate_age)
    # Create dict of Player Name,Team:Age tag
    player_age_dict = dict(
        zip((zip(roster_df["Player"], roster_df["Team"])), roster_df["Age"])
    )
    df["keys"] = list(zip(df[convert_col], df["Team"]))
    df["Age"] = (
        df["keys"]
        .map(player_age_dict)
        .infer_objects()
        .fillna("")
        .astype(str)
    )
    # Remove trailing zeroes from age
    df["Age"] = df["Age"].astype(str)
    df["Age"] = df["Age"].str.replace(".0", "")
    return df


def calculate_age(birthdate):
    """Calculates the age of a player based on their birthdate according to
    when the NPB season ends (June 30th)

    Parameters:
    birthdate (datetime object): The birthdate of the player

    Returns:
    npb_age (int): The age of the player at the start of the NPB season"""
    cutoff = datetime(datetime.today().year, 6, 30)
    npb_age = (
        cutoff.year
        - birthdate.year
        - ((cutoff.month, cutoff.day) < (birthdate.month, birthdate.day))
    )
    return npb_age


def convert_ip_column_out(df, inn_col="IP"):
    """In baseball, innings are traditionally represented using .1 (single
    inning pitched), .2 (2 innings pitched), and whole numbers. This function
    converts the decimals FROM thirds (.33 -> .1, .66 -> .2) for sake of
    presentation

    Parameters:
    df (pandas dataframe): A pitching stat dataframe with the "thirds"
    representation
    inn_col (string): The name of the column to convert (default is "IP")

    Returns:
    temp_df[inn_col] (pandas dataframe column): An innings column
    converted back to the informal innings representation"""
    # Innings ".0 .1 .2" fix
    temp_df = pd.DataFrame(df[inn_col])
    # Get the ".0 .3 .7" in the innings column
    ip_decimals = temp_df[inn_col] % 1
    # Make the original innings column whole numbers
    temp_df[inn_col] = temp_df[inn_col] - ip_decimals
    # Convert IP decimals to thirds and re-add them to the whole numbers
    ip_decimals = (ip_decimals / 0.3333333333) / 10
    df[inn_col] = temp_df[inn_col] + ip_decimals
    # Entries with .3 are invalid: add 1 and remove the decimals
    x = temp_df[inn_col] + ip_decimals
    condlist = [((x % 1) < 0.29), ((x % 1) >= 0.29)]
    choicelist = [x, (x - (x % 1)) + 1]
    temp_df[inn_col] = np.select(condlist, choicelist)
    temp_df[inn_col] = temp_df[inn_col].apply(lambda x: f"{x:.1f}")
    temp_df[inn_col] = temp_df[inn_col].astype(float)
    return temp_df[inn_col]


def convert_ip_column_in(df, inn_col="IP"):
    """Converts the decimals in the IP column TO thirds (.1 -> .33, .2 -> .66)
    for stat calculations

    Parameters:
    df (pandas dataframe): A pitching stat dataframe with the traditional
    .1/.2 IP representation
    inn_col (string): The name of the column to convert (default is "IP")

    Returns:
    temp_df[inn_col] (pandas dataframe column): An IP column converted for stat
    calculations"""
    temp_df = pd.DataFrame(df[inn_col])
    # Get the ".0 .1 .2" in the 'IP' column
    ip_decimals = temp_df[inn_col] % 1
    # Make the original 'IP' column whole numbers
    temp_df[inn_col] = temp_df[inn_col] - ip_decimals
    # Multiply IP decimals by .3333333333 and readd them to the whole numbers
    ip_decimals = (ip_decimals * 10) * 0.3333333333
    temp_df[inn_col] = temp_df[inn_col] + ip_decimals
    return temp_df[inn_col]


def select_park_factor(df, suffix, year):
    """Selects the correct park factor depending on the NPB year and team

    Parameters:
    df (pandas dataframe): The dataframe to add the park factor column to
    suffix (string): Indicates whether to use farm or reg season park factors
    year (string): The year of park factors to pull

    Returns:
    df (pandas dataframe): The pandas dataframe with the new temp park factor
    column"""
    # Check for the park factor file, if nothing is there tell user and return
    rel_dir = os.path.dirname(__file__)
    pf_file = rel_dir + "/input/" + year + "/park_factors.csv"
    pf_df = pd.read_csv(pf_file)
    # Drop all rows that are not the df's year
    pf_df = pf_df.drop(pf_df[pf_df.Year.astype(str) != year].index)
    # Drop all rows that do not match the df's league
    if suffix in ("BR", "PR"):
        pf_suffix = "NPB"
    else:
        pf_suffix = "Farm"
    pf_df = pf_df.drop(pf_df[pf_df.League != pf_suffix].index)
    # Drop remaining unneeded cols before merge
    pf_df.drop(["Year", "League"], axis=1, inplace=True)
    # Modifying all park factors for calculations
    pf_df["ParkF"] = (pf_df["ParkF"] + 1) / 2
    df = df.merge(pf_df, on="Team", how="left")
    # For team files, league avg calculations have park factor as 1.000
    df.loc[df.Team == "League Average", "ParkF"] = 1.000
    return df


def select_fip_const(suffix, year):
    """Chooses FIP constant for 2020-2024 reg and farm years

    Parameters:
    suffix (string): Indicates whether to use farm or reg season FIP constants
    year (string): The year of FIP constants to pull

    Returns:
    fip_const (float): The correct FIP const according to year and farm/NPB reg
    season"""
    rel_dir = os.path.dirname(__file__)
    fip_file = rel_dir + "/input/" + year + "/fip_const.csv"
    fip_df = pd.read_csv(fip_file)
    # Drop all rows that are not the df's year
    fip_df = fip_df.drop(fip_df[fip_df.Year.astype(str) != year].index)
    # Drop all rows that do not match the df's league
    if suffix in ("BR", "PR"):
        fip_suffix = "NPB"
    else:
        fip_suffix = "Farm"
    fip_df = fip_df.drop(fip_df[fip_df.League != fip_suffix].index)
    # Return FIP for that year and league
    fip_const = fip_df.at[fip_df.index[-1], "FIP"]
    return fip_const


def select_league(df, suffix):
    """Adds a "League" column based on the team

    Parameters:
    df (pandas dataframe): A team or player dataframe

    Returns:
    df (pandas dataframe): The dataframe with the correct "League" column added
    """
    league_dict = {}
    if suffix in ("BR", "PR", "R"):
        # Contains all 2020-2024 reg baseball team names and leagues
        league_dict = {
            "Hanshin Tigers": "CL",
            "Hiroshima Carp": "CL",
            "DeNA BayStars": "CL",
            "Yomiuri Giants": "CL",
            "Yakult Swallows": "CL",
            "Chunichi Dragons": "CL",
            "ORIX Buffaloes": "PL",
            "Lotte Marines": "PL",
            "SoftBank Hawks": "PL",
            "Rakuten Eagles": "PL",
            "Seibu Lions": "PL",
            "Nipponham Fighters": "PL",
        }
    elif suffix in ("BF", "PF", "F"):
        # Contains all 2020-2024 farm baseball team names and links
        league_dict = {
            "Hanshin Tigers": "WL",
            "Hiroshima Carp": "WL",
            "DeNA BayStars": "EL",
            "Yomiuri Giants": "EL",
            "Yakult Swallows": "EL",
            "Chunichi Dragons": "WL",
            "ORIX Buffaloes": "WL",
            "Lotte Marines": "EL",
            "SoftBank Hawks": "WL",
            "Rakuten Eagles": "EL",
            "Seibu Lions": "EL",
            "Nipponham Fighters": "EL",
            "Oisix Albirex": "EL",
            "HAYATE Ventures": "WL",
        }

    for team, league in league_dict.items():
        df.loc[df.Team == team, "League"] = league
    return df


def assign_primary_or_utl(
    row,
    pct_utl_threshold_high=0.075,
    pct_utl_threshold_low=0.05,
    pct_primary_threshold=0.50,
):
    """Given a row with positions (e.g. row['1B'], row['2B'], etc.),
    decide if the player is 'UTL' or has a primary position.

    Parameters:
    row (pandas series): A row of a dataframe with positions as columns
    pct_utl_threshold_high (float): The threshold for a player to be considered
    UTL if they have 3 or more positions >= this value
    pct_utl_threshold_low (float): The threshold for a player to be considered
    UTL if they have 4 or more positions >= this value
    pct_primary_threshold (float): The threshold for a player to be considered
    primary at a position if they have >= this value

    Returns:
    fractions.idmax (int): The player's most prominent position"""
    pos_cols = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "DH"]
    total_innings = row[pos_cols].sum()
    if total_innings == 0:
        return "No Data"

    # Rule 1: Grab all players that are solely DH and pitchers
    if (total_innings - row["DH"]) == 0:
        return "DH"
    # Rule 2: Grab all players that are solely pitchers
    if (total_innings - row["1"]) == 0:
        return "1"
    # Calculate fraction for each position
    fractions = row[pos_cols] / (total_innings - row["DH"])
    # Count how many positions >= our thresholds
    num_positions_10plus = (fractions >= pct_utl_threshold_high).sum()
    num_positions_5plus = (fractions >= pct_utl_threshold_low).sum()
    # Rule 3: If the player has 3 positions that are all in the outfield, the
    # largest OF pos is the primary
    # Rule 4: If any position >= 50%, that is primary
    if (row["7"] > 0 and row["8"] > 0 and row["9"] > 0) or any(
        fractions >= pct_primary_threshold
    ):
        return fractions.idxmax()
    # Rule 5: If 3 or more positions are >= our thresholds, label UTL
    if num_positions_10plus >= 3 or num_positions_5plus >= 4:
        return "UTL"
    # Rule 6: If none of the above, pick the position with the largest fraction
    return fractions.idxmax()


def convert_player_to_html(df, suffix, year):
    """The WordPress tables associated with this project accepts HTML code, so
    this function formats player names into <a> tags with links to the player's
    npb.jp pages. Used after stats are calculated but before any csv output

    Parameters:
    df (pandas dataframe): Any final stat dataframe
    suffix (string): Indicates the data in param df
        "BR" = reg season batting stat URLs passed in
        "PR" = reg season pitching stat URLs passed in
        "BF" = farm batting stat URLs passed in
        "PF" = farm pitching stat URLs passed in
    year (string): Indicates the stat year for df

    Returns:
    df (pandas dataframe): The final stat dataframe with valid HTML in the
    player/pitcher columns"""
    rel_dir = os.path.dirname(__file__)
    player_link_file = rel_dir + "/input/" + year + "/roster_data.csv"
    # Read in csv that contains player name and their personal page link
    link_df = pd.read_csv(player_link_file)

    # Create dict of (Name,Team):Link from roster data
    player_dict = dict(
        zip(
            (zip(link_df["Player"], link_df["Team"])),
            link_df["Link"],
        )
    )
    # Make keys from input df
    if suffix in ("PR", "PF"):
        convert_col = "Pitcher"
    else:
        convert_col = "Player"
    df["keys"] = list(zip(df[convert_col], df["Team"]))
    df["Link"] = df["keys"].map(player_dict).infer_objects().astype(str)
    # Convert raw link column to HTML code column
    df["Link"] = df.apply(build_html, args=(convert_col,), axis=1)
    # Swap HTML link col with original player name col, drop temp cols
    df[convert_col] = df["Link"]
    df = df.drop(["keys", "Link"], axis=1)

    # Check for the player link fix file (TODO: defunct?)
    player_link_fix_file = rel_dir + "/input/" + year + "/player_urls_fix.csv"
    if os.path.exists(player_link_fix_file):
        fix_df = pd.read_csv(player_link_fix_file)
        # Check year and suffix, fix if needed
        if int(year) in fix_df.Year.values and suffix in fix_df.Suffix.values:
            # Create dict of Player Name:Complete HTML tag
            fix_dict = dict(zip(fix_df["Original"], fix_df["Corrected"]))
            df[convert_col] = (
                df[convert_col]
                .map(fix_dict)
                .infer_objects()
                .fillna(df[convert_col])
                .astype(str)
            )
    return df


def translate_players(df, year):
    """Translates player names from Japanese to English using a csv file

    Parameters:
    df (pandas dataframe): A NPB stat dataframe containing player names

    Returns:
    df (pandas dataframe): The final stat dataframe with translated names"""
    rel_dir = os.path.dirname(__file__)
    translation_file = rel_dir + "/input/" + year + "/name_translations.csv"
    # Read in csv that contains player and team names in JP and EN
    translation_df = pd.read_csv(translation_file)
    # Create dict of (JP name,EN team):Eng name
    player_dict = dict(
        zip(
            (zip(translation_df["jp_name"], translation_df["en_team"])),
            translation_df["en_name"],
        )
    )
    df["keys"] = list(zip(df["Player"], df["Team"]))
    df["Player"] = (
        df["keys"]
        .map(player_dict)
        .infer_objects()
        .fillna(df["Player"])
        .astype(str)
    )
    df["Player"] = df["Player"].str.replace('"', "")
    df["Player"] = df["Player"].str.replace(",", "")
    return df


def build_html(row, name_col):
    """Insert the link and name_col text in a <a> tag, returns the tag

    Parameters:
    row (pandas series): A row of a dataframe
    name_col (str): The column name that contains the player/team names

    Returns:
    html_line (str): The <a> tag if there is a link, else just the team/player
    name"""
    if row["Link"] != "nan":
        html_line = f'<a href={row["Link"]}>{row[name_col]}</a>'
    else:
        html_line = row[name_col]
    return html_line


def make_zip(year_dir, suffix, year):
    """Groups key directories into a single zip for uploading/sending and
    makes a /zip/ directory to store the zip

    Parameters:
    year_dir (string): The directory that stores the raw, scraped NPB stats
    suffix (string): Types of files being zipped
        "S" = a given year's farm and npb directories
        "P" = a given year's plots directories
    year (string): The year of npb stats to group together"""
    zip_dir = os.path.join(year_dir, "zip")
    if not os.path.exists(zip_dir):
        os.mkdir(zip_dir)

    output_filename = ""
    if suffix == "S":
        temp_dir = os.path.join(year_dir, "/stats/temp")
        temp_dir = tempfile.mkdtemp()
        # Gather all stat dirs to put into temp
        shutil.copytree(
            year_dir + "/farm", temp_dir + "/stats/farm", dirs_exist_ok=True
        )
        shutil.copytree(
            year_dir + "/npb", temp_dir + "/stats/npb", dirs_exist_ok=True
        )
        output_filename = zip_dir + "/" + year + "upload"

    shutil.make_archive(output_filename, "zip", temp_dir)
    shutil.rmtree(temp_dir)
    print("Zip created at: " + output_filename + ".zip")


def check_input_files(rel_dir, scrape_year=datetime.now().year):
    """Checks that all input files are in the /input/ folder

    Parameters:
    rel_dir (string): The relative directory holding the project

    Returns:
    missing_files (bool): If needed files are missing, this is True, else
    False"""
    missing_files = False
    # Optional files
    player_link_fix_file = (
        rel_dir + "/input/" + scrape_year + "/player_urls_fix.csv"
    )
    if not os.path.exists(player_link_fix_file):
        print(
            "\nWARNING: No optional player link fix file detected. Provide a "
            "player_urls_fix.csv file in the /input/ directory to fix this.\n"
        )
    # Required files
    translation_file = (
        rel_dir + "/input/" + scrape_year + "/name_translations.csv"
    )
    if not os.path.exists(translation_file):
        print(
            "\nERROR: No player name translation file found, player names "
            "can't be translated...\nProvide a name_translations.csv file in"
            " the /input/ directory to fix this.\n"
        )
        missing_files = True
    player_link_file = rel_dir + "/input/" + scrape_year + "/roster_data.csv"
    if not os.path.exists(player_link_file):
        print(
            "\nERROR: No player link file found, table entries will not "
            "have links...\nProvide a roster_data.csv file in the /input/ "
            "directory to fix this.\n"
        )
        missing_files = True
    fip_file = rel_dir + "/input/" + scrape_year + "/fip_const.csv"
    if not os.path.exists(fip_file):
        print(
            "\nERROR: No FIP constant file found, calculations using FIP will "
            "be inaccurate...\nProvide a valid fip_const.csv file in the "
            "/input/ directory to fix this.\n"
        )
        missing_files = True
    pf_file = rel_dir + "/input/" + scrape_year + "/park_factors.csv"
    if not os.path.exists(pf_file):
        print(
            "\nERROR: No park factor file found, calculations using park "
            "factors will be inaccurate...\nProvide a valid park_factors.csv "
            "file in the /input/ directory to fix this.\n"
        )
        missing_files = True
    team_link_file = rel_dir + "/input/" + scrape_year + "/team_urls.csv"
    if not os.path.exists(team_link_file):
        print(
            "\nWARNING: No team link file found, table entries will not have "
            "links...\nProvide a team_urls.csv file in the /input/ directory "
            "to fix this to fix this.\n"
        )
        missing_files = True
    field_url_file = rel_dir + "/input/" + scrape_year + "/fielding_urls.csv"
    if not os.path.exists(field_url_file):
        print(
            "\nERROR: No fielding URL file found, raw fielding files will not "
            "be produced...\nProvide a valid fielding_urls.csv file in the "
            "/input/ directory to fix this.\n"
        )
        missing_files = True

    if missing_files is False:
        print("All needed input files present, continuing...")
    else:
        print("Missing needed input file(s), exiting...")
    return missing_files


def store_dataframe(df, store_dir, filename, mode):
    """
    Stores a DataFrame to disk as either a CSV file or a plain text file.

    Parameters:
        df (pandas.DataFrame): The DataFrame to store.
        store_dir (str): The directory where the file will be saved.
        filename (str): The name of the file to create.
        mode (str): The file format to use: "csv" for CSV format, "alt" for
        plain text.

    Returns:
        str: The full path to the stored file.
    """
    if not os.path.exists(store_dir):
        os.mkdir(store_dir)
    store_path = store_dir + "/" + filename
    if mode == "csv":
        df.to_csv(store_path, index=False)
    elif mode == "alt":
        df.to_string(store_path)
    return store_path


if __name__ == "__main__":
    main()
