"""
Reports API endpoints.

Handles PDF upload, processing status, and report management.
"""

import logging
import shutil
from pathlib import Path
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import Report, get_db
from app.parsers.pdf_parser import pdf_parser
from app.workers.tasks.process_report import process_report_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


# Pydantic models
class ReportResponse(BaseModel):
    id: str
    filename: str
    title: Optional[str] = None
    status: str
    page_count: Optional[int] = None
    entity_count: int
    vector_chunks: Optional[int] = None
    created_at: str

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    report_id: str
    filename: str
    status: str
    message: str
    task_id: Optional[str] = None


class StatusResponse(BaseModel):
    report_id: str
    status: str
    title: Optional[str] = None
    page_count: Optional[int] = None
    entity_count: int
    progress: Optional[dict] = None


class ReportsResponse(BaseModel):
    """Response model for list of reports."""

    reports: List[ReportResponse]
    total: int


class GraphInfoResponse(BaseModel):
    """Response model for graph information."""

    report_id: str
    nodes_count: int
    relationships_count: int
    companies: List[dict]
    industries: List[dict]
    themes: List[dict]


class VectorInfoResponse(BaseModel):
    """Response model for vector information."""

    report_id: str
    chunks_count: int
    chunks: List[dict]


@router.post("/upload", response_model=ReportResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_report(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    """
    Upload PDF report for processing.

    The file will be parsed, entities extracted, and knowledge graph built asynchronously.
    """
    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported",
        )

    try:
        # Read file content for hashing
        content = await file.read()
        await file.seek(0)  # Reset for saving

        # Calculate file hash to check for duplicates
        file_hash = pdf_parser.calculate_file_hash(content)

        # Check if file already exists
        stmt = select(Report).where(Report.file_hash == file_hash)
        result = await db.execute(stmt)
        existing_report = result.scalar_one_or_none()

        if existing_report:
            return ReportResponse(
                id=str(existing_report.id),
                filename=existing_report.filename,
                title=existing_report.title,
                status=existing_report.status,
                page_count=existing_report.page_count,
                entity_count=existing_report.entity_count,
                vector_chunks=existing_report.vector_chunks,
                created_at=existing_report.created_at.isoformat(),
            )

        # Create report record
        report_id = uuid4()
        report = Report(
            id=report_id,
            filename=file.filename,
            file_hash=file_hash,
            status="pending",
        )
        db.add(report)
        await db.commit()

        # Save file to disk
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        file_path = upload_dir / f"{report_id}.pdf"

        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Queue processing task
        task = process_report_task.delay(str(report_id), str(file_path))

        logger.info(f"Report {report_id} uploaded, task {task.id} queued")

        # Refresh to get the created report
        await db.refresh(report)

        return ReportResponse(
            id=str(report.id),
            filename=report.filename,
            title=report.title,
            status=report.status,
            page_count=report.page_count,
            entity_count=report.entity_count,
            vector_chunks=report.vector_chunks,
            created_at=report.created_at.isoformat(),
        )

    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}",
        )


@router.get("/{report_id}/status", response_model=StatusResponse)
async def get_report_status(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> StatusResponse:
    """
    Get processing status of a report.
    """
    stmt = select(Report).where(Report.id == report_id)
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    return StatusResponse(
        report_id=str(report.id),
        status=report.status,
        title=report.title,
        page_count=report.page_count,
        entity_count=report.entity_count,
    )


@router.get("", response_model=ReportsResponse)
async def list_reports(
    skip: int = 0,
    limit: int = 20,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> ReportsResponse:
    """
    List all reports with pagination.
    """
    logger.info(f"Listing reports with skip={skip}, limit={limit}, status_filter={status_filter}")

    try:
        # Count total reports
        count_stmt = select(func.count(Report.id))
        if status_filter:
            count_stmt = count_stmt.where(Report.status == status_filter)
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0

        logger.info(f"Total reports count: {total}")

        # Get paginated reports
        stmt = select(Report).order_by(Report.created_at.desc()).offset(skip).limit(limit)

        if status_filter:
            stmt = stmt.where(Report.status == status_filter)

        result = await db.execute(stmt)
        reports = result.scalars().all()

        logger.info(f"Retrieved {len(reports)} reports from database")

        report_list = [
            ReportResponse(
                id=str(r.id),
                filename=r.filename,
                title=r.title,
                status=r.status,
                page_count=r.page_count,
                entity_count=r.entity_count or 0,
                vector_chunks=r.vector_chunks,
                created_at=r.created_at.isoformat(),
            )
            for r in reports
        ]

        response = ReportsResponse(reports=report_list, total=total)
        logger.info(f"Returning response with {len(response.reports)} reports and total={response.total}")

        return response
    except Exception as e:
        logger.error(f"Error listing reports: {e}", exc_info=True)
        # Return empty response on error
        return ReportsResponse(reports=[], total=0)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    """
    Get report details by ID.
    """
    stmt = select(Report).where(Report.id == report_id)
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    return ReportResponse(
        id=str(report.id),
        filename=report.filename,
        title=report.title,
        status=report.status,
        page_count=report.page_count,
        entity_count=report.entity_count,
        created_at=report.created_at.isoformat(),
    )


@router.post("/{report_id}/retry", response_model=ReportResponse)
async def retry_report_processing(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    """
    Retry processing a failed report.
    """
    stmt = select(Report).where(Report.id == report_id)
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    # Check if file exists
    file_path = Path("uploads") / f"{report_id}.pdf"
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file not found",
        )

    # Only allow retry for failed reports
    if report.status not in ["failed", "pending"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry report with status: {report.status}",
        )

    try:
        # Update status to pending
        stmt = (
            update(Report)
            .where(Report.id == report_id)
            .values(status="pending")
        )
        await db.execute(stmt)
        await db.commit()

        # Queue processing task
        task = process_report_task.delay(str(report_id), str(file_path))
        logger.info(f"Report {report_id} retry queued, task {task.id}")

        # Refresh to get updated report
        await db.refresh(report)

        return ReportResponse(
            id=str(report.id),
            filename=report.filename,
            title=report.title,
            status=report.status,
            page_count=report.page_count,
            entity_count=report.entity_count,
            vector_chunks=report.vector_chunks,
            created_at=report.created_at.isoformat(),
        )

    except Exception as e:
        logger.error(f"Retry failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retry failed: {str(e)}",
        )


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a report and all associated data:
    - PDF file (MinIO/local storage)
    - Database records (PostgreSQL)
    - Vector embeddings (Qdrant)
    - Graph data (Neo4j)
    """
    stmt = select(Report).where(Report.id == report_id)
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    try:
        # 1. Delete PDF file
        file_path = Path("uploads") / f"{report_id}.pdf"
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted PDF file: {file_path}")

        # 2. Delete vector embeddings from Qdrant
        try:
            from app.db.qdrant import get_qdrant
            qdrant_client = await get_qdrant()
            deleted_chunks = await qdrant_client.delete_by_report_id(str(report_id))
            logger.info(f"Deleted {deleted_chunks} vector chunks from Qdrant for report {report_id}")
        except Exception as e:
            logger.warning(f"Failed to delete Qdrant vectors for report {report_id}: {e}")

        # 3. Delete graph data from Neo4j
        try:
            from app.services.graph_service import get_graph_service
            graph_service = await get_graph_service()
            graph_stats = await graph_service.delete_report_graph(report_id)
            logger.info(f"Deleted graph data from Neo4j for report {report_id}: {graph_stats}")
        except Exception as e:
            logger.warning(f"Failed to delete Neo4j graph data for report {report_id}: {e}")

        # 4. Delete from database (cascades to entities via foreign key)
        await db.delete(report)
        await db.commit()
        logger.info(f"Deleted report {report_id} from database")

    except Exception as e:
        logger.error(f"Error deleting report {report_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete report: {str(e)}",
        )


@router.get("/{report_id}/file", response_class=FileResponse)
async def get_report_file(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """
    Get PDF file for a report.
    """
    stmt = select(Report).where(Report.id == report_id)
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    file_path = Path("uploads") / f"{report_id}.pdf"
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file not found",
        )

    return FileResponse(
        path=str(file_path),
        filename=report.filename,
        media_type="application/pdf",
    )


@router.get("/{report_id}/graph", response_model=GraphInfoResponse)
async def get_report_graph(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> GraphInfoResponse:
    """
    Get graph information for a report.
    """
    stmt = select(Report).where(Report.id == report_id)
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    try:
        from app.db.neo4j import get_neo4j
        from app.db.postgres import Entity

        neo4j = await get_neo4j()

        # Get entities from PostgreSQL for this report
        entity_stmt = select(Entity).where(Entity.report_id == report_id)
        entity_result = await db.execute(entity_stmt)
        entities = entity_result.scalars().all()

        # Extract entity identifiers
        company_tickers = set()
        industry_names = set()
        theme_names = set()

        for entity in entities:
            if entity.entity_type == "Company":
                ticker = entity.properties.get("ticker") if entity.properties else None
                if ticker:
                    company_tickers.add(ticker)
            elif entity.entity_type == "Industry":
                name = entity.name
                if name:
                    industry_names.add(name)
            elif entity.entity_type == "Theme":
                name = entity.name
                if name:
                    theme_names.add(name)

        # Query Neo4j for these specific entities
        companies = []
        industries = []
        themes = []
        relationships_count = 0

        if company_tickers:
            company_query = """
            MATCH (c:Company)
            WHERE c.ticker IN $tickers
            RETURN c.name as name, c.ticker as ticker, c.industry as industry, c.market as market
            """
            company_results = await neo4j.execute_query(
                company_query, {"tickers": list(company_tickers)}
            )
            companies = [
                {
                    "name": r.get("name"),
                    "ticker": r.get("ticker"),
                    "industry": r.get("industry"),
                    "market": r.get("market"),
                }
                for r in company_results
            ]

        if industry_names:
            industry_query = """
            MATCH (i:Industry)
            WHERE i.name IN $names
            RETURN i.name as name, i.parent_industry as parent_industry
            """
            industry_results = await neo4j.execute_query(
                industry_query, {"names": list(industry_names)}
            )
            industries = [
                {
                    "name": r.get("name"),
                    "parent_industry": r.get("parent_industry"),
                }
                for r in industry_results
            ]

        if theme_names:
            theme_query = """
            MATCH (t:Theme)
            WHERE t.name IN $names
            RETURN t.name as name, t.keywords as keywords, t.description as description
            """
            theme_results = await neo4j.execute_query(theme_query, {"names": list(theme_names)})
            themes = [
                {
                    "name": r.get("name"),
                    "keywords": r.get("keywords", []),
                    "description": r.get("description"),
                }
                for r in theme_results
            ]

        # Count relationships (simplified - count all relationships in the graph)
        rel_query = """
        MATCH ()-[r]-()
        RETURN count(r) as rel_count
        """
        rel_results = await neo4j.execute_query(rel_query)
        relationships_count = rel_results[0].get("rel_count", 0) if rel_results else 0

        # Count nodes
        nodes_count = len(companies) + len(industries) + len(themes) + 1  # +1 for report node

        return GraphInfoResponse(
            report_id=str(report_id),
            nodes_count=nodes_count,
            relationships_count=relationships_count,
            companies=companies,
            industries=industries,
            themes=themes,
        )

    except Exception as e:
        logger.error(f"Failed to get graph info: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get graph info: {str(e)}",
        )


@router.get("/{report_id}/vectors", response_model=VectorInfoResponse)
async def get_report_vectors(
    report_id: UUID,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> VectorInfoResponse:
    """
    Get vector information for a report.
    """
    stmt = select(Report).where(Report.id == report_id)
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    try:
        from app.db.qdrant import get_qdrant
        import httpx
        from app.config import get_settings

        settings = get_settings()
        qdrant_client = await get_qdrant()
        collection_name = "report_chunks"

        # Scroll through vectors for this report
        scroll_url = f"http://{settings.qdrant_host}:{settings.qdrant_port}/collections/{collection_name}/points/scroll"
        
        scroll_payload = {
            "filter": {
                "must": [
                    {
                        "key": "report_id",
                        "match": {"value": str(report_id)}
                    }
                ]
            },
            "limit": limit,
            "with_payload": True,
            "with_vector": False
        }
        
        chunks = []
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(scroll_url, json=scroll_payload, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            
            points = data.get("result", {}).get("points", [])
            for point in points:
                payload = point.get("payload", {})
                chunks.append({
                    "chunk_index": payload.get("chunk_index"),
                    "page_number": payload.get("page_number"),
                    "text_preview": payload.get("text", "")[:200] + "..." if payload.get("text") else "",
                })

        return VectorInfoResponse(
            report_id=str(report_id),
            chunks_count=len(chunks),
            chunks=chunks,
        )

    except Exception as e:
        logger.error(f"Failed to get vector info: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get vector info: {str(e)}",
        )
