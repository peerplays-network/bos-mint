import json
import requests

files = [
    "test-data/2018-03-10t000000z-basketball-nba-regular-season-detroit-pistons-chicago-bulls-create-20172018.json",
    "test-data/2018-03-10t000000z-basketball-nba-regular-season-detroit-pistons-chicago-bulls-in_progress-2018-03-10t00112083z.json",
    "test-data/2018-03-10t000000z-basketball-nba-regular-season-detroit-pistons-chicago-bulls-finish-2018-03-10t021409751z.json",
    "test-data/2018-03-10t000000z-basketball-nba-regular-season-detroit-pistons-chicago-bulls-result-99-83.json",
    "test-data/2018-03-10t000000z-basketball-nba-regular-season-detroit-pistons-chicago-bulls-settle.json",
]

with open(files[0]) as fid:
    data = json.load(fid)

data.update(dict(approver="init1"))
x = requests.post(
    # "http://94.130.229.63:8011/trigger",
    "http://localhost:8010/trigger",
    json=data,
    headers={'Content-Type': 'application/json'}
)


print(x.text)
