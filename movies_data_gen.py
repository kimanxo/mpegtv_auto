import json
from utils import fetch_all_remote_vod, scan_mkv_files


# def gen_movies(root_dir):
#     with open("movies.json", "w", encoding="utf-8") as f:
#         f.write("[\n")
#         first = True
#         for movie in scan_mkv_files(root_dir):
#             if not first:
#                 f.write(",\n")
#             json.dump(movie, f, ensure_ascii=False)
#             first = False
#         f.write("\n]\n")


import os
import json
import subprocess


def gen_movies(BASE_DIR):
    movies_dir = os.path.join(BASE_DIR, "movies")
    tree_txt = "movies_tree.txt"
    movies_json = "movies.json"

    # Run the tree command and save to tree.txt
    try:
        subprocess.run(
            ["tree", "-if", "--noreport", movies_dir],
            check=True,
            stdout=open(tree_txt, "w", encoding="utf-8"),
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as e:
        print("Error running tree command:", e.stderr.decode())
        return

    # Parse tree.txt and yield movies info
    def parse_tree_txt(tree_file):
        with open(tree_file, "r", encoding="utf-8") as f:
            for line in f:
                path = line.strip()
                if path.endswith(".mkv"):
                    dir_name = os.path.basename(os.path.dirname(path))
                    yield {"name": dir_name, "path": os.path.abspath(path)}

    # Write movies.json
    with open(movies_json, "w", encoding="utf-8") as f:
        f.write("[\n")
        first = True
        for movie in parse_tree_txt(tree_txt):
            if not first:
                f.write(",\n")
            json.dump(movie, f, ensure_ascii=False, indent=4)
            first = False
        f.write("\n]\n")

    print(f"Generated {movies_json} with movies info from {movies_dir}")


# Example usage:
# gen_movies_from_base_dir("/data/media")


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
