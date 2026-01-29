"""
Response Parser Module

Handles parsing and formatting of structured responses from Grok API,
including tool calls, JSON responses, markdown content, and various output formats.
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple, Union
from enum import Enum
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.json import JSON
from xml.etree import ElementTree as ET

# Assuming logger is available
try:
    from ..utils.logging import get_logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
else:
    logger = get_logger(__name__)


class ResponseType(Enum):
    """Types of response content."""
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"
    TOOL_CALL = "tool_call"
    CODE = "code"
    ERROR = "error"


class ParsedResponse:
    """Represents a parsed response with metadata."""

    def __init__(
        self,
        content: str,
        response_type: ResponseType,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.content = content
        self.response_type = response_type
        self.tool_calls = tool_calls or []
        self.metadata = metadata or {}


class ResponseParser:
    """
    Parses and formats various types of responses from Grok API.

    Handles structured responses, tool calls, JSON, markdown, and code formatting.
    """

    def __init__(self, console: Console):
        """
        Initialize the response parser.

        Args:
            console: Rich console for display
        """
        self.console = console

        # Regex patterns for parsing
        self.tool_call_pattern = re.compile(
            r'<xai:function_call name="([^"]+)">(.*?)</xai:function_call',
            re.DOTALL
        )
        self.json_pattern = re.compile(r'^\s*[\[{]')
        self.markdown_pattern = re.compile(r'(^|\n)[#*`\-]|^\s*\d+\.')

    def parse_response(self, response: str) -> ParsedResponse:
        """
        Parse a response string and determine its type and structure.

        Args:
            response: Raw response string

        Returns:
            ParsedResponse object with type and formatted content
        """
        try:
            # Check for tool calls first
            tool_calls = self._extract_tool_calls(response)
            if tool_calls:
                return ParsedResponse(
                    content=self._format_tool_calls(tool_calls),
                    response_type=ResponseType.TOOL_CALL,
                    tool_calls=tool_calls
                )

            # Check for JSON
            if self._is_json(response):
                try:
                    parsed_json = json.loads(response)
                    return ParsedResponse(
                        content=self._format_json(parsed_json),
                        response_type=ResponseType.JSON,
                        metadata={"parsed_json": parsed_json}
                    )
                except json.JSONDecodeError:
                    pass

            # Check for markdown
            if self._is_markdown(response):
                return ParsedResponse(
                    content=response,
                    response_type=ResponseType.MARKDOWN
                )

            # Check for code blocks
            if self._contains_code(response):
                return ParsedResponse(
                    content=self._format_code(response),
                    response_type=ResponseType.CODE
                )

            # Default to text
            return ParsedResponse(
                content=response,
                response_type=ResponseType.TEXT
            )

        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return ParsedResponse(
                content=f"Error parsing response: {str(e)}\n\nRaw response:\n{response}",
                response_type=ResponseType.ERROR
            )

    def _extract_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """
        Extract tool calls from response using regex.

        Args:
            response: Response string

        Returns:
            List of tool call dictionaries
        """
        tool_calls = []

        for match in self.tool_call_pattern.finditer(response):
            tool_name = match.group(1)
            params_xml = match.group(2).strip()

            try:
                # Parse XML parameters
                params = self._parse_tool_params(params_xml)
                tool_calls.append({
                    "name": tool_name,
                    "parameters": params
                })
            except Exception as e:
                logger.warning(f"Failed to parse tool call parameters for {tool_name}: {e}")
                tool_calls.append({
                    "name": tool_name,
                    "parameters": {"raw_xml": params_xml}
                })

        return tool_calls

    def _parse_tool_params(self, params_xml: str) -> Dict[str, Any]:
        """
        Parse XML-formatted tool parameters.

        Args:
            params_xml: XML string with parameters

        Returns:
            Dictionary of parameters
        """
        params = {}

        try:
            # Wrap in root element for parsing
            wrapped_xml = f"<params>{params_xml}</params>"
            root = ET.fromstring(wrapped_xml)

            for param in root.findall('parameter'):
                name = param.get('name')
                if name:
                    # Get text content or nested structure
                    if len(param) > 0:
                        # Complex parameter with nested elements
                        params[name] = self._xml_to_dict(param)
                    else:
                        params[name] = param.text or ""

        except ET.ParseError as e:
            logger.warning(f"XML parsing error: {e}")
            # Fallback: extract using regex
            param_pattern = re.compile(r'<parameter name="([^"]+)">(.*?)</parameter', re.DOTALL)
            for match in param_pattern.finditer(params_xml):
                name = match.group(1)
                value = match.group(2).strip()
                params[name] = value

        return params

    def _xml_to_dict(self, element: ET.Element) -> Union[Dict, List, str]:
        """
        Convert XML element to dictionary/list/string.

        Args:
            element: XML element

        Returns:
            Python data structure
        """
        if len(element) == 0:
            return element.text or ""

        # Check if all children have the same tag (list)
        child_tags = [child.tag for child in element]
        if len(set(child_tags)) == 1:
            return [self._xml_to_dict(child) for child in element]

        # Dictionary
        result = {}
        for child in element:
            if child.tag in result:
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(self._xml_to_dict(child))
            else:
                result[child.tag] = self._xml_to_dict(child)

        return result

    def _is_json(self, response: str) -> bool:
        """Check if response appears to be JSON."""
        return bool(self.json_pattern.match(response.strip()))

    def _is_markdown(self, response: str) -> bool:
        """Check if response contains markdown formatting."""
        return bool(self.markdown_pattern.search(response))

    def _contains_code(self, response: str) -> bool:
        """Check if response contains code blocks."""
        return '```' in response or '`' in response

    def _format_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> str:
        """
        Format tool calls for display.

        Args:
            tool_calls: List of tool call dictionaries

        Returns:
            Formatted string
        """
        if not tool_calls:
            return ""

        formatted = []
        for i, call in enumerate(tool_calls, 1):
            name = call.get('name', 'unknown')
            params = call.get('parameters', {})

            formatted.append(f"🔧 Tool Call {i}: {name}")
            if params:
                formatted.append("Parameters:")
                for key, value in params.items():
                    if isinstance(value, (dict, list)):
                        formatted.append(f"  {key}: {json.dumps(value, indent=2)}")
                    else:
                        formatted.append(f"  {key}: {value}")
            formatted.append("")  # Empty line between calls

        return "\n".join(formatted)

    def _format_json(self, data: Any) -> str:
        """
        Format JSON data for display.

        Args:
            data: JSON data

        Returns:
            Formatted JSON string
        """
        return json.dumps(data, indent=2, ensure_ascii=False)

    def _format_code(self, response: str) -> str:
        """
        Format code blocks in response.

        Args:
            response: Response with code blocks

        Returns:
            Response with formatted code
        """
        # Basic code block formatting - could be enhanced
        return response

    def render_parsed_response(self, parsed: ParsedResponse) -> Panel:
        """
        Render a parsed response as a Rich panel.

        Args:
            parsed: ParsedResponse object

        Returns:
            Rich Panel for display
        """
        title_map = {
            ResponseType.TEXT: "Response",
            ResponseType.JSON: "JSON Response",
            ResponseType.MARKDOWN: "Markdown Response",
            ResponseType.TOOL_CALL: "Tool Calls",
            ResponseType.CODE: "Code Response",
            ResponseType.ERROR: "Error"
        }

        border_style_map = {
            ResponseType.TEXT: "blue",
            ResponseType.JSON: "green",
            ResponseType.MARKDOWN: "purple",
            ResponseType.TOOL_CALL: "yellow",
            ResponseType.CODE: "cyan",
            ResponseType.ERROR: "red"
        }

        title = f"[bold]{title_map.get(parsed.response_type, 'Response')}[/bold]"
        border_style = border_style_map.get(parsed.response_type, "blue")

        # Create appropriate content based on type
        if parsed.response_type == ResponseType.JSON:
            content = JSON(parsed.content)
        elif parsed.response_type == ResponseType.MARKDOWN:
            content = Markdown(parsed.content)
        elif parsed.response_type == ResponseType.CODE:
            # Try to detect language from code blocks
            content = self._render_code_content(parsed.content)
        else:
            content = Text(parsed.content)

        return Panel(
            content,
            title=title,
            border_style=border_style,
            title_align="left"
        )

    def _render_code_content(self, content: str) -> Union[Text, Syntax]:
        """
        Render code content with syntax highlighting if possible.

        Args:
            content: Content containing code

        Returns:
            Rich renderable
        """
        # Extract code blocks
        code_block_pattern = re.compile(r'```(\w+)?\n(.*?)\n```', re.DOTALL)
        matches = code_block_pattern.findall(content)

        if matches:
            # Use the first code block for syntax highlighting
            language, code = matches[0]
            if language:
                try:
                    return Syntax(code, language, theme="monokai", line_numbers=True)
                except Exception:
                    pass

        # Fallback to plain text
        return Text(content)

    def extract_summary(self, response: str, max_length: int = 100) -> str:
        """
        Extract a summary of the response for display.

        Args:
            response: Full response text
            max_length: Maximum summary length

        Returns:
            Summary string
        """
        # Remove tool calls for summary
        clean_response = self.tool_call_pattern.sub("", response).strip()

        if len(clean_response) <= max_length:
            return clean_response

        # Find a good break point
        truncated = clean_response[:max_length]
        last_space = truncated.rfind(" ")

        if last_space > max_length * 0.8:
            truncated = truncated[:last_space]

        return truncated + "..."