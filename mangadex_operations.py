from typing import Dict, List, Optional, Tuple, Union
from html import unescape

import cloudscraper

scraper = cloudscraper.create_scraper()

chapter_dict_type = Dict[str, Dict[str, Optional[Union[str, int]]]]
manga_dict_type = Dict[str, Union[str, List[str], int, List[int], Dict[str, str]]]
group_dict_type = Dict[str, Dict[str, str]]
complete_dict_type = Dict[str, Union[chapter_dict_type, manga_dict_type, group_dict_type, str]]


def get_chapter_count(chapter_dict: chapter_dict_type) -> int:
    processed_chapters = []
    count = 0
    for chapter_number_string, chapter_data in chapter_dict.items():
        if chapter_data["lang_code"] == "gb" and chapter_data["chapter"] not in processed_chapters:
            processed_chapters.append(chapter_data["chapter"])
            count += 1
    return count


def fetch_data(manga_id: int) -> Tuple[int, str, str, int, bool]:
    r = scraper.get(f"https://mangadex.org/api/manga/{manga_id}/")
    r.raise_for_status()
    json: complete_dict_type = r.json()
    manga = json["manga"]
    completed = manga["status"] != 1
    total = get_chapter_count(json["chapter"]) if "chapter" in json else 0
    title = unescape(manga["title"])
    cover_url = f"https://www.mangadex.org{manga['cover_url']}"
    return manga_id, title, cover_url, total, completed
