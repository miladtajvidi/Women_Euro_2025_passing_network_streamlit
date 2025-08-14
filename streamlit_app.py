import streamlit as st
import matplotlib.pyplot as plt
from Euro_Women_2025_passing_network import (
    get_match_and_events,
    extract_starting_xi,
    compute_avg_positions,
    build_passing_matrix,
    compute_node_sizes,
    plot_passing_network,
    plot_legend
)
from statsbombpy import sb
import os

COMPETITION_ID = 53  # UEFA Women's Euro
SEASON_ID = 315      # 2025
LOGO_PATH = os.path.join(os.path.dirname(__file__), 'logo.png')

st.set_page_config(page_title="Euro Women Passing Network", layout="wide")
st.title("Euro Women 2025 Passing Network Visualization")

# Load matches
def get_matches():
    matches = sb.matches(competition_id=COMPETITION_ID, season_id=SEASON_ID)
    matches["label"] = matches["home_team"] + " vs " + matches["away_team"] + " (" + matches["match_date"] + ")"
    return matches

matches_df = get_matches()
match_labels = matches_df["label"].tolist()

selected_label = st.selectbox("Select a match to visualize passing networks:", match_labels)
selected_match = matches_df[matches_df["label"] == selected_label].iloc[0]
home_team = selected_match["home_team"]
away_team = selected_match["away_team"]

# Load and process data
def plot_streamlit_passing_network():
    match, events = get_match_and_events(COMPETITION_ID, SEASON_ID, home_team, away_team)
    starting_xis = extract_starting_xi(events)
    avg_positions = compute_avg_positions(events, starting_xis)
    passing_matrix = build_passing_matrix(events, starting_xis)
    node_sizes = compute_node_sizes(passing_matrix, starting_xis)

    match_date = match['match_date']
    home_score = match['home_score']
    away_score = match['away_score']
    result_str = f"{home_team} {home_score} - {away_score} {away_team}"

    fig = plt.figure(figsize=(12, 8))
    gs = plt.GridSpec(2, 2, height_ratios=[4, 1], hspace=0.2)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    legend_ax = fig.add_subplot(gs[1, :])
    legend_ax.axis('off')

    plot_passing_network(ax1, home_team, avg_positions, passing_matrix, node_sizes)
    plot_passing_network(ax2, away_team, avg_positions, passing_matrix, node_sizes)
    ax1.set_title(f"{home_team}, Starting Eleven", fontsize=12, loc='left')
    ax2.set_title(f"{away_team}, Starting Eleven", fontsize=12, loc='left')
    plot_legend(legend_ax)

    fig.text(0.01, 0.97, "Passing Network", fontsize=16, fontweight='bold', va='top', ha='left')
    fig.text(0.99, 0.97, f"{result_str} {match_date}\nUEFA Women's Euro 2025", fontsize=12, va='top', ha='right')

    # Optionally add logo if available
    if LOGO_PATH and os.path.exists(LOGO_PATH):
        import matplotlib.image as mpimg
        branding_img = mpimg.imread(LOGO_PATH)
        logo_ax = fig.add_axes([0.43, 0.5, 0.15, 0.15], anchor='C', zorder=10)
        logo_ax.imshow(branding_img)
        logo_ax.axis('off')

    st.pyplot(fig)

if st.button("Show Passing Network"):
    plot_streamlit_passing_network()
