import json
from utils import fetch_all_remote_series, fetch_all_remote_vod, scan_series_episodes, scan_series_folders


def gen_series(ROOT_DIR):

    series = list(scan_series_folders(ROOT_DIR))

    with open("series.json", "w", encoding="utf-8") as f:
        json.dump(series, f, indent=4, ensure_ascii=False)

def generate_episodes(ROOT_DIR):
    episodes = list(scan_series_episodes(ROOT_DIR))
    with open("episodes.json", "w", encoding="utf-8") as f:
        json.dump(episodes, f, indent=4, ensure_ascii=False)


def diff_series(
    session, BASE_URL, local_json_path, output_json_path="series_diff_result.json"
):

    try:
        with open(local_json_path, "r", encoding="utf-8") as f:
            local_series = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load local JSON: {e}")
        return [], []

    remote_series = fetch_all_remote_series(session,BASE_URL)

    # Build name sets
    local_name_set = {s["name"].strip() for s in local_series if s.get("name")}
    remote_name_set = {s.get("nm", "").strip() for s in remote_series if s.get("nm")}

    # to_add: names in local but not in remote (include path from local)
    to_add = [
        {"name": s["name"], "path": s["path"]}
        for s in local_series
        if s["name"].strip() not in remote_name_set
    ]

    # to_delete: names in remote but not in local (no path available)
    to_delete = [
        {"id": s.get("id"), "name": s.get("nm", ""), "path": s.get("path", "").strip()}
        for s in remote_series
        if s.get("nm", "").strip() not in local_name_set
    ]

    # Save and display results
    output = {
        "to_add": to_add,
        "to_delete": to_delete,
    }

    try:
        with open(output_json_path, "w", encoding="utf-8") as out_file:
            json.dump(output, out_file, indent=4, ensure_ascii=False)
            print("\n🎬 Series to ADD:")
            for s in to_add:
                print(f"➕ {s['name']}, path: {s['path']}")

            print("\n🗑️ Series to DELETE:")
            for s in to_delete:
                print(f"➖ {s['name']}")

        print(f"✅ Results saved to {output_json_path}")
    except Exception as e:
        print(f"❌ Failed to save output JSON: {e}")

    return to_add, to_delete


def diff_episodes(
    session, BASE_URL, local_json_path, output_json_path="episodes_diff_result.json"
):
    try:
        with open(local_json_path, "r", encoding="utf-8") as f:
            local_episodes = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load local JSON: {e}")
        return [], []

    remote_episodes = fetch_all_remote_vod(session, BASE_URL, "series")

    # Create sets of paths with names for lookup
    local_paths = {m["path"].strip(): m["name"] for m in local_episodes}
    remote_paths = {m.get("path", "").strip(): m.get("nm", "") for m in remote_episodes}

    # episodes to ADD (in local, not in remote)
    to_add = [
        {"name": name, "path": path}
        for path, name in local_paths.items()
        if path and path not in remote_paths
    ]

    # episodes to DELETE (in remote, not in local)
    to_delete = [
        {"id": m.get("id"), "name": m.get("nm", ""), "path": path}
        for path, name in remote_paths.items()
        if path and path not in local_paths
        for m in remote_episodes
        if m.get("path", "").strip() == path
    ]

    # Save results to JSON
    output = {
        "to_add": to_add,
        "to_delete": to_delete,
    }

    try:
        with open(output_json_path, "w", encoding="utf-8") as out_file:
            json.dump(output, out_file, indent=4, ensure_ascii=False)

        print(f"✅ Results saved to {output_json_path}")
    except Exception as e:
        print(f"❌ Failed to save output JSON: {e}")

    return to_add, to_delete
