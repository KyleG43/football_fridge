import sys
import RPi.GPIO as GPIO
from time import sleep
import requests

teams = sys.argv[1:]
if not teams:
  print('Please provide at least one team name')
  exit(1)

valid_teams = [
  '49ers', 'Bears', 'Bengals', 'Bills', 'Broncos', 'Browns', 'Buccaneers', 'Cardinals',
  'Chargers', 'Chiefs', 'Colts', 'Commanders', 'Cowboys', 'Dolphins', 'Eagles', 'Falcons',
  'Giants', 'Jaguars', 'Jets', 'Lions', 'Packers', 'Panthers', 'Patriots', 'Raiders',
  'Rams', 'Ravens', 'Saints', 'Seahawks', 'Steelers', 'Texans', 'Titans', 'Vikings'
]

scores = {}
for team in teams:
  if team not in valid_teams:
    print(f'Invalid team name: {team}')
    exit(2)
  scores[team] = {'value': None, 'final': False}

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

def exit_if_no_teams_are_playing():
  if all(score['final'] for score in scores.values()):
    GPIO.cleanup()
    print('All games have ended. Exiting...')
    exit(0)

while True:
  sleep(35)

  try:
    response = requests.get('https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard')
    response.raise_for_status()
  except Exception as e:
    consecutive_errors += 1
    if consecutive_errors >= 5:
      GPIO.cleanup()
      print(f'Error retrieving scores: {e}')
      exit(3)
    continue

  consecutive_errors = 0
  first_score = True

  new_scores = {}
  for event in response.json()['events']:
    for competitor in event['competitions'][0]['competitors']:
      team = competitor['team']['name']
      score = int(competitor['score'])
      final = event['status']['type']['completed']
      
      new_scores[team] = {'value': score, 'final': final}
  
  for team, old_score in scores.items():
    if old_score['final']:
      continue

    if team in new_scores:
      new_score = new_scores[team]
      if old_score['value'] is not None and new_score['value'] > old_score['value']:
        points_scored = new_score['value'] - old_score['value']
        if points_scored >= 6:
          if first_score:
            sleep(spoiler_timeout)
            first_score = False
          print(f'{team} TOUCHDOWN')
          unlock_door(new_score['value'])
        elif points_scored == 3:
          if first_score:
            sleep(spoiler_timeout)
            first_score = False
          print(f'{team} FIELD GOAL')
          unlock_door(new_score['value'])

      scores[team] = new_score
      if scores[team]['final']:
        print(f'{team} game has ended')
        exit_if_no_teams_are_playing()
    else:
      scores[team]['final'] = True
      print(f'{team} are on bye')
      exit_if_no_teams_are_playing()
