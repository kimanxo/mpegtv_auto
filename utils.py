import os
import re
import requests


def scan_mkv_files(root_dir):
    for dirpath, dirnames, filenames in os.walk(root_dir, followlinks=False):
        for filename in filenames:
            if filename.endswith(".mkv"):
                abs_path = os.path.abspath(os.path.join(dirpath, filename))
                dir_name = os.path.basename(os.path.dirname(abs_path))
                yield {"name": dir_name, "path": abs_path}


def scan_series_folders(root_dir):
    stack = [root_dir]
    seen = set()  # to avoid duplicates if any

    while stack:
        current_dir = stack.pop()
        try:
            with os.scandir(current_dir) as it:

                for entry in it:
                    if entry.is_dir(follow_symlinks=False):
                        # This time, yield this folder as a series folder (like Dark (2017))
                        abs_path = os.path.abspath(entry.path)
                        if abs_path not in seen:
                            seen.add(abs_path)
                            # Remove the year part from the folder name, e.g. "Dark (2017)" -> "Dark"
                            name = re.sub(r"\s*\(\d{4}\)", "", entry.name).strip()
                            yield {"name": name, "path": abs_path}
        except PermissionError:
            continue  # skip folders we can't access


def scan_series_episodes(root_dir):
    stack = [root_dir]
    while stack:
        current_dir = stack.pop()
        try:
            with os.scandir(current_dir) as it:
                for entry in it:
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(entry.path)
                    elif entry.is_file(follow_symlinks=False) and entry.name.endswith(
                        ".mkv"
                    ):
                        abs_path = os.path.abspath(entry.path)
                        # rel_path = os.path.relpath(
                        #     os.path.dirname(abs_path), start=root_dir
                        # )
                        yield {
                            "path": abs_path,
                            "name": entry.name,
                        }
        except PermissionError:
            continue  # Skip directories we can't access


def fetch_all_remote_vod(session, BASE_URL, type):
    all_episodes = []
    page = 0
    max_per_page = 100

    while True:
        url = f"{BASE_URL}/vod_json?max={max_per_page}&server_id=0&status=0&type={type}&category=0&page={page}"
        try:
            response = session.get(url)
            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])
            total = data.get("total", 0)

            all_episodes.extend(items)
            print(f"📦 Page {page} fetched: {len(items)} items.")

            # Break if we've fetched all items
            if len(all_episodes) >= total:
                break

            page += 1

        except Exception as e:
            print(f"❌ Failed to fetch page {page}: {e}")
            break

    print(f"✅ Total episodes fetched: {len(all_episodes)}")
    return all_episodes


def fetch_all_remote_series(session, BASE_URL):
    all_series = []
    page = 0
    max_per_page = 100

    while True:
        url = f"{BASE_URL}/serie_json?max={max_per_page}&page={page}"
        try:
            response = session.get(url)
            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])
            total = data.get("total", 0)

            all_series.extend(items)
            print(f"📦 Page {page} fetched: {len(items)} items.")

            # Break if we've fetched all items
            if len(all_series) >= total:
                break

            page += 1

        except Exception as e:
            print(f"❌ Failed to fetch page {page}: {e}")
            break

    print(f"✅ Total series fetched: {len(all_series)}")
    return all_series


def login(base_url, username="admin", password="admin"):
    session = requests.Session()
    login_url = f"{base_url}/login.php"
    login_payload = {"action": "login", "username": username, "password": password}
    try:
        login_response = session.post(login_url, json=login_payload, timeout=10)
        login_response.raise_for_status()
        print("✅ Logged in successfully")
        return session
    except requests.RequestException as e:
        print(f"❌ Login failed: {e}")
        return None
