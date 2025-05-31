
# How to Run mpegtv\_auto Script

## 1. Prerequisites

Before running the script, make sure you have the following installed on your system:

* **Python 3** (preferably Python 3.6+)
* **tree** command-line utility

You can install them on Debian/Ubuntu-based systems via:

```bash
sudo apt update
sudo apt install python3 python3-pip tree
```

---

## 2. Script Directory Structure

Your project directory (`mpegtv_auto`) should look like this:

```
mpegtv_auto/
├── delete.py
├── delete.sh         # Script to delete files as per diff JSONs
├── __init__.py
├── main.py           # Main script to run the workflow
├── movies_data_gen.py
├── movies_data_push.py
├── series_data_gen.py
├── series_data_push.py
├── settings.py       # User-configurable settings (must be edited before run)
├── utils.py
```

---

## 3. Configuring Settings

Open `settings.py` and adjust the following variables according to your environment:

```python
BASE_URL = "http://89.58.50.9:8080"   # Your server URL
SERVER_ID = 3                         # Your server ID
BASE_DIR = "/data/media"              # Base directory where media files are stored
USERNAME = "your_username"            # Username for authentication (if needed)
PASSWORD = "your_password"            # Password for authentication (if needed)
```

Make sure these are correct before proceeding.

---

## 4. Running the Script

To run the entire process, execute the following command in the terminal **from inside the `mpegtv_auto` directory**:

```bash
python3 main.py > /your/fav/path/log.txt
```

* Replace `/your/fav/path/log.txt` with the full path and filename where you want the log output saved.
* The script output, including success messages, errors, and info, will be saved into this log file for your review.

---

## 5. Understanding Generated Files

The script execution will generate the following JSON and text files **in the current working directory** (or the directory where you run the script):

* `movies_diff_result.json`
* `series_diff_result.json`
* `episodes_diff_result.json`

These files contain properties `to_add` and `to_delete` listing the media items to add or delete.

* **Important:** Always review the `to_delete` sections inside these JSON files **before running the deletion step** to confirm that what will be deleted is correct and valid.

---

## 6. Deleting Media Files

To delete media files based on the differences, run the deletion script:

```bash
./delete.sh
```

* This script reads the `.to_delete` entries from the diff JSON files.
* It deletes only what is specified there.
* You should **only run this after verifying the deletion lists** inside the JSON files.
* The `delete.sh` file is user-executable and should **not be modified**.

---

## 7. Notes and Restrictions

* **Do NOT modify any files other than `settings.py` and `delete.sh`.** All other Python scripts and utilities must remain unchanged.
* The script requires network access to the server specified in `BASE_URL`.
* The session used by the script is kept open until all steps finish, so do not terminate the script prematurely.
* Logs will help diagnose any errors or issues; check your specified log file after execution.

