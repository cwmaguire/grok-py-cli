"""
MCP (Model Context Protocol) Client Models

Pydantic models for MCP schema version 2025-11-25.
Based on: https://github.com/modelcontextprotocol/specification/blob/main/schema/2025-11-25/schema.py
"""

from typing import Union, List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field
from enum import Enum

# Type aliases
RequestId = Union[str, int]

# JSON-RPC 2.0 base models
class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request message"""
    jsonrpc: str = Field("2.0")
    id: RequestId
    method: str
    params: Optional[Dict[str, Any]] = None

class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 response message"""
    jsonrpc: str = Field("2.0")
    id: RequestId
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Union[int, str, Dict[str, Any]]]] = None

class JSONRPCNotification(BaseModel):
    """JSON-RPC 2.0 notification message"""
    jsonrpc: str = Field("2.0")
    method: str
    params: Optional[Dict[str, Any]] = None

# Enums and literals
Role = Literal["user", "assistant", "system"]
TaskStatus = Literal["working", "input_required", "completed", "failed", "cancelled"]

# Annotations
class Annotations(BaseModel):
    """Metadata annotations for resources, tools, etc."""
    audience: Optional[List[Role]] = None
    lastModified: Optional[str] = None
    priority: Optional[int] = None

# Icon model (referenced in Resource)
class Icon(BaseModel):
    """Icon representation"""
    uri: str
    mimeType: Optional[str] = None

# Content block types
class TextContent(BaseModel):
    """Text content block"""
    type: Literal["text"] = "text"
    text: str
    annotations: Optional[Annotations] = None

class ImageContent(BaseModel):
    """Image content block"""
    type: Literal["image"] = "image"
    data: str  # base64 encoded
    mimeType: str
    annotations: Optional[Annotations] = None

class AudioContent(BaseModel):
    """Audio content block"""
    type: Literal["audio"] = "audio"
    data: str  # base64 encoded
    mimeType: str
    annotations: Optional[Annotations] = None

class ToolCallContent(BaseModel):
    """Tool call content block"""
    type: Literal["tool_call"] = "tool_call"
    toolName: str
    args: Optional[Dict[str, Any]] = None
    annotations: Optional[Annotations] = None

class ResourceLink(BaseModel):
    """Resource link content block"""
    type: Literal["resource_link"] = "resource_link"
    uri: str
    title: Optional[str] = None
    description: Optional[str] = None
    mimeType: Optional[str] = None
    annotations: Optional[Annotations] = None

# Union type for content blocks
ContentBlock = Union[TextContent, ImageContent, AudioContent, ToolCallContent, ResourceLink]

# Resource models
class Resource(BaseModel):
    """MCP Resource"""
    name: str
    title: Optional[str] = None
    uri: str
    mimeType: Optional[str] = None
    description: Optional[str] = None
    size: Optional[int] = None
    icons: Optional[List[Icon]] = None
    annotations: Optional[Annotations] = None

class ResourceTemplate(BaseModel):
    """Resource template for dynamic resources"""
    uriTemplate: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None
    annotations: Optional[Annotations] = None

# Tool models
class Tool(BaseModel):
    """MCP Tool"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSONSchema dict per Draft 2020-12
    returns: Optional[Dict[str, Any]] = None  # JSONSchema
    annotations: Optional[Annotations] = None

# Prompt models
class PromptMessage(BaseModel):
    """Message in a prompt"""
    role: Role
    content: ContentBlock

class PromptArgument(BaseModel):
    """Argument for prompt parameterization"""
    name: str
    description: Optional[str] = None
    required: Optional[bool] = None

class Prompt(BaseModel):
    """MCP Prompt"""
    name: str
    description: str
    messages: List[PromptMessage]
    arguments: Optional[List[PromptArgument]] = None
    annotations: Optional[Annotations] = None

# Task models
class Task(BaseModel):
    """MCP Task"""
    taskId: str
    status: TaskStatus
    statusMessage: Optional[str] = None
    createdAt: str
    lastUpdatedAt: str
    ttl: Optional[int] = None
    pollInterval: Optional[int] = None

# Sampling models
class SamplingMessage(BaseModel):
    """Message for sampling"""
    role: Role
    content: ContentBlock

class CreateMessageRequest(BaseModel):
    """Request to create a message via sampling"""
    messages: List[SamplingMessage]
    modelPreferences: Optional[Dict[str, Any]] = None
    systemPrompt: Optional[str] = None
    includeContext: Optional[str] = None
    temperature: Optional[float] = None
    maxTokens: Optional[int] = None
    stopSequences: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

# Capabilities models
class ClientCapabilities(BaseModel):
    """Client capabilities sent during initialization"""
    experimental: Optional[Dict[str, Dict[str, Any]]] = None
    logging: Optional[Dict[str, Any]] = None
    completions: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, bool]] = Field(default_factory=lambda: {"listChanged": True})
    resources: Optional[Dict[str, bool]] = Field(default_factory=lambda: {"subscribe": True, "listChanged": True})
    tools: Optional[Dict[str, bool]] = Field(default_factory=lambda: {"listChanged": True})
    tasks: Optional[Dict[str, Dict[str, Any]]] = Field(default_factory=lambda: {
        "list": {},
        "cancel": {},
        "requests": {"tools": {"call": {}}, "sampling": {"createMessage": {}}}
    })

class ServerCapabilities(BaseModel):
    """Server capabilities received during initialization"""
    experimental: Optional[Dict[str, Dict[str, Any]]] = None
    logging: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    tools: Optional[Dict[str, Any]] = None
    sampling: Optional[Dict[str, Any]] = None

# Initialization models
class ClientInfo(BaseModel):
    """Client information for initialization"""
    name: str
    version: str
    protocolVersion: Optional[str] = "2025-11-25"

class ServerInfo(BaseModel):
    """Server information received during initialization"""
    name: str
    version: str
    protocolVersion: Optional[str] = "2025-11-25"

class InitializeRequest(BaseModel):
    """Initialize request parameters"""
    protocolVersion: str = "2025-11-25"
    capabilities: ClientCapabilities
    clientInfo: ClientInfo

class InitializeResponse(BaseModel):
    """Initialize response result"""
    protocolVersion: str
    capabilities: ServerCapabilities
    serverInfo: ServerInfo
    instructions: Optional[str] = None

# List response models with pagination
class PaginatedResult(BaseModel):
    """Base class for paginated responses"""
    nextCursor: Optional[str] = None

class ListResourcesResult(PaginatedResult):
    """Result for resources/list"""
    resources: List[Resource]

class ListToolsResult(PaginatedResult):
    """Result for tools/list"""
    tools: List[Tool]

class ListPromptsResult(PaginatedResult):
    """Result for prompts/list"""
    prompts: List[Prompt]

class ListTasksResult(PaginatedResult):
    """Result for tasks/list"""
    tasks: List[Task]

# Resource read result
class ReadResourceResult(BaseModel):
    """Result for resources/read"""
    contents: List[ContentBlock]

# Tool call models
class ToolCallRequest(BaseModel):
    """Request parameters for tools/call"""
    name: str
    arguments: Optional[Dict[str, Any]] = None

class ToolCallResult(BaseModel):
    """Result for tools/call"""
    content: List[ContentBlock]
    isError: Optional[bool] = None

# Sampling result
class CreateMessageResult(BaseModel):
    """Result for sampling/createMessage"""
    role: Role
    content: ContentBlock
    model: str
    stopReason: Optional[str] = None

# Error model
class MCPError(BaseModel):
    """MCP error structure"""
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None

# Update forward references for Union types
TextContent.update_forward_refs()
ImageContent.update_forward_refs()
AudioContent.update_forward_refs()
ToolCallContent.update_forward_refs()
ResourceLink.update_forward_refs()