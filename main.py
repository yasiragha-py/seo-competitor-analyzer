from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
from datetime import date

from scraper import analyze_page
from database import SessionLocal, SEOResult, RequestLog


app = FastAPI()

DAILY_LIMIT = 10

def get_client_ip(req: Request) -> str:
    forwarded = req.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_client_ip(req)

class AnalyzeRequest(BaseModel):
    urls: List[str]
    respect_robots: bool = True


@app.get("/")
def home():
    return {"message": "SEO Competitor Analyzer API is running"}


@app.get("/quota")
def get_quota(req: Request):
    client_ip = get_client_ip(req)
    db = SessionLocal()
    today = str(date.today())
    log = db.query(RequestLog).filter(RequestLog.ip == client_ip, RequestLog.date == today).first()
    db.close()
    if log is None:
        return {"remaining": DAILY_LIMIT}
    return {"remaining": max(DAILY_LIMIT - log.count, 0)}


DAILY_LIMIT = 10


def check_rate_limit(ip: str, urls_count: int):
    db = SessionLocal()
    today = str(date.today())
    log = db.query(RequestLog).filter(RequestLog.ip == ip, RequestLog.date == today).first()

    if log is None:
        if urls_count > DAILY_LIMIT:
            db.close()
            raise HTTPException(status_code=429, detail=f"You requested {urls_count} URLs but only {DAILY_LIMIT} requests are allowed per day.")
        log = RequestLog(ip=ip, date=today, count=urls_count)
        db.add(log)
        db.commit()
        remaining = DAILY_LIMIT - urls_count
        db.close()
        return remaining

    remaining_before = DAILY_LIMIT - log.count
    if urls_count > remaining_before:
        db.close()
        raise HTTPException(status_code=429, detail=f"Only {remaining_before} requests left today, but you submitted {urls_count} URLs.")

    log.count += urls_count
    db.commit()
    remaining = DAILY_LIMIT - log.count
    db.close()
    return remaining


def build_comparison(results):
    valid = [r for r in results if "error" not in r]
    if len(valid) < 2:
        return None

    word_counts = {r["url"]: r["word_count"] for r in valid}
    avg_words = sum(word_counts.values()) // len(word_counts)

    all_schemas = {r["url"]: r["schemas"] for r in valid}
    missing_alt = {r["url"]: r["images_missing_alt"] for r in valid}
    missing_canonical = [r["url"] for r in valid if not r["canonical_url"]]

    return {
        "average_word_count": avg_words,
        "word_count_by_site": word_counts,
        "schemas_by_site": all_schemas,
        "images_missing_alt_by_site": missing_alt,
        "sites_missing_canonical": missing_canonical
    }


@app.post("/analyze")
def analyze(request: AnalyzeRequest, req: Request):
    client_ip = get_client_ip(req)
    remaining = check_rate_limit(client_ip, len(request.urls))

    results = []
    db = SessionLocal()

    for url in request.urls:
        result = analyze_page(url, respect_robots=request.respect_robots)
        results.append(result)

        if "error" not in result:
            entry = SEOResult(
                url=result["url"],
                title=result["title"],
                word_count=result["word_count"],
                internal_links_count=result["internal_links_count"],
                external_links_count=result["external_links_count"],
                images_count=result["images_count"],
                images_missing_alt=result["images_missing_alt"],
                schemas=", ".join(result["schemas"])
            )
            db.add(entry)

    db.commit()
    db.close()

    response = {"results": results, "remaining_today": remaining}
    comparison = build_comparison(results)
    if comparison:
        response["comparison"] = comparison

    return response


app.mount("/ui", StaticFiles(directory="static", html=True), name="static")