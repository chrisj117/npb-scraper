import os
import sys
import shutil
import tempfile
import requests
import pandas as pd
import numpy as np
from time import sleep
from random import randint
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.error import HTTPError, URLError
import matplotlib.pyplot as plt


def main():
    print("NPB/Farm League Statistic Scraper")
    # Open the directory to store the scraped stat csv files
    relDir = os.path.dirname(__file__)
    statsDir = os.path.join(relDir, "stats")
    if not (os.path.exists(statsDir)):
        os.mkdir(statsDir)

    # TODO: make input files year specific (I.E. /input/2024, /input/2025, etc)
    # TODO: docs
    # TODO: combine translations and rosterData
    # TODO: add checking raw file existence in init() (also remove warnings)
    # TODO: merge and updated npbPlayerUrlScraper roster scraping to update
    # rosterData.csv
    # TODO: more robust error checking in init()s if empty Raw data comes in
    # TODO: merge npbPlayoffScraper.py functionality
    # TODO: standardize variable names with underscores
    # TODO: generate requirements.txt
    # TODO: unit tests
    # TODO: add arg "a" to always scrape newest year

    # Check for input files (all except playerUrlsFix.csv are required)
    if check_input_files(relDir) is False:
        print("Missing needed input file(s), exiting...")
        return -1

    # Check for scrapeYear command line arg
    if len(sys.argv) == 2:
        print(
            "ARGUMENTS DETECTED: "
            + str(sys.argv)
            + "\nSetting year to: "
            + str(sys.argv[1])
        )
        # Check year given
        scrapeYear = get_scrape_year(sys.argv[1])
        print("\nProgram will scrape and create upload zip for given year.")
        # Bypass all user input functions and set flags for scraping
        argBypass = True
        npbScrapeYN = "Y"
        farmScrapeYN = "Y"
        percentileYN = "Y"
        statZipYN = "Y"
        percentileZipYN = "Y"
    elif len(sys.argv) > 2:
        print("Too many arguments. Try passing in the desired stat year.")
        sys.exit("Exiting...")
    else:
        # Give user control if a year argument isn't passed in
        argBypass = False

    # Determine whether to scrape and/or generate player percentiles
    if argBypass is False:
        scrapeYear = get_scrape_year()
        npbScrapeYN = get_user_choice("R")
        farmScrapeYN = get_user_choice("F")
        percentileYN = get_user_choice("P")
        statZipYN = get_user_choice("Z")
        percentileZipYN = get_user_choice("PZ")

    # Create year directory
    yearDir = os.path.join(statsDir, scrapeYear)
    if not (os.path.exists(yearDir)):
        os.mkdir(yearDir)

    if npbScrapeYN == "Y":
        # TODO: refactor and put raw files in their own directory
        # Scrape regular season batting and pitching URLs
        get_daily_scores(yearDir, "R", scrapeYear)
        get_stats(yearDir, "BR", scrapeYear)
        get_stats(yearDir, "PR", scrapeYear)
        get_standings(yearDir, "C", scrapeYear)
        get_standings(yearDir, "P", scrapeYear)
        get_fielding(yearDir, "R", scrapeYear)
    # NPB Daily Scores
    npbDailyScores = DailyScoresData(statsDir, yearDir, "R", scrapeYear)
    # NPB Individual Fielding
    # NOTE: fielding must be organized before any player stats to obtain player
    # positions
    npbFielding = FieldingData(statsDir, yearDir, "R", scrapeYear)
    # NPB Team Fielding
    npbTeamFielding = TeamFieldingData(
        npbFielding.df, statsDir, yearDir, "R", scrapeYear
    )
    # NPB Standings
    # NOTE: standings must be organized before any player stats to calculate
    # correct IP/PA drop consts
    centralStandings = StandingsData(statsDir, yearDir, "C", scrapeYear)
    pacificStandings = StandingsData(statsDir, yearDir, "P", scrapeYear)
    # NPB Player stats
    npbBatPlayerStats = PlayerData(statsDir, yearDir, "BR", scrapeYear)
    npbPitchPlayerStats = PlayerData(statsDir, yearDir, "PR", scrapeYear)
    # Adding positions to batting stats
    npbBatPlayerStats.append_positions(npbFielding.df, npbPitchPlayerStats.df)
    # NPB Team stats
    npbBatTeamStats = TeamData(
        npbBatPlayerStats.df, statsDir, yearDir, "BR", scrapeYear
    )
    npbPitchTeamStats = TeamData(
        npbPitchPlayerStats.df, statsDir, yearDir, "PR", scrapeYear
    )
    # NPB team summary
    npbTeamSummary = TeamSummaryData(
        npbTeamFielding.df,
        centralStandings.df,
        pacificStandings.df,
        npbBatTeamStats.df,
        npbPitchTeamStats.df,
        statsDir,
        yearDir,
        "R",
        scrapeYear,
    )
    # NPB output
    npbDailyScores.output_final()
    npbBatPlayerStats.output_final()
    npbPitchPlayerStats.output_final()
    npbBatTeamStats.output_final()
    npbPitchTeamStats.output_final()
    centralStandings.output_final(npbBatTeamStats.df, npbPitchTeamStats.df)
    pacificStandings.output_final(npbBatTeamStats.df, npbPitchTeamStats.df)
    npbFielding.output_final()
    npbTeamFielding.output_final()
    npbTeamSummary.output_final()
    print("Regular season statistics finished!\n")

    if farmScrapeYN == "Y":
        get_stats(yearDir, "BF", scrapeYear)
        get_stats(yearDir, "PF", scrapeYear)
        get_standings(yearDir, "E", scrapeYear)
        get_standings(yearDir, "W", scrapeYear)
        get_fielding(yearDir, "F", scrapeYear)
    # Farm Fielding
    farmFielding = FieldingData(statsDir, yearDir, "F", scrapeYear)
    # NPB Team Fielding
    farmTeamFielding = TeamFieldingData(
        farmFielding.df, statsDir, yearDir, "F", scrapeYear
    )
    # Farm Standings
    easternStandings = StandingsData(statsDir, yearDir, "E", scrapeYear)
    westernStandings = StandingsData(statsDir, yearDir, "W", scrapeYear)
    # Farm Player stats
    farmBatPlayerStats = PlayerData(statsDir, yearDir, "BF", scrapeYear)
    farmPitchPlayerStats = PlayerData(statsDir, yearDir, "PF", scrapeYear)
    # Adding positions to batting stats
    farmBatPlayerStats.append_positions(
        farmFielding.df, farmPitchPlayerStats.df
    )
    # Farm Team stats
    farmBatTeamStats = TeamData(
        farmBatPlayerStats.df, statsDir, yearDir, "BF", scrapeYear
    )
    farmPitchTeamStats = TeamData(
        farmPitchPlayerStats.df, statsDir, yearDir, "PF", scrapeYear
    )
    # Farm output
    farmBatPlayerStats.output_final()
    farmPitchPlayerStats.output_final()
    farmBatTeamStats.output_final()
    farmPitchTeamStats.output_final()
    easternStandings.output_final(farmBatTeamStats.df, farmPitchTeamStats.df)
    westernStandings.output_final(farmBatTeamStats.df, farmPitchTeamStats.df)
    farmFielding.output_final()
    farmTeamFielding.output_final()
    print("Farm statistics finished!\n")

    # Generate player percentile plots
    if percentileYN == "Y":
        npbBatPlayerStats.generate_plots(yearDir, npbFielding.df)
        npbPitchPlayerStats.generate_plots(yearDir)
        farmBatPlayerStats.generate_plots(yearDir, farmFielding.df)
        farmPitchPlayerStats.generate_plots(yearDir)

    # Make upload zips for manual uploads
    # TODO: refactor and put zip files in their own directory
    if statZipYN == "Y":
        make_zip(yearDir, "S", scrapeYear)
    if percentileZipYN == "Y":
        make_zip(yearDir, "P", scrapeYear)

    if argBypass is False:
        input("Press Enter to exit. ")


class Stats:
    """Parent class Stats variables:
    statsDir (string): The dir that holds all year stats and player URL file
    suffix (string): Indicates league or farm/NPB reg season stats
    year (string): The year that the stats will cover
    yearDir (string):The directory to store relevant year statistics

    OOP hierarchy:
    stats (statsDir, yearDir, suffix, year)
        - individual stats (statsDir, suffix, year)
        - team stats (playerDf, statsDir, suffix, year)
        - standings stats (statsDir, suffix, year)

    Purpose: keeps dataframes in memory to pass around for other functions
    (I.E. IP/PA drop const calculations and standingsNewStats()), stat
    organization for Final and Alt files"""

    def __init__(self, statsDir, yearDir, suffix, year):
        self.statsDir = statsDir
        self.suffix = suffix
        self.year = year
        self.yearDir = yearDir


class PlayerData(Stats):
    def __init__(self, statsDir, yearDir, suffix, year):
        """PlayerData new variables:
        df (pandas dataframe): Holds an entire NPB league's individual
        batting/pitching stats"""
        super().__init__(statsDir, yearDir, suffix, year)
        # Initialize data frame to store stats
        self.df = pd.read_csv(
            self.yearDir + "/" + year + "StatsRaw" + suffix + ".csv"
        )
        # Modify df for correct stats
        if self.suffix == "BF" or self.suffix == "BR":
            self.org_bat()
        elif self.suffix == "PF" or self.suffix == "PR":
            self.org_pitch()

    def __str__(self):
        """Outputs the Alt view of the associated dataframe (no HTML team or
        player names, no csv formatting, shows entire df instead of only
        Leaders)"""
        return self.df.to_string()

    def output_final(self):
        """Outputs final files for upload using the filtered and organized
        stat dataframes (NOTE: IP and PA drop constants are determined in this
        function)"""
        # Make dir that will store alt views of the dataframes
        altDir = os.path.join(self.yearDir, "alt")
        if not (os.path.exists(altDir)):
            os.mkdir(altDir)
        # Make dirs that will store files uploaded to yakyucosmo.com
        uploadDir = self.yearDir
        if self.suffix == "PR" or self.suffix == "BR":
            uploadDir = os.path.join(self.yearDir, "npb")
            if not (os.path.exists(uploadDir)):
                os.mkdir(uploadDir)
        elif self.suffix == "PF" or self.suffix == "BF":
            uploadDir = os.path.join(self.yearDir, "farm")
            if not (os.path.exists(uploadDir)):
                os.mkdir(uploadDir)

        # Print organized dataframe to file
        newCsvAlt = altDir + "/" + self.year + "AltView" + self.suffix + ".csv"
        self.df.to_string(newCsvAlt)
        # Add blank Rank column for Wordpress table counter
        self.df["Rank"] = ""
        moveCol = self.df.pop("Rank")
        self.df.insert(0, "Rank", moveCol)
        # Make deep copy of original df to avoid HTML in df's team/player names
        finalDf = self.df.copy()
        # Convert player/team names to HTML that contains appropriate URLs
        if int(self.year) == datetime.now().year:
            finalDf = convert_player_to_html(finalDf, self.suffix, self.year)
        finalDf = convert_team_to_html(finalDf, "Abb")
        # Print final file with all players
        newCsvFinal = (
            uploadDir + "/" + self.year + "StatsFinal" + self.suffix + ".csv"
        )
        finalDf.to_csv(newCsvFinal, index=False)
        # Make deep copy again for leader's file
        leaderDf = self.df.copy()
        # Get df with number of games played by each team for IP/PA drop consts
        gameDf = self.get_team_games()
        # Add new column (called 'GTeam') for team's games played
        leaderDf = leaderDf.merge(gameDf, on="Team", suffixes=(None, "Team"))

        # AltView, Final, and Leader file output
        if self.suffix == "PR" or self.suffix == "PF":
            # Drop all players below the IP/PA threshold
            if self.suffix == "PF":
                leaderDf = leaderDf.drop(
                    leaderDf[leaderDf.IP < (leaderDf["GTeam"] * 0.8)].index
                )
            else:
                leaderDf = leaderDf.drop(
                    leaderDf[leaderDf.IP < leaderDf["GTeam"]].index
                )
            # Drop temp GTeamIP column
            leaderDf.drop(["GTeam"], axis=1, inplace=True)

            # Convert player/team names to HTML that contains appropriate URLs
            if int(self.year) == datetime.now().year:
                leaderDf = convert_player_to_html(
                    leaderDf, self.suffix, self.year
                )
            leaderDf = convert_team_to_html(leaderDf, "Abb")
            # Output leader file as a csv
            newCsvLeader = (
                uploadDir + "/" + self.year + "Leaders" + self.suffix + ".csv"
            )
            leaderDf.to_csv(newCsvLeader, index=False)

            print(
                "The pitching leaders file will be stored in: " + newCsvLeader
            )
            print(
                "An alternative view of the pitching results will be stored "
                "in: " + newCsvAlt
            )
            print(
                "The final organized pitching results will be stored in: "
                + newCsvFinal
            )

        # Leader file is calculated differently for batters
        elif self.suffix == "BR" or self.suffix == "BF":
            # Drop all players below the IP/PA threshold (PA gets rounded down)
            if self.suffix == "BF":
                leaderDf = leaderDf.drop(
                    leaderDf[
                        leaderDf.PA < np.floor((leaderDf["GTeam"] * 2.7))
                    ].index
                )
            else:
                leaderDf = leaderDf.drop(
                    leaderDf[
                        leaderDf.PA < np.floor((leaderDf["GTeam"] * 3.1))
                    ].index
                )
            # Drop temp GTeamIP column
            leaderDf.drop(["GTeam"], axis=1, inplace=True)

            # Convert player/team names to HTML that contains appropriate URLs
            if int(self.year) == datetime.now().year:
                leaderDf = convert_player_to_html(
                    leaderDf, self.suffix, self.year
                )
            leaderDf = convert_team_to_html(leaderDf, "Abb")
            # Output leader file as a csv
            newCsvLeader = (
                uploadDir + "/" + self.year + "Leaders" + self.suffix + ".csv"
            )
            leaderDf.to_csv(newCsvLeader, index=False)

            print(
                "The batting leaders file will be stored in: " + newCsvLeader
            )
            print(
                "An alternative view of the batting results will be stored "
                "in: " + newCsvAlt
            )
            print(
                "The final organized batting results will be stored in: "
                + newCsvFinal
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
        self.df["IP"] = convert_ip_column_in(self.df)

        # Counting stat column totals
        totalIP = self.df["IP"].sum()
        totalHR = self.df["HR"].sum()
        totalSO = self.df["SO"].sum()
        totalBB = self.df["BB"].sum()
        totalHB = self.df["HB"].sum()
        totalER = self.df["ER"].sum()
        totalBF = self.df["BF"].sum()
        totalERA = 9 * (totalER / totalIP)
        temp1 = 13 * totalHR
        temp2 = 3 * (totalBB + totalHB)
        temp3 = 2 * totalSO
        totalFIP = ((temp1 + temp2 - temp3) / totalIP) + select_fip_const(
            self.suffix, self.year
        )
        totalkwERA = round((4.80 - (10 * ((totalSO - totalBB) / totalBF))), 2)

        # Individual statistic calculations
        # Calculate kwERA
        self.df["kwERA"] = round(
            (4.80 - (10 * ((self.df["SO"] - self.df["BB"]) / self.df["BF"]))),
            2,
        )
        self.df = select_park_factor(self.df, self.suffix, self.year)
        tempERAP = 100 * ((totalERA * self.df["ParkF"]) / self.df["ERA"])
        self.df["ERA+"] = round(tempERAP, 0)
        self.df["ERA+"] = self.df["ERA+"].astype(str).replace("inf", "999")
        self.df["ERA+"] = self.df["ERA+"].astype(float)
        self.df["K%"] = round(self.df["SO"] / self.df["BF"], 3)
        self.df["BB%"] = round(self.df["BB"] / self.df["BF"], 3)
        self.df["K-BB%"] = round(self.df["K%"] - self.df["BB%"], 3)
        # Calculate FIP
        temp1 = 13 * self.df["HR"]
        temp2 = 3 * (self.df["BB"] + self.df["HB"])
        temp3 = 2 * self.df["SO"]
        self.df["FIP"] = round(
            ((temp1 + temp2 - temp3) / self.df["IP"])
            + select_fip_const(self.suffix, self.year),
            2,
        )
        # Calculate FIP-
        self.df["FIP-"] = round(
            (100 * (self.df["FIP"] / (totalFIP * self.df["ParkF"]))), 0
        )
        # Calculate WHIP
        self.df["WHIP"] = round(
            (self.df["BB"] + self.df["H"]) / self.df["IP"], 2
        )
        # Calculate HR%
        self.df["HR%"] = self.df["HR"] / self.df["BF"]
        # Calculate kwERA-
        self.df["kwERA-"] = round((100 * (self.df["kwERA"] / (totalkwERA))), 0)
        # Calculate Diff
        self.df["Diff"] = round((self.df["ERA"] - self.df["FIP"]), 2)

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
        formatMapping = {
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
        for key, value in formatMapping.items():
            self.df[key] = self.df[key].apply(value.format)

        # Replace all infs in batting stat cols
        self.df["ERA"] = self.df["ERA"].astype(str)
        self.df["ERA"] = self.df["ERA"].str.replace("inf", "")
        self.df["FIP"] = self.df["FIP"].astype(str)
        self.df["FIP"] = self.df["FIP"].str.replace("inf", "")
        self.df["FIP-"] = self.df["FIP-"].astype(str)
        self.df["FIP-"] = self.df["FIP-"].str.replace("inf", "")
        self.df["WHIP"] = self.df["WHIP"].astype(str)
        self.df["WHIP"] = self.df["WHIP"].str.replace("inf", "")
        self.df["Diff"] = self.df["Diff"].astype(str)
        self.df["Diff"] = self.df["Diff"].str.replace("nan", "")
        # Add age and throwing/batting arm columns
        colOrder = [
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
        if int(self.year) == datetime.now().year:
            self.df = add_roster_data(self.df, self.suffix)
            colOrder.insert(-1, "Age")
            colOrder.insert(-1, "T")
        if self.suffix == "PF":
            colOrder.remove("HLD")
        self.df = self.df[colOrder]
        # Changing .33 to .1 and .66 to .2 in the IP column
        self.df["IP"] = convert_ip_column_out(self.df)
        self.df = select_league(self.df, self.suffix)

    def org_bat(self):
        """Organize the raw batting stat csv and add additional stats"""
        # Unnecessary data removal
        # Remove all players if their PA is 0
        self.df = self.df.drop(self.df[self.df.PA == 0].index)
        # Drop last column
        self.df.drop(
            self.df.columns[len(self.df.columns) - 1], axis=1, inplace=True
        )

        # Counting stat column totals used in other calculations
        totalAB = self.df["AB"].sum()
        totalH = self.df["H"].sum()
        total2B = self.df["2B"].sum()
        total3B = self.df["3B"].sum()
        totalHR = self.df["HR"].sum()
        totalSF = self.df["SF"].sum()
        totalBB = self.df["BB"].sum()
        totalHP = self.df["HP"].sum()
        totalOBP = (totalH + totalBB + totalHP) / (
            totalAB + totalBB + totalHP + totalSF
        )
        totalSLG = (
            (totalH - total2B - total3B - totalHR)
            + (2 * total2B)
            + (3 * total3B)
            + (4 * totalHR)
        ) / totalAB

        # Individual statistic calculations
        self.df["OPS"] = round(self.df["SLG"] + self.df["OBP"], 3)
        self.df = select_park_factor(self.df, self.suffix, self.year)
        self.df["OPS+"] = round(
            100
            * ((self.df["OBP"] / totalOBP) + (self.df["SLG"] / totalSLG) - 1),
            0,
        )
        self.df["OPS+"] = self.df["OPS+"] / self.df["ParkF"]
        self.df["ISO"] = round(self.df["SLG"] - self.df["AVG"], 3)
        self.df["K%"] = round(self.df["SO"] / self.df["PA"], 3)
        self.df["BB%"] = round(self.df["BB"] / self.df["PA"], 3)
        self.df["BB/K"] = round(self.df["BB"] / self.df["SO"], 2)
        self.df["TTO%"] = (
            self.df["BB"] + self.df["SO"] + self.df["HR"]
        ) / self.df["PA"]
        self.df["TTO%"] = self.df["TTO%"].apply("{:.1%}".format)
        numer = self.df["H"] - self.df["HR"]
        denom = self.df["AB"] - self.df["SO"] - self.df["HR"] + self.df["SF"]
        self.df["BABIP"] = round((numer / denom), 3)

        # Remove temp Park Factor column
        self.df.drop("ParkF", axis=1, inplace=True)
        # "Mercedes Cristopher Crisostomo" name shortening to "Mercedes CC"
        self.df["Player"] = (
            self.df["Player"]
            .astype(str)
            .replace("Mercedes Cristopher Crisostomo", "Mercedes CC")
        )
        # "Tysinger Brandon Taiga" name shortening to "Tysinger Brandon"
        self.df["Player"] = (
            self.df["Player"]
            .astype(str)
            .replace("Mercedes Cristopher Crisostomo", "Mercedes CC")
        )
        # Number formatting
        formatMapping = {
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
        }
        for key, value in formatMapping.items():
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
        colOrder = [
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
            "Pos",
            "Team",
        ]
        if int(self.year) == datetime.now().year:
            self.df = add_roster_data(self.df, self.suffix)
            colOrder.insert(-2, "Age")
            colOrder.insert(-1, "B")
        self.df = self.df[colOrder]
        self.df = select_league(self.df, self.suffix)

    def get_team_games(self):
        """Combines Central and Pacific (NPB) or Eastern and Western (farm)
        team games played into a single dataframe

        Returns:
        ipPaDf (pandas dataframe): A dataframe with 2 columns: team name and
        # of games that team has played"""
        # Make new raw const file in write mode (made in writeStandingsStats())
        constDir = os.path.join(self.yearDir, "dropConst")
        if not (os.path.exists(constDir)):
            os.mkdir(constDir)

        # Read in the correct raw const files for reg season or farm
        # Regular season team,game files
        if self.suffix == "BR" or self.suffix == "PR":
            stdFile1 = constDir + "/" + self.year + "ConstRawC.csv"
            stdFile2 = constDir + "/" + self.year + "ConstRawP.csv"
        # Farm team,game files
        if self.suffix == "BF" or self.suffix == "PF":
            stdFile1 = constDir + "/" + self.year + "ConstRawW.csv"
            stdFile2 = constDir + "/" + self.year + "ConstRawE.csv"

        # Combine into 1 raw const df/file
        stdDf1 = pd.read_csv(stdFile1)
        stdDf2 = pd.read_csv(stdFile2)
        constStds = [stdDf1, stdDf2]
        ipPaDf = pd.concat(constStds)

        # DEBUG: this file should have all combined teams and games
        # newCsvName = (constDir + "/" + self.year + "Const" + self.suffix +
        # ".csv")
        # constFile = ipPaDf.to_string(newCsvName)
        return ipPaDf

    def append_positions(self, fieldDf, pitchDf):
        """Adds the primary position of a player to the player dataframe

        Parameters:
        fieldDf (pandas dataframe): Holds an entire NPB league's fielding stats
        pitchDf (pandas dataframe): Holds an entire NPB league's individual
        pitching stats"""
        # Create a temp df with players as rows and all pos they play as cols
        dfPivot = fieldDf.pivot_table(
            index="Player",
            columns="Pos",
            values="Inn",
            aggfunc="sum",
            fill_value=0,
        )
        # Append IP for position 1 (pitchers) as a new column "1"
        dfPivot = pd.merge(
            dfPivot,
            pitchDf[["Pitcher", "IP"]].rename(
                columns={"Pitcher": "Player", "IP": "1"}
            ),
            on="Player",
            how="outer",
        )
        # Fill NaN values in all colums with 0 (if needed)
        dfPivot = dfPivot.fillna(0)
        # Get primary positions
        dfPivot["Pos"] = dfPivot.apply(assign_primary_or_utl, axis=1)
        # Extract only the player_id and primary_position:
        tempPrimaryDf = dfPivot[["Player", "Pos"]]
        # Then merge if needed:
        self.df = pd.merge(self.df, tempPrimaryDf, on="Player", how="left")
        # Swap temp Pos with updated Pos, drop placeholder Pos, rename
        self.df["Pos_x"], self.df["Pos_y"] = self.df["Pos_y"], self.df["Pos_x"]
        self.df = self.df.drop("Pos_y", axis=1)
        self.df = self.df.rename(columns={"Pos_x": "Pos"})
        # NaN means player wasn't on fielding df and pitching df (N/A data) OR
        # was a pinch hitter
        self.df["Pos"] = self.df["Pos"].fillna("")
        return

    def generate_plots(self, storeDir, fieldDf=None):
        """Generates percentile plots for player statistics and saves them as
        PNG files.

        Parameters:
        storeDir (string): The directory where the generated plots will be
        stored.
        fieldDf (pandas dataframe, optional): Holds an entire NPB league's
        fielding stats. Required for calculating defensive metrics when
        generating batting percentile plots.

        Functionality:
        - Determines the relevant statistics to plot based on the suffix
        (e.g., batting or pitching).
        - Filters players based on minimum thresholds for plate appearances
        (batters) or innings pitched (pitchers).
        - Calculates percentiles for selected statistics and adjusts for
        metrics where lower values are better.
        - For batters, calculates a "Defense" metric using fielding stats
        if `fieldDf` is provided.
        - Creates horizontal bar plots for each player, showing their
        percentile ranks across the selected statistics.
        - Saves the plots as PNG files in a directory structure based on the
        suffix and year.

        Notes:
        - Requires matplotlib for generating plots.
        - Percentile calculations normalize values between 0 and 100.
        - Defensive metrics are only included for batters if `fieldDf` is
        provided.

        Output:
        - PNG files for each player's percentile plot are saved in the
        specified directory.
        - Prints the location of the generated plots to the console."""
        # Create dir for plots
        plotDir = os.path.join(storeDir, "plots")
        if not (os.path.exists(plotDir)):
            os.mkdir(plotDir)
        plotDir = os.path.join(plotDir, self.suffix)
        if not (os.path.exists(plotDir)):
            os.mkdir(plotDir)
        print("Generating " + self.suffix + " player percentile plots...")

        # Suffix determines stats to be put into percentiles
        # Players must meet IP criteria to avoid skewing percentiles
        if self.suffix == "PR" or self.suffix == "PF":
            nameCol = "Pitcher"
            plotCols = ["K-BB%", "BB%", "K%", "HR%", "WHIP", "FIP-", "ERA+"]
            invertCols = ["HR%", "WHIP", "FIP-", "BB%"]
            plotDf = self.df[self.df.IP > 25.0].copy()
        elif self.suffix == "BR" or self.suffix == "BF":
            nameCol = "Player"
            plotCols = ["Defense", "BB/K", "BB%", "K%", "BABIP", "ISO", "OPS+"]
            invertCols = ["K%"]
            plotDf = self.df[self.df.PA > 50.0].copy()

            # Defense stat calculation
            tempDf = fieldDf[nameCol].drop_duplicates()
            # Each TZR in fielding must have Pos Adj applied to it
            fieldDf["TZR"] = fieldDf["TZR"].apply(
                pd.to_numeric, errors="coerce"
            )
            fieldDf["TZR"] = fieldDf["TZR"].fillna(0)
            fieldDf["Pos Adj"] = fieldDf["Pos Adj"].apply(
                pd.to_numeric, errors="coerce"
            )
            fieldDf["TZR"] = fieldDf["TZR"] + fieldDf["Pos Adj"]
            # Combine all TZRs and Inn per player
            tempDf = pd.merge(
                tempDf,
                fieldDf.groupby(nameCol, as_index=False)["TZR"].sum(),
                on=nameCol,
            )
            tempDf = pd.merge(
                tempDf,
                fieldDf.groupby(nameCol, as_index=False)["Inn"].sum(),
                on=nameCol,
            )
            # Calculate Defense (similar to TZR/143) and prep for plotting
            tempDf["Defense"] = (tempDf["TZR"] / tempDf["Inn"]) * 1287
            plotDf = pd.merge(
                plotDf, tempDf[[nameCol, "Defense"]], on=nameCol, how="inner"
            )

        # Generate percentiles for given cols
        for col in plotCols:
            # Standardize all stat cols as floats
            if "%" in col:
                plotDf[col] = (
                    plotDf[col].str.rstrip("%").astype("float") / 100.0
                )
            else:
                plotDf[col] = plotDf[col].astype("float")
            plotDf[col] = plotDf[col].rank(pct=True)
            # Percentile adjustment (I.E. 0th percentile = lowest)
            plotDf[col] = (plotDf[col] - plotDf[col].min()) / (
                plotDf[col].max() - plotDf[col].min()
            )
            # invertCols are stats where lower = better
            if col in invertCols:
                plotDf[col] = 1.0 - plotDf[col]
            plotDf[col] = plotDf[col] * 100
            # Convert to whole numbers for display on bar
            plotDf[col] = plotDf[col].astype("int")

        # Generate percentile graphs for each player
        for player in plotDf[nameCol]:
            playerData = plotDf[plotDf[nameCol] == player][plotCols].T
            plt.figure(figsize=(8, 5))
            # Generate colors based on value
            colorVals = []
            for value in playerData[
                plotDf[plotDf[nameCol] == player].index[0]
            ]:
                if value < 10:
                    color = "#000066"
                elif value < 20:
                    color = "#0000CC"
                elif value < 30:
                    color = "#4D4DFF"
                elif value < 40:
                    color = "#B3B3FF"
                elif value < 50:
                    color = "#4A4A4A"
                elif value < 60:
                    color = "#4A2121"
                elif value < 70:
                    color = "#CC5C5A"
                elif value < 80:
                    color = "#8C2929"
                elif value < 90:
                    color = "#8C1212"
                elif value < 100:
                    color = "#660000"
                colorVals.append(color)
            barContainer = plt.barh(
                playerData.index,
                playerData[plotDf[plotDf[nameCol] == player].index[0]],
                color=colorVals,
                alpha=0.7,
            )
            # Display data values on the bars
            for bar in barContainer:
                # Determine where and how data appears on bar graph
                # 0 displays at edge of bar graph along with 1 and 2 (min
                # offset is -2)
                if bar.get_width() <= 2:
                    width = 0
                    dataVal = bar.get_width()
                # Never display 100 in percentiles, max is 99
                elif bar.get_width() >= 100:
                    width = bar.get_width() - 3
                    dataVal = 99
                # Smallest values should be closer to edge of bar
                elif bar.get_width() < 10:
                    width = bar.get_width() - 2
                    dataVal = bar.get_width()
                # Display values for double digit values
                else:
                    width = bar.get_width() - 3
                    dataVal = bar.get_width()
                plt.text(
                    width,  # Position the text relative to the bar
                    bar.get_y() + bar.get_height() / 2,  # Center vertically
                    f"{int(dataVal)}",
                    va="center",  # Align the text vertically
                    ha="left",  # Align the text horizontally
                    fontsize=9,
                    color="black",
                )
            # Graph and axis names, styles
            plt.xlabel("Percentile Rank")
            plt.title(f"{player} - Stat Percentiles")
            plt.xlim(0, 100)
            plt.grid(axis="x", linestyle="--", alpha=0.7)
            plt.savefig(
                plotDir
                + "/"
                + self.year
                + player.replace(" ", "")
                + self.suffix
                + ".png"
            )
            plt.close()

        print(
            self.suffix
            + " player percentile plots can be found at: "
            + plotDir
        )


class TeamData(Stats):
    def __init__(self, playerDf, statsDir, yearDir, suffix, year):
        """TeamData new variables:
        playerDf (pandas dataframe): Holds an entire NPB league's individual
        batting/pitching stats"""
        super().__init__(statsDir, yearDir, suffix, year)
        self.playerDf = playerDf.copy()
        # Initialize df for teams stats
        if self.suffix == "BF" or self.suffix == "BR":
            self.org_team_bat()
        elif self.suffix == "PF" or self.suffix == "PR":
            self.org_team_pitch()

    def __str__(self):
        """Outputs the Alt view of the associated dataframe (no HTML
        team or player names, no csv formatting, shows entire df instead of
        only Leaders)"""
        return self.df.to_string()

    def output_final(self):
        """Outputs final files for upload using the team stat dataframes"""
        # Make dir that will store alt views of the dataframes
        altDir = os.path.join(self.yearDir, "alt")
        if not (os.path.exists(altDir)):
            os.mkdir(altDir)
        # Make dirs that will store files uploaded to yakyucosmo.com
        uploadDir = self.yearDir
        if self.suffix == "PR" or self.suffix == "BR":
            uploadDir = os.path.join(self.yearDir, "npb")
            if not (os.path.exists(uploadDir)):
                os.mkdir(uploadDir)
        elif self.suffix == "PF" or self.suffix == "BF":
            uploadDir = os.path.join(self.yearDir, "farm")
            if not (os.path.exists(uploadDir)):
                os.mkdir(uploadDir)
        # Print organized dataframe to file
        newCsvAlt = altDir + "/" + self.year + "TeamAlt" + self.suffix + ".csv"
        self.df.to_string(newCsvAlt)
        # Add blank counter (#) column for Wordpress table counter
        self.df["#"] = ""
        moveCol = self.df.pop("#")
        self.df.insert(0, "#", moveCol)
        # Make output copy to avoid modifying original df
        finalDf = self.df.copy()
        # Insert HTML code for team names
        finalDf = convert_team_to_html(finalDf, "Full")
        # Print output file for upload
        newCsvFinal = (
            uploadDir + "/" + self.year + "Team" + self.suffix + ".csv"
        )
        finalDf.to_csv(newCsvFinal, index=False)

        # Pitching TeamAlt and Team file location outputs
        if self.suffix == "PR" or self.suffix == "PF":
            print(
                "The final organized team pitching results will be stored "
                "in: " + newCsvFinal
            )
            print(
                "An alternative view of team pitching results will be stored"
                "in: " + newCsvAlt
            )

        elif self.suffix == "BR" or self.suffix == "BF":
            print(
                "The final organized team batting results will be stored "
                "in: " + newCsvFinal
            )
            print(
                "An alternative view of team batting results will be stored "
                "in: " + newCsvAlt
            )

    def org_team_bat(self):
        """Outputs batting team stat files using the organized player stat
        dataframes"""
        # Initialize new row list with all possible teams
        rowArr = [
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
        # 2024 farm has 2 new teams
        if self.suffix == "BF" and int(self.year) >= 2024:
            rowArr.extend(["Oisix Albirex", "HAYATE Ventures"])

        # Initialize a list and put stat columns in first
        colArr = [
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
            "OPS+",
            "ISO",
            "BABIP",
            "TTO%",
            "K%",
            "BB%",
            "BB/K",
        ]

        teamBatList = []
        teamBatList.append(colArr)

        # Form team stat rows
        # REFACTOR (?)
        for row in rowArr:
            newTeamStat = [row]
            tempStatDf = self.playerDf[self.playerDf.Team == row]
            newTeamStat.append(tempStatDf["PA"].sum())
            newTeamStat.append(tempStatDf["AB"].sum())
            newTeamStat.append(tempStatDf["R"].sum())
            newTeamStat.append(tempStatDf["H"].sum())
            newTeamStat.append(tempStatDf["2B"].sum())
            newTeamStat.append(tempStatDf["3B"].sum())
            newTeamStat.append(tempStatDf["HR"].sum())
            newTeamStat.append(tempStatDf["TB"].sum())
            newTeamStat.append(tempStatDf["RBI"].sum())
            newTeamStat.append(tempStatDf["SB"].sum())
            newTeamStat.append(tempStatDf["CS"].sum())
            newTeamStat.append(tempStatDf["SH"].sum())
            newTeamStat.append(tempStatDf["SF"].sum())
            newTeamStat.append(tempStatDf["SO"].sum())
            newTeamStat.append(tempStatDf["BB"].sum())
            newTeamStat.append(tempStatDf["IBB"].sum())
            newTeamStat.append(tempStatDf["HP"].sum())
            newTeamStat.append(tempStatDf["GDP"].sum())
            totalH = tempStatDf["H"].sum()
            total2B = tempStatDf["2B"].sum()
            total3B = tempStatDf["3B"].sum()
            totalHR = tempStatDf["HR"].sum()
            totalSF = tempStatDf["SF"].sum()
            totalBB = tempStatDf["BB"].sum()
            totalHP = tempStatDf["HP"].sum()
            totalAB = tempStatDf["AB"].sum()
            totalAVG = round((totalH / totalAB), 3)
            newTeamStat.append(totalAVG)
            totalOBP = round(
                (
                    (totalH + totalBB + totalHP)
                    / (totalAB + totalBB + totalHP + totalSF)
                ),
                3,
            )
            newTeamStat.append(totalOBP)
            tempSLG1 = totalH - total2B - total3B - totalHR
            tempSLG2 = (2 * total2B) + (3 * total3B) + (4 * totalHR)
            totalSLG = round((((tempSLG1 + tempSLG2) / totalAB)), 3)
            newTeamStat.append(totalSLG)
            totalOPS = round((totalOBP + totalSLG), 3)
            newTeamStat.append(totalOPS)
            teamBatList.append(newTeamStat)

        # 2024 farm has 14 teams instead of 12
        if self.suffix == "BF" and int(self.year) >= 2024:
            teamConst = 14
        else:
            teamConst = 12
        # Getting league stat totals (last row to be appended to the dataframe)
        newTeamStat = ["League Average"]
        newTeamStat.append(round(self.playerDf["PA"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["AB"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["R"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["H"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["2B"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["3B"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["HR"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["TB"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["RBI"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["SB"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["CS"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["SH"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["SF"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["SO"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["BB"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["IBB"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["HP"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["GDP"].sum() / teamConst, 0))
        totalH = self.playerDf["H"].sum()
        total2B = self.playerDf["2B"].sum()
        total3B = self.playerDf["3B"].sum()
        totalHR = self.playerDf["HR"].sum()
        totalSF = self.playerDf["SF"].sum()
        totalBB = self.playerDf["BB"].sum()
        totalHP = self.playerDf["HP"].sum()
        totalAB = self.playerDf["AB"].sum()
        totalAVG = round((totalH / totalAB), 3)
        newTeamStat.append(totalAVG)
        totalOBP = round(
            (
                (totalH + totalBB + totalHP)
                / (totalAB + totalBB + totalHP + totalSF)
            ),
            3,
        )
        newTeamStat.append(totalOBP)
        totalSLG = round(
            (
                (
                    (
                        (totalH - total2B - total3B - totalHR)
                        + (2 * total2B)
                        + (3 * total3B)
                        + (4 * totalHR)
                    )
                    / totalAB
                )
            ),
            3,
        )
        newTeamStat.append(totalSLG)
        totalOPS = round((totalOBP + totalSLG), 3)
        newTeamStat.append(totalOPS)
        teamBatList.append(newTeamStat)

        # Initialize new team stat dataframe
        self.df = pd.DataFrame(teamBatList)
        # Import adds extra top row of numbers which misaligns columns
        # Replace with proper row and drop extra number row
        self.df.columns = self.df.iloc[0]
        self.df.drop(index=0, axis=1, inplace=True)
        # Create park factors for any remaining team stats
        # Team OPS+ needs park factors
        self.df = select_park_factor(self.df, self.suffix, self.year)

        # Total OPS of the teams / total OPS of the league
        self.df["OPS+"] = round(
            100
            * ((self.df["OBP"] / totalOBP) + (self.df["SLG"] / totalSLG) - 1),
            0,
        )
        self.df["OPS+"] = self.df["OPS+"] / self.df["ParkF"]
        self.df["ISO"] = round(self.df["SLG"] - self.df["AVG"], 3)
        self.df["K%"] = round(self.df["SO"] / self.df["PA"], 3)
        self.df["BB%"] = round(self.df["BB"] / self.df["PA"], 3)
        self.df["BB/K"] = round(self.df["BB"] / self.df["SO"], 2)
        self.df["TTO%"] = (
            self.df["BB"] + self.df["SO"] + self.df["HR"]
        ) / self.df["PA"]
        self.df["TTO%"] = self.df["TTO%"].apply("{:.1%}".format)
        numer = self.df["H"] - self.df["HR"]
        denom = self.df["AB"] - self.df["SO"] - self.df["HR"] + self.df["SF"]
        self.df["BABIP"] = round((numer / denom), 3)

        # Remove temp Park Factor column
        self.df.drop("ParkF", axis=1, inplace=True)
        # Number formatting
        formatMapping = {
            "BB%": "{:.1%}",
            "K%": "{:.1%}",
            "AVG": "{:.3f}",
            "OBP": "{:.3f}",
            "SLG": "{:.3f}",
            "OPS": "{:.3f}",
            "ISO": "{:.3f}",
            "BABIP": "{:.3f}",
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
        }
        for key, value in formatMapping.items():
            self.df[key] = self.df[key].apply(value.format)

        # Add "League" column
        self.df = select_league(self.df, self.suffix)

    def org_team_pitch(self):
        """Outputs pitching team stat files using the organized player stat
        dataframes"""
        # IP column ".1 .2 .3" calculation fix
        self.playerDf["IP"] = convert_ip_column_in(self.playerDf)
        # Initialize new row list with all possible teams
        rowArr = [
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
            rowArr.extend(["Oisix Albirex", "HAYATE Ventures"])

        # Initialize a list and put team columns in first
        colArr = [
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
        # Farm pitching stats have no HLD
        if self.suffix != "PF":
            colArr.insert(4, "HLD")

        teamPitList = []
        teamPitList.append(colArr)

        # Form team stat rows and collect all COUNTING stats
        # TODO: REFACTOR (?)
        for row in rowArr:
            newTeamStat = [row]
            tempStatDf = self.playerDf[self.playerDf.Team == row]
            newTeamStat.append(tempStatDf["W"].sum())
            newTeamStat.append(tempStatDf["L"].sum())
            newTeamStat.append(tempStatDf["SV"].sum())
            # For whatever reason, official NPB farm pitching is missing HLD
            if self.suffix == "PR":
                newTeamStat.append(tempStatDf["HLD"].sum())
            newTeamStat.append(tempStatDf["CG"].sum())
            newTeamStat.append(tempStatDf["SHO"].sum())
            newTeamStat.append(tempStatDf["BF"].sum())
            newTeamStat.append(tempStatDf["IP"].sum())
            newTeamStat.append(tempStatDf["H"].sum())
            newTeamStat.append(tempStatDf["HR"].sum())
            newTeamStat.append(tempStatDf["SO"].sum())
            newTeamStat.append(tempStatDf["BB"].sum())
            newTeamStat.append(tempStatDf["IBB"].sum())
            newTeamStat.append(tempStatDf["HB"].sum())
            newTeamStat.append(tempStatDf["WP"].sum())
            newTeamStat.append(tempStatDf["R"].sum())
            newTeamStat.append(tempStatDf["ER"].sum())
            teamPitList.append(newTeamStat)

        # Getting league stat averages for rate stats (last row to be appended)
        if self.suffix == "PF" and int(self.year) >= 2024:
            teamConst = 14
        else:
            teamConst = 12
        # League stat row formation
        newTeamStat = ["League Average"]
        newTeamStat.append(round(self.playerDf["W"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["L"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["SV"].sum() / teamConst, 0))
        if self.suffix == "PR":
            newTeamStat.append(
                round(self.playerDf["HLD"].sum() / teamConst, 0)
            )
        newTeamStat.append(round(self.playerDf["CG"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["SHO"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["BF"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["IP"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["H"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["HR"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["SO"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["BB"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["IBB"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["HB"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["WP"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["R"].sum() / teamConst, 0))
        newTeamStat.append(round(self.playerDf["ER"].sum() / teamConst, 0))
        teamPitList.append(newTeamStat)

        # League totals that are needed for other calculations
        totalIP = self.playerDf["IP"].sum()
        totalHR = self.playerDf["HR"].sum()
        totalSO = self.playerDf["SO"].sum()
        totalBB = self.playerDf["BB"].sum()
        totalHB = self.playerDf["HB"].sum()
        totalER = self.playerDf["ER"].sum()
        totalBF = self.playerDf["BF"].sum()
        totalERA = 9 * (totalER / totalIP)

        # Initialize new team stat dataframe
        self.df = pd.DataFrame(teamPitList)
        # Import adds extra top row of numbers which misaligns columns,
        # replace with proper row and drop extra number row
        self.df.columns = self.df.iloc[0]
        self.df.drop(index=0, axis=1, inplace=True)
        # Create park factor col to use for any remaining team stats
        self.df = select_park_factor(self.df, self.suffix, self.year)
        # League totals have park factor as 1.000
        self.df["ParkF"] = self.df["ParkF"].replace(0.000, 1.000)

        # Calculations for RATE stats
        self.df["ERA"] = round(9 * (self.df["ER"] / self.df["IP"]), 2)
        self.df["ERA+"] = 100 * (totalERA * self.df["ParkF"]) / self.df["ERA"]
        self.df["kwERA"] = round(
            (4.80 - (10 * ((self.df["SO"] - self.df["BB"]) / self.df["BF"]))),
            2,
        )
        totalkwERA = round((4.80 - (10 * ((totalSO - totalBB) / totalBF))), 2)
        self.df["K%"] = round(self.df["SO"] / self.df["BF"], 3)
        self.df["BB%"] = round(self.df["BB"] / self.df["BF"], 3)
        self.df["K-BB%"] = round(self.df["K%"] - self.df["BB%"], 3)
        temp1 = 13 * self.df["HR"]
        temp2 = 3 * (self.df["BB"] + self.df["HB"])
        temp3 = 2 * self.df["SO"]
        self.df["FIP"] = round(
            ((temp1 + temp2 - temp3) / self.df["IP"])
            + select_fip_const(self.suffix, self.year),
            2,
        )
        temp1 = 13 * totalHR
        temp2 = 3 * (totalBB + totalHB)
        temp3 = 2 * totalSO
        totalFIP = ((temp1 + temp2 - temp3) / totalIP) + select_fip_const(
            self.suffix, self.year
        )
        # NO PARK FACTOR TEST
        # self.df['FIP-'] = round((100 * (self.df['FIP'] / (totalFIP))), 0)
        self.df["FIP-"] = round(
            (100 * (self.df["FIP"] / (totalFIP * self.df["ParkF"]))), 0
        )
        self.df["WHIP"] = round(
            (self.df["BB"] + self.df["H"]) / self.df["IP"], 2
        )
        self.df["Diff"] = self.df["ERA"] - self.df["FIP"]
        self.df["HR%"] = self.df["HR"] / self.df["BF"]
        self.df["kwERA-"] = round((100 * (self.df["kwERA"] / totalkwERA)), 0)

        # Remove temp Park Factor column
        self.df.drop("ParkF", axis=1, inplace=True)
        # Number formatting
        formatMapping = {
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
        for key, value in formatMapping.items():
            self.df[key] = self.df[key].apply(value.format)
        # Only regular NPB pitching has HLD column
        if self.suffix == "PR":
            self.df["HLD"] = self.df["HLD"].apply("{:.0f}".format)
        # Changing .33 to .1 and .66 to .2 in the IP column
        self.df["IP"] = convert_ip_column_out(self.df)

        # Add "League" column
        self.df = select_league(self.df, self.suffix)


class StandingsData(Stats):
    def __init__(self, statsDir, yearDir, suffix, year):
        """StandingsData new variables:
        df (pandas dataframe): Holds a league's standings stats
        constDf (pandas dataframe): 2 column df with team names and the games
        they've played"""
        super().__init__(statsDir, yearDir, suffix, year)
        # Initialize dataframe and year dir to store stats
        self.df = pd.read_csv(
            self.yearDir + "/" + year + "StandingsRaw" + suffix + ".csv"
        )

        # Do bare minimum to prepare IP/PA const file for PlayerData objects
        # Further organization of stats comes later in output_final()
        # Drop last unnamed column
        self.df.drop(
            self.df.columns[len(self.df.columns) - 1], axis=1, inplace=True
        )
        # Replace all team entries with correct names from dictionary
        teamDict = {
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
        for team in teamDict:
            self.df.loc[self.df.Team == team, "Team"] = teamDict[team]
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
        self.constDf = self.df[["Team", "G"]]
        constDir = os.path.join(self.yearDir, "dropConst")
        if not (os.path.exists(constDir)):
            os.mkdir(constDir)
        newCsvConst = (
            constDir + "/" + self.year + "ConstRaw" + self.suffix + ".csv"
        )
        self.constDf.to_csv(newCsvConst, index=False)

    def __str__(self):
        """Outputs the Alt view of the associated dataframe (no HTML
        team or player names, no csv formatting, shows entire df instead of
        only Leaders)"""
        return self.df.to_string()

    def output_final(self, tbDf, tpDf):
        """Outputs final files using the standings dataframes

        Parameters:
        tbDf (pandas dataframe): An organized NPB team batting stat dataframe
        tpDf (pandas dataframe): An organized NPB team pitching stat dataframe
        """
        # Organize standings
        self.org_standings(tbDf, tpDf)

        # Make dir that will store files uploaded to yakyucosmo.com
        if self.suffix == "C" or self.suffix == "P":
            uploadDir = os.path.join(self.yearDir, "npb")
            if not (os.path.exists(uploadDir)):
                os.mkdir(uploadDir)
        elif self.suffix == "W" or self.suffix == "E":
            uploadDir = os.path.join(self.yearDir, "farm")
            if not (os.path.exists(uploadDir)):
                os.mkdir(uploadDir)
        else:
            uploadDir = self.yearDir
        # Make dir that will store alt views of the dataframes
        altDir = os.path.join(self.yearDir, "alt")
        if not (os.path.exists(altDir)):
            os.mkdir(altDir)

        # Print organized dataframe to file
        newCsvAlt = (
            altDir + "/" + self.year + "StandingsAlt" + self.suffix + ".csv"
        )
        self.df.to_string(newCsvAlt)
        # Add blank counter (#) column for Wordpress table counter
        self.df["#"] = ""
        moveCol = self.df.pop("#")
        self.df.insert(0, "#", moveCol)
        # Insert HTML code for team names
        finalDf = self.df.copy()
        finalDf = convert_team_to_html(finalDf, "Full")
        # Create Standings file name
        newCsvFinal = (
            uploadDir
            + "/"
            + self.year
            + "StandingsFinal"
            + self.suffix
            + ".csv"
        )
        finalDf.to_csv(newCsvFinal, index=False)
        # Convert the standings to a string and output to user
        stdDict = {
            "C": "Central",
            "E": "Eastern",
            "W": "Western",
            "P": "Pacific",
        }

        print(
            "The final " + stdDict[self.suffix] + " standings will be stored"
            " in: " + newCsvFinal
        )
        print(
            "An alternative view of the "
            + stdDict[self.suffix]
            + " standings will be stored in: "
            + newCsvAlt
        )

    def org_standings(self, tbDf, tpDf):
        """Organize the standings stat csv and adds new stats (RS, RA, and
        XPCT) that incorporate team data

        Parameters:
        tbDf (pandas dataframe): An organized NPB team batting stat dataframe
        tpDf (pandas dataframe): An organized NPB team pitching stat dataframe
        """
        # Merge team batting column to create 'RS'
        self.df = pd.merge(self.df, tbDf[["Team", "R"]], on="Team", how="left")
        self.df.rename(columns={"R": "RS"}, inplace=True)
        self.df["RS"] = self.df["RS"].astype(float)
        # Merge team pitching column to create 'RA'
        self.df = pd.merge(self.df, tpDf[["Team", "R"]], on="Team", how="left")
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
        formatMapping = {
            "PCT": "{:.3f}",
            "XPCT": "{:.3f}",
            "RS": "{:.0f}",
            "RA": "{:.0f}",
            "Diff": "{:.0f}",
        }
        for key, value in formatMapping.items():
            self.df[key] = self.df[key].apply(value.format)


class FieldingData(Stats):
    def __init__(self, statsDir, yearDir, suffix, year):
        """FieldingData new variables:
        df (pandas dataframe): Holds the individual fielding stats"""
        super().__init__(statsDir, yearDir, suffix, year)
        # Initialize data frame to store stats
        self.df = pd.read_csv(
            self.yearDir + "/" + year + "FieldingRaw" + suffix + ".csv"
        )
        # Modify df for correct stats
        self.org_fielding()

    def __str__(self):
        """Outputs the Alt view of the associated dataframe (no HTML
        team or player names, no csv formatting)"""
        return self.df.to_string()

    def output_final(self):
        """Outputs final files using the fielding dataframes"""
        # Make dir that will store alt views of the dataframes
        altDir = os.path.join(self.yearDir, "alt")
        if not (os.path.exists(altDir)):
            os.mkdir(altDir)
        # Make dirs that will store files uploaded to yakyucosmo.com
        uploadDir = self.yearDir
        if self.suffix == "R":
            uploadDir = os.path.join(self.yearDir, "npb")
            if not (os.path.exists(uploadDir)):
                os.mkdir(uploadDir)
        elif self.suffix == "F":
            uploadDir = os.path.join(self.yearDir, "farm")
            if not (os.path.exists(uploadDir)):
                os.mkdir(uploadDir)

        # Print organized dataframe to file
        newCsvAlt = (
            altDir + "/" + self.year + "FieldingAlt" + self.suffix + ".csv"
        )
        self.df.to_string(newCsvAlt)
        # Add blank Rank column for Wordpress table counter
        self.df["Rank"] = ""
        moveCol = self.df.pop("Rank")
        self.df.insert(0, "Rank", moveCol)
        # Make deep copy of original df to avoid HTML in df's team/player names
        finalDf = self.df.copy()
        # Convert player/team names to HTML that contains appropriate URLs
        if int(self.year) == datetime.now().year:
            finalDf = convert_player_to_html(finalDf, self.suffix, self.year)
        finalDf = convert_team_to_html(finalDf, "Abb")
        # Print final file with all players
        newCsvFinal = (
            uploadDir
            + "/"
            + self.year
            + "FieldingFinal"
            + self.suffix
            + ".csv"
        )
        finalDf.to_csv(newCsvFinal, index=False)

        if self.suffix == "R":
            print(
                "An alternative view of the regular season individual fielding"
                " results will be stored in: " + newCsvAlt
            )
            print(
                "The final organized regular season individual fielding "
                "results will be stored in: " + newCsvFinal
            )
        elif self.suffix == "F":
            print(
                "An alternative view of the farm individual fielding results "
                "will be stored in: " + newCsvAlt
            )
            print(
                "The final organized farm individual fielding results will be "
                "stored in: " + newCsvFinal
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
        posDict = {
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
            .map(posDict)
            .infer_objects()
            .fillna(self.df["Pos"])
            .astype(str)
        )
        # Translate team and player names
        teamDict = {
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
            .map(teamDict)
            .infer_objects()
            .fillna(self.df["Team"])
            .astype(str)
        )
        self.df = translate_players(self.df)
        # TZR/143 calculation and cleaning
        self.df["TZR"] = self.df["TZR"].astype(str).replace("-", "inf")
        self.df["TZR"] = self.df["TZR"].astype(float)
        self.df["TZR/143"] = (self.df["TZR"] / self.df["Inn"]) * 1287
        self.df = self.df.round({"TZR/143": 1})
        self.df["TZR/143"] = self.df["TZR/143"].astype(str).replace("inf", "")
        self.df["TZR"] = self.df["TZR"].astype(str).replace("inf", "")
        # Innings conversion
        self.df["Inn"] = convert_ip_column_out(self.df)
        # Add League and Age cols
        self.df = select_league(self.df, self.suffix)
        self.df = add_roster_data(self.df, self.suffix)
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
    def __init__(self, fieldingDf, statsDir, yearDir, suffix, year):
        """TeamFieldingData new variables:
        fieldingDf (pandas dataframe): Holds the individual fielding stats df
        df (pandas dataframe): Holds a team's fielding stats"""
        super().__init__(statsDir, yearDir, suffix, year)
        # Initialize data frame to store individual stats
        self.fieldingDf = fieldingDf.copy()
        self.df = pd.DataFrame()
        # Modify df for correct stats
        self.org_team_fielding()

    def __str__(self):
        """Outputs the Alt view of the associated dataframe (no HTML
        team or player names, no csv formatting)"""
        return self.df.to_string()

    def output_final(self):
        """Outputs final files using the team fielding dataframes"""
        # Make dir that will store alt views of the dataframes
        altDir = os.path.join(self.yearDir, "alt")
        if not (os.path.exists(altDir)):
            os.mkdir(altDir)
        # Make dirs that will store files uploaded to yakyucosmo.com
        uploadDir = self.yearDir
        if self.suffix == "R":
            uploadDir = os.path.join(self.yearDir, "npb")
            if not (os.path.exists(uploadDir)):
                os.mkdir(uploadDir)
        elif self.suffix == "F":
            uploadDir = os.path.join(self.yearDir, "farm")
            if not (os.path.exists(uploadDir)):
                os.mkdir(uploadDir)

        # Print organized dataframe to file
        newCsvAlt = (
            altDir + "/" + self.year + "TeamFieldingAlt" + self.suffix + ".csv"
        )
        self.df.to_string(newCsvAlt)
        # Add blank # column for Wordpress table counter
        self.df["#"] = ""
        moveCol = self.df.pop("#")
        self.df.insert(0, "#", moveCol)
        # Make deep copy of original df to avoid HTML in df's team/player names
        finalDf = self.df.copy()
        # Convert team names to HTML that contains appropriate URLs
        finalDf = convert_team_to_html(finalDf, "Full")
        # Print final file with all players
        newCsvFinal = (
            uploadDir
            + "/"
            + self.year
            + "TeamFieldingFinal"
            + self.suffix
            + ".csv"
        )
        finalDf.to_csv(newCsvFinal, index=False)

        if self.suffix == "R":
            print(
                "An alternative view of the regular season team fielding "
                "results will be stored in: " + newCsvAlt
            )
            print(
                "The final organized regular season team fielding results "
                "will be stored in: " + newCsvFinal
            )
        elif self.suffix == "F":
            print(
                "An alternative view of the farm team fielding results will "
                "be stored in: " + newCsvAlt
            )
            print(
                "The final organized farm team fielding results will be stored"
                " in: " + newCsvFinal
            )

    def org_team_fielding(self):
        """Organize the team fielding stat csv using the individual fielding
        stats"""
        # Convert cols that are numeric to float
        cols = self.fieldingDf.columns.drop(["Team", "League"])
        self.fieldingDf[cols] = self.fieldingDf[cols].apply(
            pd.to_numeric, errors="coerce"
        )
        # Group stats by team and append to team dataframe
        self.df["Team"] = self.fieldingDf["Team"].unique()
        self.df = pd.merge(
            self.df,
            self.fieldingDf.groupby("Team", as_index=False)["TZR"].sum(),
        )
        self.df = pd.merge(
            self.df,
            self.fieldingDf.groupby("Team", as_index=False)["Inn"].sum(),
        )
        # TODO: REMOVE (DEBUG?)
        # self.df['Inn'] = convert_ip_column_in(self.df)
        self.df["TZR/143"] = (self.df["TZR"] / self.df["Inn"]) * 1287
        self.df = pd.merge(
            self.df,
            self.fieldingDf.groupby("Team", as_index=False)["RngR"].sum(),
        )
        self.df = pd.merge(
            self.df,
            self.fieldingDf.groupby("Team", as_index=False)["ARM"].sum(),
        )
        self.df = pd.merge(
            self.df,
            self.fieldingDf.groupby("Team", as_index=False)["DPR"].sum(),
        )
        self.df = pd.merge(
            self.df,
            self.fieldingDf.groupby("Team", as_index=False)["ErrR"].sum(),
        )
        self.df = pd.merge(
            self.df,
            self.fieldingDf.groupby("Team", as_index=False)["Framing"].sum(),
        )
        self.df = pd.merge(
            self.df,
            self.fieldingDf.groupby("Team", as_index=False)["Blocking"].sum(),
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
        formatMapping = {
            "TZR": "{:.1f}",
            "TZR/143": "{:.1f}",
            "RngR": "{:.1f}",
            "ARM": "{:.1f}",
            "DPR": "{:.1f}",
            "ErrR": "{:.1f}",
            "Framing": "{:.1f}",
            "Blocking": "{:.1f}",
        }
        for key, value in formatMapping.items():
            self.df[key] = self.df[key].apply(value.format)


class TeamSummaryData(Stats):
    def __init__(
        self,
        teamFieldingDf,
        standings1Df,
        standings2Df,
        teamBatDf,
        teamPitchDf,
        statsDir,
        yearDir,
        suffix,
        year,
    ):
        """TeamSummaryData new variables:
        teamFieldingDf (pandas dataframe): Holds the team fielding stats df
        standings1Df (pandas dataframe): Holds the first half of the standings
        standings2Df (pandas dataframe): Holds the second half of the standings
        teamBatDf (pandas dataframe): Holds the team batting stats df
        teamPitchDf (pandas dataframe): Holds the team pitching stats df
        df (pandas dataframe): Holds a team's summarized stats"""
        super().__init__(statsDir, yearDir, suffix, year)
        # Initialize data frames to store team stats
        self.teamFieldingDf = teamFieldingDf
        self.standingsDf = pd.concat([standings1Df, standings2Df])
        self.teamBatDf = teamBatDf
        self.teamPitchDf = teamPitchDf
        self.df = pd.DataFrame()
        # Modify df for correct stats
        self.org_team_summary()

    def __str__(self):
        """Outputs the Alt view of the associated dataframe (no HTML
        team or player names, no csv formatting)"""
        return self.df.to_string()

    def output_final(self):
        """Outputs final files using the team summary dataframes"""
        # Make dir that will store alt views of the dataframes
        altDir = os.path.join(self.yearDir, "alt")
        if not (os.path.exists(altDir)):
            os.mkdir(altDir)
        # Make dirs that will store files uploaded to yakyucosmo.com
        uploadDir = self.yearDir
        if self.suffix == "R":
            uploadDir = os.path.join(self.yearDir, "npb")
            if not (os.path.exists(uploadDir)):
                os.mkdir(uploadDir)
        elif self.suffix == "F":
            uploadDir = os.path.join(self.yearDir, "farm")
            if not (os.path.exists(uploadDir)):
                os.mkdir(uploadDir)

        # Print organized dataframe to file
        newCsvAlt = (
            altDir + "/" + self.year + "TeamSummaryAlt" + self.suffix + ".csv"
        )
        self.df.to_string(newCsvAlt)
        # Add blank Rank column for Wordpress table counter
        self.df["#"] = ""
        moveCol = self.df.pop("#")
        self.df.insert(0, "#", moveCol)
        # Make deep copy of original df to avoid HTML in df's team/player names
        finalDf = self.df.copy()
        # Convert team names to HTML that contains appropriate URLs
        finalDf = convert_team_to_html(finalDf, "Full")
        # Print final file with all players
        newCsvFinal = (
            uploadDir
            + "/"
            + self.year
            + "TeamSummaryFinal"
            + self.suffix
            + ".csv"
        )
        finalDf.to_csv(newCsvFinal, index=False)

        if self.suffix == "R":
            print(
                "An alternative view of the regular season team summary "
                "results will be stored in: " + newCsvAlt
            )
            print(
                "The final organized regular season team summary results will "
                "be stored in: " + newCsvFinal
            )
        elif self.suffix == "F":
            print(
                "An alternative view of the farm team summary results will "
                "be stored in: " + newCsvAlt
            )
            print(
                "The final organized farm team summary results will be stored "
                "in: " + newCsvFinal
            )

    def org_team_summary(self):
        """Organize the team summary stat csv using the team stat dfs"""
        # Group stats by team and append to team dataframe
        self.df["Team"] = self.teamFieldingDf["Team"].tolist()
        self.df = pd.merge(
            self.df,
            self.teamPitchDf[["Team", "W", "L", "ERA+", "FIP-", "K-BB%", "R"]],
            on="Team",
            how="left",
        )
        self.df.rename(columns={"R": "RA"}, inplace=True)
        self.df = pd.merge(
            self.df,
            self.teamBatDf[["Team", "HR", "SB", "OPS+", "R"]],
            on="Team",
            how="left",
        )
        self.df.rename(columns={"R": "RS"}, inplace=True)
        self.df = pd.merge(
            self.df, self.standingsDf[["Team", "PCT"]], on="Team", how="left"
        )
        self.df["Diff"] = self.df["RS"].astype(int) - self.df["RA"].astype(int)
        self.df = pd.merge(
            self.df,
            self.teamFieldingDf[["Team", "TZR"]],
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
                "TZR",
            ]
        ]
        # Number formatting
        formatMapping = {"PCT": "{:.3f}"}
        for key, value in formatMapping.items():
            self.df[key] = self.df[key].apply(value.format)


class DailyScoresData(Stats):
    def __init__(self, statsDir, yearDir, suffix, year):
        """DailyScores new variables:
        df (pandas dataframe): Holds the scores of the games"""
        super().__init__(statsDir, yearDir, suffix, year)
        # Initialize dataframe to store scores
        self.df = pd.read_csv(
            self.yearDir + "/" + year + "DailyScoresRaw" + suffix + ".csv"
        )
        # Modify df for correct stats
        self.org_daily_scores()

    def __str__(self):
        """Outputs the Alt view of the associated dataframe (no HTML
        team or player names, no csv formatting)"""
        return self.df.to_string()

    def output_final(self):
        """Outputs final files using the daily score dataframes"""
        # Make dir that will store alt views of the dataframes
        altDir = os.path.join(self.yearDir, "alt")
        if not (os.path.exists(altDir)):
            os.mkdir(altDir)
        # Make dirs that will store files uploaded to yakyucosmo.com
        uploadDir = self.yearDir
        if self.suffix == "R":
            uploadDir = os.path.join(self.yearDir, "npb")
            if not (os.path.exists(uploadDir)):
                os.mkdir(uploadDir)
        elif self.suffix == "F":
            uploadDir = os.path.join(self.yearDir, "farm")
            if not (os.path.exists(uploadDir)):
                os.mkdir(uploadDir)

        # Print organized dataframe to file
        newCsvAlt = (
            altDir + "/" + self.year + "DailyScoresAlt" + self.suffix + ".csv"
        )
        self.df.to_string(newCsvAlt)
        # Make deep copy of original df to avoid HTML in df's team/player names
        finalDf = self.df.copy()
        # Convert team names to HTML that contains appropriate URLs
        finalDf = convert_team_to_html(finalDf, None)
        # Blank out score column names, rename team columns
        finalDf.rename(
            columns={
                "HomeTeam": "Home",
                "RunsHome": "",
                "RunsAway": "",
                "AwayTeam": "Away",
            },
            inplace=True,
        )
        # Print final file with most recent game scores
        newCsvFinal = (
            uploadDir
            + "/"
            + self.year
            + "DailyScoresFinal"
            + self.suffix
            + ".csv"
        )
        finalDf.to_csv(newCsvFinal, index=False)

        print(
            "An alternative view of the daily game scores will be stored "
            "in: " + newCsvAlt
        )
        print(
            "The final organized daily game scores will be stored in: "
            + newCsvFinal
        )

    def org_daily_scores(self):
        """Organize the daily score csv"""
        # Convert abbrieviated names to full team names
        abbrDict = {
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
        teamCols = ["HomeTeam", "AwayTeam"]
        for col in teamCols:
            self.df[col] = (
                self.df[col]
                .map(abbrDict)
                .infer_objects()
                .fillna(self.df[col])
                .astype(str)
            )
        # Remove trailing zeroes from scores
        runsCols = ["RunsHome", "RunsAway"]
        for col in runsCols:
            self.df[col] = self.df[col].astype(str)
            self.df[col] = self.df[col].str.replace(".0", "")
            self.df[col] = self.df[col].str.replace("nan", "*")


def get_url(tryUrl):
    """Attempts a GET request from the passed in URL

    Parameters:
    tryUrl (string): The URL to attempt opening

    Returns:
    response (Response): The URL's response"""
    try:
        print("Connecting to: " + tryUrl)
        response = requests.get(tryUrl)
        response.raise_for_status()
    # Page doesn't exist (404 not found, 403 not authorized, etc)
    except HTTPError as hp:
        print(hp)
    # Bad URL
    except URLError as ue:
        print(ue)
    return response


def get_daily_scores(yearDir, suffix, year):
    """The main daily scores scraping function that produces Raw daily scores
    files"""
    # Make output file
    outputFile = make_raw_daily_scores_file(yearDir, suffix, year)
    outputFile.write("HomeTeam,RunsHome,RunsAway,AwayTeam\n")
    # Grab URLs to scrape
    url = "https://npb.jp/bis/eng/" + year + "/games/"
    # Make GET request
    r = get_url(url)
    # Create the soup for parsing the html content
    soup = BeautifulSoup(r.content, "html.parser")
    gameDivs = soup.find_all("div", class_="contentsgame")
    # Extract table rows from npb.jp daily game stats
    for result in gameDivs:
        teams = result.find_all(class_="contentsTeam")
        runs = result.find_all(class_="contentsRuns")
        i = 0
        while i < len(teams):
            team1 = teams[i].get_text()
            team1Runs = runs[i].get_text()
            team2 = teams[i + 1].get_text()
            team2Runs = runs[i + 1].get_text()
            i += 2
            outputFile.write(
                team1 + "," + team1Runs + "," + team2Runs + "," + team2 + "\n"
            )


def get_stats(yearDir, suffix, year):
    """The main stat scraping function that produces Raw stat files.
    Saving Raw stat files allows for scraping and stat organization to be
    independent of each other

    Parameters:
    yearDir (string): The directory that stores the raw, scraped NPB stats
    suffix (string): Determines header row of csv file and indicates the stats
    that the URLs point to:
    "BR" = reg season batting stat URLs passed in
    "PR" = reg season pitching stat URLs passed in
    "BF" = farm batting stat URLs passed in
    "PF" = farm pitching stat URLs passed in
    year (string): The desired npb year to scrape"""
    # Make output file
    outputFile = make_raw_player_file(yearDir, suffix, year)
    # Grab URLs to scrape
    urlArr = get_stat_urls(suffix, year)
    # Create header row
    if suffix == "BR":
        outputFile.write(
            "Player,G,PA,AB,R,H,2B,3B,HR,TB,RBI,SB,CS,SH,SF,BB,"
            "IBB,HP,SO,GDP,AVG,SLG,OBP,Team,\n"
        )
    if suffix == "PR":
        outputFile.write(
            "Pitcher,G,W,L,SV,HLD,CG,SHO,PCT,BF,IP,,H,HR,BB,IBB,"
            "HB,SO,WP,BK,R,ER,ERA,Team,\n"
        )
    if suffix == "BF":
        outputFile.write(
            "Player,G,PA,AB,R,H,2B,3B,HR,TB,RBI,SB,CS,SH,SF,BB,"
            "IBB,HP,SO,GDP,AVG,SLG,OBP,Team,\n"
        )
    if suffix == "PF":
        outputFile.write(
            "Pitcher,G,W,L,SV,CG,SHO,PCT,BF,IP,,H,HR,BB,IBB,HB,SO,WP,BK,R,ER,"
            "ERA,Team,\n"
        )

    # Loop through all team stat pages in urlArr
    for url in urlArr:
        # Make GET request
        r = get_url(url)
        # Create the soup for parsing the html content
        soup = BeautifulSoup(r.content, "html.parser")

        # Since header row was created, skip to stat rows
        iterSoup = iter(soup.table)
        # Left handed pitcher/batter and switch hitter row skip
        next(iterSoup)
        # npb.jp header row skip
        next(iterSoup)

        # Extract table rows from npb.jp team stats
        for tableRow in iterSoup:
            # Skip first column for left handed batter/pitcher or switch hitter
            iterTable = iter(tableRow)
            next(iterTable)
            # Write output in csv file format
            for entry in iterTable:
                # Remove commas in first and last names
                entryText = entry.get_text()
                if entryText.find(","):
                    entryText = entryText.replace(",", "")
                # Write output in csv file format
                outputFile.write(entryText + ",")

            # Get team
            titleDiv = soup.find(id="stdivtitle")
            yearTitleStr = titleDiv.h1.get_text()
            # Correct team name formatting
            yearTitleStr = yearTitleStr.replace(year, "")
            if yearTitleStr.find("Fukuoka"):
                yearTitleStr = yearTitleStr.replace("Fukuoka", "")
            if yearTitleStr.find("Chiba"):
                yearTitleStr = yearTitleStr.replace("Chiba", "")
            if yearTitleStr.find("Hokkaido Nippon-Ham Fighters"):
                yearTitleStr = yearTitleStr.replace(
                    "Hokkaido Nippon-Ham Fighters", "Nipponham Fighters"
                )
            if yearTitleStr.find("Toyo"):
                yearTitleStr = yearTitleStr.replace("Toyo ", "")
            if yearTitleStr.find("YOKOHAMA DeNA BAYSTARS"):
                yearTitleStr = yearTitleStr.replace(
                    "YOKOHAMA DeNA BAYSTARS", "DeNA BayStars"
                )
            if yearTitleStr.find("Saitama"):
                yearTitleStr = yearTitleStr.replace("Saitama", "")
            if yearTitleStr.find("Tokyo"):
                yearTitleStr = yearTitleStr.replace("Tokyo", "")
            if yearTitleStr.find("Tohoku Rakuten Golden Eagles"):
                yearTitleStr = yearTitleStr.replace(
                    "Tohoku Rakuten Golden Eagles", "Rakuten Eagles"
                )
            if yearTitleStr.find("Kufu HAYATE Ventures Shizuoka"):
                yearTitleStr = yearTitleStr.replace(
                    "Kufu HAYATE Ventures Shizuoka", "HAYATE Ventures"
                )
            if yearTitleStr.find("Oisix Niigata Albirex BC"):
                yearTitleStr = yearTitleStr.replace(
                    "Oisix Niigata Albirex BC", "Oisix Albirex"
                )
            yearTitleStr = yearTitleStr.lstrip()
            yearTitleStr = yearTitleStr.rstrip()
            # Append as last entry and move to next row
            outputFile.write(yearTitleStr + ",\n")

        # Close request
        r.close()
        # Pace requests to npb.jp to avoid excessive requests
        sleep(randint(3, 5))
    # After all URLs are scraped, close output file
    outputFile.close()


def get_standings(yearDir, suffix, year):
    """Scrape the games played table for relevant stats to calculate PA/IP
    qualifier drop stats and for reference

    Parameters:
    yearDir (string): The directory to store relevant year statistics
    suffix (string): Indicates URL being scraped:
    "C" = central league reg season standing URLs passed in
    "P" = pacific league reg season standing URLs passed in
    "E" = eastern league farm standing URLs passed in
    "W" = western league farm standing URLs passed in
    year (string):The desired standings stat year"""
    outputFile = make_raw_standings_file(yearDir, suffix, year)
    # Get URL to scrape
    urlBase = "https://npb.jp/bis/eng/{0}/stats/std_{1}.html"
    url = urlBase.format(year, suffix.lower())
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
        outputFile.close()
        return

    # Create header row
    iterTable = iter(table)
    tr = next(iterTable)
    # Loop through each td in a table row
    for td in tr:
        entryText = td.get_text()
        # Skip empty column
        if entryText == "":
            continue
        # Insert each entry using csv format
        outputFile.write(entryText + ",")
    outputFile.write("\n")

    # Since header row was created, skip to stat rows
    for tr in iterTable:
        # Loop through each td in a table row
        for td in tr:
            entryText = td.get_text()
            # Standardize blank spots in the csv
            if entryText == "***":
                entryText = "--"
            # Skip empty columns
            if entryText == "":
                continue
            # Insert each entry using csv format
            outputFile.write(entryText + ",")
        # Skip duplicate named table row
        next(iterTable)
        outputFile.write("\n")

    # Close request and output file
    r.close()
    outputFile.close()
    # Pace requests to npb.jp to avoid excessive requests
    sleep(randint(3, 5))


def get_fielding(yearDir, suffix, year):
    """Scrapes the fielding stats for the desired year and suffix

    Parameters:
    yearDir (string): The directory to store relevant year statistics
    suffix (string): Indicates URL being scraped:
    "R" = regular season fielding stats
    "F" = farm fielding stats
    year (string): The desired fielding stat year"""
    relDir = os.path.dirname(__file__)
    urlFile = relDir + "/input/fieldingUrls.csv"
    # Grab singular fielding URL from file
    df = pd.read_csv(urlFile)
    df = df.drop(df[df.Year.astype(str) != year].index)
    if "R" in suffix:
        fieldLeague = "NPB"
    else:
        fieldLeague = "Farm"
    df = df.drop(df[df.League != fieldLeague].index)
    fieldingUrl = df["Link"].iloc[0]

    outputFile = make_raw_fielding_file(yearDir, suffix, year)
    r = get_url(fieldingUrl)
    soup = BeautifulSoup(r.content, "html.parser")
    # Grab all fielding table entries
    fieldingTr = soup.find_all("tr")
    for tr in fieldingTr:
        if tr.get_text() == "":
            continue
        for td in tr:
            entryText = td.get_text()
            entryText = entryText.strip()
            if entryText == "":
                continue
            outputFile.write(entryText + ",")
        outputFile.write("\n")
    r.close()
    # Pace requests to npb.jp to avoid excessive requests
    sleep(randint(3, 5))


def get_stat_urls(suffix, year):
    """Creates arrays of the correct URLs for the individual stat scraping

    Parameters:
    suffix (string): The desired mode to run in (either farm or regular season)
    year (string): The desired npb year to scrape

    Returns:
    urlArrBaseB (array - string): Contains URLs to the team batting/pitching
    stat pages"""
    if suffix == "BR":
        # Team regular season individual batting stats
        urlArrBase = [
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
        urlArrBase = [
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
        urlArrBase = [
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
        # Append new farm teams for 2024
        if year == "2024":
            # Oisix Niigata Albirex BC
            urlArrBase.append("https://npb.jp/bis/eng/2024/stats/idb2_a.html")
            # Kufu HAYATE Ventures Shizuoka
            urlArrBase.append("https://npb.jp/bis/eng/2024/stats/idb2_v.html")
    elif suffix == "PF":
        # Team farm individual pitching stats
        urlArrBase = [
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
        # Append new farm teams for 2024
        if year == "2024":
            # Oisix Niigata Albirex BC
            urlArrBase.append("https://npb.jp/bis/eng/2024/stats/idp2_a.html")
            # Kufu HAYATE Ventures Shizuoka
            urlArrBase.append("https://npb.jp/bis/eng/2024/stats/idp2_v.html")

    # Loop through each entry and change the year in the URL before returning
    for i, url in enumerate(urlArrBase):
        urlArrBase[i] = urlArrBase[i].replace("2024", year)
    return urlArrBase


def make_raw_player_file(writeDir, suffix, year):
    """Opens a file to hold all player stats inside a relative /stats/
    directory that is created before calling this function

    Parameters:
    writeDir (string): The directory that stores the scraped NPB stats
    suffix (string): Indicates the raw stat file to create:
    "BR" = reg season batting stats
    "PR" = reg season pitching stats
    "BF" = farm batting stats
    "PF" = farm pitching stats
    year (string): The desired npb year to scrape

    Returns:
    newFile (file stream object): An opened file in /stats/ named
    "[Year][Stats][Suffix].csv"""
    # Open and return the file object in write mode
    newCsvName = writeDir + "/" + year + "StatsRaw" + suffix + ".csv"
    if suffix == "BR":
        print(
            "Raw regular season batting results will be stored in: "
            + newCsvName
        )
    if suffix == "PR":
        print(
            "Raw regular season pitching results will be stored in: "
            + newCsvName
        )
    if suffix == "BF":
        print("Raw farm batting results will be stored in: " + newCsvName)
    if suffix == "PF":
        print("Raw farm pitching results will be stored in: " + newCsvName)
    newFile = open(newCsvName, "w")
    return newFile


def make_raw_daily_scores_file(writeDir, suffix, year):
    """Opens a file to hold all player stats inside a relative /stats/
    directory that is created before calling this function

    Parameters:
    writeDir (string): The directory that stores the scraped NPB stats
    year (string): The desired npb year to scrape

    Returns:
    newFile (file stream object): An opened file in /stats/ named
    "[Year]DailyScoresRaw[Suffix].csv"""
    # Open and return the file object in write mode
    newCsvName = writeDir + "/" + year + "DailyScoresRaw" + suffix + ".csv"
    print("Raw daily scores will be stored in: " + newCsvName)
    newFile = open(newCsvName, "w")
    return newFile


def make_raw_standings_file(writeDir, suffix, year):
    """Opens a file to hold all player stats inside a relative /stats/
    directory that is created before calling this function

    Parameters:
    writeDir (string): The directory that stores the scraped NPB stats
    suffix (string): Indicates the league passed in:
    "C" = central league reg season
    "P" = pacific league reg season
    "E" = eastern league farm
    "W" = western league farm
    year (string): The desired npb year to scrape

    Returns:
    newFile (file stream object): An opened file in /stats/ formatted as
    "[Year][Standings][Suffix].csv"""
    # Open and return the file object in write mode
    newCsvName = writeDir + "/" + year + "StandingsRaw" + suffix + ".csv"
    if suffix == "C":
        print(
            "Raw Central League regular season standings will be stored in: "
            + newCsvName
        )
    elif suffix == "P":
        print(
            "Raw Pacific League regular season standings will be stored in: "
            + newCsvName
        )
    elif suffix == "E":
        print(
            "Raw Eastern League farm standings will be stored in: "
            + newCsvName
        )
    elif suffix == "W":
        print(
            "Raw Western League farm standings will be stored in: "
            + newCsvName
        )
    newFile = open(newCsvName, "w")
    return newFile


def make_raw_fielding_file(writeDir, suffix, year):
    """Opens a file to hold all fielding stats inside a relative /stats/
    directory that is created before calling this function

    Parameters:
    writeDir (string): The directory that stores the scraped NPB stats
    suffix (string): Indicates the raw stat file to create:
    "R" = regular season fielding stats
    "F" = farm fielding stats
    year (string): The desired npb year to scrape

    Return:
    newFile (file stream object): An opened file in /stats/ named
    "[Year]FieldingRaw[Suffix].csv"
    """
    # Open and return the file object in write mode
    newCsvName = writeDir + "/" + year + "FieldingRaw" + suffix + ".csv"
    if suffix == "R":
        print(
            "Raw regular season fielding results will be stored in: "
            + newCsvName
        )
    if suffix == "F":
        print("Raw farm fielding results will be stored in: " + newCsvName)
    newFile = open(newCsvName, "w")
    return newFile


def get_scrape_year(argsIn=None):
    """Checks passed in arguments or gets user input for NPB stat year to
    scrape

    Parameters:
    argsIn (string): If a command line argument is given, the year is checked
    for validity. Default (None) indicates to collect user input instead

    Returns:
    argsIn (string): The desired npb stat year to scrape"""
    # User input check
    if argsIn is None:
        # Infinite loop breaks when valid input obtained
        # Either valid year or exit signal entered
        while True:
            argsIn = input(
                "Enter a NPB year between 2020-"
                + str(datetime.now().year)
                + " or Q to quit: "
            )
            if argsIn == "Q":
                sys.exit("Exiting...")
            try:
                argsIn = int(argsIn)
            except ValueError:
                print("Input must be a number (Example: 2024)")
                continue
            # Bounds for scrapable years
            # Min year on npb.jp = 2008, but scraping is only tested until 2020
            if 2020 <= argsIn <= datetime.now().year:
                print(str(argsIn) + " entered. Continuing...")
                break
            else:
                print(
                    "Please enter a valid year (2020-"
                    + str(datetime.now().year)
                    + ")."
                )
    # Argument check
    else:
        try:
            argsIn = int(argsIn)
        except ValueError:
            print("Year argument must be a number (Example: 2024)")
            sys.exit("Exiting...")
        # Bounds for scrapable years
        # Min year on npb.jp is 2008, but scraping is only tested until 2020
        if 2020 <= argsIn <= datetime.now().year:
            pass
        else:
            print(
                "Please enter a valid year (2020-"
                + str(datetime.now().year)
                + ")."
            )
            sys.exit("Exiting...")

    # Return user input as a string
    return str(argsIn)


def get_user_choice(suffix):
    """Gets user input for whether or not to undergo scraping and whether to
    place relevant files in a zip

    Parameters:
    suffix (string): Indicates the option being asked about (can be farm
    scraping "F", regular season scraping "R", stat zip file creation "Z",
    player percentile creation "P", or percentile zip file creation "PZ")

    Returns:
    userIn (string): Returns "Y" or "N" (if "Q" is chosen, program terminates)
    """
    # Loop ends for valid choice/exit
    while True:
        if suffix == "F":
            print(
                "Choose whether to pull new farm stats from npb.jp or "
                "only reorganize existing stat files.\nWARNING: EXISTING "
                "RAW FILES MUST BE PRESENT TO SKIP SCRAPING."
            )
            userIn = input("Scrape farm stats? (Y/N): ")
        elif suffix == "R":
            print(
                "Choose whether to pull new regular season stats from "
                "npb.jp or only reorganize existing stat files.\nWARNING: "
                "EXISTING RAW STAT FILES MUST BE PRESENT TO SKIP SCRAPING."
            )
            userIn = input("Scrape regular season stats stats? (Y/N): ")
        elif suffix == "Z":
            userIn = input("Output stats in a zip file? (Y/N): ")
        elif suffix == "P":
            userIn = input("Output player percentile plots? (Y/N): ")
        elif suffix == "PZ":
            userIn = input(
                "Output player percentile plots in a zip file? (Y/N): "
            )

        if userIn == "Q":
            sys.exit("Exiting...")
        elif userIn == "Y":
            print("Continuing...")
            break
        elif userIn == "N":
            print("Skipping...")
            break
        else:
            print(
                "Invalid input - enter (Y/N) to determine whether to continue "
                "or (Q) to quit."
            )
            continue
    return userIn


def convert_team_to_html(df, mode=None):
    """Formats the team names to include links to their npb.jp pages

    Parameters:
    df (pandas dataframe): A dataframe containing entries with NPB teams
    mode (string): Indicates whether to preserve full team names ("Full"),
    abbrieviate names in the <a> tags ("Abb"), or convert any team names
    found in the dataframe to linked names (None)

    Returns:
    df (pandas dataframe): The dataframe with correct links and abbrieviations
    inserted as <a> tags"""
    # Check for the team link file, if missing, tell user and return
    relDir = os.path.dirname(__file__)
    teamLinkFile = relDir + "/input/teamUrls.csv"
    linkDf = pd.read_csv(teamLinkFile)
    if mode == "Full":
        # Update Link col to have <a> tags
        linkDf["Link"] = linkDf.apply(build_html, axis=1)
        # Create dict of Team Name:Complete HTML tag and convert
        teamDict = dict(linkDf.values)
        df["Team"] = (
            df["Team"]
            .map(teamDict)
            .infer_objects()
            .fillna(df["Team"])
            .astype(str)
        )
    elif mode == "Abb":
        # Contains 2020-2024 reg/farm baseball team abbrieviations
        abbrDict = {
            "Hanshin Tigers": "Hanshin",
            "Hiroshima Carp": "Hiroshima",
            "DeNA BayStars": "DeNA",
            "Yomiuri Giants": "Yomiuri",
            "Yakult Swallows": "Yakult",
            "Chunichi Dragons": "Chunichi",
            "ORIX Buffaloes": "ORIX",
            "Lotte Marines": "Lotte",
            "SoftBank Hawks": "SoftBank",
            "Rakuten Eagles": "Rakuten",
            "Seibu Lions": "Seibu",
            "Nipponham Fighters": "Nipponham",
            "Oisix Albirex": "Oisix",
            "HAYATE Ventures": "HAYATE",
        }
        # Create temp col to have abbrieviations
        linkDf["Temp"] = (
            linkDf["Team"]
            .map(abbrDict)
            .infer_objects()
            .fillna(linkDf["Team"])
            .astype(str)
        )
        # Swap full name col with abb col to create HTML tags with abb names
        linkDf["Team"], linkDf["Temp"] = linkDf["Temp"], linkDf["Team"]
        linkDf["Link"] = linkDf.apply(build_html, axis=1)
        # Swap full name col back to original spot and delete temp col
        linkDf["Temp"], linkDf["Team"] = linkDf["Team"], linkDf["Temp"]
        linkDf = linkDf.drop("Temp", axis=1)
        # Add new, unlinked farm team abbrieviations to dataframe
        newRow = {"Team": "Oisix Albirex", "Link": "Oisix"}
        linkDf = linkDf._append(newRow, ignore_index=True)
        newRow = {"Team": "HAYATE Ventures", "Link": "HAYATE"}
        linkDf = linkDf._append(newRow, ignore_index=True)
        # Create dict of Team Name:Complete HTML tag and convert
        teamDict = dict(linkDf.values)
        df["Team"] = (
            df["Team"]
            .map(teamDict)
            .infer_objects()
            .fillna(df["Team"])
            .astype(str)
        )
    # Default mode links any team names it finds (assumes full team names are
    # present in the dataframe)
    elif mode == None:
        linkDf["Link"] = linkDf.apply(build_html, axis=1)
        # Create dict of Team Name:Complete HTML tag and convert
        teamDict = dict(linkDf.values)
        for col in df.columns:
            df[col] = (
                df[col]
                .map(teamDict)
                .infer_objects()
                .fillna(df[col])
                .astype(str)
            )

    return df


def add_roster_data(df, suffix):
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
    relDir = os.path.dirname(__file__)
    rosterDataFile = relDir + "/input/rosterData.csv"

    # Player throwing/batting arms
    rosterDf = pd.read_csv(rosterDataFile)
    convertCol = df.iloc[:, 0].name
    if suffix == "BR" or suffix == "BF" or suffix == "PR" or suffix == "PF":
        if suffix == "PR" or suffix == "PF":
            tbCol = "T"
        elif suffix == "BR" or suffix == "BF":
            tbCol = "B"
        playerArmDict = dict(zip(rosterDf["Player"], rosterDf[tbCol]))
        df[tbCol] = (
            df[convertCol]
            .map(playerArmDict)
            .infer_objects()
            .fillna(df[convertCol])
            .astype(str)
        )

    # Player age
    rosterDf["BirthDate"] = pd.to_datetime(
        rosterDf["BirthDate"], format="mixed"
    )
    rosterDf["Age"] = rosterDf["BirthDate"].apply(calculate_age)
    # Create dict of Player Name,Team:Age tag
    playerAgeDict = dict(
        zip((zip(rosterDf["Player"], rosterDf["Team"])), rosterDf["Age"])
    )
    df["keys"] = list(zip(df[convertCol], df["Team"]))
    df["Age"] = (
        df["keys"]
        .map(playerAgeDict)
        .infer_objects()
        .fillna(df[convertCol])
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
    npbAge (int): The age of the player at the start of the NPB season"""
    cutoff = datetime(datetime.today().year, 6, 30)
    npbAge = (
        cutoff.year
        - birthdate.year
        - ((cutoff.month, cutoff.day) < (birthdate.month, birthdate.day))
    )
    return npbAge


def convert_ip_column_out(df):
    """In baseball, innings are traditionally represented using .1 (single
    inning pitched), .2 (2 innings pitched), and whole numbers. This function
    converts the decimals FROM thirds (.33 -> .1, .66 -> .2) for sake of
    presentation

    Parameters:
    df (pandas dataframe): A pitching stat dataframe with the "thirds"
    representation

    Returns:
    tempDf['IP']/tempDf['Inn'] (pandas dataframe column): An innings column
    converted back to the informal innings representation"""
    if "IP" in df.columns:
        innCol = "IP"
    elif "Inn" in df.columns:
        innCol = "Inn"
    # Innings ".0 .1 .2" fix
    tempDf = pd.DataFrame(df[innCol])
    # Get the ".0 .3 .7" in the innings column
    ipDecimals = tempDf[innCol] % 1
    # Make the original innings column whole numbers
    tempDf[innCol] = tempDf[innCol] - ipDecimals
    # Convert IP decimals to thirds and re-add them to the whole numbers
    ipDecimals = (ipDecimals / 0.3333333333) / 10
    df[innCol] = tempDf[innCol] + ipDecimals
    # Entries with .3 are invalid: add 1 and remove the decimals
    x = tempDf[innCol] + ipDecimals
    condlist = [((x % 1) < 0.29), ((x % 1) >= 0.29)]
    choicelist = [x, (x - (x % 1)) + 1]
    tempDf[innCol] = np.select(condlist, choicelist)
    tempDf[innCol] = tempDf[innCol].apply("{:.1f}".format)
    tempDf[innCol] = tempDf[innCol].astype(float)
    return tempDf[innCol]


def convert_ip_column_in(df):
    """Converts the decimals in the IP column TO thirds (.1 -> .33, .2 -> .66)
    for stat calculations

    Parameters:
    df (pandas dataframe): A pitching stat dataframe with the traditional
    .1/.2 IP representation

    Returns:
    tempDf['IP'] (pandas dataframe column): An IP column converted for stat
    calculations"""
    if "IP" in df.columns:
        innCol = "IP"
    elif "Inn" in df.columns:
        innCol = "Inn"
    tempDf = pd.DataFrame(df[innCol])
    # Get the ".0 .1 .2" in the 'IP' column
    ipDecimals = tempDf[innCol] % 1
    # Make the original 'IP' column whole numbers
    tempDf[innCol] = tempDf[innCol] - ipDecimals
    # Multiply IP decimals by .3333333333 and readd them to the whole numbers
    ipDecimals = (ipDecimals * 10) * 0.3333333333
    tempDf[innCol] = tempDf[innCol] + ipDecimals
    return tempDf[innCol]


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
    relDir = os.path.dirname(__file__)
    pfFile = relDir + "/input/parkFactors.csv"
    pfDf = pd.read_csv(pfFile)
    # Drop all rows that are not the df's year
    pfDf = pfDf.drop(pfDf[pfDf.Year.astype(str) != year].index)
    # Drop all rows that do not match the df's league
    if suffix == "BR" or suffix == "PR":
        pfSuffix = "NPB"
    else:
        pfSuffix = "Farm"
    pfDf = pfDf.drop(pfDf[pfDf.League != pfSuffix].index)
    # Drop remaining unneeded cols before merge
    pfDf.drop(["Year", "League"], axis=1, inplace=True)
    # Modifying all park factors for calculations
    pfDf["ParkF"] = (pfDf["ParkF"] + 1) / 2
    df = df.merge(pfDf, on="Team", how="left")
    # For team files, league avg calculations have park factor as 1.000
    df.loc[df.Team == "League Average", "ParkF"] = 1.000
    return df


def select_fip_const(suffix, year):
    """Chooses FIP constant for 2020-2024 reg and farm years

    Parameters:
    suffix (string): Indicates whether to use farm or reg season FIP constants
    year (string): The year of FIP constants to pull

    Returns:
    fipConst (float): The correct FIP const according to year and farm/NPB reg
    season"""
    relDir = os.path.dirname(__file__)
    fipFile = relDir + "/input/fipConst.csv"
    fipDf = pd.read_csv(fipFile)
    # Drop all rows that are not the df's year
    fipDf = fipDf.drop(fipDf[fipDf.Year.astype(str) != year].index)
    # Drop all rows that do not match the df's league
    if suffix == "BR" or suffix == "PR":
        fipSuffix = "NPB"
    else:
        fipSuffix = "Farm"
    fipDf = fipDf.drop(fipDf[fipDf.League != fipSuffix].index)
    # Return FIP for that year and league
    fipConst = fipDf.at[fipDf.index[-1], "FIP"]
    return fipConst


def select_league(df, suffix):
    """Adds a "League" column based on the team

    Parameters:
    df (pandas dataframe): A team or player dataframe

    Returns:
    df (pandas dataframe): The dataframe with the correct "League" column added
    """
    if suffix == "BR" or suffix == "PR" or suffix == "R":
        # Contains all 2020-2024 reg baseball team names and leagues
        leagueDict = {
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
    elif suffix == "BF" or suffix == "PF" or suffix == "F":
        # Contains all 2020-2024 farm baseball team names and links
        leagueDict = {
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

    for team in leagueDict:
        df.loc[df.Team == team, "League"] = leagueDict[team]
    return df


def assign_primary_or_utl(
    row,
    pct_utl_thresholdHigh=0.075,
    pct_utl_thresholdLow=0.05,
    pct_primary_threshold=0.50,
):
    """Given a row with positions (e.g. row['1B'], row['2B'], etc.),
    decide if the player is 'UTL' or has a primary position.

    Parameters:
    row (pandas series): A row of a dataframe with positions as columns
    pct_utl_thresholdHigh (float): The threshold for a player to be considered
    UTL if they have 3 or more positions >= this value
    pct_utl_thresholdLow (float): The threshold for a player to be considered
    UTL if they have 4 or more positions >= this value
    pct_primary_threshold (float): The threshold for a player to be considered
    primary at a position if they have >= this value

    Returns:
    fractions.idmax (int): The player's most prominent position"""
    posCols = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "DH"]
    total_innings = row[posCols].sum()
    if total_innings == 0:
        return "No Data"

    # Rule 1: Grab all players that are solely DH and pitchers
    if (total_innings - row["DH"]) == 0:
        return "DH"
    # Rule 2: Grab all players that are solely pitchers
    if (total_innings - row["1"]) == 0:
        return "1"
    # Calculate fraction for each position
    fractions = row[posCols] / (total_innings - row["DH"])
    # Count how many positions >= our thresholds
    num_positions_10plus = (fractions >= pct_utl_thresholdHigh).sum()
    num_positions_5plus = (fractions >= pct_utl_thresholdLow).sum()
    # Rule 3: For 2 way players, if they appear on the pitching stat file
    # with at least 2.0 IP and at least 2.0 Inn fielded, label them as a 2 way
    # player (TWP)
    posCols.remove("1")
    if any(row[posCols] > 2.0) and (row["1"] > 2.0):
        return "TWP"
    # Rule 4: If the player has 3 positions that are all in the outfield, the
    # largest OF pos is the primary
    if row["7"] > 0 and row["8"] > 0 and row["9"] > 0:
        return fractions.idxmax()
    # Rule 5: If any position >= 50%, that is primary
    if any(fractions >= pct_primary_threshold):
        return fractions.idxmax()
    # Rule 6: If 3 or more positions are >= our thresholds, label UTL
    if num_positions_10plus >= 3 or num_positions_5plus >= 4:
        return "UTL"
    # Rule 7: If none of the above, pick the position with the largest fraction
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
    relDir = os.path.dirname(__file__)
    playerLinkFile = relDir + "/input/rosterData.csv"

    linkDf = pd.read_csv(playerLinkFile)
    # Create new HTML code column
    linkDf["Link"] = linkDf.apply(build_html, axis=1)
    # Create dict of Player Name:Complete HTML tag
    playerDict = dict(zip(linkDf["Player"], linkDf["Link"]))

    # Replace all player entries with HTML that leads to their pages
    if suffix == "PR" or suffix == "PF":
        convertCol = "Pitcher"
    else:
        convertCol = "Player"
    df[convertCol] = (
        df[convertCol]
        .map(playerDict)
        .infer_objects()
        .fillna(df[convertCol])
        .astype(str)
    )

    # Check for the player link fix file
    playerLinkFixFile = relDir + "/input/playerUrlsFix.csv"
    if os.path.exists(playerLinkFixFile):
        fixDf = pd.read_csv(playerLinkFixFile)
        # Check year and suffix, fix if needed
        if int(year) in fixDf.Year.values and suffix in fixDf.Suffix.values:
            # Create dict of Player Name:Complete HTML tag
            fixDict = dict(zip(fixDf["Original"], fixDf["Corrected"]))
            df[convertCol] = (
                df[convertCol]
                .map(fixDict)
                .infer_objects()
                .fillna(df[convertCol])
                .astype(str)
            )
    return df


def translate_players(df):
    """Translates player names from Japanese to English using a csv file

    Parameters:
    df (pandas dataframe): A NPB stat dataframe containing player names

    Returns:
    df (pandas dataframe): The final stat dataframe with translated names"""
    relDir = os.path.dirname(__file__)
    translationFile = relDir + "/input/nameTranslations.csv"

    # Read in csv that contains player name and their personal page link
    translateDf = pd.read_csv(translationFile)
    # Create dict of (JP name,EN team):Eng name
    playerDict = dict(
        zip(
            (zip(translateDf["jp_name"], translateDf["en_team"])),
            translateDf["en_name"],
        )
    )
    df["keys"] = list(zip(df["Player"], df["Team"]))
    df["Player"] = (
        df["keys"]
        .map(playerDict)
        .infer_objects()
        .fillna(df["Player"])
        .astype(str)
    )
    df["Player"] = df["Player"].str.replace('"', "")
    df["Player"] = df["Player"].str.replace(",", "")
    return df


def build_html(row):
    """Insert the link and text in a <a> tag, returns the tag as a string"""
    if pd.isna(row["Link"]) == False:
        htmlLine = "<a href=" "{0}" ">{1}</a>".format(row["Link"], row.iloc[0])
    else:
        htmlLine = row.iloc[0]
    return htmlLine


def make_zip(yearDir, suffix, year):
    """Groups key directories into a single zip for uploading/sending

    Parameters:
    yearDir (string): The directory that stores the raw, scraped NPB stats
    suffix (string): Types of files being zipped
        "S" = a given year's farm and npb directories
        "P" = a given year's plots directories
    year (string): The year of npb stats to group together"""
    if suffix == "S":
        tempDir = os.path.join(yearDir, "/stats/temp")
        tempDir = tempfile.mkdtemp()
        # Gather all stat dirs to put into temp
        shutil.copytree(
            yearDir + "/farm", tempDir + "/stats/farm", dirs_exist_ok=True
        )
        shutil.copytree(
            yearDir + "/npb", tempDir + "/stats/npb", dirs_exist_ok=True
        )
        outputFilename = yearDir + "/" + year + "upload"
    elif suffix == "P":
        tempDir = os.path.join(yearDir, "/plots/temp")
        tempDir = tempfile.mkdtemp()
        # Gather all percentile dirs to put into temp
        shutil.copytree(
            yearDir + "/plots/BF", tempDir + "/plots/BF", dirs_exist_ok=True
        )
        shutil.copytree(
            yearDir + "/plots/BR", tempDir + "/plots/BR", dirs_exist_ok=True
        )
        shutil.copytree(
            yearDir + "/plots/PF", tempDir + "/plots/PF", dirs_exist_ok=True
        )
        shutil.copytree(
            yearDir + "/plots/PR", tempDir + "/plots/PR", dirs_exist_ok=True
        )
        outputFilename = yearDir + "/" + year + "playerPercentiles"

    shutil.make_archive(outputFilename, "zip", tempDir)
    shutil.rmtree(tempDir)
    print("Zip created at: " + outputFilename + ".zip")


def check_input_files(relDir):
    """TODO: docs"""
    # Optional files
    playerLinkFixFile = relDir + "/input/playerUrlsFix.csv"
    if not os.path.exists(playerLinkFixFile):
        print(
            "\nWARNING: No optional player link fix file detected. Provide a "
            "playerUrlsFix.csv file in the /input/ directory to fix this.\n"
        )
    # Required files (returns False if file is missing)
    translationFile = relDir + "/input/nameTranslations.csv"
    if not (os.path.exists(translationFile)):
        print(
            "\nERROR: No player name translation file found, player names "
            "can't be translated...\nProvide a nameTranslations.csv file in"
            " the /input/ directory to fix this.\n"
        )
        return False
    playerLinkFile = relDir + "/input/rosterData.csv"
    if not (os.path.exists(playerLinkFile)):
        print(
            "\nERROR: No player link file found, table entries will not "
            "have links...\nProvide a rosterData.csv file in the /input/ "
            "directory to fix this.\n"
        )
        return False
    fipFile = relDir + "/input/fipConst.csv"
    if not (os.path.exists(fipFile)):
        print(
            "\nERROR: No FIP constant file found, calculations using FIP will "
            "be inaccurate...\nProvide a valid fipConst.csv file in the "
            "/input/ directory to fix this.\n"
        )
        return False
    pfFile = relDir + "/input/parkFactors.csv"
    if not (os.path.exists(pfFile)):
        print(
            "\nERROR: No park factor file found, calculations using park "
            "factors will be inaccurate...\nProvide a valid parkFactors.csv "
            "file in the /input/ directory to fix this.\n"
        )
        return False
    teamLinkFile = relDir + "/input/teamUrls.csv"
    if not (os.path.exists(teamLinkFile)):
        print(
            "\nWARNING: No team link file found, table entries will not have "
            "links...\nProvide a teamUrls.csv file in the /input/ directory to"
            " fix this to fix this.\n"
        )
        return False
    fieldUrlFile = relDir + "/input/fieldingUrls.csv"
    if not (os.path.exists(fieldUrlFile)):
        print(
            "\nERROR: No fielding URL file found, raw fielding files will not "
            "be produced...\nProvide a valid fieldingUrls.csv file in the "
            "/input/ directory to fix this.\n"
        )
        return False

    # Print confirmation files exist
    print("All needed input files present, continuing...")
    return True


def get_pitch_types(yearDir, year, suffix):
    # TODO: discuss scrapping this with mr yakyu
    # PITCHING TYPES SCRAPING CODE (move into a new function get_pitch_types)
    pitchTypesFile = yearDir + "/" + year + "PitchTypesRaw" + suffix + ".csv"
    print("Raw pitching types will be stored in: " + pitchTypesFile)
    # newFile = open(pitchTypesFile, "w")
    # Make GET request
    url = (
        "https://docs.google.com/spreadsheets/d/e/2PACX-"
        + "1vS6W2zDr6OWslGU0QSLhvw4xi-NpnjWEqO16OvLnU2OCJoMbKFH-"
        + "Z3FYL1sGxIFKb8flYQFgH9wphPU/pub?gid=1691151132&single=true&output=csv"
    )
    # r = get_url(url)
    testDf = pd.read_csv(url, index_col=0)
    print(testDf.to_string())


if __name__ == "__main__":
    main()
