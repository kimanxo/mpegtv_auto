import json
from utils import fetch_all_remote_vod, scan_mkv_files


def gen_movies(root_dir):
    with open("movies.json", "w", encoding="utf-8") as f:
        f.write("[\n")
        first = True
        for movie in scan_mkv_files(root_dir):
            if not first:
                f.write(",\n")
            json.dump(movie, f, ensure_ascii=False)
            first = False
        f.write("\n]\n")


def diff_movies(
    session, BASE_URL, local_json_path, output_json_path="movies_diff_result.json"
):

    try:
        with open(local_json_path, "r", encoding="utf-8") as f:
            local_movies = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load local JSON: {e}")
        return [], []

    remote_movies = fetch_all_remote_vod(session,BASE_URL, "movies")

    # Create sets of paths with names for lookup
    local_paths = {m["path"].strip(): m["name"] for m in local_movies}
    remote_paths = {m.get("path", "").strip(): m.get("nm", "") for m in remote_movies}

    # Movies to ADD (in local, not in remote)
    to_add = [
        {"name": name, "path": path}
        for path, name in local_paths.items()
        if path and path not in remote_paths
    ]

    # Movies to DELETE (in remote, not in local)
    to_delete = [
    {"id": m.get("id"), "name": m.get("nm", ""), "path": path}
    for path, name in remote_paths.items()
    if path and path not in local_paths
    for m in remote_movies
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
