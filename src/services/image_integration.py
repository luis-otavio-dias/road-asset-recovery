import os

import requests
from dotenv import load_dotenv

IMAGES_DIR = "data/images/"

load_dotenv()

os.makedirs(IMAGES_DIR, exist_ok=True)

access_token = os.environ.get("MAPILLARY_ACCESS_TOKEN")


def save_image(sign_type, id_osm, url_api):
    filename = f"{sign_type}_{id_osm}.jpg"
    filepath = os.path.join(IMAGES_DIR, filename)

    try:
        resposta = requests.get(url_api, timeout=15)
        resposta.raise_for_status()

        # Escreve os bytes da imagem no disco
        with open(filepath, "wb") as arquivo:
            arquivo.write(resposta.content)

        return filepath

    except requests.exceptions.RequestException as e:
        print(f"Erro ao baixar imagem do ativo {id_osm}: {e}")
        return "Erro no Download"


def process_asset_image(lat, lon, sign_type, id_osm):
    url = "https://graph.mapillary.com/images"
    params = {
        "fields": "id,thumb_1024_url",
        "lat": lat,
        "lng": lon,
        "radius": 50,
        "access_token": access_token,
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("data"):
            best_image = data["data"][0]
            img_url = best_image["thumb_1024_url"]
            print(f"Image ID: {best_image['id']}")
            print(f"Image Thumbnail URL: {img_url}")
            filepath = save_image(sign_type, id_osm, img_url)
            return filepath, img_url
        else:
            print("No street-level images found within the specified radius.")
            return None, None
    except Exception as e:
        print(f"Error process_asset_image: {e}")
        return None, None
