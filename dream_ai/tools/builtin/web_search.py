"""Instant-answer web search tool using the standard library only.

Calls the DuckDuckGo Instant Answer endpoint. The tool is disabled by default;
when the network is unreachable it raises a clear :class:`ToolError` instead of
crashing the agent loop.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from ... import __version__
from ...exceptions import ToolError
from ..base import Tool

_TIMEOUT = 10
_ENDPOINT = "https://api.duckduckgo.com/"


class WebSearchTool(Tool):
    """Return a short instant answer and related topic summaries for a query."""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Return a short instant answer and related topic summaries for a search query."

    @property
    def risk(self) -> str:
        return "protected"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query.",
                }
            },
            "required": ["query"],
        }

    def run(self, query: str | None = None, **kwargs: Any) -> str:
        text = (query or "").strip()
        if not text:
            raise ToolError("web_search requires a non-empty 'query' argument.")

        payload = self._fetch(text)
        return self._format(text, payload)

    def _fetch(self, query: str) -> dict[str, Any]:
        params = urllib.parse.urlencode(
            {"q": query, "format": "json", "no_html": "1", "t": "dreamai"}
        )
        url = f"{_ENDPOINT}?{params}"
        request = urllib.request.Request(
            url, headers={"User-Agent": f"DreamAI/{__version__}"}
        )
        try:
            with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # network, timeout, or decode failure
            raise ToolError(f"Web search is currently unavailable: {exc}") from exc
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _format(query: str, payload: dict[str, Any]) -> str:
        lines = [f"Search: {query}"]

        abstract = str(payload.get("AbstractText") or "").strip()
        if abstract:
            lines.append(f"Answer: {abstract}")

        summaries: list[str] = []
        for topic in payload.get("RelatedTopics") or []:
            if isinstance(topic, dict) and topic.get("Text"):
                summaries.append("- " + str(topic["Text"])[:200])
            if len(summaries) == 3:
                break
        lines.extend(summaries)

        if len(lines) == 1:
            lines.append("No instant answer found for this query.")
        return "\n".join(lines)
