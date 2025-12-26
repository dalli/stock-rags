"""
Individual pipeline tasks for parallel processing.

Each stage of the report processing pipeline is isolated as a separate task
to enable parallel execution and better failure recovery.
"""

import logging
from pathlib import Path
from uuid import UUID

from sqlalchemy import select, update

from app.db.postgres import AsyncSessionLocal, Report
from app.parsers.pdf_parser import pdf_parser
from app.services.extraction_service import get_extraction_service
from app.services.graph_service import get_graph_service
from app.services.vector_service import get_vector_service
from app.workers.celery_app import app

logger = logging.getLogger(__name__)


async def update_report_status(
    report_id: UUID, status: str, error: str = None
) -> None:
    """Update report processing status"""
    async with AsyncSessionLocal() as session:
        stmt = update(Report).where(Report.id == report_id).values(status=status)
        await session.execute(stmt)
        await session.commit()


async def get_report(report_id: UUID) -> Report:
    """Get report from database"""
    async with AsyncSessionLocal() as session:
        stmt = select(Report).where(Report.id == report_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


# ============================================================================
# Step 1: PDF Parsing
# ============================================================================


@app.task(bind=True, name="tasks.parse_pdf")
def parse_pdf_task(self, report_id: str, file_path: str) -> dict:
    """
    Parse PDF file and extract text, metadata, and tables.

    Args:
        report_id: Report UUID
        file_path: Path to uploaded PDF file

    Returns:
        dict: Parsed document data
    """
    import asyncio

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_parse_pdf_async(report_id, file_path))


async def _parse_pdf_async(report_id_str: str, file_path: str) -> dict:
    """Async implementation of PDF parsing"""
    report_id = UUID(report_id_str)

    try:
        await update_report_status(report_id, "parsing_pdf")
        logger.info(f"Parsing PDF: {file_path}")

        pdf_document = pdf_parser.parse_file(Path(file_path))

        # Store parsed data for next task
        result = {
            "report_id": report_id_str,
            "full_text": pdf_document.full_text,
            "metadata": {
                "title": pdf_document.metadata.title,
                "page_count": pdf_document.metadata.page_count,
                "creation_date": (
                    pdf_document.metadata.creation_date.isoformat()
                    if pdf_document.metadata.creation_date
                    else None
                ),
            },
            "pages": [
                {
                    "page_number": page.page_number,
                    "text": page.text,
                    "width": page.width,
                    "height": page.height,
                    "has_images": page.has_images,
                }
                for page in pdf_document.pages
            ],
        }

        logger.info(
            f"PDF parsed successfully: {pdf_document.metadata.page_count} pages"
        )
        return result

    except Exception as e:
        logger.error(f"PDF parsing failed: {e}", exc_info=True)
        await update_report_status(report_id, "failed", error=str(e))
        raise


# ============================================================================
# Step 2: Entity Extraction
# ============================================================================


@app.task(bind=True, name="tasks.extract_entities")
def extract_entities_task(self, parsed_data: dict) -> dict:
    """
    Extract entities from parsed text.

    Args:
        parsed_data: Output from parse_pdf_task

    Returns:
        dict: Entities and parsed data
    """
    import asyncio

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_extract_entities_async(parsed_data))


async def _extract_entities_async(parsed_data: dict) -> dict:
    """Async implementation of entity extraction"""
    report_id = UUID(parsed_data["report_id"])

    try:
        await update_report_status(report_id, "extracting_entities")
        logger.info(f"Extracting entities for report {report_id}")

        extraction_service = get_extraction_service()
        entities = await extraction_service.extract_entities(
            text=parsed_data["full_text"], report_type="stock_analysis"
        )

        result = {
            **parsed_data,
            "entities": entities,
        }

        logger.info(
            f"Entities extracted: {len(entities.get('companies', []))} companies, "
            f"{len(entities.get('industries', []))} industries, "
            f"{len(entities.get('themes', []))} themes"
        )
        return result

    except Exception as e:
        logger.error(f"Entity extraction failed: {e}", exc_info=True)
        await update_report_status(report_id, "failed", error=str(e))
        raise


# ============================================================================
# Step 3: Relationship Extraction
# ============================================================================


@app.task(bind=True, name="tasks.extract_relationships")
def extract_relationships_task(self, data_with_entities: dict) -> dict:
    """
    Extract relationships between entities.

    Args:
        data_with_entities: Output from extract_entities_task

    Returns:
        dict: Relationships and all previous data
    """
    import asyncio

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_extract_relationships_async(data_with_entities))


async def _extract_relationships_async(data_with_entities: dict) -> dict:
    """Async implementation of relationship extraction"""
    report_id = UUID(data_with_entities["report_id"])

    try:
        await update_report_status(report_id, "extracting_relationships")
        logger.info(f"Extracting relationships for report {report_id}")

        extraction_service = get_extraction_service()
        relationships_result = await extraction_service.extract_relations(
            text=data_with_entities["full_text"],
            entities=data_with_entities["entities"],
            report_type="stock_analysis",
        )

        result = {
            **data_with_entities,
            "relationships": relationships_result["relationships"],
        }

        logger.info(
            f"Relationships extracted: {len(relationships_result['relationships'])} relationships"
        )
        return result

    except Exception as e:
        logger.error(f"Relationship extraction failed: {e}", exc_info=True)
        await update_report_status(report_id, "failed", error=str(e))
        raise


# ============================================================================
# Step 4a: Build Knowledge Graph (Parallel with Step 4b)
# ============================================================================


@app.task(bind=True, name="tasks.build_graph")
def build_graph_task(self, extraction_data: dict) -> dict:
    """
    Build knowledge graph in Neo4j.

    Args:
        extraction_data: Output from extract_relationships_task

    Returns:
        dict: Graph statistics
    """
    import asyncio

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_build_graph_async(extraction_data))


async def _build_graph_async(extraction_data: dict) -> dict:
    """Async implementation of graph building"""
    report_id = UUID(extraction_data["report_id"])

    try:
        await update_report_status(report_id, "building_graph")
        logger.info(f"Building knowledge graph for report {report_id}")

        graph_service = await get_graph_service()
        report_title = extraction_data["metadata"]["title"] or "Untitled Report"

        from datetime import datetime

        publish_date = None
        if extraction_data["metadata"]["creation_date"]:
            publish_date = datetime.fromisoformat(
                extraction_data["metadata"]["creation_date"]
            )

        graph_stats = await graph_service.build_graph_from_extraction(
            report_id=report_id,
            report_title=report_title,
            entities=extraction_data["entities"],
            relationships=extraction_data["relationships"],
            publish_date=publish_date,
        )

        logger.info(
            f"Graph built: {graph_stats['nodes_created']} nodes, "
            f"{graph_stats['relationships_created']} relationships"
        )
        return {
            "report_id": str(report_id),
            "graph_stats": graph_stats,
        }

    except Exception as e:
        logger.error(f"Graph building failed: {e}", exc_info=True)
        await update_report_status(report_id, "failed", error=str(e))
        raise


# ============================================================================
# Step 4b: Store Vector Embeddings (Parallel with Step 4a)
# ============================================================================


@app.task(bind=True, name="tasks.store_vectors")
def store_vectors_task(self, extraction_data: dict) -> dict:
    """
    Generate and store vector embeddings in Qdrant.

    Args:
        extraction_data: Output from extract_relationships_task

    Returns:
        dict: Vector storage statistics
    """
    import asyncio

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_store_vectors_async(extraction_data))


async def _store_vectors_async(extraction_data: dict) -> dict:
    """Async implementation of vector storage"""
    report_id = UUID(extraction_data["report_id"])

    try:
        await update_report_status(report_id, "storing_embeddings")
        logger.info(f"Storing vector embeddings for report {report_id}")

        vector_service = await get_vector_service()

        # Reconstruct PDF document for chunking
        from app.parsers.pdf_parser import PDFDocument, PDFMetadata, PDFPage
        from datetime import datetime

        pages = [
            PDFPage(
                page_number=p["page_number"],
                text=p["text"],
                width=p["width"],
                height=p["height"],
                has_images=p["has_images"],
                tables=[],
            )
            for p in extraction_data["pages"]
        ]

        metadata = PDFMetadata(
            title=extraction_data["metadata"]["title"],
            page_count=extraction_data["metadata"]["page_count"],
            creation_date=(
                datetime.fromisoformat(extraction_data["metadata"]["creation_date"])
                if extraction_data["metadata"]["creation_date"]
                else None
            ),
        )

        pdf_document = PDFDocument(
            pages=pages, metadata=metadata, full_text=extraction_data["full_text"]
        )

        # Get primary company ticker
        company_ticker = None
        entities = extraction_data["entities"]
        if entities.get("companies"):
            company_ticker = entities["companies"][0].get("ticker")

        chunks_stored = await vector_service.store_document(
            report_id=report_id,
            pdf_document=pdf_document,
            company_ticker=company_ticker,
            report_type="stock_analysis",
        )

        logger.info(f"Vector embeddings stored: {chunks_stored} chunks")
        return {
            "report_id": str(report_id),
            "chunks_stored": chunks_stored,
        }

    except Exception as e:
        logger.error(f"Vector storage failed: {e}", exc_info=True)
        await update_report_status(report_id, "failed", error=str(e))
        raise


# ============================================================================
# Step 5: Generate Visualization Data
# ============================================================================


@app.task(bind=True, name="tasks.generate_visualization")
def generate_visualization_task(self, parallel_results: list) -> dict:
    """
    Generate graph visualization data.

    Args:
        parallel_results: Results from build_graph and store_vectors tasks (from chord)
            Contains: [graph_result, vector_result]

    Returns:
        dict: Visualization statistics
    """
    import asyncio

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_generate_visualization_async(parallel_results))


async def _generate_visualization_async(parallel_results: list) -> dict:
    """Async implementation of visualization generation"""
    # Extract report_id from parallel results
    graph_result = next((r for r in parallel_results if "graph_stats" in r), {})
    vector_result = next((r for r in parallel_results if "chunks_stored" in r), {})

    report_id_str = graph_result.get("report_id") or vector_result.get("report_id")
    if not report_id_str:
        raise ValueError("Cannot find report_id in parallel results")

    report_id = UUID(report_id_str)

    try:
        await update_report_status(report_id, "generating_visualization")
        logger.info(f"Generating visualization data for report {report_id}")

        from app.services.graph_visualization_service import (
            get_graph_visualization_service,
        )
        from app.db.postgres import Entity

        visualization_service = await get_graph_visualization_service()

        # Fetch entities from database
        async with AsyncSessionLocal() as db:
            entity_stmt = select(Entity).where(Entity.report_id == report_id)
            entity_result = await db.execute(entity_stmt)
            entities_db = entity_result.scalars().all()

            # Prepare entities dict from database
            entities = {
                "companies": [],
                "industries": [],
                "themes": [],
            }

            for entity in entities_db:
                if entity.entity_type == "Company":
                    entities["companies"].append(
                        {
                            "name": entity.name,
                            "ticker": entity.properties.get("ticker")
                            if entity.properties
                            else None,
                            "industry": entity.properties.get("industry")
                            if entity.properties
                            else None,
                            "market": entity.properties.get("market")
                            if entity.properties
                            else None,
                        }
                    )
                elif entity.entity_type == "Industry":
                    entities["industries"].append(
                        {
                            "name": entity.name,
                            "parent_industry": entity.properties.get("parent_industry")
                            if entity.properties
                            else None,
                        }
                    )
                elif entity.entity_type == "Theme":
                    entities["themes"].append(
                        {
                            "name": entity.name,
                            "keywords": entity.properties.get("keywords", [])
                            if entity.properties
                            else [],
                            "description": entity.properties.get("description")
                            if entity.properties
                            else None,
                        }
                    )

            visualization_data = await visualization_service.generate_visualization_data(
                report_id=report_id,
                entities=entities,
                db=db,
            )

        logger.info(
            f"Visualization generated: {visualization_data['stats']['node_count']} nodes, "
            f"{visualization_data['stats']['relationship_count']} relationships"
        )

        # Merge results from parallel tasks
        graph_result = next((r for r in parallel_results if "graph_stats" in r), {})
        vector_result = next((r for r in parallel_results if "chunks_stored" in r), {})

        return {
            "report_id": str(report_id),
            "graph_stats": graph_result.get("graph_stats", {}),
            "chunks_stored": vector_result.get("chunks_stored", 0),
            "visualization_stats": visualization_data["stats"],
        }

    except Exception as e:
        logger.warning(
            f"Visualization generation failed (non-critical): {e}", exc_info=True
        )
        # Continue even if visualization fails
        graph_result = next((r for r in parallel_results if "graph_stats" in r), {})
        vector_result = next((r for r in parallel_results if "chunks_stored" in r), {})

        return {
            "report_id": str(report_id),
            "graph_stats": graph_result.get("graph_stats", {}),
            "chunks_stored": vector_result.get("chunks_stored", 0),
            "visualization_stats": {"node_count": 0, "relationship_count": 0},
        }


# ============================================================================
# Step 6: Finalize Report
# ============================================================================


@app.task(bind=True, name="tasks.finalize_report")
def finalize_report_task(self, final_stats: dict) -> dict:
    """
    Update report metadata and mark as completed.

    Args:
        final_stats: Output from generate_visualization_task

    Returns:
        dict: Final processing statistics
    """
    import asyncio

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_finalize_report_async(final_stats))


async def _finalize_report_async(final_stats: dict) -> dict:
    """Async implementation of report finalization"""
    report_id = UUID(final_stats["report_id"])

    try:
        logger.info(f"Finalizing report {report_id}")

        # Fetch report to get metadata
        async with AsyncSessionLocal() as session:
            report_stmt = select(Report).where(Report.id == report_id)
            report_result = await session.execute(report_stmt)
            report = report_result.scalar_one_or_none()

            if not report:
                raise ValueError(f"Report {report_id} not found")

            # Update report metadata
            stmt = (
                update(Report)
                .where(Report.id == report_id)
                .values(
                    entity_count=final_stats["graph_stats"].get("nodes_created", 0),
                    vector_chunks=final_stats.get("chunks_stored", 0),
                    status="completed",
                )
            )
            await session.execute(stmt)
            await session.commit()

            # Refresh to get updated values
            await session.refresh(report)

        result = {
            "report_id": str(report_id),
            "status": "completed",
            "pages": report.page_count,
            "graph_nodes": final_stats["graph_stats"].get("nodes_created", 0),
            "graph_relationships": final_stats["graph_stats"].get(
                "relationships_created", 0
            ),
            "visualization_nodes": final_stats["visualization_stats"].get(
                "node_count", 0
            ),
            "visualization_relationships": final_stats["visualization_stats"].get(
                "relationship_count", 0
            ),
            "vector_chunks": final_stats.get("chunks_stored", 0),
        }

        logger.info(f"Report processing completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Report finalization failed: {e}", exc_info=True)
        await update_report_status(report_id, "failed", error=str(e))
        raise
