import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import pandas as pd

START_URL = "http://books.toscrape.com/"

# mapping word ratings from the css class to ints
RATINGS = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5
}

hdr = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def _get_rating(card):
    # rating is baked into class list, e.g. ['star-rating', 'Three']
    r_tag = card.find("p", class_="star-rating")
    if not r_tag:
        return None
    for cls in r_tag.get("class", []):
        if cls in RATINGS:
            return RATINGS[cls]
    return None


def parse_item(card, page_url):
    # visible link text is often cut off with '...', full title lives in title attr
    a_tag = card.h3.find("a") if card.h3 else None
    if a_tag and a_tag.has_attr("title"):
        title = a_tag["title"]
    elif a_tag:
        title = a_tag.text.strip()
    else:
        title = "N/A"

    link = urljoin(page_url, a_tag["href"]) if (a_tag and a_tag.has_attr("href")) else ""

    p_tag = card.find("p", class_="price_color")
    raw_price = p_tag.text.strip() if p_tag else ""

    avail_tag = card.find("p", class_="instock availability")
    stock_txt = avail_tag.text.strip() if avail_tag else ""

    img_tag = card.find("img")
    img_src = urljoin(page_url, img_tag["src"]) if (img_tag and img_tag.has_attr("src")) else ""

    return {
        "title": title,
        "price_raw": raw_price,
        "rating": _get_rating(card),
        "availability": stock_txt,
        "product_url": link,
        "image_url": img_src
    }


def scrape_books(start_url=START_URL, max_pages=5, delay=0.5):
    curr_url = start_url
    records = []
    p_num = 1

    print(f"Scraping up to {max_pages} pages from {start_url}...")

    while curr_url and p_num <= max_pages:
        print(f"[p.{p_num}] fetching: {curr_url}")
        try:
            res = requests.get(curr_url, headers=hdr, timeout=10)
            res.raise_for_status()
        except requests.RequestException as err:
            print(f"Fetch failed on {curr_url}: {err}")
            break

        soup = BeautifulSoup(res.text, "html.parser")
        pods = soup.find_all("article", class_="product_pod")
        print(f"  got {len(pods)} books")

        for pod in pods:
            item = parse_item(pod, curr_url)
            item["page"] = p_num
            records.append(item)

        # pagination: next button is in <li class="next">
        next_li = soup.find("li", class_="next")
        if next_li and next_li.find("a"):
            curr_url = urljoin(curr_url, next_li.find("a")["href"])
            p_num += 1
        else:
            curr_url = None

        # be polite to the host
        time.sleep(delay)

    print(f"\nScrape finished: {len(records)} total records pulled.")
    return records


def clean_and_export(data):
    if not data:
        print("No data to process.")
        return None

    df = pd.DataFrame(data)

    # stash raw data first
    df.to_csv("output_raw.csv", index=False, encoding="utf-8-sig")

    # dedupe
    before_len = len(df)
    df = df.drop_duplicates(subset=["title", "product_url"])
    if len(df) < before_len:
        print(f"Dropped {before_len - len(df)} duplicates")

    # price column cleanup: site sends weird pound sign encodings sometimes (Â£, £)
    clean_price = (
        df["price_raw"]
        .astype(str)
        .str.replace("£", "", regex=False)
        .str.replace("Â", "", regex=False)
        .str.strip()
    )
    df["price_gbp"] = pd.to_numeric(clean_price, errors="coerce")

    # stock flag + cleanup extra whitespace/newlines from html
    df["in_stock"] = df["availability"].str.lower().str.contains("in stock", na=False)
    df["availability_clean"] = df["availability"].str.replace(r"\s+", " ", regex=True).str.strip()

    final_cols = [
        "title",
        "price_gbp",
        "rating",
        "in_stock",
        "availability_clean",
        "product_url",
        "image_url",
        "page"
    ]
    cleaned = df[final_cols]
    cleaned.to_csv("output_cleaned.csv", index=False, encoding="utf-8-sig")
    print("Exported cleaned data -> output_cleaned.csv")

    # TODO: consider extracting category name from the sidebar if needed later
    print("\nPreview (first 5):")
    for _, row in cleaned.head(5).iterrows():
        t = row["title"][:38] + "..." if len(row["title"]) > 38 else row["title"]
        print(f"  {t:<42} | GBP {row['price_gbp']:<5.2f} | {row['rating']}/5 | {row['availability_clean']}")

    return cleaned


if __name__ == "__main__":
    books = scrape_books(max_pages=5)
    if books:
        clean_and_export(books)
