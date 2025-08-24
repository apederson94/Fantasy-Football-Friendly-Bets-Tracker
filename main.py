from github import Github
import requests
import pandas as pd
import yaml

def download_weekly_player_stats(year: int) -> str:
    # Get asset download URL from GitHub repo
    g = Github()
    repo = g.get_repo('nflverse/nflverse-data')
    release = repo.get_release('stats_player')
    asset_name = f'stats_player_week_{year}.parquet'
    players_weekly_2024 = next(a for a in release.get_assets() if a.name == asset_name)
    download_url = players_weekly_2024.browser_download_url

    # Download asset
    # players_weekly_2024.download_asset('player_data.csv')
    response = requests.get(download_url, stream=True)
    response.raise_for_status()

    # write the data to a file so that we can stash it for later
    with open(asset_name, "wb") as f_out:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f_out.write(chunk)

    return asset_name


def get_player_pts(player: dict, current_week: int, df: pd.DataFrame) -> float:
    # calculate the custom player data
    if 'custom_score' in player:
        return player['custom_score'] * current_week

    # get all weekly stats for a player up until the current week and then sum them
    return df.loc[(df['player_display_name'] == player['name']) & (df['week'] <= current_week), 'fantasy_points_ppr'].sum()


def calculate_winner(bet: dict, bet_idx: int, week: int, df: pd.DataFrame) -> dict:
    # get the data for the player who is being bet to be higher in points
    player_plus = bet['player_plus']
    player_plus_pts = get_player_pts(player_plus, week, df)

    # get the data for the player who is being bet to be lower in points
    player_minus = bet['player_minus']
    player_minus_pts = get_player_pts(player_minus, week, df)

    if player_plus_pts > player_minus_pts:
        return {
            "bet": bet_idx,
            "winner": bet['player_plus']['bettors']
        }
    else:
        return {
            "bet": bet_idx,
            "winner": bet['player_minus']['bettors']
        }


def player_cumulative_df(players: list, stats_df: pd.DataFrame) -> pd.DataFrame:
  """
  takes a list of players and calculated the pivoted cumsum of fantasy_points
  for easy comparisons
  """

  # one issue you're going to have here is that making sure the players names
  # are lined up with the dataframe from the API repsonse
  is_in = stats_df['player_display_name'].isin(players)
  picked_df = stats_df.loc[is_in]
  picked_df = picked_df.sort_values(by=['player_display_name', 'week'])
  select_df = picked_df[['player_display_name', 'week', 'fantasy_points']]
  select_df['cumulative_points'] = select_df.groupby('player_display_name')['fantasy_points'].cumsum()

  pivot_df = select_df.pivot(index='player_display_name', columns='week', values='cumulative_points').ffill(axis=1).reset_index().style.hide(axis='index')

  return pivot_df


def main():
    with open('bets.yaml', 'r') as bets_file:
        yearly_bets = yaml.safe_load(bets_file)

    weekly_winners = []

    for year in yearly_bets:
        # Download player data only the first time you run this script otherwise runs will take longer
        # and you'll get rate limited by GitHub
        # data_file_name = download_weekly_player_stats(year)

        # This name format comes from the GitHub repo
        data_file_name = f'stats_player_week_{year}.parquet'

        df = pd.read_parquet(data_file_name)
        bets = yearly_bets[year]

        # weeks 1-18, range is non-inclusive
        # Doing this manually for now since I haven't figured out quite how to compare across dataframes
        for week in range(1, 19):
            this_week_winners = []
            weekly_winners.append(this_week_winners)

            for bet_idx, bet in enumerate(bets):
                winner = calculate_winner(bet, bet_idx, week, df)
                this_week_winners.append(winner)

    # print out the weekly winners for each bet
    for week_num, week in enumerate(weekly_winners):
        for winner in week:
            print(f'Week {week_num+1}: {winner}')


if __name__ == '__main__':
    main()
