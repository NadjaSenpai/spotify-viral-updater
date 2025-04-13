import csv
import os
from dotenv import load_dotenv
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.client import SpotifyException
from requests.exceptions import RequestException
import requests
from playwright.sync_api import sync_playwright

load_dotenv()
os.environ["SPOTIPY_DEBUG"] = "1"

def decode_state_json():
    encoded = os.getenv("STATE_JSON_B64")
    if not encoded:
        print("❌ STATE_JSON_B64 が定義されていません")
        return False
    decoded = base64.b64decode(encoded).decode("utf-8")
    with open("state.json", "w", encoding="utf-8") as f:
        f.write(decoded)
    print("✅ state.json を展開しました")
    return True

def try_download_with_browser(p, browser_type):
    print(f"🧪 Trying with: {browser_type.name}")
    browser = browser_type.launch(headless=True)
    context = browser.new_context(
        storage_state="state.json",
        accept_downloads=True,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        locale="ja-JP",
        timezone_id="Asia/Tokyo",
        geolocation={"longitude": 139.6917, "latitude": 35.6895},
        permissions=["geolocation"]
    )
    page = context.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    try:
        page.goto("https://charts.spotify.com/charts/view/viral-jp-daily/latest", timeout=30000)
        page.wait_for_load_state("domcontentloaded")
        page.evaluate("document.getElementById('onetrust-banner-sdk')?.remove()")

        page.locator('button[data-encore-id="buttonTertiary"]').first.wait_for(timeout=15000)
        with page.expect_download(timeout=15000) as download_info:
            page.locator('button[data-encore-id="buttonTertiary"]').first.click()

        download = download_info.value
        download.save_as("viral.csv")
        print("✅ CSVダウンロード完了: viral.csv")
        cat viral.csv
        return True

    except Exception as e:
        print(f"❌ {browser_type.name} failed:", e)
        try:
            page.screenshot(path=f"debug_{browser_type.name}.png", full_page=True)
        except:
            pass
        return False

    finally:
        browser.close()

def download_spotify_csv():
    with sync_playwright() as p:
        if not try_download_with_browser(p, p.chromium):
            print("❌ Chromiumで失敗したので終了します")

def update_playlist():
    print("🎯 環境変数チェック")
    print("CLIENT_ID:", os.getenv("SPOTIPY_CLIENT_ID"))
    print("PLAYLIST_ID:", os.getenv("SPOTIFY_PLAYLIST_ID"))

    if not os.path.exists("viral.csv"):
        print("❌ viral.csv が見つかりません。プレイリスト更新をスキップします。")
        return

    class TimeoutSession(requests.Session):
        def request(self, *args, **kwargs):
            kwargs.setdefault("timeout", 10)
            return super().request(*args, **kwargs)

    session = TimeoutSession()

    sp = Spotify(auth_manager=SpotifyOAuth(
        scope="playlist-modify-public playlist-modify-private",
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    ), requests_session=session)
    print("✅ Spotipy認証OK")

    playlist_id = os.getenv("SPOTIFY_PLAYLIST_ID")
    print("🎧 playlist_id:", playlist_id)

    try:
        print("🛰 プレイリスト情報取得中...")
        playlist_info = sp.playlist(playlist_id)
        print("📦 プレイリスト名:", playlist_info["name"])
    except SpotifyException as e:
        print("❌ Spotify API エラー:", e)
        return
    except RequestException as e:
        print("❌ リクエストタイムアウトや通信エラー:", e)
        return
    except Exception as e:
        print("❌ その他のエラー:", e)
        return

    results = sp.playlist_items(playlist_id)
    track_uris = [item["track"]["uri"] for item in results["items"]]
    if track_uris:
        sp.playlist_remove_all_occurrences_of_items(playlist_id, track_uris)
        print(f"🧹 {len(track_uris)} 件のトラックを削除しました")

    with open("viral.csv", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        uris = [row["uri"] for row in reader if row["uri"].startswith("spotify:track:")]
    if uris:
        sp.playlist_add_items(playlist_id, uris)
        print(f"🎵 {len(uris)} 件のトラックをプレイリストに追加しました")

if __name__ == "__main__":
    if decode_state_json():
        download_spotify_csv()
        update_playlist()