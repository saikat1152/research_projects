import os
import requests

from config import COORDS_FILE, get_access_token, merge_coordinates

ACCESS_TOKEN = get_access_token()
USERNAME = "saikat25"

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "images")


def get_my_images(username):
    """Retrieve all images uploaded by the given username with coordinates."""
    url = "https://graph.mapillary.com/images"
    params = {
        "access_token": ACCESS_TOKEN,
        "creator_username": username,
        "fields": "id,geometry,computed_geometry,captured_at,compass_angle,thumb_2048_url",
        "limit": 2000,
    }
    all_images = []

    while url:
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        all_images.extend(data.get("data", []))

        # Follow pagination cursor if present
        url = data.get("paging", {}).get("next")
        params = None  # next URL already contains all params

    return all_images


def download_image(image_id, thumb_url, dest_dir):
    """Download a single image and save it as <image_id>.jpg."""
    filepath = os.path.join(dest_dir, f"{image_id}.jpg")
    if os.path.exists(filepath):
        print(f"  [SKIP] {image_id}.jpg already exists")
        return filepath

    resp = requests.get(thumb_url, stream=True)
    resp.raise_for_status()
    with open(filepath, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return filepath


def main():
    # Fetch image metadata from Mapillary API
    images = get_my_images(USERNAME)
    print(f"\nTotal images uploaded by {USERNAME}: {len(images)}\n")

    if not images:
        print("No images found.")
        return

    # Create images directory
    os.makedirs(IMAGES_DIR, exist_ok=True)

    # Download images and collect coordinate rows
    rows = []
    for i, img in enumerate(images, 1):
        image_id = img["id"]
        lon, lat = img["geometry"]["coordinates"]  # GeoJSON: [lon, lat]
        comp = img.get("computed_geometry", {}).get("coordinates", [None, None])
        comp_lon, comp_lat = comp if len(comp) == 2 else (None, None)
        thumb_url = img.get("thumb_2048_url")

        filename = f"{image_id}.jpg"
        if thumb_url:
            print(f"[{i}/{len(images)}] Downloading {filename} ...")
            download_image(image_id, thumb_url, IMAGES_DIR)
        else:
            print(f"[{i}/{len(images)}] No thumbnail for {image_id}, skipping download")

        rows.append({
            "image_id": image_id, "filename": filename,
            "latitude": lat, "longitude": lon,
            "computed_latitude": comp_lat, "computed_longitude": comp_lon,
            "compass_angle": img.get("compass_angle"),
            "captured_at": img.get("captured_at"),
        })

    # Merge into coordinates.csv (dedupe by image_id) instead of overwriting
    before, after = merge_coordinates(rows)
    print(f"coordinates.csv: {before} -> {after} rows")

    print(f"\n--- Done ---")
    print(f"Images saved to:      {os.path.abspath(IMAGES_DIR)}")
    print(f"Coordinates saved to: {os.path.abspath(COORDS_FILE)}")


if __name__ == "__main__":
    main()

