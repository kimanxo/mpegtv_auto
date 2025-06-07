import json
import requests
import urllib.parse
from collections import defaultdict
from settings import SERVER_ID
from utils import fetch_all_remote_series


def push_series(session, BASE_URL):
    upload_url = f"{BASE_URL}/serie_item"  # Replace with actual endpoint

    try:
        with open("series_diff_result.json", "r", encoding="utf-8") as f:
            diff_data = json.load(f)
            series = diff_data.get("to_add", [])
    except Exception as e:
        print(f"❌ Failed to load series_diff_result.json: {e}")
        return

    if not series:
        print("📭 No series to add. The to_add list is empty.")
        return

    for serie in series:
        name = serie.get("name")
        path = serie.get("path")

        if not name or not path:
            continue  # Skip invalid entries

        form_data = {
            "action": "add",
            "name": name,
        }

        try:
            res = session.post(upload_url, data=form_data, timeout=10)
            res.raise_for_status()
            
        except requests.RequestException as e:
            print(f"❌ Failed to send {name}: {e}")


def push_episodes(session, BASE_URL):
    try:
        # Step 1: Fetch all series from the server
        all_series = fetch_all_remote_series(session, BASE_URL)

        # Step 2: Build a name → id mapping
        series_names_ids = [{"id": s["id"], "name": s["nm"]} for s in all_series]
        name_to_id = {s["name"].strip().lower(): s["id"] for s in series_names_ids}

        # Step 3: Load episodes from JSON
        with open(
            "episodes_diff_result.json",
            "r",
            encoding="utf-8",
        ) as f:
            diff_data = json.load(f)
            episodes = diff_data.get("to_add", [])

        print("adding episodes...")
        for ep in episodes:
            episode_path = ep.get("path", "")
            episode_name = ep.get("name", "")
            

            # Extract series name before the year (first " (")
            split_index = episode_name.find(" -")
            if split_index == -1:
                continue  # Skip if format is unexpected

            raw_serie_name = episode_name[:split_index].strip().lower()
            serie_id = name_to_id.get(raw_serie_name)
            
            
            if serie_id:

                payload = {
                    "action": "insert",
                    "serie_id": serie_id,
                    "server_id": SERVER_ID,
                    "path": "/".join(episode_path.split("/")[:-1]),
                    "name": episode_name,
                }
                try:
                   
                    

                    res = session.post(
                        f"{BASE_URL}/serie_episodes", data=payload, timeout=15
                    )
                    res.raise_for_status()
                    
                except requests.RequestException as e:
                    print(f"❌ Failed to insert episode {payload.get('name')} : {e}")

        print("✅ All episodes processed successfully.")

    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def series_tmdb(session, BASE_URL):
    try:
        # Step 1: Load to_add series from series_diff_result.json
        with open("series_diff_result.json", "r", encoding="utf-8") as f:
            diff_data = json.load(f)
            to_add_series = diff_data.get("to_add", [])

        if not to_add_series:
            print("📭 No series to add. Skipping TMDB metadata.")
            return

        def normalize_name(name):
            return name.strip().lower()

        # Build a set of normalized names to match from local "to_add" list
        to_add_names = set(
            normalize_name(s["name"]) for s in to_add_series if "name" in s
        )

        # Step 2: Fetch all series from the server
        all_series = fetch_all_remote_series(session, BASE_URL)

        # Step 3: Filter server series whose normalized "nm" matches the normalized local names
        matched_series = [
            s for s in all_series if normalize_name(s.get("nm", "")) in to_add_names
        ]

        print(f"🔍 Matched {len(matched_series)} new series for TMDB enrichment.")

        # Step 4: Enrich each matched series
        for serie in matched_series:
            serie_id = serie.get("id")
            name = serie.get("nm", "").strip()

            if not serie_id or not name:
                continue

            # Step 5: Get detailed series info by ID
            detail_url = f"{BASE_URL}/serie_json?id={serie_id}"
            detail_response = session.get(detail_url)
            detail_response.raise_for_status()
            detail_data = detail_response.json()
            items = detail_data.get("items", [])
            if not items:
                continue
            item = items[0]

            # Step 6: Query TMDB for metadata
            query = urllib.parse.quote_plus(name)
            tmdb_url = f"{BASE_URL}/tmdb?action=getSerie&query={query}&lang=de"

            try:
                tmdb_response = session.get(tmdb_url)
                tmdb_response.raise_for_status()
                tmdb_data = tmdb_response.json()

                if tmdb_data:
                    sub_id = tmdb_data[0].get("id")
                    sub = f"{BASE_URL}/tmdb?action=setSerie&id={sub_id}&serieid={serie_id}&lang=de"
                    sub_response = session.get(sub)
                    sub_response.raise_for_status()
                    
                else:
                    print(f"❌ No TMDB result for: {name}")

            except requests.RequestException as e:
                print(f"❌ TMDB request failed for {name}: {e}")

    except Exception as e:
        print(f"❌ Failed TMDB process: {e}")


def create_and_categorize_series(session, SERVER_ID, BASE_URL):
    try:
        # Step 1: Fetch all remote series from the server
        remote_series = fetch_all_remote_series(session, BASE_URL)

        # Step 2: Load local series to_add from your series_diff_result.json
        try:
            with open("series_diff_result.json", "r", encoding="utf-8") as f:
                local_data = json.load(f)
                to_add = local_data.get("to_add", [])
        except Exception as e:
            print(f"❌ Failed to load local to_add series: {e}")
            return

        if not to_add:
            print("ℹ️ No series to add (to_add list is empty).")
            return

        # Step 3: Build sets/maps for efficient matching by name
        remote_names_map = {serie.get("nm"): serie for serie in remote_series}

        # Find matched series by name that are new to be categorized
        matched_series = []
        for local_serie in to_add:
            name = local_serie.get("name")
            if name and name in remote_names_map:
                matched_series.append(remote_names_map[name])

        if not matched_series:
            print("ℹ️ No matching remote series found for to_add names.")
            return

        print(f"Found {len(matched_series)} matched series to categorize.")

        # Step 4: Extract genres and years from matched series
        genres = set()
        years = set()
        for serie in matched_series:
            for genre in serie.get("genre", "").split(","):
                genre = genre.strip()
                if genre:
                    genres.add(genre)
            date = serie.get("date", "")
            if date:
                years.add(date.split("-")[0])

        # Step 5: Fetch all existing categories remotely
        cat_url = f"{BASE_URL}/category_json?nolist=1&max=0&type=65"
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
                "type": 65,
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

        # Step 8: Assign matched series to all relevant categories (existing + new)
        # Create a map: category_id -> list of serie IDs
        category_to_series = defaultdict(list)

        for serie in matched_series:
            serie_id = serie.get("id")
            if not serie_id:
                continue
            date = serie.get("date", "")
            genres_list = [
                g.strip() for g in serie.get("genre", "").split(",") if g.strip()
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
                category_to_series[cat_id].append(str(serie_id))
        
        # Step 9: Push category assignments to server (one request per category)
        for category_id, serie_ids in category_to_series.items():

            try:
                # Step A: Fetch existing movies already assigned to this category
                existing_series_url = (f"{BASE_URL}/category_json?id={category_id}")
                res = session.get(existing_series_url, timeout=10)
                res.raise_for_status()
                existing_series_data = res.json()
                existing_serie_ids = existing_series_data.get("items",[])
                existing_serie_ids = existing_serie_ids[0].get("list",[])
            except requests.RequestException as e:
                print(f"❌ Failed to fetch existing series for category ID {category_id}: {e}")
                existing_serie_ids = []

            # Step B: Combine existing and new serie IDs (deduplicated)
            combined_serie_ids = set(existing_serie_ids) | set(serie_ids)
            payload = {
                "action": "edit",
                "category_id": category_id,
                "list": ",".join(str(x) for x in combined_serie_ids) + ",",
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

