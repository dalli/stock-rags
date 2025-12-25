"""Qdrant vector database connection and utilities."""

from typing import Any, Dict, List, Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import get_settings

settings = get_settings()


class QdrantClient:
    """Qdrant client for vector database operations."""

    def __init__(self) -> None:
        """Initialize Qdrant client."""
        self.client: Optional[AsyncQdrantClient] = None
        self.collection_name = "report_chunks"

    async def connect(self) -> None:
        """Connect to Qdrant database."""
        self.client = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )

    async def close(self) -> None:
        """Close Qdrant connection."""
        if self.client:
            await self.client.close()

    async def create_collection(self) -> None:
        """Create report_chunks collection if it doesn't exist."""
        if not self.client:
            await self.connect()

        collections = await self.client.get_collections()
        collection_names = [c.name for c in collections.collections]

        if self.collection_name not in collection_names:
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=settings.embedding_dimension,
                    distance=Distance.COSINE,
                ),
            )

    async def insert_vectors(
        self,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
    ) -> None:
        """Insert vectors with payloads."""
        if not self.client:
            await self.connect()

        if ids is None:
            import uuid

            ids = [str(uuid.uuid4()) for _ in vectors]

        points = [
            PointStruct(id=id_, vector=vector, payload=payload)
            for id_, vector, payload in zip(ids, vectors, payloads)
        ]

        await self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

    async def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors."""
        if not self.client:
            await self.connect()

        # For Qdrant 1.7.4 compatibility, use HTTP API directly
        # The query_points method may not be available in older server versions
        import httpx
        
        url = f"http://{settings.qdrant_host}:{settings.qdrant_port}/collections/{self.collection_name}/points/search"
        
        payload = {
            "vector": query_vector,
            "limit": limit,
            "score_threshold": score_threshold,
        }
        
        if filters:
            payload["filter"] = filters

        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(url, json=payload, timeout=30.0)
            response.raise_for_status()
            data = response.json()

        return [
            {
                "id": result.get("id"),
                "score": result.get("score"),
                "payload": result.get("payload", {}),
            }
            for result in data.get("result", [])
        ]

    async def delete_by_report_id(self, report_id: str) -> int:
        """Delete all vectors for a specific report_id.
        
        Args:
            report_id: Report ID to delete vectors for
            
        Returns:
            Number of vectors deleted
        """
        if not self.client:
            await self.connect()

        # For Qdrant 1.7.4 compatibility, use HTTP API directly
        import httpx
        
        # First, search for all points with this report_id to get their IDs
        scroll_url = f"http://{settings.qdrant_host}:{settings.qdrant_port}/collections/{self.collection_name}/points/scroll"
        
        scroll_payload = {
            "filter": {
                "must": [
                    {
                        "key": "report_id",
                        "match": {"value": report_id}
                    }
                ]
            },
            "limit": 1000,
            "with_payload": False,
            "with_vector": False
        }
        
        deleted_count = 0
        async with httpx.AsyncClient() as http_client:
            while True:
                response = await http_client.post(scroll_url, json=scroll_payload, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                
                points = data.get("result", {}).get("points", [])
                if not points:
                    break
                
                # Extract point IDs
                point_ids = [point.get("id") for point in points if point.get("id")]
                
                if point_ids:
                    # Delete points
                    delete_url = f"http://{settings.qdrant_host}:{settings.qdrant_port}/collections/{self.collection_name}/points/delete"
                    delete_payload = {"points": point_ids}
                    
                    delete_response = await http_client.post(delete_url, json=delete_payload, timeout=30.0)
                    delete_response.raise_for_status()
                    deleted_count += len(point_ids)
                
                # Check if there are more points
                if not data.get("result", {}).get("next_page_offset"):
                    break
                
                scroll_payload["offset"] = data["result"]["next_page_offset"]
        
        return deleted_count

    async def check_health(self) -> bool:
        """Check Qdrant connection health."""
        try:
            if not self.client:
                await self.connect()
            await self.client.get_collections()
            return True
        except Exception:
            return False


# Global client instance
qdrant_client = QdrantClient()


async def get_qdrant() -> QdrantClient:
    """Get Qdrant client instance."""
    if not qdrant_client.client:
        await qdrant_client.connect()
    return qdrant_client
