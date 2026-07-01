import os

import pandas as pd
import requests
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


OVERPASS_URL = "https://overpass-api.de/api/interpreter"


HTTP_200_OK = 200

headers = {
    "User-Agent": "RoadAssetRecovery/1.0 (mailto:luisodsilva@gmail.com)"
}


def get_route_coordinates(start_lat, start_lon, end_lat, end_lon):
    osrm_url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}"
    params = {"overview": "full", "geometries": "geojson"}

    response = requests.get(osrm_url, params=params)
    response.raise_for_status()
    data = response.json()

    return data["routes"][0]["geometry"]["coordinates"]


def get_assets_along_route(route_coords, headers=headers, search_radius=20):
    overpass_coords = ", ".join([f"{lat},{lon}" for lon, lat in route_coords])

    query = f"""
    [out:json][timeout:320];
    (
      node["traffic_sign"~"^BR:"](
        around:{search_radius}, {overpass_coords}
      );
      node["highway"="speed_camera"](
        around:{search_radius}, {overpass_coords}
      );
    );
    out body;
    """

    overpass_url = "http://overpass-api.de/api/interpreter"
    response = requests.post(
        overpass_url, data={"data": query}, headers=headers, timeout=340
    )
    response.raise_for_status()

    return response.json()


def classify_sign(osm_code):
    if osm_code.get("highway") == "speed_camera":
        return "speed-camera", "radar"

    sign_code = osm_code.get("traffic_sign")
    if sign_code:
        code = sign_code.replace("BR:", "").upper()
        if code.startswith("A-"):
            return "warning-sign", sign_code
        if code.startswith("R-"):
            return "regulatory-sign", sign_code
        if code.startswith(("I-", "S-", "T-")):
            return "guide-sign", sign_code
        if code.startswith("ED-"):
            return "educational-sign", sign_code

    return "other-roadside-element", "unknown"


@app.post("/search_assets")
def search_assets(
    start_lat: float, start_lon: float, end_lat: float, end_lon: float
):
    try:
        route_coords = get_route_coordinates(
            start_lat, start_lon, end_lat, end_lon
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"OSRM API connection error: {str(e)}",
        )
    except (IndexError, KeyError):
        raise HTTPException(
            status_code=404,
            detail="Could not find valid route for the provided coordinates.",
        )

    try:
        response = get_assets_along_route(route_coords)
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else 502
        raise HTTPException(
            status_code=status,
            detail=f"Overpass API returned an error: {e}",
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Overpass API connection error: {str(e)}",
        )
    except ValueError:
        raise HTTPException(
            status_code=502,
            detail="Received invalid data from Overpass API.",
        )

    if not response or "elements" not in response:
        raise HTTPException(
            status_code=502,
            detail="Failed to retrieve assets from Overpass API",
        )

    elements = response.get("elements", [])

    parsed_signs: list[dict] = []
    for el in elements:
        tags = el.get("tags", {})
        sign_type, sign_code = classify_sign(tags)
        parsed_signs.append(
            {
                "id": el.get("id"),
                "latitude": el.get("lat"),
                "longitude": el.get("lon"),
                "sign_code": sign_code,
                "sign_type": sign_type,
            }
        )

    os.makedirs("data", exist_ok=True)

    df = pd.DataFrame(parsed_signs)
    df.to_csv("data/brazil_traffic_signs.csv", index=False)

    return {
        "count": len(parsed_signs),
        "signs": parsed_signs,
        "csv_path": "data/brazil_traffic_signs.csv",
    }


@app.get("/download_csv")
def download_csv():
    """Download the CSV file containing traffic signs."""
    return FileResponse(
        "data/brazil_traffic_signs.csv", filename="brazil_traffic_signs.csv"
    )


app.mount("/", StaticFiles(directory="static_dir", html=True), name="static")


def local_search_assets(start_lat, start_lon, end_lat, end_lon):
    print("Fetching data from Overpass API... This may take a moment.")
    route_coords = get_route_coordinates(
        start_lat, start_lon, end_lat, end_lon
    )

    response = get_assets_along_route(route_coords)

    data = response
    elements = data.get("elements", [])

    parsed_signs = []
    for el in elements:
        tags = el.get("tags", {})
        sign_type, sign_code = classify_sign(tags)

        parsed_signs.append(
            {
                "id": el.get("id"),
                "latitude": el.get("lat"),
                "longitude": el.get("lon"),
                "sign_code": sign_code,
                "sign_type": sign_type,
            }
        )

    df = pd.DataFrame(parsed_signs)

    print(f"Successfully retrieved {len(df)} traffic signs!")
    print(df.head())
    df.to_csv("data/brazil_traffic_signs.csv", index=False)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
