import os
import json
import time
import requests
from datetime import datetime

# =========================
# PATH SETUP
# =========================
ROOT = os.path.dirname(os.path.dirname(__file__))

DATA_PATH = os.path.join(ROOT, "data", "appid_metadata.json")
ZIP_DIR = os.path.join(ROOT, "zips")
STATE_PATH = os.path.join(ROOT, "state", "cursor.json")
CONFIG_PATH = os.path.join(ROOT, "config", "api_list.json")

os.makedirs(ZIP_DIR, exist_ok=True)

# =========================
# CONFIG
# =========================
BATCH_SIZE = 100                  # test lokal (production: 100)
REQUEST_DELAY = 3.0             # jeda antar API fallback
APPID_DELAY = 8              # ⬅️ JEDA ANTAR APPID (INI KUNCI)
REQUEST_TIMEOUT = 30


# =========================
# LOAD CONFIG
# =========================
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

HEADERS = {
    "User-Agent": config["default_user_agent"]
}

api_list = [api for api in config["api_list"] if api["enabled"]]

# =========================
# LOAD STATE
# =========================
with open(STATE_PATH, "r", encoding="utf-8") as f:
    state = json.load(f)

cursor_index = state.get("index", 0)

# =========================
# LOAD APPID SOURCE (READ ONLY)
# =========================
print("[INFO] Loading AppID metadata...")
with open(DATA_PATH, "r", encoding="utf-8") as f:
    appid_data = json.load(f)

appid_list = list(appid_data.keys())
total_appids = len(appid_list)

print(f"[INFO] Total AppIDs available: {total_appids}")
print(f"[INFO] Cursor index: {cursor_index}")

# =========================
# BATCH SLICE
# =========================
start = cursor_index
end = min(cursor_index + BATCH_SIZE, total_appids)
batch_appids = appid_list[start:end]

print(f"[INFO] Processing AppID index {start} → {end - 1}")

downloaded = 0
processed = 0

# =========================
# FETCH LOOP
# =========================
for i, appid in enumerate(batch_appids):
    processed += 1
    zip_path = os.path.join(ZIP_DIR, f"{appid}.zip")

    found = False

    if os.path.exists(zip_path):
        print(f"[SKIP] {appid}.zip already exists")
    else:
        for api in api_list:
            url = api["url"].replace("<appid>", appid)

            try:
                resp = requests.get(
                    url,
                    headers=HEADERS,
                    timeout=REQUEST_TIMEOUT,
                    allow_redirects=True,
                )

                if resp.status_code == api["success_code"]:
                    content = resp.content

                    if not content.startswith(b"PK"):
                        print(f"[INVALID] {appid} from {api['name']} (not ZIP)")
                    else:
                        with open(zip_path, "wb") as f:
                            f.write(content)

                        print(f"[OK] {appid}.zip from {api['name']}")
                        downloaded += 1
                        found = True
                        break

                elif resp.status_code == api["unavailable_code"]:
                    print(f"[MISS] {appid} not in {api['name']}")

                else:
                    print(f"[WARN] {appid} {api['name']} returned {resp.status_code}")

            except requests.RequestException as e:
                print(f"[ERROR] {appid} {api['name']} → {e}")

            # Use API-specific delay if defined, otherwise fallback to global
            delay = api.get("custom_delay", REQUEST_DELAY)
            time.sleep(delay)

        if not found:
            print(f"[FAIL] {appid} not found in any API")

    # =========================
    # GLOBAL APPID THROTTLE
    # =========================
    if i < len(batch_appids) - 1:
        print(f"[WAIT] Sleeping {APPID_DELAY} seconds before next AppID")
        time.sleep(APPID_DELAY)

# =========================
# UPDATE STATE
# =========================
state["index"] = end
state["total_processed"] += processed
state["total_downloaded"] += downloaded
state["last_run"] = datetime.utcnow().isoformat() + "Z"

with open(STATE_PATH, "w", encoding="utf-8") as f:
    json.dump(state, f, indent=2)

print("====================================")
print(f"[DONE] Batch finished")
print(f"[INFO] Processed: {processed}")
print(f"[INFO] Downloaded: {downloaded}")
print(f"[INFO] Next cursor index: {state['index']}")
