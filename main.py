import json
import os
import firebase_admin
from firebase_admin import credentials, firestore
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import time

# Initialize Firebase
def init_firebase():
    cred_path = "/Users/besabunjaku/repos/Vitola/vitola-32c8b-firebase-adminsdk-fbsvc-ea69047c01.json"
    
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    return firestore.client()

# Stub scraper
def scrape_cigars_international():
    base_url = "https://www.cigarsinternational.com"
    list_url = f"{base_url}/shop/big-list-of-cigars-brands/1803000/"
    cigars = []

    # Setup headless Chrome
    options = uc.ChromeOptions()
    options.headless = False
    driver = uc.Chrome(options=options)

    print(f"Scraping master cigar list from {list_url}...")
    driver.get(list_url)
    time.sleep(10)  # wait for JS to load

    soup = BeautifulSoup(driver.page_source, "lxml")
    links = soup.select("a.biglist-browser-mobile-view")
    print(f"🧾 Found {len(links)} brand links")

    progress_file = "progress.json"
    last_scraped_url = None
    if os.path.exists(progress_file):
        with open(progress_file, "r") as pf:
            progress_data = json.load(pf)
            last_scraped_url = progress_data.get("last_url")

    skip = bool(last_scraped_url)

    for link in links:
        brand_url = base_url + link["href"]
        if skip:
            if brand_url == last_scraped_url:
                skip = False
            continue
        try:
            print(f"➡️ Visiting brand page: {brand_url}")
            driver.get(brand_url)

            cigar_soup = BeautifulSoup(driver.page_source, "lxml")

            # Extract cigar name
            name_tag = cigar_soup.select_one("div.prod-hgroup h1 span[itemprop='name']")
            name = name_tag.text.strip() if name_tag else "Unknown"

            # Attempt to extract brand from table row
            brand_tag = cigar_soup.select_one("tr:has(td:contains('Brand:')) td a.brand-name")
            brand = brand_tag.text.strip() if brand_tag else name

            # Extract review count and rating
            review_tag = cigar_soup.select_one("a.prod-stat-reviews span.prod-stat-count")
            review_count = review_tag.text.strip() if review_tag else "0"

            rating_tag = cigar_soup.select_one("span.stars-wrapper span[title]")
            rating = rating_tag["title"] if rating_tag else "N/A"

            # Description
            description_tag = cigar_soup.select_one("div[itemprop='description']")
            description = description_tag.get_text(strip=True) if description_tag else "N/A"

            # Extract main image URL from main product image
            image_tag = cigar_soup.select_one("img.img-fluid.lazyloaded")
            image_url = f"https:{image_tag['src']}" if image_tag and 'src' in image_tag.attrs else None

            # Initialize all attributes
            vitola = wrapper = strength = origin = flavored = pressed = has_tip = binder = filler = sweet = "Unknown"

            rows = cigar_soup.select("table.characteristics tr")
            for row in rows:
                cols = row.find_all("td")
                if len(cols) != 2:
                    continue
                label = cols[0].get_text(strip=True)
                value = cols[1].get_text(strip=True)
                if "Profile" in label:
                    strength = cols[1].div["title"] if cols[1].div and "title" in cols[1].div.attrs else value
                elif "Wrapper" in label:
                    wrapper = value
                elif "Origin" in label:
                    origin = value
                elif "Shapes" in label:
                    vitola = value
                elif "Flavored" in label:
                    flavored = value
                elif "Pressed" in label:
                    pressed = value
                elif "Has Tip" in label:
                    has_tip = value
                elif "Binder" in label:
                    binder = value
                elif "Filler" in label:
                    filler = value
                elif "Sweet" in label:
                    sweet = value

            cigars.append({
                "brand": brand,
                "name": name,
                "vitola": vitola,
                "wrapper": wrapper,
                "strength": strength,
                "origin": origin,
                "flavored": flavored,
                "pressed": pressed,
                "has_tip": has_tip,
                "binder": binder,
                "filler": filler,
                "sweet": sweet,
                "manufacturer": None,
                "rolled_by": None,
                "rating": rating,
                "review_count": review_count,
                "description": description,
                "image_url": image_url,
                "source": "CigarsInternational",
                "famous_exclusive": None,
                "wrapper_color": None
            })
            with open(progress_file, "w") as pf:
                json.dump({"last_url": brand_url}, pf)
        except Exception as e:
            print("❌ Failed to scrape brand/cigar page:", e)

    driver.quit()
    return cigars

def scrape_neptune_cigars():
    base_url = "https://www.neptunecigar.com"
    list_url = f"{base_url}/browse/brand"

    options = uc.ChromeOptions()
    options.headless = False
    driver = uc.Chrome(options=options)

    print(f"Scraping Neptune Cigar brands from {base_url}...")
    driver.get(base_url)

    soup = BeautifulSoup(driver.page_source, "lxml")
    brand_div = soup.select_one("#divBrands")
    brand_links = brand_div.select("li.classItem a[href]") if brand_div else []
    print(f"🧾 Found {len(brand_links)} brand links")

    cigars = []

    for link in brand_links:
        brand_url = base_url + link["href"]
        print(f"➡️ Visiting brand page: {brand_url}")
        try:
            driver.get(brand_url)
            cigar_soup = BeautifulSoup(driver.page_source, "lxml")

            name_tag = cigar_soup.select_one("h1.av_brand_summary_name[itemprop='name']")
            name = name_tag.text.strip() if name_tag else "Unknown"

            brand_tag = cigar_soup.select_one("h1[itemprop='name']")
            brand = brand_tag.text.strip() if brand_tag else name

            description_tag = cigar_soup.select_one("div.av_brand_summary_description")
            description = description_tag.get_text(strip=True) if description_tag else "N/A"

            image_tag = cigar_soup.select_one("meta[itemprop='image']")
            image_url = f"https:{image_tag['content']}" if image_tag and 'content' in image_tag.attrs else None

            def get_spec(soup, label):
                for item in soup.select("ul.pr_specList li.pr_pItem"):
                    divs = item.find_all("div", recursive=False)
                    if len(divs) >= 2 and label.lower() in divs[0].text.strip().lower():
                        value_divs = divs[1].find_all("div", recursive=False)
                        if value_divs:
                            return value_divs[0].get_text(strip=True)
                        return divs[1].get_text(strip=True)
                return "Unknown"

            origin = get_spec(cigar_soup, "Cigar Origin")
            strength = cigar_soup.select_one("#strengthCursor div")
            strength = strength.text.strip() if strength else "Unknown"
            wrapper = get_spec(cigar_soup, "Wrapper")
            binder = get_spec(cigar_soup, "Binder")
            filler = get_spec(cigar_soup, "Filler")
            manufacturer = get_spec(cigar_soup, "Manufacturer")
            rolled_by = get_spec(cigar_soup, "Rolled by")

            # Extract rating and review_count from new HTML structure
            rating_tag = cigar_soup.select_one("div.divOverall > div:nth-of-type(2)")
            rating = rating_tag.text.strip() if rating_tag else None

            review_count_tag = cigar_soup.select_one("div.divOverall")
            review_count = "Unknown"
            if review_count_tag:
                review_texts = review_count_tag.find_all("div")
                for div in review_texts:
                    text = div.get_text(strip=True)
                    if text.lower().endswith("reviews"):
                        review_count = text.split()[0]
                        break

            # Extract all vitola values from multiple .parent_single_attrs_toshow elements, filtering out non-shape descriptors
            vitola_tags = cigar_soup.select("div.parent_single_attrs_toshow")
            vitolas = set()
            for tag in vitola_tags:
                parts = tag.get_text(strip=True).split(",")
                for part in parts:
                    shape = part.strip()
                    # Filter out non-shape descriptors like 'Medium', 'Maduro', 'from Nicaragua'
                    if shape.lower() not in [
                        "medium", "mild", "full", "maduro", "natural", "claro", "oscuro",
                        "from nicaragua", "from honduras", "from dominican republic"
                    ]:
                        vitolas.add(shape)
            vitola = ", ".join(sorted(vitolas)) if vitolas else "Unknown"

            cigars.append({
                "brand": brand,
                "name": name,
                "vitola": vitola,
                "wrapper": wrapper,
                "strength": strength,
                "origin": origin,
                "flavored": None,
                "pressed": None,
                "has_tip": None,
                "binder": binder,
                "filler": filler,
                "sweet": None,
                "manufacturer": manufacturer,
                "rolled_by": rolled_by,
                "rating": rating,
                "review_count": review_count,
                "description": description,
                "image_url": image_url,
                "source": "NeptuneCigar",
                "famous_exclusive": None,
                "wrapper_color": None
            })

        except Exception as e:
            print("❌ Failed to scrape brand page:", e)

    driver.quit()
    return cigars

def scrape_famous_smoke():
    base_url = "https://www.famous-smoke.com"
    list_url = f"{base_url}/cigars"
    cigars = []

    options = uc.ChromeOptions()
    options.headless = False
    driver = uc.Chrome(options=options)

    # Progress file handling for continuation
    progress_file = "progress.json"
    last_scraped_page = 43 # 43
    if os.path.exists(progress_file):
        with open(progress_file, "r") as pf:
            progress_data = json.load(pf)
            last_scraped_page = progress_data.get("last_page", 43)

    # Start from the last recorded page
    driver.get(f"{list_url}?p={last_scraped_page}")

    page = last_scraped_page
    total_pages = 1
    while True:
        paged_url = f"{list_url}?p={page}"
        print(f"📄 Scraping page {page} - {paged_url}")
        # Update progress after printing page number
        with open(progress_file, "w") as pf:
            json.dump({"last_page": page}, pf)
        driver.get(paged_url)
        soup = BeautifulSoup(driver.page_source, "lxml")
        pagination_items = soup.select("ul.items.pages-items li a.page span:nth-of-type(2), ul.items.pages-items li strong.page span:nth-of-type(2)")
        try:
            total_pages = max([int(item.get_text(strip=True)) for item in pagination_items if item.get_text(strip=True).isdigit()] or [1])
        except ValueError:
            total_pages = page  # fallback to prevent infinite loop
        if page > total_pages:
            break
        product_links = [a["href"] for a in soup.select("a.product-item-link") if a.has_attr("href")]

        for prod_url in product_links:
            try:
                print(f"➡️ Visiting cigar page: {prod_url}")
                driver.get(prod_url)
                prod_soup = BeautifulSoup(driver.page_source, "lxml")

                name_tag = prod_soup.select_one("span.base")
                name = name_tag.text.strip() if name_tag else "Unknown"

                brand_tag = prod_soup.select_one("th:contains('Brand') + td")
                brand = brand_tag.text.strip() if brand_tag else name

                description_tag = prod_soup.select_one("div.value[data-role='content'] p")
                description = description_tag.text.strip() if description_tag else "N/A"

                image_tag = prod_soup.select_one("img.fotorama__img")
                image_url = image_tag["src"] if image_tag else None

                review_tag = prod_soup.select_one("span.sv-product-review-small__text")
                review_count = review_tag.text.strip().split()[0] if review_tag else "0"

                rating_tag = prod_soup.select_one("span.sv-product-review-small__rating")
                rating = rating_tag.text.strip("()") if rating_tag else "N/A"

                # Spec table parsing
                def get_spec(label):
                    th = prod_soup.find("th", string=lambda x: x and label.lower() in x.lower())
                    if th and th.find_next_sibling("td"):
                        return th.find_next_sibling("td").text.strip()
                    return None

                vitola = get_spec("Cigar Shape")
                strength = get_spec("Strength")
                origin = get_spec("Country of Origin")
                wrapper = get_spec("Wrapper Leaf")
                wrapper_color = get_spec("Wrapper Color")
                binder = filler = flavored = pressed = has_tip = sweet = rolled_by = manufacturer = None
                rolled_by = get_spec("Made")
                cigar_size = get_spec("Cigar Size")
                package_quantity = get_spec("Package Quantity")
                quantity_per_package = get_spec("Quantity per Packaging")
                package_type = get_spec("Package Type")
                wrapper_origin = get_spec("Wrapper Origin")
                exclusive = get_spec("Famous Exclusive")

                cigars.append({
                    "brand": brand,
                    "name": name,
                    "vitola": vitola,
                    "wrapper": wrapper,
                    "strength": strength,
                    "origin": origin,
                    "flavored": flavored,
                    "pressed": pressed,
                    "has_tip": has_tip,
                    "binder": binder,
                    "filler": filler,
                    "sweet": sweet,
                    "manufacturer": manufacturer,
                    "rolled_by": rolled_by,
                    "rating": rating,
                    "review_count": review_count,
                    "description": description,
                    "image_url": image_url,
                    "famous_exclusive": exclusive,
                    "wrapper_color": wrapper_color,
                    "source": "FamousSmoke",
                    "sweet": None,
                    "has_tip": None
                })
            except Exception as e:
                print("❌ Failed to scrape product:", e)
        page += 1

    driver.quit()
    return cigars

# Store each cigar in Firestore, skipping duplicates by brand and name
def store_cigars(db, cigars):
    for cigar in cigars:
        try:
            existing = db.collection("cigars") \
                .where("brand", "==", cigar["brand"]) \
                .where("name", "==", cigar["name"]) \
                .stream()

            if any(existing):
                print(f"🔁 Skipped duplicate: {cigar['brand']} - {cigar['name']}")
                continue

            db.collection("cigars").add(cigar)
            print(f"✅ Added: {cigar['brand']} - {cigar['name']}")
        except Exception as e:
            print(f"❌ Error storing {cigar['name']}: {e}")

# Main entry
if __name__ == "__main__":
    db = init_firebase()
    # cigars = scrape_cigars_international()
    # cigars = scrape_neptune_cigars()
    cigars = scrape_famous_smoke()
    store_cigars(db, cigars)