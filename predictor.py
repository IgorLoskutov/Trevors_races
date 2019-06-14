import asyncio
import requests

from concurrent.futures import ThreadPoolExecutor

from user_agent import generate_user_agent

from bs4 import BeautifulSoup


from time import strftime, gmtime, time


import json


class Parser:
    """gets and store races params name, time, id"""

    def __init__(self, url_, headers):
        self.session = requests.Session()
        self.response = self.session.get(url=url_, headers=headers)
        self.soup = self._get_soup()
        self._get_races()

    def _get_soup(self):
        return BeautifulSoup(self.response.content, 'html.parser')   

    def _get_containers(self, tag: str, klass: str):
        containers = self.soup.find_all(tag, klass)
        return containers

    def _get_races(self):
        """makes a set of tuples with race params"""

        self.races = set()
        for _ in self._get_containers('a', "RC-meetingItem__link js-navigate-url"):
            link = _.get('href')
            race_id = link.split('/')[5]
            self.races.add(race_id)
        self.races = sorted(list(self.races))


class Predictor:
    """retrieve respond to ajax request and get predictions data"""

    def __init__(self, race, headers):
        self.ajax_url = 'https://www.racingpost.com/horses/predictor/proxy/{race}?time={time}'.format(
            race=race,
            time=time()
        )
        self.race_prediction = requests.get(self.ajax_url, headers=headers)
        self.horses_data = []
        if self.race_prediction.status_code == 200:
            self.horses_data = self._get_race_prediction()

    def _get_race_prediction(self):
        """gets data from ajax respond and parses horses data """

        race_data = json.loads(self.race_prediction.content.decode())
        horses_data = []
        horses = race_data['data']['runners']
        horses = enumerate(     # no position data can be get from the site
            sorted(             # position generated trough sorting by score descending
                horses.values(),
                key=lambda x: x['score'],
                reverse=True
            ),
            1   # generate position data starting from '1st place' at score=100
        )
        for position, horse in horses:
            horse_name = horse['name']
            horse_num = str(horse['saddle_cloth_number'])
            horse_score = str(horse['score'])
            horse_race = (
                race_data['data']['race']['diffusion_competition_name']
                .lower().capitalize()
            )
            horse_time = race_data['data']['race']['diffusion_event_name']
            horse_position = str(position)

            horse_data = ','.join(
                (horse_name,
                 horse_num,
                 horse_score,
                 horse_position,
                 horse_race,
                 horse_time,
                 )
            ) + ';'
            if horse_data:
                horses_data.append(horse_data)
        return horses_data


if __name__ == "__main__":

    url = 'https://www.racingpost.com/racecards/'
    headers = {
        'Host': 'www.racingpost.com',
        'User-Agent': generate_user_agent(device_type='desktop', os=('mac', 'linux')),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }

    parser = Parser(url, headers)

    def get_response():
        loop = asyncio.get_event_loop()
        future = asyncio.ensure_future(request_ajax())
        loop.run_until_complete(future)


    async def request_ajax():
        csv_string_ = ''
        with ThreadPoolExecutor(max_workers=25) as requester:
            loop = asyncio.get_event_loop()
            task = [
                loop.run_in_executor(requester, Predictor, race, headers)
                for race in parser.races
            ]
            for response in await asyncio.gather(*task):
                if response.horses_data:
                    csv_string_ += '\n'.join(response.horses_data) + '\n'
            with open(
                '_'.join(
                    (strftime('%y%m%d', gmtime()),
                     'predict.csv',)),
                    'w') as csv:
                csv.write(csv_string_)


    get_response()
