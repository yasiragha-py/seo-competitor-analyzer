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
        if not rp.can_fetch("*", url) and not rp.can_fetch("*", url.rstrip("/") + "/"):
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

    title = soup.title.text.strip() if soup.title else None

    meta = soup.find("meta", attrs={"name": "description"})
    description = meta.get("content", "").strip() if meta else None

    h1 = soup.find("h1")
    h1_text = h1.text.strip() if h1 else None

    h2s = [h.get_text(" ", strip=True) for h in soup.find_all("h2")]
    h3s = [h.get_text(" ", strip=True) for h in soup.find_all("h3")]

    text = soup.get_text(" ", strip=True)
    word_count = len(text.split())

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

    images = []
    for image in soup.find_all("img"):
        images.append({
            "src": image.get("src"),
            "alt": image.get("alt")
        })

    canonical = soup.find("link", attrs={"rel": "canonical"})
    canonical_url = canonical.get("href") if canonical else None

    robots = soup.find("meta", attrs={"name": "robots"})
    robots_content = robots.get("content") if robots else None

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
        "images_missing_alt": len([i for i in images if not i["alt"]])
    }