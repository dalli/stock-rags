"""
Entity and Relationship Extraction Service

Uses LLM to extract structured information from financial reports.
"""

import json
import logging
from typing import Any, Optional

from app.llm.router import get_llm_router
from app.prompts.loader import get_prompt_loader

logger = logging.getLogger(__name__)


class ExtractionService:
    """
    Service for extracting entities and relationships from financial text.

    Uses prompt templates and LLM providers to parse unstructured text
    into structured entities and relationships for knowledge graph.
    """

    def __init__(self) -> None:
        self.prompt_loader = get_prompt_loader()
        self.llm_router = get_llm_router()

    async def extract_entities(
        self,
        text: str,
        report_type: str = "stock_analysis",
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Extract entities from financial text.

        Args:
            text: Text content to extract entities from
            report_type: Type of report (stock_analysis, industry, macro)
            provider: LLM provider to use (None = default)
            model: LLM model to use (None = default)

        Returns:
            Dictionary containing extracted entities
        """
        try:
            # Load and render prompt template
            template = self.prompt_loader.load("extraction/entity_extraction.yaml")
            system_prompt, user_prompt = template.render(text=text, report_type=report_type)

            # Get output schema for structured generation
            output_schema = template.output_schema

            # Get LLM provider
            llm = self.llm_router.get_provider(provider, model)

            logger.info(
                f"Extracting entities using {llm.provider_name}/{llm.model_name} "
                f"from {len(text)} chars"
            )

            # Generate structured output
            result = await llm.generate_structured(
                prompt=user_prompt, system_prompt=system_prompt, schema=output_schema
            )

            # Log extraction statistics
            entities_found = result.get("entities_found", {})
            logger.info(f"Extracted entities: {entities_found}")

            return result

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}", exc_info=True)
            raise

    async def extract_relations(
        self,
        text: str,
        entities: dict[str, Any],
        report_type: str = "stock_analysis",
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Extract relationships between entities in financial text.

        Args:
            text: Text content to extract relationships from
            entities: Previously extracted entities
            report_type: Type of report
            provider: LLM provider to use
            model: LLM model to use

        Returns:
            Dictionary containing extracted relationships
        """
        try:
            # Convert entities to JSON string for prompt
            entities_json = json.dumps(entities, indent=2, ensure_ascii=False)

            # Load and render prompt template
            template = self.prompt_loader.load("extraction/relation_extraction.yaml")
            system_prompt, user_prompt = template.render(
                text=text, entities=entities_json, report_type=report_type
            )

            # Get output schema
            output_schema = template.output_schema

            # Get LLM provider
            llm = self.llm_router.get_provider(provider, model)

            logger.info(
                f"Extracting relationships using {llm.provider_name}/{llm.model_name}"
            )

            # Generate structured output
            result = await llm.generate_structured(
                prompt=user_prompt, system_prompt=system_prompt, schema=output_schema
            )

            # Log extraction statistics
            relationships_found = result.get("relationships_found", 0)
            logger.info(f"Extracted {relationships_found} relationships")

            return result

        except Exception as e:
            logger.error(f"Relation extraction failed: {e}", exc_info=True)
            raise

    async def extract_all(
        self,
        text: str,
        report_type: str = "stock_analysis",
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Extract both entities and relationships from text.
        """
        # Extract entities first
        entities = await self.extract_entities(text, report_type, provider, model)

        # Extract relationships based on entities
        relationships = await self.extract_relations(text, entities, report_type, provider, model)

        return {"entities": entities, "relationships": relationships}


# Global service instance
_extraction_service: Optional[ExtractionService] = None


def get_extraction_service() -> ExtractionService:
    """Get global extraction service instance."""
    global _extraction_service
    if _extraction_service is None:
        _extraction_service = ExtractionService()
    return _extraction_service
