import re
import warnings
from html import unescape
from typing import Dict, List, Optional, Tuple, Union

import bs4
import cloudscraper

warnings.filterwarnings("ignore", category=UserWarning, module='bs4')

manga_link_regex = re.compile("/manga/([0-9]+)/[\S]+")

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


def get_list_data(section_number):
    r = scraper.get(f"https://mangadex.org/list/555579/{section_number}/2/1")
    soup = bs4.BeautifulSoup(r.text)
    page_link_regex = re.compile(fr"/list/555579/{section_number}/2/([0-9]+)")
    highest_page = max(
        [int(page_link_regex.search(a["href"]).group(1)) for a in soup.find_all("a", href=page_link_regex)] + [1])
    total_ids = [int(manga_link_regex.search(item["href"]).group(1)) for item in
                 soup.find_all("a", href=manga_link_regex)]
    for page in range(2, highest_page + 1):
        r = scraper.get(f"https://mangadex.org/list/555579/{section_number}/2/{page}")
        soup = bs4.BeautifulSoup(r.text)
        total_ids += [int(manga_link_regex.search(item["href"]).group(1)) for item in
                      soup.find_all("a", href=manga_link_regex)]
    return total_ids


def update_from_mangadex():
    completed_number = 2
    reading_number = 1
    dropped_number = 5
    reading = get_list_data(reading_number)
    completed = get_list_data(completed_number)
    dropped = get_list_data(dropped_number)
    return reading, completed, dropped
