def greet():
    print("SEO Competitor Analyzer is running!")


greet()

import requests


url = "https://example.com"

headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(url, headers=headers)

print(response.status_code)
print(response.text[:500])

import requests
from bs4 import BeautifulSoup


url = "https://example.com"

headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(url, headers=headers)

soup = BeautifulSoup(response.text, "html.parser")

print(soup.title.text)

h1 = soup.find("h1")

if h1:
    print("H1:", h1.text.strip())
else:
    print("H1: Not found")

def analyze_page(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

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

    return {
        "url": url,
        "title": title,
        "meta_description": description,
        "h1": h1_text,
        "h2": h2s,
        "h3": h3s,
        "word_count": word_count
    }


result = analyze_page("https://example.com")

print(result)

from urllib.parse import urljoin, urlparse

def get_links(soup, base_url):
    internal_links = []
    external_links = []

    base_domain = urlparse(base_url).netloc

    for link in soup.find_all("a", href=True):
        full_url = urljoin(base_url, link["href"])

        domain = urlparse(full_url).netloc

        if domain == base_domain:
            internal_links.append(full_url)
        else:
            external_links.append(full_url)

    return internal_links, external_links

internal, external = get_links(soup, url)
print(internal)
print(external)

images = []

for image in soup.find_all("img"):
    images.append({
        "src": image.get("src"),
        "alt": image.get("alt")
    })

print(images)


canonical = soup.find(
    "link",
    attrs={"rel": "canonical"}
)

canonical_url = canonical.get("href") if canonical else None

print(canonical_url)

robots = soup.find(
    "meta",
    attrs={"name": "robots"}
)

robots_content = (
    robots.get("content")
    if robots
    else None
)

print(robots_content)


schema_scripts = soup.find_all(
    "script",
    attrs={"type": "application/ld+json"}
)

schemas = []

for script in schema_scripts:
    schemas.append(script.get_text(strip=True))

print(schemas)