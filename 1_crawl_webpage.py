import json
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from pathlib import Path

DATA_PATH = Path('data')
DATA_PATH.mkdir(exist_ok=True)

def scrape_cim_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        data = {}

        # 1. Extract "Fitxa tècnica" data
        # We look for the header 'Fitxa tècnica' and get its parent container
        fitxa_header = soup.find('h4', string=lambda t: t and 'Fitxa tècnica' in t)
        if fitxa_header:
            container = fitxa_header.find_parent('div')
            # The data is in pairs of col-6 divs
            items = container.find_all('div', class_='col-6')

            for i in range(0, len(items), 2):
                if i + 1 < len(items):
                    label = items[i].get_text(strip=True).replace(':', '')
                    value = items[i+1].get_text(strip=True)
                    data[label] = value

        # 2. Check for "Cim essencial" flag
        # It's inside a div with "cim essencial" text
        essencial_flag = soup.find('strong', string=lambda t: t and 'Cim essencial' in t)
        data['es_cim_essencial'] = essencial_flag is not None

        # 3. Bonus: Get the Peak Name (h1)
        peak_name = soup.find('h1')
        if peak_name:
            data['nom_cim'] = peak_name.get_text(strip=True)

        return data

    except Exception as e:
        return {"error": str(e)}



def main():

    raw_data = json.load(open('data.json'))
    cims = pd.DataFrame(raw_data['data'])

    url_pattern = re.compile(r'href="(.*?)"')
    cims['url'] = cims['html'].apply(lambda x: url_pattern.search(x).group(1) if url_pattern.search(x) else None)

    for _, c in tqdm(cims.iterrows(), total=cims.shape[0]):

        cim_data = scrape_cim_data(c['url'])
        cim_data_dict = dict(
            **c.to_dict(),
            **cim_data
        )

        to_save_data = {
            "assencions": cim_data_dict["Assencions"],
            "url" : cim_data_dict["url"],
            "comarca": cim_data_dict["Comarca"],
            "altitud": int(re.sub(r'\D', '', cim_data_dict['Altitud'])),
            "latitud": float(cim_data_dict['Latitud'][:-1]),
            "longitud": float(cim_data_dict['Longitud'][:-1]),
            "utm_31t_x": cim_data_dict["UTM 31T X"],
            "utm_31t_y" : cim_data_dict["UTM 31T Y"],
            "essencial": cim_data_dict["es_cim_essencial"],
            "nom": cim_data_dict["nom_cim"],
        }

        file_name = to_save_data['nom'].replace(' ', '_')
        file_path = DATA_PATH / f'{file_name}.json'

        with open(file_path, 'w') as f:
            json.dump(c.to_dict(), f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()
