import requests
import json
import csv

def main():
    api_base_url = 'https://lscluster.hockeytech.com/feed/index.php'
    general_params = {
        'season': 8,
        'key': '446521baf8c38984',
        'client_code': 'pwhl',
    }
    players_params = {
        'feed': 'statviewfeed',
        'view': 'players',
        'team': 'all',
        'position': 'skaters',
        'sort': 'points',
        'limit': 250
    }
    games_params = {
        'feed': 'modulekit',
        'view': 'player',
        'category': 'gamebygame',
    }
    my_team_name = "Two Rooks Are Better Than One Knight"
    my_players_names = [
        "Abby Newhook",
        "Marie-Philip Poulin",
        "Sarah Fillier",
        "Daryl Watts",
        "Emily Clark",
        "Hannah Miller",
        "Jessie Eldridge",
        "Abby Hustler",
    ]

    players_json = get_api_response(api_base_url, players_params | general_params)
    api_player_list = deep_get(players_json, [0, 'sections', 0, 'data'], [])
    player_id_by_player_name = {deep_get(player, ['row', 'name'], ''): deep_get(player, ['row', 'player_id'], '') for player in api_player_list}
                    
    fantasy_points_by_team_name = {}
    fantasy_points_by_player_name = {}

    with open('pwhl_fantasy_teams.csv', mode='r') as csv_file:
        teams_file = csv.reader(csv_file)
        next(teams_file)    # skip the header row
        
        for team_row in teams_file:
            team_name = team_row[0]
            players_array = team_row[1:]

            team_fantasy_points = 0
            if any('(G)' in player_info for player_info in players_array) and sum(['(D)' in player_info for player_info in players_array]) >= 2:
                team_fantasy_points += 10
            if any(player_info.endswith('R') for player_info in players_array):
                team_fantasy_points += 10
            
            for player_info in players_array:
                player_name = player_info[:player_info.find('(')-1].strip()
                
                if player_name not in player_id_by_player_name:
                    fantasy_points_by_player_name[player_name] = 0
                
                if player_name in fantasy_points_by_player_name:
                    team_fantasy_points += fantasy_points_by_player_name[player_name]
                    continue
                fantasy_points_by_player_name[player_name] = 0
                
                player_id = player_id_by_player_name[player_name]
                games_json = get_api_response(api_base_url, {'player_id': player_id} | games_params | general_params)
                games = deep_get(games_json, ['SiteKit', 'Player', 'games'], [])
                for game in games:
                    if '(G)' in player_info:
                        fantasy_points = get_goalie_fantasy_points_by_game(game)
                    else:
                        fantasy_points = get_skater_fantasy_points_by_game(game)
                    fantasy_points_by_player_name[player_name] += fantasy_points
                
                team_fantasy_points += fantasy_points_by_player_name[player_name]

            fantasy_points_by_team_name[team_name] = team_fantasy_points

    ranked_team_list = list(sorted(fantasy_points_by_team_name.items(), key=lambda item: item[1], reverse=True))
    for ranked_team_index, ranked_team in enumerate(ranked_team_list):
        # print my team points
        if ranked_team[0] == my_team_name:
            print(f'{ranked_team_index + 1}. {ranked_team[0]} - {ranked_team[1]}')
    
    # print my player points
    for player_name in my_players_names:
        print(f'{player_name}: {fantasy_points_by_player_name[player_name]}')


def get_skater_fantasy_points_by_game(game):
    goals = int(game.get('goals', 0))
    assists = int(game.get('assists', 0))
    plus_minus_pts = 5 if int(game.get('plusminus') or 0) > 0 else 0
    
    return goals + assists + plus_minus_pts


def get_goalie_fantasy_points_by_game(game):
    win_pts = 5 if int(game.get('win') or 0) == 1 else 0
    shutout_pts = 5 if int(game.get('shutout') or 0) == 1 else 0
    
    return win_pts + shutout_pts


def get_api_response(api_base_url, params_dict):
    headers = {'Content-Type': 'application/json'}
    params_str = '&'.join([f'{param[0]}={param[1]}' for param in params_dict.items()])
    
    r = requests.get(f'{api_base_url}?{params_str}', headers=headers)
    if r.status_code != 200:
        raise Exception(f'request failed: {r}')

    # The API returns JSONP format wrapped in parentheses: ([...])
    # Strip the leading ( and trailing ) to get valid JSON
    response_text = r.text.strip()
    if response_text.startswith('(') and response_text.endswith(')'):
        response_text = response_text[1:-1]
    json_data = json.loads(response_text)

    return json_data


def deep_get(dictionary, keys, default=None):
    current = dictionary
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        elif isinstance(current, list):
            if isinstance(key, int) and -1 <= key < len(current):
                current = current[key]
            else:
                return default
        else:
            return default
        if current is None:
            return default
    
    return current
    

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f'error in main(): {e}')

