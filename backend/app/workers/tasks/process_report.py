"""
Celery task for processing PDF reports.

Orchestrates the parallel processing pipeline using Celery chains and groups.
"""

import logging
from uuid import UUID

from celery import chain, chord, group
from sqlalchemy import select, update

from app.db.postgres import AsyncSessionLocal, Report
from app.workers.celery_app import app

# Import individual pipeline tasks
from app.workers.tasks.pipeline_tasks import (
    build_graph_task,
    extract_entities_task,
    extract_relationships_task,
    finalize_report_task,
    generate_visualization_task,
    parse_pdf_task,
    store_vectors_task,
)

logger = logging.getLogger(__name__)


@app.task(bind=True, name="process_report")
def process_report_task(self, report_id: str, file_path: str) -> dict:
    """
    Orchestrate parallel PDF report processing pipeline.

    Pipeline stages:
    1. Parse PDF (sequential)
    2. Extract entities (sequential)
    3. Extract relationships (sequential)
    4. Build graph + Store vectors (parallel)
    5. Generate visualization (sequential, after parallel tasks)
    6. Finalize report (sequential)

    Args:
        report_id: Report UUID
        file_path: Path to uploaded PDF file

    Returns:
        Processing statistics
    """
    logger.info(f"Starting parallel pipeline for report {report_id}")

    # Build the pipeline using Celery primitives
    # chain: sequential execution (A → B → C)
    # chord: parallel execution with callback (group([A, B]) → callback)

    pipeline = chain(
        # Step 1: Parse PDF
        parse_pdf_task.si(report_id, file_path),

        # Step 2: Extract entities
        extract_entities_task.s(),

        # Step 3: Extract relationships
        extract_relationships_task.s(),

        # Step 4 & 5: Parallel execution (graph + vectors)
        # chord executes tasks in parallel, then calls callback with results
        chord(
            group(
                build_graph_task.s(),
                store_vectors_task.s(),
            ),
            # Step 6: Generate visualization (receives parallel results)
            generate_visualization_task.s(),
        ),

        # Step 7: Finalize report
        finalize_report_task.s(),
    )

    # Execute pipeline asynchronously
    result = pipeline.apply_async()

    logger.info(f"Pipeline initiated for report {report_id}, task chain ID: {result.id}")

    # Return task info (actual results will be available when pipeline completes)
    return {
        "report_id": report_id,
        "status": "processing",
        "pipeline_id": result.id,
    }


# Legacy sequential processing function (kept for reference/fallback)
# The new parallel pipeline is defined above in process_report_task
