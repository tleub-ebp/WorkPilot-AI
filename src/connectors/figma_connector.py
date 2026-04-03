#!/usr/bin/env python3
"""
Figma API Connector
====================

Bidirectional integration with the Figma API for the Design-to-Code pipeline.

Features:
    - Fetch file/node data (designs, components, styles)
    - Extract design tokens from Figma styles
    - Export images/renders from Figma nodes
    - Post comments back to Figma (code generation status)
    - Bidirectional sync: Figma → Code and Code metadata → Figma

Usage:
    from src.connectors.figma_connector import FigmaConnector

    connector = FigmaConnector(access_token="figma_token")
    file_data = await connector.get_file("file_key")
    image = await connector.export_node_image("file_key", "node_id")
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

FIGMA_API_BASE = "https://api.figma.com/v1"


@dataclass
class FigmaNode:
    """Represents a Figma node (frame, component, etc.)."""
    id: str
    name: str
    type: str
    children: list["FigmaNode"] = field(default_factory=list)
    styles: dict[str, Any] = field(default_factory=dict)
    absolute_bounding_box: dict[str, float] | None = None
    fills: list[dict[str, Any]] = field(default_factory=list)
    strokes: list[dict[str, Any]] = field(default_factory=list)
    effects: list[dict[str, Any]] = field(default_factory=list)
    characters: str | None = None  # For TEXT nodes
    style: dict[str, Any] | None = None  # Typography style


@dataclass
class FigmaDesignToken:
    """A design token extracted from Figma."""
    name: str
    value: str
    category: str  # color, typography, spacing, effect
    figma_style_key: str | None = None


@dataclass
class FigmaExportResult:
    """Result of exporting an image from Figma."""
    node_id: str
    image_url: str
    image_data: str | None = None  # base64
    format: str = "png"
    scale: float = 2.0


class FigmaConnector:
    """
    Connector for bidirectional Figma API integration.

    Supports:
    - Reading file structures and node trees
    - Exporting node images for Vision AI analysis
    - Extracting design tokens from Figma styles
    - Posting comments back to Figma designs
    """

    def __init__(self, access_token: str | None = None):
        self.access_token = access_token or os.getenv("FIGMA_ACCESS_TOKEN", "")
        if not self.access_token:
            logger.warning("No Figma access token provided. Figma operations will fail.")

    @property
    def _headers(self) -> dict[str, str]:
        """HTTP headers for Figma API requests."""
        return {
            "X-Figma-Token": self.access_token,
            "Content-Type": "application/json",
        }

    def is_configured(self) -> bool:
        """Check if the Figma connector is properly configured."""
        return bool(self.access_token)

    # =========================================================================
    # FILE & NODE OPERATIONS
    # =========================================================================

    async def get_file(self, file_key: str) -> dict[str, Any]:
        """
        Get the full Figma file data.

        Args:
            file_key: The Figma file key (from the URL).

        Returns:
            The file data including the document tree.
        """
        import httpx

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(
                f"{FIGMA_API_BASE}/files/{file_key}",
                headers=self._headers,
            )
            response.raise_for_status()
            return response.json()

    async def get_file_nodes(
        self, file_key: str, node_ids: list[str]
    ) -> dict[str, Any]:
        """
        Get specific nodes from a Figma file.

        Args:
            file_key: The Figma file key.
            node_ids: List of node IDs to retrieve.

        Returns:
            Node data for the requested IDs.
        """
        import httpx

        ids_param = ",".join(node_ids)
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(
                f"{FIGMA_API_BASE}/files/{file_key}/nodes",
                headers=self._headers,
                params={"ids": ids_param},
            )
            response.raise_for_status()
            return response.json()

    async def get_file_styles(self, file_key: str) -> dict[str, Any]:
        """
        Get all styles defined in a Figma file.

        Args:
            file_key: The Figma file key.

        Returns:
            Style data including colors, typography, effects.
        """
        import httpx

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(
                f"{FIGMA_API_BASE}/files/{file_key}/styles",
                headers=self._headers,
            )
            response.raise_for_status()
            return response.json()

    # =========================================================================
    # IMAGE EXPORT
    # =========================================================================

    async def export_node_image(
        self,
        file_key: str,
        node_id: str,
        format: str = "png",
        scale: float = 2.0,
    ) -> FigmaExportResult:
        """
        Export a Figma node as an image.

        Args:
            file_key: The Figma file key.
            node_id: The node ID to export.
            format: Image format (png, jpg, svg, pdf).
            scale: Export scale (1x, 2x, 3x, etc.).

        Returns:
            FigmaExportResult with image URL and optionally base64 data.
        """
        import httpx

        async with httpx.AsyncClient(timeout=60) as client:
            # Get the image URL from Figma
            response = await client.get(
                f"{FIGMA_API_BASE}/images/{file_key}",
                headers=self._headers,
                params={
                    "ids": node_id,
                    "format": format,
                    "scale": str(scale),
                },
            )
            response.raise_for_status()
            data = response.json()

            image_url = data.get("images", {}).get(node_id, "")
            if not image_url:
                raise ValueError(f"No image URL returned for node {node_id}")

            # Download the actual image and convert to base64
            import base64

            img_response = await client.get(image_url)
            img_response.raise_for_status()
            image_base64 = base64.b64encode(img_response.content).decode("utf-8")

            return FigmaExportResult(
                node_id=node_id,
                image_url=image_url,
                image_data=image_base64,
                format=format,
                scale=scale,
            )

    async def export_multiple_nodes(
        self,
        file_key: str,
        node_ids: list[str],
        format: str = "png",
        scale: float = 2.0,
    ) -> list[FigmaExportResult]:
        """Export multiple Figma nodes as images."""
        import httpx

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(
                f"{FIGMA_API_BASE}/images/{file_key}",
                headers=self._headers,
                params={
                    "ids": ",".join(node_ids),
                    "format": format,
                    "scale": str(scale),
                },
            )
            response.raise_for_status()
            data = response.json()

            results = []
            images = data.get("images", {})
            for nid in node_ids:
                url = images.get(nid, "")
                results.append(FigmaExportResult(
                    node_id=nid,
                    image_url=url,
                    format=format,
                    scale=scale,
                ))
            return results

    # =========================================================================
    # DESIGN TOKEN EXTRACTION
    # =========================================================================

    async def extract_design_tokens(self, file_key: str) -> list[FigmaDesignToken]:
        """
        Extract design tokens from a Figma file's styles.

        Extracts colors, typography, effects, and grids.

        Args:
            file_key: The Figma file key.

        Returns:
            List of extracted design tokens.
        """
        tokens: list[FigmaDesignToken] = []

        try:
            styles_data = await self.get_file_styles(file_key)
            meta_styles = styles_data.get("meta", {}).get("styles", [])

            for style in meta_styles:
                style_type = style.get("style_type", "")
                name = style.get("name", "unknown")
                key = style.get("key", "")

                if style_type == "FILL":
                    tokens.append(FigmaDesignToken(
                        name=self._to_token_name(name),
                        value="",  # Will be resolved from node data
                        category="color",
                        figma_style_key=key,
                    ))
                elif style_type == "TEXT":
                    tokens.append(FigmaDesignToken(
                        name=self._to_token_name(name),
                        value="",
                        category="typography",
                        figma_style_key=key,
                    ))
                elif style_type == "EFFECT":
                    tokens.append(FigmaDesignToken(
                        name=self._to_token_name(name),
                        value="",
                        category="effect",
                        figma_style_key=key,
                    ))
                elif style_type == "GRID":
                    tokens.append(FigmaDesignToken(
                        name=self._to_token_name(name),
                        value="",
                        category="spacing",
                        figma_style_key=key,
                    ))

            # Resolve token values from the file data
            if tokens:
                tokens = await self._resolve_token_values(file_key, tokens)

        except Exception as e:
            logger.error(f"Failed to extract Figma design tokens: {e}")

        logger.info(f"Extracted {len(tokens)} design tokens from Figma file {file_key}")
        return tokens

    async def _resolve_token_values(
        self, file_key: str, tokens: list[FigmaDesignToken]
    ) -> list[FigmaDesignToken]:
        """Resolve actual values for design tokens by reading the file."""
        try:
            file_data = await self.get_file(file_key)
            styles = file_data.get("styles", {})

            # Build a map of style keys to their definitions
            for token in tokens:
                if token.figma_style_key and token.figma_style_key in styles:
                    style_info = styles[token.figma_style_key]
                    # The actual value requires traversing the document tree
                    # For now, store the style name as reference
                    if not token.value:
                        token.value = f"figma:{style_info.get('name', token.name)}"

        except Exception as e:
            logger.warning(f"Could not resolve Figma token values: {e}")

        return tokens

    # =========================================================================
    # COMMENTS (Bidirectional Sync)
    # =========================================================================

    async def post_comment(
        self,
        file_key: str,
        message: str,
        node_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Post a comment on a Figma file or specific node.

        Used for bidirectional sync: notify designers that code has been generated.

        Args:
            file_key: The Figma file key.
            message: The comment text.
            node_id: Optional node ID to attach the comment to.

        Returns:
            The created comment data.
        """
        import httpx

        payload: dict[str, Any] = {"message": message}
        if node_id:
            # Figma expects client_meta with node_id for positioned comments
            payload["client_meta"] = {"node_id": node_id}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{FIGMA_API_BASE}/files/{file_key}/comments",
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def get_comments(self, file_key: str) -> list[dict[str, Any]]:
        """Get all comments on a Figma file."""
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{FIGMA_API_BASE}/files/{file_key}/comments",
                headers=self._headers,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("comments", [])

    # =========================================================================
    # COMPONENT LISTING
    # =========================================================================

    async def get_file_components(self, file_key: str) -> list[dict[str, Any]]:
        """
        Get all components defined in a Figma file.

        Returns:
            List of component metadata (name, id, description, etc.).
        """
        import httpx

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(
                f"{FIGMA_API_BASE}/files/{file_key}/components",
                headers=self._headers,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("meta", {}).get("components", [])

    # =========================================================================
    # HELPERS
    # =========================================================================

    @staticmethod
    def _to_token_name(figma_name: str) -> str:
        """Convert a Figma style name to a design token name."""
        # Figma names: "Color/Primary/500" → "color-primary-500"
        return (
            figma_name.lower()
            .replace("/", "-")
            .replace(" ", "-")
            .replace("_", "-")
            .strip("-")
        )

    @staticmethod
    def parse_figma_url(url: str) -> dict[str, str] | None:
        """
        Parse a Figma URL to extract file key and optional node ID.

        Supports:
            https://www.figma.com/file/FILE_KEY/Title
            https://www.figma.com/file/FILE_KEY/Title?node-id=NODE_ID
            https://www.figma.com/design/FILE_KEY/Title?node-id=NODE_ID

        Returns:
            Dict with 'file_key' and optionally 'node_id', or None.
        """
        import re

        # Match Figma file URLs
        pattern = r"figma\.com/(?:file|design)/([a-zA-Z0-9]+)"
        match = re.search(pattern, url)
        if not match:
            return None

        result: dict[str, str] = {"file_key": match.group(1)}

        # Extract node-id from query params
        node_pattern = r"node-id=([^&]+)"
        node_match = re.search(node_pattern, url)
        if node_match:
            result["node_id"] = node_match.group(1).replace("%3A", ":")

        return result
