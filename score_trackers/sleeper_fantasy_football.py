# Sleeper API docs: https://docs.sleeper.com/

import sys
import requests
import RPi.GPIO as GPIO
from time import sleep
from datetime import datetime, timedelta

teams = sys.argv[1:]
if not teams:
  print('Please provide at least one team name')
  exit(1)

league_id = '1258269470326001664'

try:
  users = requests.get(f'https://api.sleeper.app/v1/league/{league_id}/users').json()
except Exception as e:
  print(f'Error retrieving users: {e}')
  exit(2)

team_to_user = {}
for user in users:
  if 'team_name' in user['metadata']:
    team_to_user[user['metadata']['team_name']] = user['user_id']
  else:
    team_to_user[f'Team {user["display_name"]}'] = user['user_id']

try:
  rosters = requests.get(f'https://api.sleeper.app/v1/league/{league_id}/rosters').json()
except Exception as e:
  print(f'Error retrieving rosters: {e}')
  exit(3)

user_to_roster = {roster['owner_id']: roster['roster_id'] for roster in rosters}

team_to_roster = {}
for team in teams:
  if team not in team_to_user.keys():
    print(f'Invalid team name: {team}')
    exit(4)
  team_to_roster[team] = user_to_roster[team_to_user[team]]

try:
  week = requests.get('https://api.sleeper.app/v1/state/nfl').json()['week']
except Exception as e:
  print(f'Error retrieving week: {e}')
  exit(5)

try:
  players = requests.get('https://api.sleeper.app/v1/players/nfl').json()
except Exception as e:
  print(f'Error retrieving players: {e}')
  exit(6)

box_scores = {team: None for team in teams}
consecutive_errors = 0

pin = 16
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)
GPIO.setup(pin, GPIO.OUT)
GPIO.output(pin, GPIO.HIGH)

def unlock_door(seconds):
  GPIO.output(pin, GPIO.LOW)
  sleep(seconds)
  GPIO.output(pin, GPIO.HIGH)

while(True):
  sleep(5)

  try:
    matchups = requests.get(f'https://api.sleeper.app/v1/league/{league_id}/matchups/{week}').json()
  except Exception as e:
    consecutive_errors += 1
    if consecutive_errors >= 5:
      print(f'Error retrieving matchups: {e}')
      GPIO.cleanup()
      exit(7)
    continue

  consecutive_errors = 0

  new_box_scores = {}
  for team in teams:
    for matchup in matchups:
      if team_to_roster[team] == matchup['roster_id']:
        new_box_scores[team] = [
          {
            'id': player_id,
            'name': f'{players[player_id]["first_name"]} {players[player_id]["last_name"]}' if player_id != '0' else None,
            'position': players[player_id]['position'] if player_id != '0' else None,
            'points': points
          }
          for player_id, points in zip(matchup['starters'], matchup['starters_points'])
        ]

  for team, old_box_score in box_scores.items():
    new_box_score = new_box_scores[team]
    for old_player, new_player in zip(old_box_score['players'], new_box_score['players']):
      if new_player['id'] == old_player['id'] and new_player['points'] > old_player['points']:
        points_scored = new_player['points'] - old_player['points']
        if new_player['position'] == 'DEF':
          if points_scored == 10:
            pass
          elif points_scored >= 6:
            print(f'{team} TOUCHDOWN ({new_player["name"]})')
            unlock_door(60)
          elif points_scored >= 2:
            print(f'{team} BIG DEFENSIVE PLAY ({new_player["name"]})')
            unlock_door(45)
        elif new_player['position'] != 'K' and points_scored >= 6:
          print(f'{team} TOUCHDOWN ({new_player["name"]})')
          unlock_door(60)
        elif new_player['position'] == 'QB' and points_scored >= 4:
          print(f'{team} PASSING TOUCHDOWN ({new_player["name"]})')
          unlock_door(45)
        elif new_player['position'] == 'K' and points_scored >= 3:
          print(f'{team} FIELD GOAL ({new_player["name"]})')
          unlock_door(30)

    box_scores[team] = new_box_score  
