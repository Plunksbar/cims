import pandas as pd
import json
from tqdm import tqdm
import requests
from pathlib import Path
from time import sleep

DATA_PATH = Path('data')
DATA_PATH.mkdir(exist_ok=True)

from_location = (41.412814361296455, 2.190303226868076)  # Barcelona coordinates

api_endpoint_template = "http://router.project-osrm.org/route/v1/driving/{from_lon},{from_lat};{to_lon},{to_lat}?overview=full&geometries=polyline"


def get_route_from_clot(lat, lon, retries=3):
    url = api_endpoint_template.format(
        from_lon=from_location[1],
        from_lat=from_location[0],
        to_lon=lon,
        to_lat=lat
    )

    try:
        response = requests.get(url).json()
    except:
        if retries > 0:
            sleep(1)
            return get_route_from_clot(lat, lon, retries - 1)
        else:
            return None

    if response.get('code') == 'Ok':
        return response['routes']

    return None


"""
Example of data file:
{
    "assencions": "1504",
    "url": "https://www.feec.cat/activitats/100-cims/cim/balandrau/",
    "comarca": "Ripollès",
    "altitud": 2585,
    "latitud": 42.3701065555,
    "longitud": 2.21956587983,
    "utm_31t_x": "435742",
    "utm_31t_y": "4691165",
    "essencial": true,
    "nom": "Balandrau"
}
"""


def main():

    for cim in tqdm(DATA_PATH.glob('*.json')):

        data = json.load(cim.open())
        print(cim.stem)
        if "routes" in data:
            continue

        routes = get_route_from_clot(data['latitud'], data['longitud'])

        if not routes:
            print(f"Error getting route for {data['nom']}")
            continue

        data['routes'] = routes

        with open(cim, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        sleep(1)


if __name__ == "__main__":
    main()
