import threading
import time
import warnings
from typing import Optional, Tuple

import cloudscraper
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pokestarfan_dataclasses.mangadex import MangadexManga, MangadexMangaList, Status
from pokestarfan_dataclasses.mangadex.enum import Following

warnings.filterwarnings("ignore", category=UserWarning)

retry_strategy = Retry(
    total=3,
    status_forcelist=[429, 500, 502, 503, 504],
    backoff_factor=1
)
adapter = HTTPAdapter(max_retries=retry_strategy)


class CustomCloudScraper(cloudscraper.CloudScraper):

    def __init__(self, *args, sleep_time: int = 1, **kwargs):
        super().__init__(*args, **kwargs)
        self.sleep_time = sleep_time
        self.last_request = 0
        self.lock = threading.Lock()
        self.cookies.set("mangadex_rememberme_token", "c1eb6e7a761e1792bba2da65b6fcbe2d03b03471f2b87abfbdcb6eef9dda00a5")
        self.headers[
            "User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_1_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36"
        self.headers["Accepts"] = "application/json"

    def request(self, method, url, *args, **kwargs):
        with self.lock:
            if time.time() - self.last_request < self.sleep_time:
                time.sleep((self.last_request + self.sleep_time) - time.time())
            self.last_request = time.time()
        return super().request(method, url, *args, **kwargs)


scraper = CustomCloudScraper(sleep_time=1)
scraper.mount("https://", adapter)
scraper.mount("http://", adapter)


def fetch_data(manga_id: int) -> Tuple[int, str, str, int, bool, Optional[int]]:
    r = scraper.get(f"https://api.mangadex.org/v2/manga/{manga_id}/?include=chapters")
    r.raise_for_status()
    manga = MangadexManga.guess_v2(r.json())
    completed = manga.status != Status.Ongoing
    total = len(manga.chapters)
    return manga_id, manga.title, manga.cover_url, total, completed, manga.mal_id


def update_from_mangadex():
    r = scraper.get(f"https://api.mangadex.org/v2/user/555579/followed-manga?hentai=1")
    r.raise_for_status()
    data = MangadexMangaList.from_mdlist(r.json())
    completed = data.filter_user_follow(Following.Completed).id_list()
    dropped = data.filter_user_follow(Following.Dropped).id_list()
    combo = completed + dropped
    reading = [item.id for item in data if item.id not in combo]
    return reading, completed, dropped
