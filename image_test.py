import os
import requests

from config import COORDS_FILE, get_access_token, merge_coordinates

ACCESS_TOKEN = get_access_token()

# Add one known image_id per new capture session/sequence here
KNOWN_IMAGE_IDS = [
    "1072386045550484",
    "2168595857019988",
    "1400303565542189"

]

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "images")


def get_sequence_id(image_id):
    resp = requests.get(
        f"https://graph.mapillary.com/{image_id}",
        params={"access_token": ACCESS_TOKEN, "fields": "id,sequence"}
    )
    resp.raise_for_status()
    return resp.json().get("sequence")


def get_image_ids_in_sequence(sequence_id):
    resp = requests.get(
        "https://graph.mapillary.com/image_ids",
        params={"access_token": ACCESS_TOKEN, "sequence_id": sequence_id}
    )
    resp.raise_for_status()
    return [obj["id"] for obj in resp.json().get("data", [])]


def get_image_details(image_id):
    resp = requests.get(
        f"https://graph.mapillary.com/{image_id}",
        params={
            "access_token": ACCESS_TOKEN,
            "fields": "id,geometry,computed_geometry,captured_at,compass_angle,thumb_2048_url"
        }
    )
    resp.raise_for_status()
    return resp.json()


def download_image(image_id, thumb_url, dest_dir):
    filepath = os.path.join(dest_dir, f"{image_id}.jpg")
    if os.path.exists(filepath):
        return filepath
    resp = requests.get(thumb_url, stream=True)
    resp.raise_for_status()
    with open(filepath, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return filepath


def main():
    os.makedirs(IMAGES_DIR, exist_ok=True)

    all_image_ids = set()
    for known_id in KNOWN_IMAGE_IDS:
        seq_id = get_sequence_id(known_id)
        if seq_id:
            ids = get_image_ids_in_sequence(seq_id)
            print(f"Sequence {seq_id}: {len(ids)} images")
            all_image_ids.update(ids)

    print(f"\nTotal unique images to fetch: {len(all_image_ids)}\n")

    rows = []
    for i, image_id in enumerate(sorted(all_image_ids), 1):
        img = get_image_details(image_id)
        lon, lat = img["geometry"]["coordinates"]
        comp = img.get("computed_geometry", {}).get("coordinates", [None, None])
        comp_lon, comp_lat = comp if len(comp) == 2 else (None, None)

        filename = f"{image_id}.jpg"
        thumb_url = img.get("thumb_2048_url")
        if thumb_url:
            print(f"[{i}/{len(all_image_ids)}] Downloading {filename}")
            download_image(image_id, thumb_url, IMAGES_DIR)

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

    print(f"\nDone. Images: {IMAGES_DIR}\nCSV: {COORDS_FILE}")


if __name__ == "__main__":
    main()