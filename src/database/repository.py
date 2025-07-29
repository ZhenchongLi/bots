from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional, List, Dict, Any
from datetime import datetime
import orjson as json

from src.models.request_log import RequestLog


class RequestLogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_log(
        self,
        method: str,
        path: str,
        client_ip: Optional[str] = None,
        request_headers: Optional[Dict[str, str]] = None,
        request_body: Optional[Dict[str, Any]] = None,
        response_status: Optional[int] = None,
        response_headers: Optional[Dict[str, str]] = None,
        response_body: Optional[Dict[str, Any]] = None,
        processing_time: Optional[float] = None,
    ) -> RequestLog:
        log_entry = RequestLog(
            method=method,
            path=path,
            client_ip=client_ip,
            request_headers=json.dumps(request_headers).decode() if request_headers else None,
            request_body=json.dumps(request_body).decode() if request_body else None,
            response_status=response_status,
            response_headers=json.dumps(response_headers).decode() if response_headers else None,
            response_body=json.dumps(response_body).decode() if response_body else None,
            processing_time=processing_time,
        )
        
        self.session.add(log_entry)
        await self.session.commit()
        await self.session.refresh(log_entry)
        return log_entry

    async def get_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        method: Optional[str] = None,
        path_filter: Optional[str] = None,
    ) -> List[RequestLog]:
        query = select(RequestLog).order_by(desc(RequestLog.timestamp))
        
        if method:
            query = query.where(RequestLog.method == method)
        if path_filter:
            query = query.where(RequestLog.path.contains(path_filter))
            
        query = query.limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_log_by_id(self, log_id: int) -> Optional[RequestLog]:
        result = await self.session.execute(
            select(RequestLog).where(RequestLog.id == log_id)
        )
        return result.scalar_one_or_none()