"""Performs basic functionality tests on npb_scrape.py"""

from datetime import datetime
import os
import unittest
import shutil
import npb_scrape


class TestNpbScrape(unittest.TestCase):
    """A class to unit test npb_scrape.py"""

    def setUp(self):
        super().__init__()

        # NOTE: Testing year is current year for now, but should work to 2020
        self.scrape_year = npb_scrape.get_scrape_year(str(datetime.now().year))

        # Open the directory to store the scraped stat csv files
        self.rel_dir = os.path.dirname(__file__)
        self.stats_dir = os.path.join(self.rel_dir, "test_stats")
        if not os.path.exists(self.stats_dir):
            os.mkdir(self.stats_dir)

        # Create year directory
        self.year_dir = os.path.join(self.stats_dir, self.scrape_year)
        if not os.path.exists(self.year_dir):
            os.mkdir(self.year_dir)

        # Create raw directory
        self.raw_dir = os.path.join(self.year_dir, "raw")
        if not os.path.exists(self.raw_dir):
            os.mkdir(self.raw_dir)

    def tearDown(self):
        # Delete test_stats dir and all sub files
        shutil.rmtree(self.stats_dir)
        return super().tearDown()

    # These tests simply check that the correct raw files are present
    def test_get_stats(self):
        """test_get_stats() tests existence of player stat files after
        running get_stats()"""
        npb_scrape.get_stats(self.year_dir, "BR", self.scrape_year)
        bat_npb = self.raw_dir + "/" + self.scrape_year + "StatsRawBR.csv"
        is_exist = os.path.exists(bat_npb)
        self.assertTrue(is_exist, msg="No raw player stat BR file")

        npb_scrape.get_stats(self.year_dir, "PR", self.scrape_year)
        pitch_npb = self.raw_dir + "/" + self.scrape_year + "StatsRawPR.csv"
        is_exist = os.path.exists(pitch_npb)
        self.assertTrue(is_exist, msg="No raw player stat PR file")

        npb_scrape.get_stats(self.year_dir, "BF", self.scrape_year)
        bat_farm = self.raw_dir + "/" + self.scrape_year + "StatsRawBF.csv"
        is_exist = os.path.exists(bat_farm)
        self.assertTrue(is_exist, msg="No raw player stat BF file")

        npb_scrape.get_stats(self.year_dir, "PF", self.scrape_year)
        pitch_farm = self.raw_dir + "/" + self.scrape_year + "StatsRawPF.csv"
        is_exist = os.path.exists(pitch_farm)
        self.assertTrue(is_exist, msg="No raw player stat PF file")

    def test_get_standings(self):
        """test_get_standings() tests existence of standings stat files after
        running get_standings()"""
        npb_scrape.get_standings(self.year_dir, "C", self.scrape_year)
        std_c = self.raw_dir + "/" + self.scrape_year + "StandingsRawC.csv"
        is_exist = os.path.exists(std_c)
        self.assertTrue(is_exist, msg="No raw standings C file")

        npb_scrape.get_standings(self.year_dir, "E", self.scrape_year)
        std_e = self.raw_dir + "/" + self.scrape_year + "StandingsRawE.csv"
        is_exist = os.path.exists(std_e)
        self.assertTrue(is_exist, msg="No raw standings E file")

        npb_scrape.get_standings(self.year_dir, "P", self.scrape_year)
        std_p = self.raw_dir + "/" + self.scrape_year + "StandingsRawP.csv"
        is_exist = os.path.exists(std_p)
        self.assertTrue(is_exist, msg="No raw standings P file")

        npb_scrape.get_standings(self.year_dir, "W", self.scrape_year)
        std_w = self.raw_dir + "/" + self.scrape_year + "StandingsRawW.csv"
        is_exist = os.path.exists(std_w)
        self.assertTrue(is_exist, msg="No raw standings W file")

    def test_get_fielding(self):
        """test_get_daily_stats() tests existence of fielding stat files after
        running get_fielding()"""
        npb_scrape.get_fielding(self.year_dir, "R", self.scrape_year)
        field_npb = self.raw_dir + "/" + self.scrape_year + "FieldingRawR.csv"
        is_exist = os.path.exists(field_npb)
        self.assertTrue(is_exist, msg="No raw fielding R file")

        npb_scrape.get_fielding(self.year_dir, "F", self.scrape_year)
        field_farm = self.raw_dir + "/" + self.scrape_year + "FieldingRawF.csv"
        is_exist = os.path.exists(field_farm)
        self.assertTrue(is_exist, msg="No raw fielding F file")

    def test_get_daily_stats(self):
        """test_get_daily_stats() tests existence of daily stat files after
        running get_daily_scores() (only if the test year is the current year)
        """
        if self.scrape_year != str(datetime.now().year):
            self.skipTest(
                "get_daily_stats() skipped, test year is not current year"
            )

        npb_scrape.get_daily_scores(self.year_dir, "R", self.scrape_year)
        daily = self.raw_dir + "/" + self.scrape_year + "DailyScoresRawR.csv"
        is_exist = os.path.exists(daily)
        self.assertTrue(is_exist, msg="No raw daily scores R file")


if __name__ == "__main__":
    unittest.main()
