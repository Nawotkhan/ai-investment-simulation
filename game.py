!pip install ipywidgets numpy-financial pandas matplotlib
!pip install ipywidgets numpy-financial

import random
import pickle
import os
import numpy as np
import numpy_financial as npf
import ipywidgets as widgets
from IPython.display import display, clear_output, HTML
import pandas as pd
import matplotlib.pyplot as plt

%matplotlib inline

# ---------------------------
# CONFIGURATION & GLOBALS
# ---------------------------
DISCOUNT_RATE = 0.10
ROUNDS = 5
INITIAL_CAPITAL = 5_000_000  # $5M per player

# Global game state variables:
player_names = []          # List of player names
players = {}               # Dictionary mapping player names to their data
game_log = []              # Log of each turn (list of dictionaries)
current_round = 1          # Current round (1 to ROUNDS)
current_player_index = 0   # Index of player whose turn is active
current_market_event = None  # The market event for the current round

# ---------------------------
# DATA DEFINITIONS
# ---------------------------
# 10 Investment Projects
projects = [
    {"icon": "💹", "name": "Crypto Exchange Expansion", "cost": 2_000_000, "life": 3, "cash_inflows": [1_200_000, 1_200_000, 1_200_000], "option": "Expand", "risk": "High"},
    {"icon": "🛡️", "name": "AI Fraud Detection System", "cost": 1_500_000, "life": 3, "cash_inflows": [1_000_000, 1_000_000, 1_000_000], "option": "Delay", "risk": "Medium"},
    {"icon": "🏦", "name": "Neobank Acquisition", "cost": 3_000_000, "life": 5, "cash_inflows": [1_500_000]*5, "option": "Expand or Abandon", "risk": "High"},
    {"icon": "🔒", "name": "GDPR & Data Protection", "cost": 1_000_000, "life": 2, "cash_inflows": [800_000, 800_000], "option": "Abandon", "risk": "Low"},
    {"icon": "🤖", "name": "AI Customer Support Chatbots", "cost": 500_000, "life": 3, "cash_inflows": [400_000, 400_000, 400_000], "option": "Expand", "risk": "Low"},
    {"icon": "🔗", "name": "Blockchain Partnership", "cost": 1_800_000, "life": 4, "cash_inflows": [1_200_000]*4, "option": "Delay", "risk": "Medium"},
    {"icon": "🤖", "name": "AI-Powered Robo Advisors", "cost": 2_200_000, "life": 4, "cash_inflows": [1_300_000]*4, "option": "Expand", "risk": "Medium"},
    {"icon": "💳", "name": "Digital Wallet Launch", "cost": 1_200_000, "life": 3, "cash_inflows": [900_000]*3, "option": "Abandon", "risk": "Medium"},
    {"icon": "✅", "name": "Fintech Compliance Tool", "cost": 900_000, "life": 2, "cash_inflows": [600_000, 600_000], "option": "Expand", "risk": "Low"},
    {"icon": "🌍", "name": "Cross-Border Payments Upgrade", "cost": 1_600_000, "life": 3, "cash_inflows": [1_000_000]*3, "option": "Delay", "risk": "High"}
]

# 5 Financing Options (if needed in a later version, for stats and display)
financing_options = [
    {"name": "Equity", "description": "Issue shares; no repayment; dilutes ownership"},
    {"name": "Bank Loan", "description": "Debt with 7% interest; must repay annually"},
    {"name": "Venture Capital", "description": "VC funding; no interest; trade equity/board seat"},
    {"name": "Retained Earnings", "description": "Use accumulated profits; free but limited"},
    {"name": "Government Grant", "description": "Non-repayable funds; requires innovation"}
]

# 5 Market Events (each event affects cash inflows)
market_events = [
    {"name": "Regulatory Overhaul", "description": "Compliance costs rise by 20%", "effect": lambda inflows: [cf * 0.8 for cf in inflows]},
    {"name": "Cyberattack Breach", "description": "System hacked; penalty of $500K", "effect": lambda inflows: [max(0, cf - 500000) for cf in inflows]},
    {"name": "Interest Rate Hike", "description": "Loans cost more (no cash inflow change)", "effect": lambda inflows: inflows},
    {"name": "Economic Downtime", "description": "Inflows reduced by 20%", "effect": lambda inflows: [cf * 0.8 for cf in inflows]},
    {"name": "Positive Tech Regulation", "description": "Boost of $300K inflow", "effect": lambda inflows: [cf + 300000 for cf in inflows]}
]

# ---------------------------
# FINANCIAL CALCULATION FUNCTIONS
# ---------------------------
def calculate_npv(cash_flows, cost):
    return sum(cf / (1 + DISCOUNT_RATE)**(i + 1) for i, cf in enumerate(cash_flows)) - cost

def calculate_irr(cash_flows, cost):
    return npf.irr([-cost] + cash_flows)

def calculate_payback(cash_flows, cost):
    cumulative = 0
    for i, cf in enumerate(cash_flows):
        cumulative += cf
        if cumulative >= cost:
            return i + 1
    return float('inf')

def calculate_pi(cash_flows, cost):
    return sum(cf / (1 + DISCOUNT_RATE)**(i + 1) for i, cf in enumerate(cash_flows)) / cost

# ---------------------------
# DASHBOARD & OUTPUT FUNCTIONS
# ---------------------------
def display_dashboard():
    clear_output(wait=True)
    dashboard_html = "<h2 style='color:white;background-color:#333;padding:10px;'>Player Dashboard</h2>"
    dashboard_html += "<table style='width:100%; border-collapse: collapse; color:white;'>"
    dashboard_html += "<tr style='background-color:#444;'><th style='padding:5px;border:1px solid #555;'>Player</th>"
    dashboard_html += "<th style='padding:5px;border:1px solid #555;'>Capital</th>"
    dashboard_html += "<th style='padding:5px;border:1px solid #555;'>Projects</th>"
    dashboard_html += "<th style='padding:5px;border:1px solid #555;'>Cumulative NPV</th></tr>"
    for pname, pdata in players.items():
        proj_str = "<br>".join(pdata.get("projects", []))
        dashboard_html += f"<tr style='background-color:#222;'><td style='padding:5px;border:1px solid #555;'>{pname}</td>"
        dashboard_html += f"<td style='padding:5px;border:1px solid #555;'>${pdata['capital']:,}</td>"
        dashboard_html += f"<td style='padding:5px;border:1px solid #555;'>{proj_str}</td>"
        dashboard_html += f"<td style='padding:5px;border:1px solid #555;'>${pdata.get('cumulative_npv', 0):,.2f}</td></tr>"
    dashboard_html += "</table>"
    display(HTML(dashboard_html))
    display(control_box)

# ---------------------------
# INTERACTIVE WIDGETS & CONTROLS
# ---------------------------
round_info = widgets.HTML(value="", placeholder="Round info")
turn_info = widgets.HTML(value="", placeholder="Turn info")
project_dropdown = widgets.Dropdown(options=[], description="Project:")
financing_dropdown = widgets.Dropdown(options=[], description="Financing:")
decision_dropdown = widgets.Dropdown(options=[], description="Decision:")

submit_turn_btn = widgets.Button(description="Submit Turn", button_style="primary")
next_round_btn = widgets.Button(description="Next Round", button_style="info")

# Container for controls – will be updated for each turn
control_box = widgets.VBox([round_info])

# ---------------------------
# GAME FLOW FUNCTIONS
# ---------------------------
def start_round():
    global current_market_event, current_player_index, current_round
    if current_round > ROUNDS:
        end_game()
        return
    # At the start of each round, draw one market event (common to all players)
    current_market_event = random.choice(market_events)
    current_player_index = 0
    round_info.value = f"<b>Round {current_round}</b>: Market Event - <span style='color:#ffcc00;'>{current_market_event['name']}</span> (<i>{current_market_event['description']}</i>)"
    display_dashboard()
    next_turn()

def next_turn():
    global current_player_index, current_round
    if current_player_index >= len(player_names):
        # End of current round; prompt to move to next round
        round_info.value = f"End of Round {current_round}. Click 'Next Round' to proceed."
        control_box.children = [round_info, next_round_btn]
        return

    # Set up the active player's turn
    current_player = player_names[current_player_index]
    turn_info.value = f"<b>{current_player}'s Turn</b>"
    # Populate project dropdown with options (includes icon and cost)
    project_dropdown.options = [(f"{p['icon']} {p['name']} (${p['cost']:,})", p['name']) for p in projects]
    # Populate financing options
    financing_dropdown.options = [(f"{f['name']} - {f['description']}", f['name']) for f in financing_options]
    # Options for decision: Invest (Continue), Delay (shift cash flows), Abandon
    decision_dropdown.options = [("Invest (Continue)", "Continue"), ("Delay", "Delay"), ("Abandon", "Abandon")]
    
    control_box.children = [round_info, turn_info, project_dropdown, financing_dropdown, decision_dropdown, submit_turn_btn]

def submit_turn_action(b):
    global current_player_index
    player = player_names[current_player_index]
    selected_project_name = project_dropdown.value
    selected_financing = financing_dropdown.value
    decision = decision_dropdown.value
    # Identify project details from the list
    proj = next((p for p in projects if p['name'] == selected_project_name), None)
    if not proj:
        turn_info.value = "Error: Project not found."
        return
    # Get the project's base cash inflows and apply the market event effect
    base_inflows = proj['cash_inflows']
    effective_inflows = current_market_event['effect'](base_inflows)
    if decision == "Delay":
        # Shift inflows by one year (simulate delay)
        effective_inflows = [0] + effective_inflows[:-1]
    npv_value = 0
    if decision != "Abandon":
        npv_value = calculate_npv(effective_inflows, proj['cost'])
    # Update player's portfolio & capital if not abandoned
    if decision != "Abandon":
        players[player]['capital'] -= proj['cost']
        players[player]['cumulative_npv'] += npv_value
        players[player]['projects'].append(f"{proj['name']} ({decision}, {selected_financing}) <br>NPV: ${npv_value:,.2f}")
    else:
        players[player]['projects'].append(f"{proj['name']} (Abandoned)")
    # Log the turn data
    game_log.append({
        "Round": current_round,
        "Player": player,
        "Project": proj['name'],
        "Financing": selected_financing,
        "Decision": decision,
        "NPV": npv_value
    })
    current_player_index += 1
    display_dashboard()
    next_turn()

def next_round_action(b):
    global current_round
    current_round += 1
    start_round()

def end_game():
    clear_output(wait=True)
    # Calculate final results for each player
    results = {}
    for pname in player_names:
        pdata = players[pname]
        final_capital = pdata['capital'] + pdata.get('cumulative_npv', 0)
        roi = (final_capital - INITIAL_CAPITAL) / INITIAL_CAPITAL
        results[pname] = {'final_capital': final_capital, 'roi': roi, 'cumulative_npv': pdata.get('cumulative_npv', 0)}
    
    # Determine winner (sorted by ROI, then cumulative NPV)
    sorted_results = sorted(results.items(), key=lambda x: (x[1]['roi'], x[1]['cumulative_npv']), reverse=True)
    winner = sorted_results[0][0]
    
    result_html = "<h2 style='color:white;background-color:#333;padding:10px;'>Final Results</h2>"
    result_html += "<table style='width:100%; border-collapse: collapse; color:white;'>"
    result_html += "<tr style='background-color:#444;'><th style='padding:5px;border:1px solid #555;'>Player</th>"
    result_html += "<th style='padding:5px;border:1px solid #555;'>Final Capital</th>"
    result_html += "<th style='padding:5px;border:1px solid #555;'>Cumulative NPV</th>"
    result_html += "<th style='padding:5px;border:1px solid #555;'>ROI</th></tr>"
    for pname, pdata in results.items():
        result_html += f"<tr style='background-color:#222;'><td style='padding:5px;border:1px solid #555;'>{pname}</td>"
        result_html += f"<td style='padding:5px;border:1px solid #555;'>${pdata['final_capital']:,}</td>"
        result_html += f"<td style='padding:5px;border:1px solid #555;'>${pdata['cumulative_npv']:,.2f}</td>"
        result_html += f"<td style='padding:5px;border:1px solid #555;'>{pdata['roi']*100:.2f}%</td></tr>"
    result_html += "</table>"
    
    winner_message = f"<h2 style='color:yellow;background-color:#333;padding:10px;'>Winner: {winner}!</h2>"
    display(HTML(winner_message))
    display(HTML(result_html))
    
    # Display the game log as a DataFrame
    df_log = pd.DataFrame(game_log)
    display(HTML("<h3 style='color:white;background-color:#333;padding:10px;'>Game Log</h3>"))
    display(df_log)
    
    # Plot cumulative NPV progression by round
    try:
        pivot = df_log.pivot_table(index="Round", columns="Player", values="NPV", aggfunc="sum").fillna(0).cumsum()
        pivot.plot(kind="bar", figsize=(10,5), title="Cumulative NPV Progression by Round")
        plt.ylabel("Cumulative NPV")
        plt.show()
    except Exception as e:
        print("Plot error:", e)

# ---------------------------
# HOOK UP BUTTON ACTIONS
# ---------------------------
submit_turn_btn.on_click(submit_turn_action)
next_round_btn.on_click(next_round_action)

# ---------------------------
# PLAYER SETUP UI
# ---------------------------
def setup_players_ui():
    clear_output(wait=True)
    header = widgets.HTML("<h2 style='color:white;background-color:#333;padding:10px;'>Player Setup</h2>")
    # Create text boxes for four players
    player1 = widgets.Text(value="CFO 1", description="Player 1:")
    player2 = widgets.Text(value="CFO 2", description="Player 2:")
    player3 = widgets.Text(value="CFO 3", description="Player 3:")
    player4 = widgets.Text(value="CFO 4", description="Player 4:")
    start_btn = widgets.Button(description="Start Game", button_style="success")
    
    def on_start(b):
        global player_names, players, current_round, current_player_index
        player_names = [player1.value.strip(), player2.value.strip(), player3.value.strip(), player4.value.strip()]
        players = {name: {"capital": INITIAL_CAPITAL, "projects": [], "cumulative_npv": 0} for name in player_names}
        current_round = 1
        current_player_index = 0
        clear_output()
        display(control_box)
        start_round()
    
    start_btn.on_click(on_start)
    setup_box = widgets.VBox([header, player1, player2, player3, player4, start_btn])
    display(setup_box)

# ---------------------------
# START THE GAME!
# ---------------------------
setup_players_ui()
