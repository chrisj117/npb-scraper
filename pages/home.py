"""Home page for multiple dashboards in Streamlit"""

import streamlit as st


def main():
    """Home page that provides descriptions of stats offered"""

    st.image(
        "https://sp-ao.shortpixel.ai/client/to_webp,q_glossy,ret_img,w_120,h_120/https://www.yakyucosmo.com/wp-content/uploads/2024/08/Yakyu-Cosmo-Logo3-transparent.png",
        width=50,
    )
    st.title("Yakyu Cosmopolitan Dashboard")

    st.header("Team Overview")
    st.write(
        "The team overview displays the primary lineup, rotation, and "
        "bullpen for Nippon Professional Baseball teams. The starting "
        "player at each position is the one who has logged the most "
        "defensive innings (unless they lead at a different position, "
        "in which case the player with the second-most innings is "
        "selected). Also included are the top three bench/reserve "
        "players, determined by plate appearances (PA) among all "
        "non-starters. Their handedness (B), home runs (HR), stolen "
        "bases (SB), strikeout rate (K%), walk rate (BB%), batting "
        "average (AVG), and on-base plus slugging plus (OPS+) are shown. "
        "Starting pitchers are ranked by innings pitched (IP). Their "
        "handedness (T), wins (W), complete games (CG), strikeout rate "
        "(K%), walk rate (BB%), earned run average (ERA), and fielding "
        "independent pitching minus (FIP-) are shown. Relief pitchers "
        "are sorted in order of saves (SV) and holds (HLD) instead."
    )
    st.header("Player Percentiles")
    st.write(
        "The batter and pitcher percentiles visualize a player's key statistics using bar graphs. These percentiles are relative metrics, indicating how a player ranks compared to others across the league. For example, ranking in the 95th percentile means the player is among the top 5% in the league for that stat. A plate appearances (PA) or innings pitched (IP) filter can be applied to adjust the sample of players used for comparison. The absolute minimum for these is 25 PA and 10 IP. Higher percentiles indicate better performance."
    )
    st.write(
        "A hitter's following stats are shown:\n- On Base plus Slugging Plus (OPS+)\n- Isolated Power (ISO)\n- Batting Average on Balls in Play (BABIP)\n- Strikeout Rate (K%)\n- Walk Rate (BB%)\n- Walk to Strikeout Ratio (BB/K)\n- Position-Adjusted Total Zone Runs (Def Value)"
    )
    st.write(
        "Additionally, the following position-specific defensive metrics are included:"
    )
    st.write(
        "- Framing Value per 143 Games (Framing - Catchers)\n- Arm Runs per 143 Games (Arm - Catchers & Outfielders)\n- Double Play Runs per 143 Games (DPR - Infielders)\n- Range Runs per 143 Games (Range - Infielders & Outfielders)"
    )
    st.write("A pitcher's following stats are shown:")
    st.write(
        "- Earned Run Average Plus (ERA+)\n- Fielding Independent Pitching Minus (FIP-)\n- Walks plus Hits per Inning Pitched (WHIP)\n- Strikeout Rate (K%)\n- Walk Rate (BB%)\n- Strikeout Rate minus Walk Rate (K-BB%)"
    )
    st.write("All player's raw stats are displayed below the percentiles.")


if __name__ == "__main__":
    main()
