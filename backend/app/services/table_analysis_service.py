"""
Table Analysis Service

Uses LLM to analyze financial tables from stock reports.
"""

import json
import logging
from typing import Any, Optional

from app.llm.router import get_llm_router
from app.prompts.loader import get_prompt_loader
from app.parsers.pdf_parser import PDFTable

logger = logging.getLogger(__name__)


class TableAnalysisService:
    """
    Service for analyzing financial tables from PDF reports.

    Uses prompt templates and LLM providers to analyze table data
    and generate insights for investors.
    """

    def __init__(self) -> None:
        self.prompt_loader = get_prompt_loader()
        self.llm_router = get_llm_router()

    def _detect_table_type(self, table: PDFTable) -> str:
        """
        Detect table type based on content

        Args:
            table: PDFTable object

        Returns:
            Table type string (financial, valuation, performance, etc.)
        """
        if not table.data or len(table.data) < 2:
            return "general"

        # Check first row for headers
        headers = [str(cell).lower() for cell in table.data[0] if cell]

        # Financial indicators
        financial_keywords = ["매출", "영업이익", "순이익", "revenue", "operating", "net income", "sales"]
        valuation_keywords = ["per", "pbr", "ev/ebitda", "psr", "배수", "multiple"]
        performance_keywords = ["성장률", "growth", "변동", "change", "전년", "yoy", "qoq"]

        header_text = " ".join(headers)

        if any(keyword in header_text for keyword in financial_keywords):
            if any(keyword in header_text for keyword in valuation_keywords):
                return "valuation"
            return "financial"
        elif any(keyword in header_text for keyword in performance_keywords):
            return "performance"
        else:
            return "general"

    async def analyze_table(
        self,
        table: PDFTable,
        table_type: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Analyze a financial table and generate insights.

        Args:
            table: PDFTable object to analyze
            table_type: Type of table (None = auto-detect)
            provider: LLM provider to use (None = default)
            model: LLM model to use (None = default)

        Returns:
            Dictionary containing analysis results
        """
        try:
            # Auto-detect table type if not provided
            if table_type is None:
                table_type = self._detect_table_type(table)

            # Convert table to markdown format
            from app.parsers.pdf_parser import pdf_parser

            table_markdown = pdf_parser.table_to_markdown(table)
            table_json = pdf_parser.table_to_json(table)

            # Use markdown for readability, but also include JSON for structured data
            table_data = f"Markdown Format:\n{table_markdown}\n\nJSON Format:\n{json.dumps(table_json, ensure_ascii=False, indent=2)}"

            # Load and render prompt template
            template = self.prompt_loader.load("reasoning/table_analysis.yaml")
            system_prompt, user_prompt = template.render(
                table_data=table_data,
                table_type=table_type,
            )

            # Get LLM provider
            llm_provider = self.llm_router.get_provider(provider, model)

            # Get output schema from template
            output_schema = template.output_schema

            # Call LLM with structured output
            logger.info(f"Analyzing table from page {table.page_number}, type: {table_type}")
            analysis_result = await llm_provider.generate_structured(
                prompt=user_prompt,
                system_prompt=system_prompt,
                schema=output_schema,
            )

            # Add metadata
            analysis_result["table_metadata"] = {
                "page_number": table.page_number,
                "table_index": table.table_index,
                "table_type": table_type,
            }

            logger.info(f"Table analysis completed for page {table.page_number}")
            return analysis_result

        except Exception as e:
            logger.error(f"Table analysis failed: {e}", exc_info=True)
            # Return error result
            return {
                "error": str(e),
                "summary": "표 분석 중 오류가 발생했습니다.",
                "analysis": {
                    "growth": "",
                    "profitability": "",
                    "valuation": "",
                },
                "key_takeaways": {
                    "positive_signal": "",
                    "risk_factor": "",
                },
                "analyst_opinion": "",
                "table_metadata": {
                    "page_number": table.page_number,
                    "table_index": table.table_index,
                    "table_type": table_type or "unknown",
                },
            }

