import os

import pandas as pd
import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from services.assets_identification import (
    classify_sign,
    get_assets_along_route,
    get_route_coordinates,
)
from services.image_integration import process_asset_image

router = APIRouter()


@router.post("/search_assets")
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
        elements = response.get("elements", [])
    except requests.exceptions.HTTPError as e:
        raise HTTPException(
            status_code=e.response.status_code if e.response else 502,
            detail=f"Overpass API error: {e}",
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Overpass API connection error: {e}",
        )
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=502,
            detail="Invalid or empty response from Overpass API",
        )

    parsed_signs: list[dict] = []
    for el in elements:
        tags = el.get("tags", {})
        sign_type, sign_code = classify_sign(tags)

        lat = el.get("lat")
        lon = el.get("lon")
        id_osm = el.get("id")

        # Integrate image capture logic
        image_path, image_url = process_asset_image(
            lat,
            lon,
            sign_type,
            id_osm,
        )

        parsed_signs.append(
            {
                "id_osm": id_osm,
                "latitude": lat,
                "longitude": lon,
                "sign_code": sign_code,
                "sign_type": sign_type,
                "image_url": image_url,
                "image_path": image_path,
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


@router.get("/download_csv")
def download_csv():
    """Download the CSV file containing traffic signs."""
    return FileResponse(
        "data/brazil_traffic_signs.csv", filename="brazil_traffic_signs.csv"
    )
