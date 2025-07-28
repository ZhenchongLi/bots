from typing import Optional, List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models
import json
import hashlib
from src.config.settings import settings


class VectorStore:
    def __init__(self):
        self.client: Optional[QdrantClient] = None
        self.collection_name = "request_logs"
        
        if settings.qdrant_url:
            self.client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key,
            )
    
    async def init_collection(self):
        if not self.client:
            return
            
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                # Create collection for storing request/response embeddings
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=1536,  # OpenAI text-embedding-ada-002 dimension
                        distance=models.Distance.COSINE,
                    ),
                )
        except Exception as e:
            print(f"Failed to initialize Qdrant collection: {e}")
    
    async def store_request_log(
        self,
        log_id: int,
        request_data: Dict[str, Any],
        response_data: Dict[str, Any],
        embedding: Optional[List[float]] = None,
    ):
        if not self.client or not embedding:
            return
            
        try:
            # Create payload with request/response data
            payload = {
                "log_id": log_id,
                "request_method": request_data.get("method"),
                "request_path": request_data.get("path"),
                "response_status": response_data.get("status"),
                "timestamp": request_data.get("timestamp"),
                "request_summary": self._create_text_summary(request_data),
                "response_summary": self._create_text_summary(response_data),
            }
            
            # Generate unique point ID
            point_id = self._generate_point_id(log_id)
            
            # Store in Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload,
                    )
                ],
            )
        except Exception as e:
            print(f"Failed to store in Qdrant: {e}")
    
    async def search_similar_requests(
        self,
        query_embedding: List[float],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        if not self.client:
            return []
            
        try:
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
            )
            
            return [
                {
                    "log_id": hit.payload["log_id"],
                    "score": hit.score,
                    "request_summary": hit.payload["request_summary"],
                    "response_summary": hit.payload["response_summary"],
                    "timestamp": hit.payload["timestamp"],
                }
                for hit in search_result
            ]
        except Exception as e:
            print(f"Failed to search in Qdrant: {e}")
            return []
    
    def _create_text_summary(self, data: Dict[str, Any]) -> str:
        # Create a text summary of request/response for embedding
        if "method" in data and "path" in data:
            # Request data
            method = data.get("method", "")
            path = data.get("path", "")
            body = data.get("body", {})
            return f"{method} {path} {json.dumps(body) if body else ''}"
        else:
            # Response data
            status = data.get("status", "")
            body = data.get("body", {})
            return f"Status: {status} {json.dumps(body) if body else ''}"
    
    def _generate_point_id(self, log_id: int) -> str:
        # Generate unique point ID based on log ID
        return hashlib.sha256(f"log_{log_id}".encode()).hexdigest()[:16]