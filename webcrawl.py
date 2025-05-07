import os
import pdb
from openai import OpenAI
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import json
from datetime import datetime

from prompts import SYSTEM_MESSAGE, TOOLS
# from anthropic import ClaudeClient


# client = ClaudeClient(api_key="sk-ant-api03-Z-1234567890")

TEAM_ID = 597089

TEAMS = {
    597089: "Wooster Fighting Scots",
}


roster_url = "https://stats.ncaa.org/teams/{team_id}/roster"
# TODO: Make a function to get the pitcher and which side they are pitching from on each team. We can also use this to get the full names of each player from each of the games to standardize them on the csv

#Get the starting pitcher for each team here: 
individual_stats_url = "https://stats.ncaa.org/contests/{game_id}/individual_stats"

# Define headers to mimic a browser
HEADERS = {
    "Host": "stats.ncaa.org",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:138.0) Gecko/20100101 Firefox/138.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Referer": "https://stats.ncaa.org/contests/6358448/individual_stats",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "If-None-Match": "W/\"6679bbe64d30ce8d43d9cb8f8f72f7d6\"",
    "Priority": "u=0, i",
    "TE": "trailers"
}

url = f"https://stats.ncaa.org/teams/{TEAM_ID}"

NON_HITTING_PLAYS = [
    "to p for",
    "balk",
    "stole",
    "caught stealing",
    "wild pitch",
    "passed ball",
    "pinch hit",
]


def non_hitting_play(play_description):
    for play in NON_HITTING_PLAYS:
        if play in play_description:
            return True
    return False

class GameState:
    def __init__(self, home_team, away_team, final_home_score, final_away_score):
        self.home_team = home_team
        self.away_team = away_team
        self.current_home_score = 0
        self.current_away_score = 0
        self.runner_on_first = ""
        self.runner_on_second = ""
        self.runner_on_third = ""
        self.outs = 0
        self.home_lineup_position = 1
        self.away_lineup_position = 1
        self.pinch_hitter = False
        self.final_home_score = final_home_score
        self.final_away_score = final_away_score

    def update_state(self, state):
        self.runner_on_first = state['runner_on_first']
        self.runner_on_second = state['runner_on_second']
        self.runner_on_third = state['runner_on_third']
        self.outs = state['outs']
        

    def create_prompt(self, play_description):
        prompt = f"""
        You are a baseball analyst. You are given a play description and you need to update the game state based on the play description.
        Before the play, the game state was:
        "Runner on first: {self.runner_on_first}
        Runner on second: {self.runner_on_second}
        Runner on third: {self.runner_on_third}
        Outs: {self.outs}

        The play description is:
        {play_description}

        Please use the 'add_play' tool to update the game state based on the current state and the play description, and add a row to the database with the correct information given the play description.
        """
        return prompt

    def reset_inning(self):
        self.runner_on_first, self.runner_on_second, self.runner_on_third = "", "", ""
        self.outs = 0
        self.pinch_hitter = False

        #TODO: Add home pitcher, away pitcher, etc


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_team_stats(team_id, game_ids=[]):
    url = f"https://stats.ncaa.org/teams/{team_id}"
    # Make the request with the headers
    response = requests.get(url, headers=HEADERS)
    html_content = response.text
    soup = BeautifulSoup(html_content, "html.parser")

    # Find all game links that match the pattern for box scores
    game_links = []
    final_home_score = 0
    final_away_score = 0
    game_states = []
    if not game_ids:
        game_ids = []
        
    
        # Find all game links that match the pattern for box scores
        for link in soup.find_all('a', href=True, class_="skipMask", attrs={"target": "BOX_SCORE_WINDOW"}):

            match = re.search(r'/contests/(\d+)/box_score', link['href'])
            if match:
                game_id = match.group(1)
                game_ids.append(game_id)


            game_url = link['href']
            game_result = link.text.strip()
            game_links.append({
                'url': f"https://stats.ncaa.org{game_url}",
                'result': game_result
            })

            try:
                # Find the index of the first dash
                dash_index = game_result.find('-')
                if dash_index != -1:
                    # Use regex to extract scores around the dash
                    score_pattern = r'(\d+)-(\d+)'
                    match = re.search(score_pattern, game_result)

                    if match:
                        # Convert to integers to ensure proper data type
                        final_away_score = int(match.group(1))
                        final_home_score = int(match.group(2))
                        game_states.append(GameState("", "", final_away_score, final_home_score))

                    else:
                        pdb.set_trace()
                        print(f"Error parsing game result: {game_result}")
            except:
                print(f"Error parsing game result: {game_result}")
        # Print the results
        if len(game_links) > 0:
            print(f"Found {len(game_links)} game links:")
            
        else:
            raise Exception("No game links found")
    print("We have ", len(game_states), " game states")
    
    # Once we have all the game IDs, we can go through and get the play by play data for each game
    index = 0
    for game_id in game_ids:
        
        game_state = game_states[index]
        index += 1
        play_by_play_url = f"https://stats.ncaa.org/contests/{game_id}/play_by_play"
        play_by_play_response = requests.get(play_by_play_url, headers=HEADERS)
        play_by_play_html = play_by_play_response.text
        play_by_play_soup = BeautifulSoup(play_by_play_html, "html.parser")
        
        # Find team links with text content (not images)
        team_links = play_by_play_soup.find_all('a', target="TEAMS_WIN", class_="skipMask", href=True)
        # Filter to only links that have text content (not images)
        text_team_links = [link for link in team_links if link.text.strip()]
        
        # Get home and away team information
        if len(text_team_links) >= 2:
            # First link is home team, second is away team
            home_team_link = text_team_links[1]
            away_team_link = text_team_links[0]
            
            # Extract team IDs from href attributes
            home_team_id = re.search(r'/teams/(\d+)', home_team_link['href']).group(1)
            away_team_id = re.search(r'/teams/(\d+)', away_team_link['href']).group(1)
            
            # Extract team names
            home_team_name = home_team_link.text.strip()
            away_team_name = away_team_link.text.strip()

            # Find the table with game information
            game_table = play_by_play_soup.find('table', attrs={"style": "border-collapse: collapse"})
            
            # Initialize variables
            game_date = None
            game_location = None
            game_attendance = None
            
            if game_table:
                # Find all grey_text cells that might contain our data
                grey_cells = game_table.find_all('td', class_="grey_text")
                
                for i, cell in enumerate(grey_cells):
                    cell_text = cell.text.strip()
                    
                    # Check for date format (MM/DD/YYYY)
                    if re.match(r'\d{2}/\d{2}/\d{4}', cell_text):
                        game_date = datetime.strptime(cell_text, '%m/%d/%Y')
                    
                    # Check for attendance format
                    elif 'Attendance:' in cell_text:
                        game_attendance = int(cell_text.split("Attendance:")[1].strip())
                    
                    # If we found date and attendance, the cell between them is location
                    elif game_date is not None and game_attendance is None and i > 0:
                        game_location = cell_text
            
            # If we couldn't find the data, debug
            if not all([game_date, game_location, game_attendance]):
                print(f"Missing game data for Game ID: {game_id}, at link: {play_by_play_url}")


            print(f"Game ID: {game_id} on {game_date} at {game_location} with {game_attendance} in attendance")
            print(f"Home Team: {home_team_name} (ID: {home_team_id}), Final Score: {game_state.final_home_score}")
            print(f"Away Team: {away_team_name} (ID: {away_team_id}), Final Score: {game_state.final_away_score}")

            inning = 1
            # Create a list to store all at-bat data
            at_bat_data = []

            for inning_soup in play_by_play_soup.find_all('div', class_="card-body"):
                # Find the table body with play-by-play data
                table_body = inning_soup.find('tbody')
                if table_body:
                    # Process each row in the table
                    for row in table_body.find_all('tr'):
                        cells = row.find_all('td')
                        if len(cells) == 3:

                            if 'pinch hit' in cells[0].text.strip().lower():
                                game_state.pinch_hitter = True
                                continue

                            away_play = cells[0].text.strip()
                            score_text = cells[1].text.strip()
                            home_play = cells[2].text.strip()

                            
                            is_away_batting = bool(away_play)
                            play_description = away_play if is_away_batting else home_play
                            batting_team = away_team_name if is_away_batting else home_team_name
                            fielding_team = home_team_name if is_away_batting else away_team_name
                            
                            
                            messages = [
                                {"role": "system", "content": SYSTEM_MESSAGE},
                                {"role": "user", "content": game_state.create_prompt(play_description)}
                            ]
                            response = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=messages,
                                tools=TOOLS,
                               
                            )

                            tool_call = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
                           
                            result = tool_call['result']
                            hitter = tool_call['hitter']
                            hit_type = tool_call['hit_type']
                            hit_location = tool_call['hit_location']
                            runs_scored = tool_call['runs_scored']
                            
                            # Prepare data for this at-bat
                            if hitter != 'N':
                                at_bat = {
                                    'GAME ID': game_id,
                                    'GAME DATE': game_date,
                                    'GAME LOCATION': game_location,
                                    'GAME ATTENDANCE': game_attendance,
                                    'HOME TEAM': home_team_name,
                                    'AWAY TEAM': away_team_name,
                                    'INNING': inning,
                                    'HITTER': hitter,
                                    'RESULT': result,
                                    'HIT TYPE': hit_type,
                                    'HIT LOCATION': hit_location,
                                    'RUNS SCORED': runs_scored,
                                    'BATTING TEAM': batting_team,
                                    'FIELDING TEAM': fielding_team,
                                    'PLAY DESCRIPTION': play_description,
                                    'FINAL AWAY SCORE': game_state.final_away_score,
                                    'FINAL HOME SCORE': game_state.final_home_score,
                                    'RUNNER ON FIRST': game_state.runner_on_first,
                                    'RUNNER ON SECOND': game_state.runner_on_second,
                                    'RUNNER ON THIRD': game_state.runner_on_third,
                                    'OUTS': game_state.outs,
                                    'LINEUP POSITION': game_state.away_lineup_position if is_away_batting else game_state.home_lineup_position,
                                    'PINCH HITTER': game_state.pinch_hitter,
                                    'RUNS SCORED': runs_scored,

                                }

                               
                                if is_away_batting:
                                    game_state.away_lineup_position = (game_state.away_lineup_position % 9) + 1
                                else:
                                    game_state.home_lineup_position = (game_state.home_lineup_position % 9) + 1
                                game_state.pinch_hitter = False

                             
                            state = tool_call['state']

                            game_state.update_state(state)

                            if game_state.outs >= 3:
                                game_state.reset_inning()
                            
                            # Add to our data collection
                            at_bat_data.append(at_bat)
                            # Convert datetime objects to strings for JSON serialization
                            at_bat_copy = at_bat.copy()
                            if 'GAME DATE' in at_bat_copy and isinstance(at_bat_copy['GAME DATE'], datetime):
                                at_bat_copy['GAME DATE'] = at_bat_copy['GAME DATE'].strftime('%Y-%m-%d')
                            print("Added at_bat: ", json.dumps(at_bat_copy, indent=4))
                            at_bat_data[-1] = at_bat
                

                inning += 1
            
            # Convert collected data to DataFrame
            plays_df = pd.DataFrame(at_bat_data)
            print(f"Collected {len(plays_df)} plays for game ID: {game_id}")
            
            # Save to CSV for further processing
            plays_df.to_csv(f"games/game_{game_id}_plays.csv", index=False)
                
        else:
            print(f"Could not find both teams for game ID: {game_id}, at link: {play_by_play_url}")
            continue
            

def get_team_roster(team_id):
    url = f"https://stats.ncaa.org/teams/{team_id}/roster"
    response = requests.get(url, headers=HEADERS)
    html_content = response.text
    soup = BeautifulSoup(html_content, "html.parser")
    roster_table = soup.find('table', id="rosters_form_players_16840_data_table")
    # Find all player links
    player_rows = roster_table.find_all('tr')
    player_ids = []
    player_data = []
    for row in player_rows:
        print("Found a row in player rows")
        cells = row.find_all('td')
        if len(cells) > 0 and row.find('a'):
            link = row.find('a')['href']
            player_id = re.search(r'/players/(\d+)', link).group(1) if re.search(r'/players/(\d+)', link) else ""
            
            # Extract data from table cells
            player_info = {
                'id': player_id,
                'number': cells[2].text.strip() if len(cells) > 2 else "",
                'name': cells[3].text.strip() if len(cells) > 3 else "",
                'position': cells[5].text.strip() if len(cells) > 5 else "",
                'height': cells[6].text.strip() if len(cells) > 6 else "",
                'bats': cells[7].text.strip() if len(cells) > 7 else "",
                'throws': cells[8].text.strip() if len(cells) > 8 else ""
            }
            
            player_ids.append(player_id)
            player_data.append(player_info)
            print(f"Player: {player_info}")
    
    # Create players directory if it doesn't exist
    os.makedirs('players', exist_ok=True)
    
    # Convert player data to DataFrame and save to CSV
    players_df = pd.DataFrame(player_data)
    csv_path = f"players/team_{team_id}_players.csv"
    players_df.to_csv(csv_path, index=False)
    print(f"Saved roster to {csv_path}")
            
    return player_data
    

# This function would call GPT to analyze the play and update state

if __name__ == "__main__":

    # get_team_stats(TEAM_ID)
    get_team_roster(TEAM_ID)
