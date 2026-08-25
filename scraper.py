import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
from urllib.robotparser import RobotFileParser


def analyze_page(url):
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return {"error": "Invalid URL. Must include https:// or http://"}

    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
        if not rp.can_fetch("*", url):
            return {"error": "Scraping disallowed by robots.txt for this URL"}
    except:
        pass

    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return {"error": "Request timed out"}
    except requests.exceptions.ConnectionError:
        return {"error": "Could not connect to the website"}
    except requests.exceptions.HTTPError:
        return {"error": f"HTTP error: {response.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}

    soup = BeautifulSoup(response.text, "html.parser")

    # --- Basic fields ---
    title = soup.title.text.strip() if soup.title else None

    meta = soup.find("meta", attrs={"name": "description"})
    description = meta.get("content", "").strip() if meta else None

    h1 = soup.find("h1")
    h1_text = h1.text.strip() if h1 else None

    h2s = [h.get_text(" ", strip=True) for h in soup.find_all("h2")]
    h3s = [h.get_text(" ", strip=True) for h in soup.find_all("h3")]

    text = soup.get_text(" ", strip=True)
    word_count = len(text.split())

    # --- Links ---
    internal_links = []
    external_links = []
    base_domain = urlparse(url).netloc
    for link in soup.find_all("a", href=True):
        full_url = urljoin(url, link["href"])
        domain = urlparse(full_url).netloc
        if domain == base_domain:
            internal_links.append(full_url)
        else:
            external_links.append(full_url)
    internal_links = list(set(internal_links))
    external_links = list(set(external_links))

    # --- Images ---
    images = []
    for image in soup.find_all("img"):
        images.append({
            "src": image.get("src"),
            "alt": image.get("alt")
        })

    # --- Canonical ---
    canonical = soup.find("link", attrs={"rel": "canonical"})
    canonical_url = canonical.get("href") if canonical else None

    # --- Robots meta ---
    robots = soup.find("meta", attrs={"name": "robots"})
    robots_content = robots.get("content") if robots else None

    # --- Schema (JSON-LD, handles @graph) ---
    schema_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    schema_types = set()
    for script in schema_scripts:
        try:
            data = json.loads(script.get_text(strip=True))
            items = data.get("@graph", [data]) if isinstance(data, dict) else data
            for item in items:
                if isinstance(item, dict) and "@type" in item:
                    schema_types.add(item["@type"])
        except:
            pass
    schemas = list(schema_types)

    # --- STEP: Title & Meta Description length check ---
    title_length = len(title) if title else 0
    title_length_status = (
        "Good" if 50 <= title_length <= 60
        else "Too short" if title_length < 50 and title_length > 0
        else "Too long" if title_length > 60
        else "Missing"
    )

    description_length = len(description) if description else 0
    description_length_status = (
        "Good" if 150 <= description_length <= 160
        else "Too short" if description_length < 150 and description_length > 0
        else "Too long" if description_length > 160
        else "Missing"
    )

    # --- STEP: Open Graph & Twitter Card tags ---
    og_tags = {}
    for tag in soup.find_all("meta", attrs={"property": lambda p: p and p.startswith("og:")}):
        og_tags[tag.get("property")] = tag.get("content")

    twitter_tags = {}
    for tag in soup.find_all("meta", attrs={"name": lambda n: n and n.startswith("twitter:")}):
        twitter_tags[tag.get("name")] = tag.get("content")

    social_tags = {
        "open_graph": og_tags,
        "open_graph_present": len(og_tags) > 0,
        "twitter_card": twitter_tags,
        "twitter_card_present": len(twitter_tags) > 0
    }

    # --- STEP: Mobile viewport tag check ---
    viewport = soup.find("meta", attrs={"name": "viewport"})
    viewport_present = viewport is not None
    viewport_content = viewport.get("content") if viewport else None

    # --- STEP: AEO Readiness Score ---
    question_words = ["what", "how", "why", "when", "where", "who", "which", "can", "does", "is"]
    all_headings = h2s + h3s
    question_headings = [
        h for h in all_headings
        if h.strip().lower().split(" ")[0] in question_words or h.strip().endswith("?")
    ]
    question_heading_count = len(question_headings)

    has_faq_schema = "FAQPage" in schemas
    has_short_paragraphs = word_count > 0 and (word_count / max(len(all_headings), 1)) < 150

    aeo_score = 0
    aeo_max = 5
    aeo_breakdown = {}

    aeo_breakdown["question_format_headings"] = question_heading_count > 0
    if question_heading_count > 0:
        aeo_score += 1

    aeo_breakdown["faq_schema_present"] = has_faq_schema
    if has_faq_schema:
        aeo_score += 1

    aeo_breakdown["concise_answer_blocks"] = has_short_paragraphs
    if has_short_paragraphs:
        aeo_score += 1

    aeo_breakdown["h1_present"] = h1_text is not None
    if h1_text is not None:
        aeo_score += 1

    aeo_breakdown["any_schema_present"] = len(schemas) > 0
    if len(schemas) > 0:
        aeo_score += 1

    aeo_readiness = {
        "score": aeo_score,
        "max_score": aeo_max,
        "question_format_headings_count": question_heading_count,
        "breakdown": aeo_breakdown
    }

    # --- STEP: Broken internal links check (checks first 15 internal links only, for speed) ---
    broken_links = []
    links_to_check = internal_links[:15]
    for link in links_to_check:
        try:
            r = requests.head(link, headers=headers, timeout=5, allow_redirects=True)
            if r.status_code >= 400:
                broken_links.append({"url": link, "status": r.status_code})
        except requests.exceptions.RequestException:
            broken_links.append({"url": link, "status": "Failed to connect"})

    broken_links_check = {
        "checked_count": len(links_to_check),
        "broken_count": len(broken_links),
        "broken_links": broken_links
    }

    return {
        "url": url,
        "title": title,
        "meta_description": description,
        "h1": h1_text,
        "h2": h2s,
        "h3": h3s,
        "word_count": word_count,
        "internal_links": internal_links,
        "external_links": external_links,
        "images": images,
        "canonical_url": canonical_url,
        "robots_content": robots_content,
        "schemas": schemas,
        "internal_links_count": len(internal_links),
        "external_links_count": len(external_links),
        "images_count": len(images),
        "images_missing_alt": len([i for i in images if not i["alt"]]),
        "title_length": title_length,
        "title_length_status": title_length_status,
        "description_length": description_length,
        "description_length_status": description_length_status,
        "social_tags": social_tags,
        "viewport_present": viewport_present,
        "viewport_content": viewport_content,
        "aeo_readiness": aeo_readiness,
        "broken_links_check": broken_links_check
    }
