from github import Github
import requests
import pandas as pd
from copy import deepcopy
import yaml

def download_player_data(file_name: str):
    # Get asset download URL from GitHub repo
    g = Github()
    repo = g.get_repo('nflverse/nflverse-data')
    release = repo.get_release('stats_player')
    players_weekly_2024 = next(a for a in release.get_assets() if a.name == 'stats_player_week_2024.parquet')
    download_url = players_weekly_2024.browser_download_url

    # Download asset
    # players_weekly_2024.download_asset('player_data.csv')
    response = requests.get(download_url, stream=True)
    response.raise_for_status()

    with open(data_file_name, "wb") as f_out:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f_out.write(chunk)


def get_player_pts(player: dict, current_week: int, df: pd.DataFrame) -> float:
    if 'custom_score' in player:
        return player['custom_score'] * current_week

    return df.loc[(df['player_display_name'] == player['name']) & (df['week'] <= current_week), 'fantasy_points_ppr'].sum()

def main():
    with open('bets.yaml', 'r') as bets_file:
        yearly_bets = yaml.safe_load(bets_file)

    data_file_name = 'weekly_player_data_2024.parquet'
    # download_player_data(data_file_name)

    df = pd.read_parquet(data_file_name)

    weekly_winners = []

    # weeks 1-18, range is non-inclusive

    for bets in yearly_bets:
        for week in range(1, 19):
            this_week_winners = []
            weekly_winners.append(this_week_winners)
            for bet_idx, bet in enumerate(bets):
                player_plus = bet['player_plus']
                player_plus_pts = get_player_pts(player_plus, df)

                player_minus = bet['player_minus']
                player_minus_pts = get_player_pts(player_minus, df)

                if player_plus_pts > player_minus_pts:
                    winner = {
                        "bet": bet_idx,
                        "winner": bet['player_plus']['bettors']
                    }
                    this_week_winners.append(winner)
                else:
                    winner = {
                        "bet": bet_idx,
                        "winner": bet['player_minus']['bettors']
                    }
                    this_week_winners.append(winner)


    for week_num, week in enumerate(weekly_winners):
        for winner in week:
            print(f'Week {week_num+1}: {winner}')
