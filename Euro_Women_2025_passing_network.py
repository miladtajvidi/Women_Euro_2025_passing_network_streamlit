import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from mplsoccer import VerticalPitch
import matplotlib.image as mpimg
from statsbombpy import sb
import pandas as pd
import numpy as np
from collections import defaultdict
import os

# --- PARAMETERS ---
# Change these to analyze a different match
COMPETITION_ID = 53  # e.g. UEFA Women's Euro
SEASON_ID = 315      # e.g. 2025

# Step 1: List all available matches for the selected competition and season

def print_available_matches(competition_id, season_id):
    matches = sb.matches(competition_id=competition_id, season_id=season_id)
    print("\nAvailable matches for competition ID", competition_id, "and season ID", season_id)
    print("{:<30} {:<30} {:<12}".format("Home Team", "Away Team", "Date"))
    print("-"*75)
    for _, row in matches.iterrows():
        print("{:<30} {:<30} {:<12}".format(row['home_team'], row['away_team'], row['match_date']))
    print("\nChoose the home_team and away_team from the above list.")
    return matches

# Print matches for user reference
_matches_df = print_available_matches(COMPETITION_ID, SEASON_ID)

# Set these after viewing the printed list
HOME_TEAM = "England Women's"
AWAY_TEAM = "Netherlands Women's"

LOGO_PATH = os.path.join(os.path.dirname(__file__), 'logo.png')  # Adjust if needed

# --- SCALING CONSTANTS (should match legend) ---
NODE_SIZES = [50, 100, 150, 200]  # for legend (matplotlib marker size)
NODE_PASS_COUNTS = [1, 25, 60, 100]  # corresponding pass counts for legend
EDGE_WIDTHS = [1, 2, 4, 6]  # for legend (matplotlib linewidth)
EDGE_PASS_COUNTS = [4, 12, 24, 40]  # corresponding pass counts for legend

NODE_BASE_SIZE = NODE_SIZES[0]
NODE_SCALE = (NODE_SIZES[-1] - NODE_SIZES[0]) / (NODE_PASS_COUNTS[-1] - NODE_PASS_COUNTS[0])
EDGE_BASE_WIDTH = EDGE_WIDTHS[0]
EDGE_SCALE = (EDGE_WIDTHS[-1] - EDGE_WIDTHS[0]) / (EDGE_PASS_COUNTS[-1] - EDGE_PASS_COUNTS[0])

# --- DATA LOADING & PROCESSING ---
def get_match_and_events(competition_id, season_id, home_team, away_team):
    matches = sb.matches(competition_id=competition_id, season_id=season_id)
    match = matches[(matches['home_team'] == home_team) & (matches['away_team'] == away_team)]
    if match.empty:
        raise ValueError("Match not found. Check team names and IDs.")
    match_id = match['match_id'].values[0]
    events = sb.events(match_id=match_id)
    return match.iloc[0], events

def extract_starting_xi(events):
    starting_xi = events[events['type'].apply(lambda x: x['name'] if isinstance(x, dict) else x) == 'Starting XI']
    starting_xis = {}
    for _, row in starting_xi.iterrows():
        team = row['team']
        lineup = row['tactics']['lineup']
        player_names = [player['player']['name'] for player in lineup]
        starting_xis[team] = player_names
    return starting_xis

def compute_avg_positions(events, starting_xis):
    on_ball_types = [
        'Ball Receipt','Ball Recovery','Dispossessed','Duel','Block','Clearance',
        'Interception','Carry', 'Dribble', 'Pass', 'Shot','Pressure','Foul Committed',
        'Foul Won','Goal Keeper','Shield','50/50','Error','Miscontrol','Dribbled Past']
    on_ball_events = events[events['type'].apply(lambda x: x['name'] if isinstance(x, dict) else x).isin(on_ball_types)]
    avg_positions = {}
    for team, players in starting_xis.items():
        avg_positions[team] = {}
        for player in players:
            player_events = on_ball_events[(on_ball_events['player'] == player) & (on_ball_events['team'] == team)]
            locations = player_events['location'].dropna().tolist()
            if locations:
                avg_x = np.mean([loc[0] for loc in locations])
                avg_y = np.mean([loc[1] for loc in locations])
                avg_positions[team][player] = (avg_x, avg_y)
            else:
                avg_positions[team][player] = (np.nan, np.nan)
    return avg_positions

def build_passing_matrix(events, starting_xis):
    pass_events = events[events['type'].apply(lambda x: x['name'] if isinstance(x, dict) else x) == 'Pass']
    completed_passes = pass_events[pass_events['pass_outcome'].isna()]
    passing_matrix = {}
    for team, players in starting_xis.items():
        passing_matrix[team] = defaultdict(int)
        team_passes = completed_passes[completed_passes['team'] == team]
        for _, row in team_passes.iterrows():
            passer = row['player']
            recipient = row['pass_recipient']
            if passer in players and recipient in players:
                passing_matrix[team][(passer, recipient)] += 1
    return passing_matrix

def compute_node_sizes(passing_matrix, starting_xis):
    node_sizes = {}
    for team, players in starting_xis.items():
        node_sizes[team] = {}
        for player in players:
            node_sizes[team][player] = sum(
                passing_matrix[team][(player, teammate)]
                for teammate in players if (player, teammate) in passing_matrix[team]
            )
    return node_sizes

def scale_node_size(pass_count):
    # Linear scaling between NODE_PASS_COUNTS[0] and NODE_PASS_COUNTS[-1]
    if pass_count <= NODE_PASS_COUNTS[0]:
        return NODE_SIZES[0]
    if pass_count >= NODE_PASS_COUNTS[-1]:
        return NODE_SIZES[-1]
    return NODE_SIZES[0] + (pass_count - NODE_PASS_COUNTS[0]) * NODE_SCALE

def scale_edge_width(pass_count):
    if pass_count <= EDGE_PASS_COUNTS[0]:
        return EDGE_WIDTHS[0]
    if pass_count >= EDGE_PASS_COUNTS[-1]:
        return EDGE_WIDTHS[-1]
    return EDGE_WIDTHS[0] + (pass_count - EDGE_PASS_COUNTS[0]) * EDGE_SCALE

# --- PLOTTING ---
def plot_passing_network(ax, team, avg_positions, passing_matrix, node_sizes):
    pitch = VerticalPitch(pitch_type='statsbomb', pitch_color='white', line_color='black')
    pitch.draw(ax=ax)
    players = avg_positions[team]
    # Plot nodes (players)
    for player, (x, y) in players.items():
        if not np.isnan(x) and not np.isnan(y):
            size = scale_node_size(node_sizes[team][player])
            ax.scatter(y, x, s=size, color='skyblue', edgecolors='black', zorder=3)
            ax.text(y, x, player.split()[0], ha='center', va='center', fontsize=9, zorder=4)
    # Plot edges (passes)
    for (passer, recipient), count in passing_matrix[team].items():
        x1, y1 = players[passer]
        x2, y2 = players[recipient]
        if not (np.isnan(x1) or np.isnan(y1) or np.isnan(x2) or np.isnan(y2)):
            width = scale_edge_width(count)
            ax.plot([y1, y2], [x1, x2], color='dodgerblue',
                    linewidth=width, alpha=0.7, zorder=2)
    # Title is set in main(), not here.

def plot_legend(ax):
    # --- Custom circles legend ---
    circle_x = [0.43, 0.47, 0.51, 0.55]
    circle_y = 0.75
    for x, s in zip(circle_x, NODE_SIZES):
        ax.plot(x, circle_y, 'o', color='skyblue', markersize=s/10, markeredgecolor='black', clip_on=False)  # match node color
    ax.annotate(
        '', xy=(circle_x[0], circle_y-0.2), xytext=(circle_x[-1], circle_y-0.2),
        arrowprops=dict(arrowstyle='<-', lw=1, color='skyblue'), annotation_clip=False
    )
    ax.text(circle_x[0], circle_y-0.25, f'{NODE_PASS_COUNTS[0]} pass', ha='center', va='top', fontsize=11)
    ax.text(circle_x[-1], circle_y-0.25, f'{NODE_PASS_COUNTS[-1]}+ passes', ha='center', va='top', fontsize=11)
    # --- Custom lines legend ---
    line_x = [0.43, 0.47, 0.51, 0.55]
    line_y = 0.15
    for x, lw in zip(line_x, EDGE_WIDTHS):
        ax.plot([
            x-0.0125, x+0.0125], [line_y-0.02165, line_y+0.02165], color='dodgerblue', lw=lw, solid_capstyle='round', clip_on=False)  # match edge color
    ax.annotate(
        '', xy=(line_x[0], line_y-0.15), xytext=(line_x[-1], line_y-0.15),
        arrowprops=dict(arrowstyle='<-', lw=1, color='dodgerblue'), annotation_clip=False
    )
    ax.text(line_x[0], line_y-0.2, f'{EDGE_PASS_COUNTS[0]} passes', ha='center', va='top', fontsize=11)
    ax.text(line_x[-1], line_y-0.2, f'{EDGE_PASS_COUNTS[-1]}+ passes', ha='center', va='top', fontsize=11)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

# --- MAIN FUNCTION ---
def main(competition_id, season_id, home_team, away_team, logo_path=None):
    match, events = get_match_and_events(competition_id, season_id, home_team, away_team)
    starting_xis = extract_starting_xi(events)
    avg_positions = compute_avg_positions(events, starting_xis)
    passing_matrix = build_passing_matrix(events, starting_xis)
    node_sizes = compute_node_sizes(passing_matrix, starting_xis)

    # Extract match info for titles
    match_date = match['match_date']
    home_score = match['home_score']
    away_score = match['away_score']
    result_str = f"{home_team} {home_score} - {away_score} {away_team}"

    # Set up the figure and grid
    fig = plt.figure(figsize=(12, 8))
    gs = GridSpec(2, 2, height_ratios=[4, 1], hspace=0.2)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    legend_ax = fig.add_subplot(gs[1, :])
    legend_ax.axis('off')

    # Draw passing networks
    plot_passing_network(ax1, home_team, avg_positions, passing_matrix, node_sizes)
    plot_passing_network(ax2, away_team, avg_positions, passing_matrix, node_sizes)
    ax1.set_title(f"{home_team}, Starting Eleven", fontsize=12, loc='left')
    ax2.set_title(f"{away_team}, Starting Eleven", fontsize=12, loc='left')

    # Draw legend
    plot_legend(legend_ax)

    # Titles
    fig.text(0.01, 0.97, "Passing Network", fontsize=16, fontweight='bold', va='top', ha='left')
    fig.text(0.99, 0.97, f"{result_str} {match_date}\nUEFA Women's Euro 2025",
             fontsize=12, va='top', ha='right')

    # Add branding icon between pitches
    if logo_path and os.path.exists(logo_path):
        branding_img = mpimg.imread(logo_path)
        logo_ax = fig.add_axes([0.43, 0.5, 0.15, 0.15], anchor='C', zorder=10)
        logo_ax.imshow(branding_img)
        logo_ax.axis('off')

    plt.show()

# --- RUN ---
if __name__ == "__main__":
    main(COMPETITION_ID, SEASON_ID, HOME_TEAM, AWAY_TEAM, LOGO_PATH)
