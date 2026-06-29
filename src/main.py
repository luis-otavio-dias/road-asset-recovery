import pandas as pd
import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

query = """
[out:json][timeout:300];
area["ISO3166-1"="BR"]->.searchArea;

node["traffic_sign"~"^BR:"](area.searchArea);
out body;
"""

HTTP_200_OK = 200

headers = {
    "User-Agent": "RoadAssetRecovery/1.0 (mailto:luisodsilva@gmail.com)"
}

print("Fetching data from Overpass API... This may take a moment.")
response = requests.post(
    url=OVERPASS_URL,
    data={"data": query},
    headers=headers,
    timeout=320,
)

if response.status_code == HTTP_200_OK:
    data = response.json()
    elements = data.get("elements", [])

    parsed_signs = []
    for el in elements:
        tags = el.get("tags", {})
        parsed_signs.append(
            {
                "id": el.get("id"),
                "latitude": el.get("lat"),
                "longitude": el.get("lon"),
                "sign_code": tags.get("traffic_sign"),
                "direction": tags.get("direction"),
            }
        )

    df = pd.DataFrame(parsed_signs)

    print(f"Successfully retrieved {len(df)} traffic signs!")
    print(df.head())
    df.to_csv("brazil_traffic_signs.csv", index=False)

else:
    print(f"Error fetching data. Status code: {response.status_code}")
