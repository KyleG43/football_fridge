import sys
import RPi.GPIO as GPIO
from time import sleep
import requests

teams = sys.argv[1:]
if not teams:
  print('Please provide at least one team name')
  exit(1)

valid_teams = {
  'mlb': [
    'Angels', 'Astros', 'Athletics', 'Blue Jays', 'Braves', 'Brewers',
    'Cardinals', 'Cubs', 'Diamondbacks', 'Dodgers', 'Giants', 'Guardians',
    'Mariners', 'Marlins', 'Mets', 'Nationals', 'Orioles', 'Padres',
    'Phillies', 'Pirates', 'Rangers', 'Rays', 'Red Sox', 'Reds',
    'Rockies', 'Royals', 'Tigers', 'Twins', 'White Sox', 'Yankees'
  ],
  'mls': [
    'Atlanta United FC', 'Austin FC', 'CF Montréal', 'Charlotte FC', 'Chicago Fire FC',
    'Colorado Rapids', 'Columbus Crew', 'D.C. United', 'FC Cincinnati', 'FC Dallas',
    'Houston Dynamo FC', 'Inter Miami CF', 'LA Galaxy', 'LAFC', 'Minnesota United FC',
    'Nashville SC', 'New England Revolution', 'New York City FC', 'New York Red Bulls', 'Orlando City SC',
    'Philadelphia Union', 'Portland Timbers', 'Real Salt Lake', 'San Diego FC', 'San Jose Earthquakes',
    'Seattle Sounders FC', 'Sporting Kansas City', 'St. Louis City SC', 'Toronto FC', 'Vancouver Whitecaps FC'
  ],
  'nfl': [
    '49ers', 'Bears', 'Bengals', 'Bills', 'Broncos', 'Browns', 'Buccaneers', 'Cardinals',
    'Chargers', 'Chiefs', 'Colts', 'Commanders', 'Cowboys', 'Dolphins', 'Eagles', 'Falcons',
    'Giants', 'Jaguars', 'Jets', 'Lions', 'Packers', 'Panthers', 'Patriots', 'Raiders',
    'Rams', 'Ravens', 'Saints', 'Seahawks', 'Steelers', 'Texans', 'Titans', 'Vikings'
  ]
}

leagues = {
  'mlb': {
    'active': False,
    'url': 'https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard'
  },
  'mls': {
    'active': False,
    'url': 'https://site.api.espn.com/apis/site/v2/sports/soccer/usa.1/scoreboard'
  },
  'nfl': {
    'active': False,
    'url': 'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard'
  }
}

get_league = lambda team: next((league for league, teams in valid_teams.items() if team in teams), None)

scores = {}
for team in teams:
  if not any(team in league for league in valid_teams.values()):
    print(f'Invalid team name: {team}')
    exit(2)
  league = get_league(team)
  scores[team] = {'value': None, 'final': False, 'league': league}
  leagues[league]['active'] = True

consecutive_errors = 0
spoiler_timeout = 30

pin = 16
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)
GPIO.setup(pin, GPIO.OUT)
GPIO.output(pin, GPIO.HIGH)

def unlock_door():
  GPIO.output(pin, GPIO.LOW)
  sleep(60)
  GPIO.output(pin, GPIO.HIGH)

def exit_if_no_teams_are_active():
  for league in leagues.values():
    league['active'] = False
  
  for score in scores.values():
    if not score['final']:
      leagues[score['league']]['active'] = True

  if all(not league['active'] for league in leagues.values()):
    GPIO.cleanup()
    print('No teams are playing. Exiting...')
    exit(0)

while True:
  sleep(15)

  events = {}
  try:
    for league, details in leagues.items():
      if details['active']:
        response = requests.get(details['url'])
        response.raise_for_status()
        events[league] = response.json()['events']
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
  for league_events in events.values():
    for event in league_events:
      for competitor in event['competitions'][0]['competitors']:
        team = competitor['team']['name']
        score = int(competitor['score'])
        final = event['status']['type']['completed']
        league = get_league(team)

        new_scores[team] = {'value': score, 'final': final, 'league': league}

  for team, old_score in scores.items():
    if old_score['final']:
      continue

    if team in new_scores:
      new_score = new_scores[team]
      if old_score['value'] is not None and new_score['value'] > old_score['value']:
        points_scored = new_score['value'] - old_score['value']
        if (new_score['league'] == 'nfl' and points_scored >= 2) or (new_score['league'] != 'nfl' and points_scored >= 1):
          if first_score:
            sleep(spoiler_timeout)
            first_score = False
          print(f'{team} scored! ({old_score["value"]} -> {new_score["value"]})')
          unlock_door()

      scores[team] = new_score
      if scores[team]['final']:
        print(f'{team} game has ended')
        exit_if_no_teams_are_active()
    else:
      scores[team]['final'] = True
      print(f"{team} don't play today")
      exit_if_no_teams_are_active()
