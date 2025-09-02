# espn_api library: https://github.com/cwendt94/espn-api

from espn_api.football import League
import sys
import RPi.GPIO as GPIO
from time import sleep
from datetime import datetime, timedelta

teams = sys.argv[1:]
if not teams:
  print('Please provide at least one team name')
  exit(1)

try:
  league = League(league_id=245774800, year=2024)
except Exception as e:
  print(f'Error retrieving league: {e}')
  exit(2)

valid_teams = [team.team_name for team in league.teams]

box_scores = {}
for team in teams:
  if team not in valid_teams:
    print(f'Invalid team name: {team}')
    exit(3)
  box_scores[team] = {'lineup': None, 'no_active_players': False}

consecutive_errors = 0
spoiler_timeout = 30

pin = 16
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)
GPIO.setup(pin, GPIO.OUT)
GPIO.output(pin, GPIO.HIGH)

def unlock_door(seconds):
  GPIO.output(pin, GPIO.LOW)
  sleep(seconds)
  GPIO.output(pin, GPIO.HIGH)

def exit_if_all_teams_have_no_active_players():
  if all(box_score['no_active_players'] for box_score in box_scores.values()):
    print('All teams have no active players')
    GPIO.cleanup()
    exit(0)

while True:
  sleep(35)

  try:
    updated_box_scores = league.box_scores(league.current_week)
  except Exception as e:
    consecutive_errors += 1
    if consecutive_errors >= 5:
      print(f'Error retrieving box scores: {e}')
      GPIO.cleanup()
      exit(4)
    continue

  consecutive_errors = 0
  first_score = True

  new_box_scores = {}
  for matchup in updated_box_scores:
    # home team
    team = matchup.home_team.team_name
    lineup = matchup.home_lineup
    new_box_scores[team] = {'lineup': lineup, 'no_active_players': False}

    # away team
    team = matchup.away_team.team_name
    lineup = matchup.away_lineup
    new_box_scores[team] = {'lineup': lineup, 'no_active_players': False}
  
  for team, old_box_score in box_scores.items():
    if old_box_score['no_active_players']:
      continue

    if team in new_box_scores:
      new_box_score = new_box_scores[team]
      old_lineup = old_box_score['lineup']
      new_lineup = new_box_score['lineup']
      if old_lineup is not None and len(new_lineup) == len(old_lineup):
        new_box_score['no_active_players'] = True
        for i in range(len(new_lineup)):
          new_player = new_lineup[i]
          if new_player.slot_position in ['BE', 'IR'] or new_player.on_bye_week:
            continue

          old_player = old_lineup[i]
          if new_player.points > old_player.points and new_player.name == old_player.name:
            points_scored = new_player.points - old_player.points
            if new_player.position == 'D/ST' and points_scored >= 10:
              pass
            elif new_player.position != 'K' and points_scored >= 6:
              if first_score:
                sleep(spoiler_timeout)
                first_score = False
              print(f'{team} TOUCHDOWN ({new_player.name})')
              unlock_door(new_player.points)
            elif new_player.position == 'QB' and points_scored >= 4:
              if first_score:
                sleep(spoiler_timeout)
                first_score = False
              print(f'{team} TOUCHDOWN ({new_player.name})')
              unlock_door(new_player.points)
            elif new_player.position == 'K' and points_scored >= 3:
              if first_score:
                sleep(spoiler_timeout)
                first_score = False
              print(f'{team} FIELD GOAL ({new_player.name})')
              unlock_door(new_player.points)

          if new_player.game_date <= datetime.now() <= new_player.game_date + timedelta(hours=3, minutes=15):
            new_box_score['no_active_players'] = False

      box_scores[team] = new_box_score
      if box_scores[team]['no_active_players']:
        print(f'{team} has no active players')
        exit_if_all_teams_have_no_active_players()
    else:
      print(f'{team} are on bye')
      box_scores[team]['no_active_players'] = True
      exit_if_all_teams_have_no_active_players()
