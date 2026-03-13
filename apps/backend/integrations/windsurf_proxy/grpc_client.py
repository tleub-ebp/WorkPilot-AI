"""
Windsurf gRPC Chat Client
==========================

HTTP/2 gRPC client for communicating with the Windsurf language server.
Uses manual protobuf encoding (no .proto files needed) and httpx for HTTP/2.

Ported from opencode-windsurf-auth/src/plugin/grpc-client.ts

Protocol:
    POST http://localhost:{port}/exa.language_server_pb.LanguageServerService/RawGetChatMessage
    Content-Type: application/grpc
    X-Codeium-Csrf-Token: {csrf_token}
    connect-protocol-version: 1

Message format:
    RawGetChatMessageRequest {
        Field 1: metadata (Metadata message)
        Field 2: chat_messages (repeated ChatMessage)
        Field 3: system_prompt_override (string, optional)
        Field 4: chat_model (enum)
        Field 5: chat_model_name (string, optional)
    }
"""

from __future__ import annotations

import logging
import struct
import time
import uuid
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from integrations.windsurf_proxy.auth import WindsurfCredentials

logger = logging.getLogger(__name__)

# gRPC endpoint path
GRPC_SERVICE_PATH = "/exa.language_server_pb.LanguageServerService/RawGetChatMessage"

# Chat message source enum
SOURCE_USER = 1
SOURCE_SYSTEM = 2
SOURCE_ASSISTANT = 3

# Protobuf wire types
WIRE_VARINT = 0
WIRE_LENGTH_DELIMITED = 2

# Timeout for chat requests (seconds)
CHAT_TIMEOUT = 120.0


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

    Metadata {
        Field 1: api_key (string)
        Field 2: ide_name (string)
        Field 3: ide_version (string)
        Field 4: extension_version (string)
        Field 5: session_id (string)
        Field 6: locale (string)
    }
    """
    from integrations.windsurf_proxy.discovery import get_metadata_fields

    fields = get_metadata_fields()
    parts = bytearray()

    parts.extend(_encode_string_field(fields["api_key"], credentials.api_key))
    parts.extend(_encode_string_field(fields["ide_name"], "windsurf"))
    parts.extend(_encode_string_field(fields["ide_version"], credentials.version))
    parts.extend(_encode_string_field(fields["extension_version"], credentials.version))
    parts.extend(_encode_string_field(fields["session_id"], str(uuid.uuid4())))
    parts.extend(_encode_string_field(fields["locale"], "en"))

    return bytes(parts)


def _build_chat_message(role: str, content: str, conversation_id: str) -> bytes:
    """Build a ChatMessage protobuf message.

    ChatMessage {
        Field 1: message_id (string)
        Field 2: source (enum: 1=USER, 2=SYSTEM, 3=ASSISTANT)
        Field 3: timestamp (google.protobuf.Timestamp)
        Field 4: conversation_id (string)
        Field 5: content (string — UserChatMessage.text / SystemChatMessage.text)
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

    # Content is a nested message — for user messages it's UserChatMessage { text: field 1 }
    # We encode the text as a sub-message in field 5
    inner_content = _encode_string_field(1, content)
    parts.extend(_encode_bytes_field(5, inner_content))

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
    """Wrap a protobuf payload in gRPC framing.

    gRPC frame: [compression_flag: 1 byte] [length: 4 bytes big-endian] [payload]
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
    """Extract text content from a RawChatMessage response.

    RawChatMessage contains the response text in field 5 (bot_message → text).
    We do a simple scan for string fields that contain the actual text content.
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

                # Field 5 in RawChatMessage is the bot_message
                # Inside that, field 1 is the text content
                if field_number == 5:
                    # Try to extract text from nested message
                    inner_text = _extract_inner_text(field_data)
                    if inner_text:
                        texts.append(inner_text)
            elif wire_type == 5:  # 32-bit fixed
                offset = new_offset + 4
            elif wire_type == 1:  # 64-bit fixed
                offset = new_offset + 8
            else:
                break
        except (IndexError, ValueError):
            break

    return "".join(texts)


def _extract_inner_text(data: bytes) -> str:
    """Extract text from a nested protobuf message (BotChatMessage → text field)."""
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

                # Field 1 in BotChatMessage is typically the text
                if field_number == 1:
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


def _parse_grpc_frames(data: bytes) -> list[bytes]:
    """Parse gRPC frames from raw response data.

    Each frame: [compression: 1 byte] [length: 4 bytes BE] [payload: length bytes]
    """
    frames = []
    offset = 0

    while offset + 5 <= len(data):
        _compression = data[offset]
        length = struct.unpack(">I", data[offset + 1 : offset + 5])[0]
        offset += 5

        if offset + length > len(data):
            break

        frames.append(data[offset : offset + length])
        offset += length

    return frames


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
    """Stream a chat response from the Windsurf language server via gRPC.

    Args:
        credentials: Windsurf credentials (csrf_token, port, api_key, version)
        messages: List of message dicts with "role" and "content" keys
        model_enum: ChatModelType enum integer value
        model_name: Model name string for gRPC
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
        "content-type": "application/grpc",
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

                # Accumulate response data and parse gRPC frames
                buffer = bytearray()
                async for chunk in response.aiter_bytes():
                    buffer.extend(chunk)

                    # Try to parse complete gRPC frames from buffer
                    while len(buffer) >= 5:
                        frame_length = struct.unpack(">I", buffer[1:5])[0]
                        total_frame = 5 + frame_length

                        if len(buffer) < total_frame:
                            break  # Wait for more data

                        frame_payload = bytes(buffer[5:total_frame])
                        del buffer[:total_frame]

                        # Extract text from this frame
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
