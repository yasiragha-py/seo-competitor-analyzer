# SEO Competitor Analyzer

A Python backend that scrapes and analyzes web pages for on-page SEO signals. Built with FastAPI, BeautifulSoup, and SQLAlchemy.

## Features
Fetches HTML via requests and BeautifulSoup. Extracts title, meta description, headings, canonical tags, Open Graph and Twitter Card tags, JSON-LD structured data, and internal/external links. Checks internal links for broken status codes. Computes a readiness score based on heading structure and schema presence. Compares metrics across multiple URLs in a single request. Stores results in SQLite via SQLAlchemy. Enforces a daily rate limit per client IP. Respects robots.txt by default with an override path for authorized checks.

## Stack
Python, FastAPI, Pydantic, BeautifulSoup4, Requests, SQLAlchemy, SQLite, HTML/CSS/JavaScript frontend

## API
POST /analyze accepts a list of URLs and returns per-site metrics plus a comparison summary. GET /quota returns remaining daily requests for the caller.

## Run locally
pip install -r requirements.txt
uvicorn main:app --reload

## Deployment
Configured for Railway with a render.yaml for alternate platforms.

## Contact
Email: aghayasirkhan59@gmail.com
LinkedIn: www.linkedin.com/in/yasir-agha-63a99073

