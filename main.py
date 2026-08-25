from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
from datetime import date

from scraper import analyze_page
from database import SessionLocal, SEOResult, RequestLog


app = FastAPI()

DAILY_LIMIT = 20


class AnalyzeRequest(BaseModel):
    urls: List[str]


@app.get("/")
def home():
    return {"message": "SEO Competitor Analyzer API is running"}


def check_rate_limit(ip: str):
    db = SessionLocal()
    today = str(date.today())
    log = db.query(RequestLog).filter(RequestLog.ip == ip, RequestLog.date == today).first()

    if log is None:
        log = RequestLog(ip=ip, date=today, count=1)
        db.add(log)
        db.commit()
        db.close()
        return

    if log.count >= DAILY_LIMIT:
        db.close()
        raise HTTPException(status_code=429, detail=f"Daily limit of {DAILY_LIMIT} requests reached. Try again tomorrow.")

    log.count += 1
    db.commit()
    db.close()


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
    client_ip = req.client.host
    check_rate_limit(client_ip)

    results = []
    db = SessionLocal()

    for url in request.urls:
        result = analyze_page(url)
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

    response = {"results": results}
    comparison = build_comparison(results)
    if comparison:
        response["comparison"] = comparison

    return response


app.mount("/ui", StaticFiles(directory="static", html=True), name="static")