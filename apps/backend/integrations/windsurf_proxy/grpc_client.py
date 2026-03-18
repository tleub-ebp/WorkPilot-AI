"""
Windsurf gRPC Chat Client
==========================

HTTP/2 Connect-protocol client for communicating with the Windsurf language server.
Uses manual protobuf encoding (no .proto files needed) and httpx for HTTP/2.

Ported from opencode-windsurf-auth/src/plugin/grpc-client.ts

Protocol (Connect protocol, NOT raw gRPC):
    Streaming RPCs:
        POST http://localhost:{port}/exa.language_server_pb.LanguageServerService/RawGetChatMessage
        Content-Type: application/connect+proto
        X-Codeium-Csrf-Token: {csrf_token}
        connect-protocol-version: 1

    Unary RPCs:
        Content-Type: application/proto

Message format:
    RawGetChatMessageRequest {
        Field 1: metadata (Metadata message)
        Field 2: chat_messages (repeated ChatMessage)
        Field 3: system_prompt_override (string, optional)
        Field 4: chat_model (enum)
        Field 5: chat_model_name (string, optional)
    }

    ChatMessage {
        Field 1: message_id (string)
        Field 2: source (enum: 1=USER, 2=SYSTEM, 3=ASSISTANT)
        Field 3: timestamp (Timestamp)
        Field 4: conversation_id (string)
        Field 5: intent (ChatMessageIntent) — 3-level nesting:
                  intent(f5) → IntentGeneric(f1) → text(f1)
    }

    RawGetChatMessageResponse {
        Field 1: delta_message (RawChatMessage)
        Field 2: delta_tool_calls (repeated ChatToolCall)
    }

    RawChatMessage {
        Field 5: text (string — direct, NOT nested)
    }
"""

from __future__ import annotations

import json
import logging
import struct
import time
import uuid
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from integrations.windsurf_proxy.auth import WindsurfCredentials

logger = logging.getLogger(__name__)

# Service base path
GRPC_SERVICE_BASE = "/exa.language_server_pb.LanguageServerService"

# RPC endpoint paths
GRPC_SERVICE_PATH = f"{GRPC_SERVICE_BASE}/RawGetChatMessage"
INIT_PANEL_PATH = f"{GRPC_SERVICE_BASE}/InitializeCascadePanelState"

# Chat message source enum
SOURCE_USER = 1
SOURCE_SYSTEM = 2
SOURCE_ASSISTANT = 3

# Protobuf wire types
WIRE_VARINT = 0
WIRE_LENGTH_DELIMITED = 2

# Timeout for chat requests (seconds)
CHAT_TIMEOUT = 120.0

# Whether the cascade panel has been initialized for this session
_panel_initialized = False


# =============================================================================
# Protobuf Encoding Utilities (manual, no protobuf dependency)
# =============================================================================


def _encode_varint(value: int) -> bytes:
    """Encode an integer as a protobuf varint."""
    result = bytearray()
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value & 0x7F)
    return bytes(result)


def _encode_tag(field_number: int, wire_type: int) -> bytes:
    """Encode a protobuf field tag."""
    return _encode_varint((field_number << 3) | wire_type)


def _encode_string_field(field_number: int, value: str) -> bytes:
    """Encode a string as a length-delimited protobuf field."""
    encoded = value.encode("utf-8")
    return _encode_tag(field_number, WIRE_LENGTH_DELIMITED) + _encode_varint(len(encoded)) + encoded


def _encode_bytes_field(field_number: int, value: bytes) -> bytes:
    """Encode raw bytes as a length-delimited protobuf field."""
    return _encode_tag(field_number, WIRE_LENGTH_DELIMITED) + _encode_varint(len(value)) + value


def _encode_varint_field(field_number: int, value: int) -> bytes:
    """Encode a varint (int/enum/bool) protobuf field."""
    return _encode_tag(field_number, WIRE_VARINT) + _encode_varint(value)


def _encode_timestamp() -> bytes:
    """Encode current time as a google.protobuf.Timestamp message.

    Timestamp: { seconds: int64 (field 1), nanos: int32 (field 2) }
    """
    now = time.time()
    seconds = int(now)
    nanos = int((now - seconds) * 1e9)
    return _encode_varint_field(1, seconds) + _encode_varint_field(2, nanos)


# =============================================================================
# Message Building
# =============================================================================


def _build_metadata(credentials: WindsurfCredentials) -> bytes:
    """Build the Metadata protobuf message.

    Real field numbers from extension.js analysis:
        Field 1: ide_name (string)
        Field 2: extension_version (string)
        Field 3: api_key (string)
        Field 4: locale (string)
        Field 5: os (string)
        Field 7: ide_version (string)
        Field 9: request_id (uint64)
        Field 10: session_id (string)
        Field 12: extension_name (string)
        Field 26: plan_name (string)
    """
    from integrations.windsurf_proxy.discovery import get_metadata_fields

    import platform

    fields = get_metadata_fields()
    parts = bytearray()

    parts.extend(_encode_string_field(fields["api_key"], credentials.api_key))
    parts.extend(_encode_string_field(fields["ide_name"], "windsurf"))
    parts.extend(_encode_string_field(fields["ide_version"], credentials.version))
    parts.extend(_encode_string_field(fields["extension_version"], credentials.version))
    parts.extend(_encode_string_field(fields["session_id"], str(uuid.uuid4())))
    parts.extend(_encode_string_field(fields["locale"], "en"))

    # Additional fields that the extension sends (use hardcoded field numbers
    # since discovery.py doesn't track all of them)
    os_name = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(
        platform.system(), "windows"
    )
    # Only add os if not already covered by discovery fields
    if "os" not in fields:
        parts.extend(_encode_string_field(5, os_name))
    parts.extend(_encode_varint_field(9, 1))  # request_id
    parts.extend(_encode_string_field(12, "codeium.windsurf"))  # extension_name
    parts.extend(_encode_string_field(26, "Pro"))  # plan_name

    return bytes(parts)


def _build_chat_message(role: str, content: str, conversation_id: str) -> bytes:
    """Build a ChatMessage protobuf message.

    ChatMessage {
        Field 1: message_id (string)
        Field 2: source (enum: 1=USER, 2=SYSTEM, 3=ASSISTANT)
        Field 3: timestamp (google.protobuf.Timestamp)
        Field 4: conversation_id (string)
        Field 5: intent (ChatMessageIntent) — 3-level nesting
    }

    Intent nesting (from extension.js analysis):
        ChatMessage.intent (f5) = ChatMessageIntent {
            f1: generic (IntentGeneric, oneof)
        }
        IntentGeneric {
            f1: text (string)
        }
    """
    source_map = {
        "user": SOURCE_USER,
        "system": SOURCE_SYSTEM,
        "assistant": SOURCE_ASSISTANT,
    }
    source = source_map.get(role.lower(), SOURCE_USER)

    parts = bytearray()
    parts.extend(_encode_string_field(1, str(uuid.uuid4())))  # message_id
    parts.extend(_encode_varint_field(2, source))  # source enum
    parts.extend(_encode_bytes_field(3, _encode_timestamp()))  # timestamp
    parts.extend(_encode_string_field(4, conversation_id))  # conversation_id

    # 3-level nesting: intent(f5) → IntentGeneric(f1) → text(f1)
    text_field = _encode_string_field(1, content)          # IntentGeneric.text
    intent_generic = _encode_bytes_field(1, text_field)     # ChatMessageIntent.generic
    parts.extend(_encode_bytes_field(5, intent_generic))    # ChatMessage.intent

    return bytes(parts)


def _build_chat_request(
    credentials: WindsurfCredentials,
    messages: list[dict[str, str]],
    model_enum: int,
    model_name: str,
    system_prompt: str | None = None,
) -> bytes:
    """Build the RawGetChatMessageRequest protobuf.

    RawGetChatMessageRequest {
        Field 1: metadata (Metadata)
        Field 2: chat_messages (repeated ChatMessage)
        Field 3: system_prompt_override (string, optional)
        Field 4: chat_model (enum)
        Field 5: chat_model_name (string, optional)
    }
    """
    conversation_id = str(uuid.uuid4())
    parts = bytearray()

    # Field 1: metadata
    metadata = _build_metadata(credentials)
    parts.extend(_encode_bytes_field(1, metadata))

    # Field 2: chat_messages (repeated)
    for msg in messages:
        chat_msg = _build_chat_message(
            role=msg.get("role", "user"),
            content=msg.get("content", ""),
            conversation_id=conversation_id,
        )
        parts.extend(_encode_bytes_field(2, chat_msg))

    # Field 3: system_prompt_override (optional)
    if system_prompt:
        parts.extend(_encode_string_field(3, system_prompt))

    # Field 4: chat_model (enum)
    parts.extend(_encode_varint_field(4, model_enum))

    # Field 5: chat_model_name (string)
    if model_name:
        parts.extend(_encode_string_field(5, model_name))

    return bytes(parts)


def _frame_grpc_message(payload: bytes) -> bytes:
    """Wrap a protobuf payload in gRPC/Connect framing.

    Frame: [compression_flag: 1 byte] [length: 4 bytes big-endian] [payload]
    """
    return struct.pack(">BI", 0, len(payload)) + payload


# =============================================================================
# Response Parsing
# =============================================================================


def _decode_varint(data: bytes, offset: int) -> tuple[int, int]:
    """Decode a protobuf varint starting at offset. Returns (value, new_offset)."""
    value = 0
    shift = 0
    while offset < len(data):
        byte = data[offset]
        value |= (byte & 0x7F) << shift
        offset += 1
        if not (byte & 0x80):
            break
        shift += 7
    return value, offset


def _extract_text_from_response(payload: bytes) -> str:
    """Extract text content from a RawGetChatMessageResponse frame.

    Response structure (from extension.js analysis):
        RawGetChatMessageResponse {
            Field 1: delta_message (RawChatMessage)
            Field 2: delta_tool_calls (repeated ChatToolCall)
        }
        RawChatMessage {
            Field 1: message_id (string)
            Field 2: source (enum)
            Field 3: timestamp (Timestamp)
            Field 4: conversation_id (string)
            Field 5: text (string — DIRECT, not nested)
            Field 6: in_progress (bool)
            Field 7: is_error (bool)
        }
    """
    texts = []
    offset = 0

    while offset < len(payload):
        try:
            tag, new_offset = _decode_varint(payload, offset)
            field_number = tag >> 3
            wire_type = tag & 0x07

            if wire_type == WIRE_VARINT:
                _, new_offset = _decode_varint(payload, new_offset)
                offset = new_offset
            elif wire_type == WIRE_LENGTH_DELIMITED:
                length, new_offset = _decode_varint(payload, new_offset)
                field_data = payload[new_offset : new_offset + length]
                offset = new_offset + length

                # Field 1: delta_message (RawChatMessage)
                if field_number == 1:
                    text = _extract_text_from_raw_chat_message(field_data)
                    if text:
                        texts.append(text)
            elif wire_type == 5:  # 32-bit fixed
                offset = new_offset + 4
            elif wire_type == 1:  # 64-bit fixed
                offset = new_offset + 8
            else:
                break
        except (IndexError, ValueError):
            break

    return "".join(texts)


def _extract_text_from_raw_chat_message(data: bytes) -> str:
    """Extract text from RawChatMessage (field 5 is direct string)."""
    offset = 0
    while offset < len(data):
        try:
            tag, new_offset = _decode_varint(data, offset)
            field_number = tag >> 3
            wire_type = tag & 0x07

            if wire_type == WIRE_VARINT:
                _, new_offset = _decode_varint(data, new_offset)
                offset = new_offset
            elif wire_type == WIRE_LENGTH_DELIMITED:
                length, new_offset = _decode_varint(data, new_offset)
                field_data = data[new_offset : new_offset + length]
                offset = new_offset + length

                # Field 5: text (direct string in RawChatMessage)
                if field_number == 5:
                    try:
                        return field_data.decode("utf-8")
                    except UnicodeDecodeError:
                        pass
            elif wire_type == 5:
                offset = new_offset + 4
            elif wire_type == 1:
                offset = new_offset + 8
            else:
                break
        except (IndexError, ValueError):
            break
    return ""


def _parse_connect_frames(data: bytes) -> list[tuple[int, bytes]]:
    """Parse Connect protocol frames from raw response data.

    Each frame: [flags: 1 byte] [length: 4 bytes BE] [payload: length bytes]
    flags=0x00: data frame, flags=0x02: trailer frame (JSON)
    """
    frames = []
    offset = 0

    while offset + 5 <= len(data):
        flags = data[offset]
        length = struct.unpack(">I", data[offset + 1 : offset + 5])[0]
        offset += 5

        if offset + length > len(data):
            break

        frames.append((flags, data[offset : offset + length]))
        offset += length

    return frames


def _check_connect_trailer(trailer_data: bytes) -> str | None:
    """Check a Connect trailer frame for errors. Returns error message or None."""
    try:
        trailer = json.loads(trailer_data.decode("utf-8"))
        error = trailer.get("error", {})
        if error:
            code = error.get("code", "unknown")
            message = error.get("message", "unknown error")
            return f"{code}: {message}"
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    return None


# =============================================================================
# Panel Initialization
# =============================================================================


async def _ensure_panel_initialized(credentials: WindsurfCredentials) -> None:
    """Call InitializeCascadePanelState if not already done.

    This must be called before RawGetChatMessage to set up the server-side
    Cascade panel state.  Without it, RawGetChatMessage returns
    "failed_precondition: There was an error with your Cascade session".
    """
    global _panel_initialized
    if _panel_initialized:
        return

    try:
        import httpx
    except ImportError:
        raise ImportError("httpx is required for Windsurf gRPC client. Install with: pip install httpx[http2]")

    metadata = _build_metadata(credentials)
    init_req = bytearray()
    init_req.extend(_encode_bytes_field(1, metadata))  # metadata
    init_req.extend(_encode_varint_field(3, 1))         # workspace_trusted = true

    url = f"http://localhost:{credentials.port}{INIT_PANEL_PATH}"
    headers = {
        "content-type": "application/proto",
        "x-codeium-csrf-token": credentials.csrf_token,
        "connect-protocol-version": "1",
    }

    logger.debug(f"[WindsurfGRPC] InitializeCascadePanelState: POST {url}")

    try:
        async with httpx.AsyncClient(http2=True, timeout=15.0) as client:
            resp = await client.post(url, content=bytes(init_req), headers=headers)
            if resp.status_code == 200:
                _panel_initialized = True
                logger.debug("[WindsurfGRPC] Panel initialized successfully")
            else:
                body = resp.content[:300].decode("utf-8", errors="replace")
                raise WindsurfError(
                    f"InitializeCascadePanelState failed (status={resp.status_code}): {body}",
                    WindsurfErrorCode.STREAM_ERROR,
                )
    except WindsurfError:
        raise
    except Exception as e:
        raise WindsurfError(
            f"InitializeCascadePanelState error: {e}",
            WindsurfErrorCode.CONNECTION_FAILED,
            details=e,
        )


# =============================================================================
# Public API
# =============================================================================


async def stream_chat(
    credentials: WindsurfCredentials,
    messages: list[dict[str, str]],
    model_enum: int,
    model_name: str,
    system_prompt: str | None = None,
) -> AsyncIterator[str]:
    """Stream a chat response from the Windsurf language server via Connect protocol.

    Args:
        credentials: Windsurf credentials (csrf_token, port, api_key, version)
        messages: List of message dicts with "role" and "content" keys
        model_enum: ChatModelType enum integer value
        model_name: Model name string (should include MODEL_ prefix)
        system_prompt: Optional system prompt override

    Yields:
        Text chunks from the response as they arrive.

    Raises:
        WindsurfError: On connection or streaming errors.
    """
    from integrations.windsurf_proxy.auth import WindsurfError, WindsurfErrorCode

    try:
        import httpx
    except ImportError:
        raise ImportError("httpx is required for Windsurf gRPC client. Install with: pip install httpx[http2]")

    # Ensure panel is initialized (required for RawGetChatMessage)
    await _ensure_panel_initialized(credentials)

    # Build the protobuf request
    request_payload = _build_chat_request(
        credentials=credentials,
        messages=messages,
        model_enum=model_enum,
        model_name=model_name,
        system_prompt=system_prompt,
    )
    grpc_data = _frame_grpc_message(request_payload)

    url = f"http://localhost:{credentials.port}{GRPC_SERVICE_PATH}"
    headers = {
        # Connect protocol for streaming RPCs (NOT application/grpc!)
        "content-type": "application/connect+proto",
        "x-codeium-csrf-token": credentials.csrf_token,
        "connect-protocol-version": "1",
        "user-agent": "workpilot-windsurf-proxy/1.0",
    }

    logger.debug(f"[WindsurfGRPC] POST {url} (model={model_name}, {len(messages)} messages)")

    try:
        async with httpx.AsyncClient(http2=True, timeout=CHAT_TIMEOUT) as client:
            async with client.stream("POST", url, content=grpc_data, headers=headers) as response:
                if response.status_code != 200:
                    error_body = b""
                    async for chunk in response.aiter_bytes():
                        error_body += chunk
                    raise WindsurfError(
                        f"gRPC request failed with status {response.status_code}: {error_body.decode('utf-8', errors='replace')}",
                        WindsurfErrorCode.CONNECTION_FAILED,
                    )

                # Accumulate response data and parse Connect protocol frames
                buffer = bytearray()
                async for chunk in response.aiter_bytes():
                    buffer.extend(chunk)

                    # Try to parse complete frames from buffer
                    while len(buffer) >= 5:
                        frame_length = struct.unpack(">I", buffer[1:5])[0]
                        total_frame = 5 + frame_length

                        if len(buffer) < total_frame:
                            break  # Wait for more data

                        flags = buffer[0]
                        frame_payload = bytes(buffer[5:total_frame])
                        del buffer[:total_frame]

                        # Check for trailer frames (flags=0x02)
                        if flags == 0x02:
                            error_msg = _check_connect_trailer(frame_payload)
                            if error_msg:
                                # If Cascade session expired, reset panel so next call re-initializes
                                if "failed_precondition" in error_msg.lower():
                                    global _panel_initialized
                                    _panel_initialized = False
                                    logger.info("[WindsurfGRPC] Cascade session expired, panel reset for re-initialization")
                                raise WindsurfError(
                                    f"Windsurf server error: {error_msg}",
                                    WindsurfErrorCode.STREAM_ERROR,
                                )
                            continue

                        # Data frame — extract text from protobuf
                        text = _extract_text_from_response(frame_payload)
                        if text:
                            yield text

    except httpx.ConnectError as e:
        raise WindsurfError(
            f"Failed to connect to Windsurf language server at localhost:{credentials.port}: {e}",
            WindsurfErrorCode.CONNECTION_FAILED,
            details=e,
        )
    except httpx.TimeoutException as e:
        raise WindsurfError(
            f"Windsurf gRPC request timed out after {CHAT_TIMEOUT}s: {e}",
            WindsurfErrorCode.STREAM_ERROR,
            details=e,
        )


async def chat(
    credentials: WindsurfCredentials,
    messages: list[dict[str, str]],
    model_enum: int,
    model_name: str,
    system_prompt: str | None = None,
) -> str:
    """Send a chat request and return the full response text.

    Non-streaming convenience wrapper around stream_chat().
    """
    text_parts = []
    async for chunk in stream_chat(credentials, messages, model_enum, model_name, system_prompt):
        text_parts.append(chunk)
    return "".join(text_parts)
