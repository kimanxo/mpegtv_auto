import json
import requests
import urllib.parse
from collections import defaultdict
import requests

from utils import fetch_all_remote_vod


def push_movies(session, SERVER_ID, BASE_URL):
    upload_url = f"{BASE_URL}/vod_item"  # Replace with actual endpoint

    try:
        with open("movies_diff_result.json", "r", encoding="utf-8") as f:
            diff_data = json.load(f)
            movies = diff_data.get("to_add", [])
    except Exception as e:
        print(f"❌ Failed to load movies_diff_result.json: {e}")
        return

    if not movies:
        print("📭 No movies to add. The to_add list is empty.")
        return

    for movie in movies:
        name = movie.get("name")
        path = movie.get("path")

        if not name or not path:
            continue  # Skip invalid entries

        form_data = {
            "action": "add",
            "name": name,
            "path": path,
            "server_id": SERVER_ID,
        }

        try:
            res = session.post(upload_url, data=form_data, timeout=10)
            res.raise_for_status()
            
        except requests.RequestException as e:
            print(f"❌ Failed to send {name}: {e}")


def movies_tmdb(session, SERVER_ID, BASE_URL):
    try:
        # Step 1: Load to_add movies from movies_diff_result.json
        with open("movies_diff_result.json", "r", encoding="utf-8") as f:
            diff_data = json.load(f)
            to_add_movies = diff_data.get("to_add", [])

        if not to_add_movies:
            print("📭 No movies to add. Skipping TMDB metadata.")
            return

        # Build set of paths to match
        to_add_paths = set(m["path"].strip() for m in to_add_movies if "path" in m)

        # Step 2: Fetch all movies from the panel
        all_panel_movies = fetch_all_remote_vod(session, BASE_URL, "movies")
        # Step 3: Filter panel movies that match to_add paths
        matched_movies = [
            m for m in all_panel_movies if m.get("path", "").strip() in to_add_paths
        ]

        print(f"🔍 Matched {len(matched_movies)} movie(s) for TMDB enrichment.")

        for movie in matched_movies:
            movie_id = movie.get("id")
            name = movie.get("nm")  # Example: "The Shawshank Redemption (1994)"

            if not movie_id or not name:
                continue

            # Step 4: Extract title and year
            if "(" in name and ")" in name:
                title = name.rsplit("(", 1)[0].strip()
                year = name.rsplit("(", 1)[1].replace(")", "").strip()
            else:
                print(f"⚠️ Skipping malformed title: {name}")
                continue

            # Step 5: Build and send TMDB query
            query = urllib.parse.quote_plus(title)
            tmdb_url = (
                f"{BASE_URL}/tmdb?action=getMovie&query={query}&lang=de&year={year}"
            )

            try:
                tmdb_response = session.get(tmdb_url)
                tmdb_response.raise_for_status()
                tmdb_data = tmdb_response.json()

                if tmdb_data:
                    sub_id = tmdb_data[0].get("id")
                    sub_url = f"{BASE_URL}/tmdb?action=setMovie&id={sub_id}&movieid={movie_id}&lang=de"
                    sub_response = session.get(sub_url)
                    sub_response.raise_for_status()
                    
                else:
                    print(f"❌ No TMDB result for: {title} ({year})")

            except requests.RequestException as e:
                print(f"❌ TMDB request failed for {title} ({year}): {e}")

    except Exception as e:
        print(f"❌ Failed TMDB process: {e}")


def create_and_categorize_movies(session, SERVER_ID, BASE_URL):
    try:
        # Step 1: Fetch all remote movies from the server
        remote_movies = fetch_all_remote_vod(session, BASE_URL, "movies")

        # Step 2: Load local movies to_add from your movies_diff_result.json
        try:
            with open("movies_diff_result.json", "r", encoding="utf-8") as f:
                local_data = json.load(f)
                to_add = local_data.get("to_add", [])
        except Exception as e:
            print(f"❌ Failed to load local to_add movies: {e}")
            return

        if not to_add:
            print("ℹ️ No movies to add (to_add list is empty).")
            return

        # Step 3: Build sets/maps for efficient matching by path
        remote_paths_map = {movie.get("path"): movie for movie in remote_movies}
        to_add_paths_set = {movie.get("path") for movie in to_add if movie.get("path")}

        # Find matched movies by path that are new to be categorized
        matched_movies = []
        for local_movie in to_add:
            path = local_movie.get("path")
            if path and path in remote_paths_map:
                matched_movies.append(remote_paths_map[path])

        if not matched_movies:
            print("ℹ️ No matching remote movies found for to_add paths.")
            return

        print(f"Found {len(matched_movies)} matched movies to categorize.")

        # Step 4: Extract genres and years from matched movies
        genres = set()
        years = set()
        for movie in matched_movies:
            for genre in movie.get("genre", "").split(","):
                genre = genre.strip()
                if genre:
                    genres.add(genre)
            date = movie.get("date", "")
            if date:
                years.add(date.split("-")[0])

        # Step 5: Fetch all existing categories remotely
        cat_url = f"{BASE_URL}/category_json?nolist=1&max=0&type=33"
        cat_response = session.get(cat_url)
        cat_response.raise_for_status()
        cat_data = cat_response.json()
        existing_categories = cat_data.get("items", [])

        # Build map of existing categories by name (nm)
        existing_cat_names = {
            cat.get("nm") for cat in existing_categories if cat.get("nm")
        }

        # Step 6: Prepare new categories to create (genres + years) that don't exist yet
        new_categories = set()
        for g in genres:
            if g not in existing_cat_names:
                new_categories.add(g)
        for y in years:
            if y not in existing_cat_names:
                new_categories.add(y)

        # Step 7: Create new categories on the server and build a full category map (name -> id)
        category_map = {
            cat.get("nm"): cat.get("id")
            for cat in existing_categories
            if cat.get("nm") and cat.get("id")
        }

        for cat_name in new_categories:
            form_data = {
                "action": "add",
                "name": cat_name,
                "title": cat_name,
                "type": 33,
                "flag_adult": "off",
                # Use genre_pattern if cat_name is genre else year_pattern if year (basic heuristic)
                "genre_pattern": cat_name if cat_name in genres else "",
                "year_pattern": cat_name if cat_name in years else "",
                "server_id": SERVER_ID,
            }
            try:
                res = session.post(
                    f"{BASE_URL}/category_item", data=form_data, timeout=10
                )
                res.raise_for_status()
                cat_id = res.json().get("id") or res.text
                category_map[cat_name] = cat_id
                
            except requests.RequestException as e:
                print(f"❌ Failed to create category '{cat_name}': {e}")

        # Step 8: Assign matched movies to all relevant categories (existing + new)
        # Create a map: category_id -> list of movie IDs
        category_to_movies = defaultdict(list)

        for movie in matched_movies:
            movie_id = movie.get("id")
            if not movie_id:
                continue
            date = movie.get("date", "")
            genres_list = [
                g.strip() for g in movie.get("genre", "").split(",") if g.strip()
            ]
            matched_categories = set()

            # Add genre categories if exist
            for genre in genres_list:
                cat_id = category_map.get(genre)
                if cat_id:
                    matched_categories.add(cat_id)

            # Add year category if exist
            if date:
                year = date.split("-")[0]
                cat_id = category_map.get(year)
                if cat_id:
                    matched_categories.add(cat_id)

            for cat_id in matched_categories:
                category_to_movies[cat_id].append(str(movie_id))

        # Step 9: Push category assignments to server (one request per category)
        for category_id, movie_ids in category_to_movies.items():

            try:
    # Step A: Fetch existing movies already assigned to this category
                existing_movies_url = f"{BASE_URL}/vod_json?type=movies&category={category_id}"
                res = session.get(existing_movies_url, timeout=10)
                res.raise_for_status()
                existing_movies_data = res.json()
                existing_movie_ids = [str(movie.get("id")) for movie in existing_movies_data.get("items", []) if movie.get("id")]
            except requests.RequestException as e:
                print(f"❌ Failed to fetch existing movies for category ID {category_id}: {e}")
                existing_movie_ids = []

            # Step B: Combine existing and new movie IDs (deduplicated)
            combined_movie_ids = set(existing_movie_ids) | set(movie_ids)
            payload = {
                "action": "edit",
                "category_id": category_id,
                "list": ",".join(combined_movie_ids) + ",",
            }
            try:
                res = session.post(
                    f"{BASE_URL}/category_item", data=payload, timeout=15
                )
                res.raise_for_status()
                cat_name = next(
                    (name for name, cid in category_map.items() if cid == category_id),
                    "unknown",
                )
                
            except requests.RequestException as e:
                print(f"❌ Failed to update category ID {category_id}: {e}")

    except requests.RequestException as e:
        print(f"❌ Failed during process: {e}")
