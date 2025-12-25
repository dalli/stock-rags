"""
Celery task for processing PDF reports.

Handles PDF parsing, entity extraction, graph building, and vector storage.
"""

import logging
from uuid import UUID

from sqlalchemy import select, update

from app.db.postgres import AsyncSessionLocal, Report
from app.parsers.pdf_parser import pdf_parser
from app.services.extraction_service import get_extraction_service
from app.services.graph_service import get_graph_service
from app.services.table_analysis_service import TableAnalysisService
from app.services.vector_service import get_vector_service
from app.workers.celery_app import app

logger = logging.getLogger(__name__)


def _format_table_analysis(table, analysis_result: dict) -> str:
    """Format table analysis result as text"""
    if "error" in analysis_result:
        return f"표 분석 중 오류 발생: {analysis_result.get('error', 'Unknown error')}"

    formatted = []
    formatted.append(analysis_result.get("summary", ""))

    analysis = analysis_result.get("analysis", {})
    if analysis:
        if analysis.get("growth"):
            formatted.append(f"성장성: {analysis['growth']}")
        if analysis.get("profitability"):
            formatted.append(f"수익성: {analysis['profitability']}")
        if analysis.get("valuation"):
            formatted.append(f"밸류에이션: {analysis['valuation']}")

    takeaways = analysis_result.get("key_takeaways", {})
    if takeaways:
        if takeaways.get("positive_signal"):
            formatted.append(f"긍정 신호: {takeaways['positive_signal']}")
        if takeaways.get("risk_factor"):
            formatted.append(f"리스크 요인: {takeaways['risk_factor']}")

    if analysis_result.get("analyst_opinion"):
        formatted.append(f"애널리스트 의견: {analysis_result['analyst_opinion']}")

    return "\n".join(formatted)


@app.task(bind=True, name="process_report")
def process_report_task(self, report_id: str, file_path: str) -> dict:
    """
    Process uploaded PDF report.

    Args:
        report_id: Report UUID
        file_path: Path to uploaded PDF file

    Returns:
        Processing statistics
    """
    import asyncio

    # Run async processing in sync context
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_process_report_async(report_id, file_path))


async def _process_report_async(report_id_str: str, file_path: str) -> dict:
    """Async implementation of report processing"""
    report_id = UUID(report_id_str)

    try:
        logger.info(f"Starting processing for report {report_id}")

        # Step 1: Parse PDF
        await update_report_status(report_id, "parsing_pdf")
        logger.info(f"Parsing PDF: {file_path}")
        from pathlib import Path

        pdf_document = pdf_parser.parse_file(Path(file_path))

        # Step 1.5: Analyze tables and add analysis to document
        if pdf_document.tables:
            await update_report_status(report_id, "analyzing_tables")
            logger.info(f"Analyzing {len(pdf_document.tables)} tables found in document")
            table_analysis_service = TableAnalysisService()

            # Analyze each table and add analysis text to document
            enhanced_pages = []
            for page in pdf_document.pages:
                page_text = page.text
                if page.tables:
                    for table in page.tables:
                        try:
                            # Analyze table
                            analysis_result = await table_analysis_service.analyze_table(table)

                            # Format analysis as text to add after table
                            analysis_text = _format_table_analysis(table, analysis_result)

                            # Find table position in page text and add analysis
                            # For now, append analysis at the end of page text
                            page_text += f"\n\n[표 분석 - 페이지 {table.page_number}, 표 {table.table_index + 1}]\n{analysis_text}"
                        except Exception as e:
                            logger.warning(f"Failed to analyze table on page {table.page_number}: {e}")

                # Update page with enhanced text
                from app.parsers.pdf_parser import PDFPage
                enhanced_pages.append(
                    PDFPage(
                        page_number=page.page_number,
                        text=page_text,
                        width=page.width,
                        height=page.height,
                        has_images=page.has_images,
                        tables=page.tables,
                    )
                )

            # Update document with enhanced pages
            pdf_document.pages = enhanced_pages
            pdf_document.full_text = "\n\n".join(page.text for page in enhanced_pages)

        # Step 2: Extract entities
        await update_report_status(report_id, "extracting_entities")
        logger.info(f"Extracting entities from {pdf_document.metadata.page_count} pages")
        extraction_service = get_extraction_service()

        # Extract entities first
        entities_result = await extraction_service.extract_entities(
            text=pdf_document.full_text, report_type="stock_analysis"
        )
        # entities_result already contains the entities dict (companies, industries, etc.)
        entities = entities_result

        # Step 3: Extract relationships
        await update_report_status(report_id, "extracting_relationships")
        logger.info("Extracting relationships")
        relationships_result = await extraction_service.extract_relations(
            text=pdf_document.full_text,
            entities=entities,
            report_type="stock_analysis"
        )
        relationships = relationships_result["relationships"]

        # Step 4: Build knowledge graph
        await update_report_status(report_id, "building_graph")
        logger.info("Building knowledge graph")
        graph_service = await get_graph_service()

        # Get report title from metadata or entities
        report_title = pdf_document.metadata.title or "Untitled Report"

        graph_stats = await graph_service.build_graph_from_extraction(
            report_id=report_id,
            report_title=report_title,
            entities=entities,
            relationships=relationships,
            publish_date=pdf_document.metadata.creation_date,
        )

        # Step 5: Store vector embeddings
        await update_report_status(report_id, "storing_embeddings")
        logger.info("Generating and storing embeddings")
        vector_service = await get_vector_service()

        # Get primary company ticker if available
        company_ticker = None
        if entities.get("companies"):
            company_ticker = entities["companies"][0]["ticker"]

        chunks_stored = await vector_service.store_document(
            report_id=report_id,
            pdf_document=pdf_document,
            company_ticker=company_ticker,
            report_type="stock_analysis",
        )

        # Step 6: Update report metadata
        await update_report_metadata(
            report_id=report_id,
            title=report_title,
            page_count=pdf_document.metadata.page_count,
            entity_count=graph_stats["nodes_created"],
            vector_chunks=chunks_stored,
            status="completed",
        )

        stats = {
            "report_id": report_id_str,
            "status": "completed",
            "pages": pdf_document.metadata.page_count,
            "entities_found": entities.get("entities_found", {}),
            "graph_nodes": graph_stats["nodes_created"],
            "graph_relationships": graph_stats["relationships_created"],
            "vector_chunks": chunks_stored,
        }

        logger.info(f"Report processing completed: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Report processing failed: {e}", exc_info=True)

        # Update status to failed
        await update_report_status(report_id, "failed", error=str(e))

        return {
            "report_id": report_id_str,
            "status": "failed",
            "error": str(e),
        }


async def update_report_status(
    report_id: UUID, status: str, error: str = None
) -> None:
    """Update report processing status"""
    async with AsyncSessionLocal() as session:
        stmt = (
            update(Report)
            .where(Report.id == report_id)
            .values(status=status)
        )
        await session.execute(stmt)
        await session.commit()


async def update_report_metadata(
    report_id: UUID,
    title: str,
    page_count: int,
    entity_count: int,
    vector_chunks: int,
    status: str,
) -> None:
    """Update report metadata after processing"""
    async with AsyncSessionLocal() as session:
        stmt = (
            update(Report)
            .where(Report.id == report_id)
            .values(
                title=title,
                page_count=page_count,
                entity_count=entity_count,
                vector_chunks=vector_chunks,
                status=status,
            )
        )
        await session.execute(stmt)
        await session.commit()
