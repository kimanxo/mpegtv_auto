import json
import requests

from settings import BASE_URL
from utils import login

# Path to your JSON file
movies_json_file = "movies_diff_result.json"
episodes_json_file = "episodes_diff_result.json"
series_json_file = "series_diff_result.json"


# Main logic
session = login(BASE_URL)
# Load JSON

def delete_vod(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Loop over items in "to_delete" and send POST request
    to_delete_list = data.get("to_delete", [])

    if not to_delete_list:
        print("ℹ️ No movies / episodes to delete.")
    else:
        for item in to_delete_list:
            item_id = item.get("id")
            item_name = item.get("name")

            if item_id:
                print(f"Deleting {item_name}: {item_id}")
                try:
                    response = session.get(
                        f"{BASE_URL}/vod_json?id={item_id}&action=delete",
                        data={"action": "delete", "id": item_id},
                    )
                    response.raise_for_status()
                    print(f"✅ Deleted {item_name}: {item_id}")
                except requests.RequestException as e:
                    print(f"❌ Failed to delete ID {item_id}: {e}")


def delete_series():
    with open(series_json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Loop over items in "to_delete" and send POST request
    to_delete_list = data.get("to_delete", [])

    if not to_delete_list:
        print("ℹ️ No series to delete.")
    else:
        for item in to_delete_list:
            item_id = item.get("id")
            item_name = item.get("name")
            if item_id:
                print(f"Deleting {item_name}: {item_id}")
                try:
                    response = session.get(
                        f"{BASE_URL}/serie_json?nolist=1&id={item_id}&action=delete",
                        data={"action": "delete", "id": item_id, "nolist": 1},
                    )
                    response.raise_for_status()
                    print(f"✅ Deleted {item_name}: {item_id}")
                except requests.RequestException as e:
                    print(f"❌ Failed to delete ID {item_id}: {e}")


delete_vod(movies_json_file)
delete_vod(episodes_json_file)
delete_series()
