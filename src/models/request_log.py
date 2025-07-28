from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    method = Column(String(10), nullable=False)
    path = Column(String(255), nullable=False)
    client_ip = Column(String(45))
    
    request_headers = Column(Text)
    request_body = Column(Text)
    
    response_status = Column(Integer)
    response_headers = Column(Text)
    response_body = Column(Text)
    
    processing_time = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)