import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import pandas as pd

base_url = "http://books.toscrape.com/"

rating_lookup = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def parse_card(card, curr_url):
    # grab title from the <a> tag's title attr (visible text is often truncated with ...)
    a_tag = card.h3.find("a")
    title = a_tag.get("title", a_tag.text.strip()) if a_tag else "Unknown"
    href = a_tag["href"] if a_tag and a_tag.has_attr("href") else ""
    prod_url = urljoin(curr_url, href)

    # price string comes with a currency symbol (e.g. £51.77 or Â£51.77)
    p_tag = card.find("p", class_="price_color")
    raw_price = p_tag.text.strip() if p_tag else ""

    # rating is in class like ['star-rating', 'Three']
    rating_val = None
    r_tag = card.find("p", class_="star-rating")
    if r_tag:
        for c in r_tag.get("class", []):
            if c in rating_lookup:
                rating_val = rating_lookup[c]
                break

    stock_tag = card.find("p", class_="instock availability")
    stock = stock_tag.text.strip() if stock_tag else ""

    img = card.find("img")
    img_url = urljoin(curr_url, img["src"]) if img and img.has_attr("src") else ""

    return {
        "title": title,
        "price_raw": raw_price,
        "rating": rating_val,
        "availability": stock,
        "product_url": prod_url,
        "image_url": img_url,
    }


def scrape_catalog(start_url=base_url, max_pages=5, delay=0.5):
    url = start_url
    results = []
    page = 1

    print(f"Scraping up to {max_pages} pages...")

    while url and page <= max_pages:
        print(f"[Page {page}] -> {url}")
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"Failed to fetch {url}: {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.find_all("article", class_="product_pod")
        print(f"  found {len(cards)} items")

        for c in cards:
            row = parse_card(c, url)
            row["page"] = page
            results.append(row)

        # find next button
        nxt = soup.find("li", class_="next")
        if nxt and nxt.find("a"):
            url = urljoin(url, nxt.find("a")["href"])
            page += 1
        else:
            url = None

        time.sleep(delay)  # polite crawl delay

    print(f"Done scraping. Collected {len(results)} items across {page - 1} pages.")
    return results


def clean_dataset(raw_records):
    df = pd.DataFrame(raw_records)

    # backup raw data before touching it
    df.to_csv("output_raw.csv", index=False, encoding="utf-8-sig")

    # dedupe just in case
    init_len = len(df)
    df = df.drop_duplicates(subset=["title", "product_url"])
    if len(df) < init_len:
        print(f"Dropped {init_len - len(df)} duplicate rows")

    # clean up price col: strip currency symbol and encoding artifacts
    df["price_gbp"] = (
        df["price_raw"]
        .astype(str)
        .str.replace("£", "", regex=False)
        .str.replace("Â", "", regex=False)
        .str.strip()
    )
    df["price_gbp"] = pd.to_numeric(df["price_gbp"], errors="coerce")

    # normalize stock status
    df["in_stock"] = df["availability"].str.lower().str.contains("in stock", na=False)
    df["availability_clean"] = df["availability"].str.replace(r"\s+", " ", regex=True).str.strip()

    cols = [
        "title",
        "price_gbp",
        "rating",
        "in_stock",
        "availability_clean",
        "product_url",
        "image_url",
        "page",
    ]
    clean_df = df[cols]
    clean_df.to_csv("output_cleaned.csv", index=False, encoding="utf-8-sig")
    print("Saved clean data to output_cleaned.csv")

    # print a quick peek
    print("\nSample records:")
    for _, r in clean_df.head(5).iterrows():
        print(f"  {r['title'][:40]:<42} | GBP {r['price_gbp']:<5.2f} | {r['rating']}/5 | {r['availability_clean']}")

    return clean_df


if __name__ == "__main__":
    items = scrape_catalog(max_pages=5)
    if items:
        clean_dataset(items)
