"""Import Patnet Aichi suspicious-person notices into a CSV map ledger."""

import argparse
import csv
import hashlib
import json
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "http://patnet.jp/"
GEOCODER_URL = "https://msearch.gsi.go.jp/address-search/AddressSearch"
FIELDS = ["id", "date", "tag", "location", "reportedLocation", "locationAccuracy",
          "lat", "lng", "description", "sourceUrl", "lastChecked"]
HEADERS = {"User-Agent": "AichiSafetyRadar/1.0 (public safety map; contact via repository)"}
TIMEOUT = (10, 30)
GEOCODE_CACHE = {}


def month_start(months_back=0):
    current = date.today()
    index = current.year * 12 + current.month - 1 - months_back
    return date(index // 12, index % 12 + 1, 1)


def fetch_soup(url, session):
    response = session.get(url, timeout=TIMEOUT, headers=HEADERS)
    response.raise_for_status()
    # Parsing response bytes lets BeautifulSoup honor the document's own charset.
    return BeautifulSoup(response.content, "html.parser")


def category_text(post):
    utility = post.select_one(".entry-utility")
    return utility.get_text(" ", strip=True) if utility else ""


def post_permalink(post, base_url):
    heading = post.select_one(".entry-title a[href]")
    if not heading:
        heading = post.select_one("h2 a[href], h3 a[href]")
    return urljoin(base_url, heading["href"]) if heading else ""


def archive_posts(month_url, session, cutoff):
    """Walk WordPress monthly archive pages until they pass the requested cutoff."""
    url = month_url
    found = []
    visited = set()
    while url and url not in visited:
        visited.add(url)
        soup = fetch_soup(url, session)
        posts = soup.select("#main .post")
        if not posts:
            break
        page_dates = []
        for post in posts:
            published = post.select_one(".entry-date")
            date_text = published.get_text(" ", strip=True) if published else post.get_text(" ", strip=True)
            match = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", date_text)
            posted_on = date(int(match.group(1)), int(match.group(2)), int(match.group(3))) if match else None
            if posted_on:
                page_dates.append(posted_on)
            if posted_on and posted_on < cutoff:
                continue
            if "不審者情報" not in category_text(post):
                continue
            permalink = post_permalink(post, url)
            if permalink:
                found.append((permalink, posted_on))
        if page_dates and max(page_dates) < cutoff:
            break
        older = soup.select_one(".navigation a[rel='next'], a.next.page-numbers, .nav-previous a")
        url = urljoin(url, older["href"]) if older and older.get("href") else ""
        time.sleep(0.2)
    return found


def extract_article(permalink, posted_on, session):
    soup = fetch_soup(permalink, session)
    post = soup.select_one("#main .post") or soup
    heading = post.select_one(".entry-title") or soup.title
    title = heading.get_text(" ", strip=True) if heading else "不審者情報"
    body = post.select_one(".entry-content")
    content = body.get_text("\n", strip=True) if body else post.get_text("\n", strip=True)
    category = category_text(post)
    if "不審者情報" not in category:
        return None

    place_match = re.search(r"■\s*発生場所\s*[:：]?\s*(.+?)(?=\s*■|$)", content, re.S)
    raw_place = re.sub(r"\s+", "", place_match.group(1)).strip("。、「」『』") if place_match else ""
    municipality = normalize_municipality(raw_place or title)
    if not municipality:
        return None
    event_match = re.search(r"■\s*発生日時\s*[:：]?\s*(.+?)(?=\s*■|$)", content, re.S)
    event_date = event_match.group(1).strip() if event_match else (posted_on.isoformat() if posted_on else "")
    # Public summary deliberately excludes identifying descriptions from the report.
    if "つきまとい" in content:
        tag = "つきまとい"
    elif "盗撮" in content or "ちかん" in content:
        tag = "のぞき・盗撮"
    else:
        tag = "声かけ・不審者情報"
    title_safe = re.sub(r"[☆★■◆◇●◎【】\[\]]", "", title).strip()
    description = f"{tag}に関する情報です。詳細は掲載元の記事をご確認ください。"
    latlng = geocode_area(municipality, session)
    if latlng:
        lat, lng = latlng
        accuracy = "municipality"
        label = f"{municipality}付近（地域代表点）"
    else:
        # Fallback is still coarse and does not pretend to be an incident address.
        lat, lng, accuracy, label = 35.1802, 136.9066, "prefecture", "愛知県内（地域未特定）"
    return {"id": hashlib.sha256(permalink.encode("utf-8")).hexdigest()[:20],
            "date": event_date, "tag": tag, "location": label,
            "reportedLocation": municipality, "locationAccuracy": accuracy,
            "lat": lat, "lng": lng, "description": description,
            "sourceUrl": permalink,
            "lastChecked": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def normalize_municipality(text):
    text = text.replace("愛知県", "")
    # Keep Nagoya's ward for a useful but non-address-level map point.
    match = re.search(r"名古屋市\s*[一-龯ぁ-んァ-ヶ]+区", text)
    if match:
        return re.sub(r"\s+", "", match.group(0))
    match = re.search(r"(?:[一-龯ぁ-んァ-ヶ]+郡\s*)?[一-龯ぁ-んァ-ヶ]+(?:市|町|村)", text)
    return re.sub(r"\s+", "", match.group(0)) if match else ""


def geocode_area(municipality, session):
    if municipality in GEOCODE_CACHE:
        return GEOCODE_CACHE[municipality]
    response = session.get(GEOCODER_URL, params={"q": f"愛知県{municipality}"}, timeout=TIMEOUT, headers=HEADERS)
    response.raise_for_status()
    results = response.json()
    if not results:
        GEOCODE_CACHE[municipality] = None
        return None
    lng, lat = results[0]["geometry"]["coordinates"]
    GEOCODE_CACHE[municipality] = (float(lat), float(lng))
    time.sleep(0.2)
    return GEOCODE_CACHE[municipality]


def load_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def save_outputs(csv_path, json_path, rows):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="パトネットあいちの不審者情報をCSVに蓄積し地図データに変換")
    parser.add_argument("--months", type=int, default=1, help="取得する直近月数（1〜12）")
    parser.add_argument("--csv", type=Path, default=Path("data/incidents.csv"))
    parser.add_argument("--json", type=Path, default=Path("data/incidents.json"))
    args = parser.parse_args()
    if not 1 <= args.months <= 12:
        parser.error("--months は1から12の範囲で指定してください")

    session = requests.Session()
    cutoff = month_start(args.months - 1)
    reports = []
    for back in reversed(range(args.months)):
        first = month_start(back)
        month_url = f"{BASE_URL}{first.year}/{first.month:02d}/"
        reports.extend(archive_posts(month_url, session, cutoff))
    # Deduplicate links before requesting article pages.
    reports = list({url: posted for url, posted in reports}.items())
    print(f"記事リンク候補: {len(reports)}件")

    rows = load_csv(args.csv)
    by_id = {row.get("id"): row for row in rows}
    existing_ids = set(by_id)
    added = 0
    for permalink, posted_on in reports:
        identifier = hashlib.sha256(permalink.encode("utf-8")).hexdigest()[:20]
        if identifier in existing_ids:
            continue
        try:
            record = extract_article(permalink, posted_on, session)
            if record:
                rows.append(record)
                existing_ids.add(record["id"])
                added += 1
            time.sleep(0.25)
        except (requests.RequestException, ValueError, KeyError, TypeError) as error:
            print(f"取得・ジオコード失敗: {permalink}: {error}")
    save_outputs(args.csv, args.json, rows)
    print(f"CSV新規追加: {added}件 / 累計: {len(rows)}件")
    print(f"出力: {args.csv} / {args.json}")


if __name__ == "__main__":
    main()
