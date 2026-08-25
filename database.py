from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

engine = create_engine("sqlite:///seo_data.db")
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class SEOResult(Base):
    __tablename__ = "seo_results"

    id = Column(Integer, primary_key=True)
    url = Column(String)
    title = Column(String)
    word_count = Column(Integer)
    internal_links_count = Column(Integer)
    external_links_count = Column(Integer)
    images_count = Column(Integer)
    images_missing_alt = Column(Integer)
    schemas = Column(Text)


class RequestLog(Base):
    __tablename__ = "request_log"

    id = Column(Integer, primary_key=True)
    ip = Column(String)
    date = Column(String)
    count = Column(Integer, default=1)


Base.metadata.create_all(engine)