"""
Windsurf Cascade Chat Client
============================

Implements Windsurf's full Cascade flow for models that require it
(SWE-1.6 family, plus any model routed by string UID rather than enum).

Flow:
    1. StartCascade              → cascade_id
    2. SendUserCascadeMessage    → starts server-side generation
    3. Poll GetCascadeTrajectorySteps until status=IDLE → assemble text

Unlike RawGetChatMessage, Cascade accepts a single text payload (not a
messages array), so the full prior conversation must be flattened into the
outgoing text when starting a new cascade.

Transport: Connect protocol (`application/proto`) — NOT raw gRPC. Ported
protobuf field numbers from dwgx/WindsurfAPI src/windsurf.js.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import TYPE_CHECKING

from integrations.windsurf_proxy.auth import WindsurfError, WindsurfErrorCode
from integrations.windsurf_proxy.grpc_client import (
    GRPC_SERVICE_BASE,
    _build_metadata,
    _encode_bytes_field,
    _encode_string_field,
    _encode_varint_field,
    _ensure_panel_initialized,
)

if TYPE_CHECKING:
    from integrations.windsurf_proxy.auth import WindsurfCredentials

logger = logging.getLogger(__name__)

START_CASCADE_PATH = f"{GRPC_SERVICE_BASE}/StartCascade"
SEND_CASCADE_PATH = f"{GRPC_SERVICE_BASE}/SendUserCascadeMessage"
GET_STEPS_PATH = f"{GRPC_SERVICE_BASE}/GetCascadeTrajectorySteps"
GET_STATUS_PATH = f"{GRPC_SERVICE_BASE}/GetCascadeTrajectory"

# Trajectory status (CortexTrajectoryStatus from extension.js)
STATUS_IDLE = 1

# Step types (CortexTrajectoryStepType)
STEP_PLANNER_RESPONSE = 15
STEP_ERROR_MESSAGE = 17

# Planner modes (ConversationalPlannerMode)
PLANNER_MODE_NO_TOOL = 3

# Section override modes
SECTION_OVERRIDE_MODE_OVERRIDE = 1

# Poll tuning
_POLL_INTERVAL = 0.4
_MAX_WAIT = 180.0
_IDLE_GRACE = 8.0
_NO_GROWTH_STALL = 25.0


# =============================================================================
# Protobuf builders
# =============================================================================


def _build_start_cascade_request(
    credentials: WindsurfCredentials, session_id: str
) -> bytes:
    """StartCascadeRequest { metadata = 1 }."""
    metadata = _build_metadata(credentials, session_id=session_id)
    return _encode_bytes_field(1, metadata)


def _build_cascade_config(model_enum: int, model_uid: str) -> bytes:
    """Build CascadeConfig — planner config + brain config.

    CascadeConfig {
        field 1: planner_config (CascadePlannerConfig)
        field 7: brain_config (BrainConfig)
    }
    CascadePlannerConfig {
        field 2: conversational (CascadeConversationalPlannerConfig)
        field 15: requested_model_deprecated (ModelOrAlias)
        field 34: plan_model_uid (string)
        field 35: requested_model_uid (string)
    }
    CascadeConversationalPlannerConfig {
        field 4: planner_mode (ConversationalPlannerMode)
    }
    """
    # Conversational planner config: NO_TOOL mode (we emulate tools via text
    # in the prompt, same as RawGetChatMessage path).
    conversational = _encode_varint_field(4, PLANNER_MODE_NO_TOOL)

    # Planner parts: conversational + model routing
    planner_parts = bytearray()
    planner_parts.extend(_encode_bytes_field(2, conversational))

    # Set BOTH the modern uid field (35) and deprecated enum field (15) when
    # available. Free-tier accounts sometimes report "user status is nil"
    # during InitializeCascadePanelState and the server rejects the chat with
    # "neither PlanModel nor RequestedModel specified" if only field 35 is
    # populated. Setting both covers both validator paths.
    if model_uid:
        planner_parts.extend(_encode_string_field(35, model_uid))  # requested_model_uid
        planner_parts.extend(_encode_string_field(34, model_uid))  # plan_model_uid
    if model_enum and model_enum > 0:
        # requested_model_deprecated = ModelOrAlias { model = 1 (enum) }
        model_or_alias = _encode_varint_field(1, model_enum)
        planner_parts.extend(_encode_bytes_field(15, model_or_alias))
        # plan_model_deprecated = Model (enum directly at field 1)
        planner_parts.extend(_encode_varint_field(1, model_enum))

    if not model_uid and not model_enum:
        raise ValueError(
            "_build_cascade_config: at least one of model_uid or model_enum required"
        )

    # BrainConfig { enabled=true (f1), update_strategy.dynamic_update={} (f6.f6) }
    brain_parts = bytearray()
    brain_parts.extend(_encode_varint_field(1, 1))  # enabled=true
    brain_parts.extend(_encode_bytes_field(6, _encode_bytes_field(6, b"")))

    cascade_parts = bytearray()
    cascade_parts.extend(_encode_bytes_field(1, bytes(planner_parts)))
    cascade_parts.extend(_encode_bytes_field(7, bytes(brain_parts)))
    return bytes(cascade_parts)


def _build_send_cascade_request(
    credentials: WindsurfCredentials,
    cascade_id: str,
    text: str,
    model_enum: int,
    model_uid: str,
    session_id: str,
) -> bytes:
    """SendUserCascadeMessageRequest.

    Fields:
        1: cascade_id (string)
        2: items (TextOrScopeItem { text = 1 })
        3: metadata (Metadata)
        5: cascade_config (CascadeConfig)
    """
    parts = bytearray()
    parts.extend(_encode_string_field(1, cascade_id))

    # Field 2: TextOrScopeItem { text = 1 }
    text_item = _encode_string_field(1, text)
    parts.extend(_encode_bytes_field(2, text_item))

    # Field 3: metadata
    metadata = _build_metadata(credentials, session_id=session_id)
    parts.extend(_encode_bytes_field(3, metadata))

    # Field 5: cascade_config
    cascade_config = _build_cascade_config(model_enum, model_uid)
    parts.extend(_encode_bytes_field(5, cascade_config))

    return bytes(parts)


def _build_get_steps_request(cascade_id: str, offset: int = 0) -> bytes:
    """GetCascadeTrajectoryStepsRequest { cascade_id=1, step_offset=2 }."""
    parts = bytearray()
    parts.extend(_encode_string_field(1, cascade_id))
    if offset > 0:
        parts.extend(_encode_varint_field(2, offset))
    return bytes(parts)


def _build_get_status_request(cascade_id: str) -> bytes:
    """GetCascadeTrajectoryRequest { cascade_id=1 }."""
    return _encode_string_field(1, cascade_id)


# =============================================================================
# Protobuf parsers
# =============================================================================


def _decode_varint(data: bytes, offset: int) -> tuple[int, int]:
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


def _parse_fields(data: bytes) -> list[tuple[int, int, bytes | int]]:
    """Iterate protobuf fields. Returns list of (field_number, wire_type, value).

    For wire_type=0 (varint) value is an int; for wire_type=2 (length-delimited)
    value is the raw bytes. Unknown wire types stop iteration.
    """
    out: list[tuple[int, int, bytes | int]] = []
    offset = 0
    while offset < len(data):
        tag, offset = _decode_varint(data, offset)
        field_number = tag >> 3
        wire_type = tag & 0x07
        if wire_type == 0:
            value, offset = _decode_varint(data, offset)
            out.append((field_number, 0, value))
        elif wire_type == 2:
            length, offset = _decode_varint(data, offset)
            out.append((field_number, 2, data[offset : offset + length]))
            offset += length
        elif wire_type == 5:
            offset += 4
        elif wire_type == 1:
            offset += 8
        else:
            break
    return out


def _get_field(fields, number: int, wire_type: int):
    for fn, wt, val in fields:
        if fn == number and wt == wire_type:
            return val
    return None


def _get_all_fields(fields, number: int, wire_type: int) -> list:
    return [val for fn, wt, val in fields if fn == number and wt == wire_type]


def _parse_start_cascade_response(buf: bytes) -> str:
    """StartCascadeResponse { cascade_id = 1 (string) }."""
    val = _get_field(_parse_fields(buf), 1, 2)
    return val.decode("utf-8") if isinstance(val, bytes) else ""


def _parse_status_response(buf: bytes) -> int:
    """GetCascadeTrajectoryResponse { ..., status = 2 (enum) }."""
    val = _get_field(_parse_fields(buf), 2, 0)
    return int(val) if isinstance(val, int) else 0


def _parse_trajectory_steps(buf: bytes) -> list[dict]:
    """Extract planner text, thinking, and error info from each trajectory step.

    GetCascadeTrajectoryStepsResponse { repeated CortexTrajectoryStep steps=1 }
    CortexTrajectoryStep {
        1: type (enum; 15=PLANNER_RESPONSE, 17=ERROR_MESSAGE)
        4: status
        20: planner_response { 1: response, 3: thinking, 8: modified_response }
        24: error_message { 3: CortexErrorDetails }
        31: error (CortexErrorDetails)
    }
    CortexErrorDetails { 1: user_error_message, 2: short_error, 3: full_error }
    """
    fields = _parse_fields(buf)
    steps = _get_all_fields(fields, 1, 2)
    out: list[dict] = []

    for step_bytes in steps:
        sf = _parse_fields(step_bytes)
        step_type = _get_field(sf, 1, 0)
        status = _get_field(sf, 4, 0)

        entry = {
            "type": int(step_type) if isinstance(step_type, int) else 0,
            "status": int(status) if isinstance(status, int) else 0,
            "text": "",
            "response_text": "",
            "modified_text": "",
            "thinking": "",
            "error_text": "",
        }

        # planner_response (field 20)
        planner = _get_field(sf, 20, 2)
        if isinstance(planner, bytes):
            pf = _parse_fields(planner)
            resp = _get_field(pf, 1, 2)
            modified = _get_field(pf, 8, 2)
            think = _get_field(pf, 3, 2)
            if isinstance(resp, bytes):
                entry["response_text"] = resp.decode("utf-8", errors="replace")
            if isinstance(modified, bytes):
                entry["modified_text"] = modified.decode("utf-8", errors="replace")
            if isinstance(think, bytes):
                entry["thinking"] = think.decode("utf-8", errors="replace")
            entry["text"] = entry["modified_text"] or entry["response_text"]

        # Error extraction: prefer step.error_message (field 24), fall back to
        # step.error (field 31). Both wrap CortexErrorDetails.
        def _read_details(details_bytes: bytes) -> str:
            ed = _parse_fields(details_bytes)
            for fnum in (1, 2, 3):
                val = _get_field(ed, fnum, 2)
                if isinstance(val, bytes):
                    s = val.decode("utf-8", errors="replace").strip()
                    if s:
                        return s.split("\n")[0][:300]
            return ""

        err_msg = _get_field(sf, 24, 2)
        if isinstance(err_msg, bytes):
            inner = _get_field(_parse_fields(err_msg), 3, 2)
            if isinstance(inner, bytes):
                entry["error_text"] = _read_details(inner)
        if not entry["error_text"]:
            err_field = _get_field(sf, 31, 2)
            if isinstance(err_field, bytes):
                entry["error_text"] = _read_details(err_field)

        out.append(entry)

    return out


# =============================================================================
# HTTP transport (Connect protocol, unary)
# =============================================================================


async def _unary_call(
    credentials: WindsurfCredentials, path: str, payload: bytes, timeout: float = 30.0
) -> bytes:
    """POST an unary Connect-protocol RPC and return the raw response body."""
    try:
        import httpx
    except ImportError as e:
        raise ImportError(
            "httpx is required for Windsurf Cascade client. Install: pip install httpx[http2]"
        ) from e

    url = f"http://localhost:{credentials.port}{path}"
    headers = {
        "content-type": "application/proto",
        "x-codeium-csrf-token": credentials.csrf_token,
        "connect-protocol-version": "1",
        "user-agent": "workpilot-windsurf-proxy/1.0",
    }

    async with httpx.AsyncClient(http2=True, timeout=timeout) as client:
        resp = await client.post(url, content=payload, headers=headers)
        if resp.status_code != 200:
            body = resp.content[:500].decode("utf-8", errors="replace")
            raise WindsurfError(
                f"Cascade RPC {path} failed (status={resp.status_code}): {body}",
                WindsurfErrorCode.STREAM_ERROR,
            )
        # Connect unary content-type=application/proto returns the raw protobuf
        # message body (no Connect framing envelope). Error responses use
        # content-type=application/json with {code, message}.
        ct = resp.headers.get("content-type", "")
        if ct.startswith("application/json"):
            import json as _json

            try:
                err = _json.loads(resp.content.decode("utf-8", errors="replace"))
                code = err.get("code", "unknown")
                message = err.get("message", "unknown error")
                raise WindsurfError(
                    f"Windsurf server error: {code}: {message}",
                    WindsurfErrorCode.STREAM_ERROR,
                )
            except ValueError:
                pass
        return resp.content


# =============================================================================
# Conversation flattening
# =============================================================================


def _flatten_messages(messages: list[dict]) -> str:
    """Cascade accepts a single text payload, so pack u/a turns as a transcript
    and put the system prompt on top. The current user turn is kept separate
    so the model knows which message it must answer.
    """
    system_parts: list[str] = []
    convo: list[dict] = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if not isinstance(content, str):
            content = str(content)
        if role == "system":
            system_parts.append(content)
        else:
            convo.append({"role": role, "content": content})

    sys_text = "\n".join(p for p in system_parts if p).strip()

    if len(convo) <= 1:
        user_text = convo[-1]["content"] if convo else ""
    else:
        lines: list[str] = []
        for turn in convo[:-1]:
            label = "User" if turn["role"] == "user" else "Assistant"
            lines.append(f"{label}: {turn['content']}")
        latest = convo[-1]["content"]
        user_text = (
            "[Conversation so far]\n"
            + "\n\n".join(lines)
            + "\n\n[Current user message]\n"
            + latest
        )

    return (sys_text + "\n\n" + user_text) if sys_text else user_text


# =============================================================================
# Public API
# =============================================================================


async def cascade_chat(
    credentials: WindsurfCredentials,
    messages: list[dict],
    model_enum: int,
    model_uid: str,
) -> str:
    """Run a full Cascade turn and return the assembled response text.

    Args:
        credentials: Discovered Windsurf credentials.
        messages: OpenAI-format [{role, content}, ...]. The full conversation
            is flattened into a single text payload (Cascade doesn't accept
            a messages array on turn 1).
        model_enum: ChatModelType enum int (0 if model is UID-only, e.g. SWE-1.6).
        model_uid: Model UID string ("swe-1-6", "swe-1-6-fast", or
            "MODEL_<ENUM>" for enum-style models).

    Raises:
        WindsurfError on transport or server-side error (including a cascade
        step of type ERROR_MESSAGE).

    Returns:
        The final assembled response text (response_text + modified_response
        top-up), stripped of the upstream error/trailer envelopes.
    """
    await _ensure_panel_initialized(credentials)

    session_id = str(uuid.uuid4())
    text = _flatten_messages(messages)

    logger.debug(
        "[WindsurfCascade] Starting cascade uid=%s enum=%d text_len=%d",
        model_uid,
        model_enum,
        len(text),
    )

    # Step 1: StartCascade
    start_payload = _build_start_cascade_request(credentials, session_id)
    start_resp = await _unary_call(credentials, START_CASCADE_PATH, start_payload)
    cascade_id = _parse_start_cascade_response(start_resp)
    if not cascade_id:
        raise WindsurfError(
            "StartCascade returned empty cascade_id",
            WindsurfErrorCode.STREAM_ERROR,
        )
    logger.debug("[WindsurfCascade] Cascade started: %s", cascade_id)

    # Step 2: SendUserCascadeMessage
    send_payload = _build_send_cascade_request(
        credentials, cascade_id, text, model_enum, model_uid, session_id
    )
    await _unary_call(credentials, SEND_CASCADE_PATH, send_payload)
    logger.debug("[WindsurfCascade] Message sent, polling trajectory")

    # Step 3: Poll until IDLE or stall
    yielded_by_step: dict[int, int] = {}
    chunks: list[str] = []

    saw_active = False
    saw_text = False
    idle_count = 0
    last_growth = asyncio.get_event_loop().time()
    last_step_count = 0
    last_status = -1
    start_time = asyncio.get_event_loop().time()

    while True:
        now = asyncio.get_event_loop().time()
        if now - start_time > _MAX_WAIT:
            logger.warning(
                "[WindsurfCascade] max_wait (%ss) reached, returning partial",
                _MAX_WAIT,
            )
            break

        await asyncio.sleep(_POLL_INTERVAL)

        steps_resp = await _unary_call(
            credentials,
            GET_STEPS_PATH,
            _build_get_steps_request(cascade_id, 0),
        )
        steps = _parse_trajectory_steps(steps_resp)

        # Surface error steps as exceptions — the cascade refused the request
        # (permission, model unavailable, quota, etc.).
        for step in steps:
            if step["type"] == STEP_ERROR_MESSAGE and step["error_text"]:
                logger.warning(
                    "[WindsurfCascade] Cascade error step: %s", step["error_text"]
                )
                raise WindsurfError(
                    f"Windsurf server error: {step['error_text']}",
                    WindsurfErrorCode.STREAM_ERROR,
                )

        if len(steps) > last_step_count:
            last_step_count = len(steps)
            last_growth = now

        for i, step in enumerate(steps):
            live = step["response_text"] or step["text"]
            if not live:
                continue
            prev = yielded_by_step.get(i, 0)
            if len(live) > prev:
                chunks.append(live[prev:])
                yielded_by_step[i] = len(live)
                saw_text = True
                last_growth = now

        # Status check
        status_resp = await _unary_call(
            credentials, GET_STATUS_PATH, _build_get_status_request(cascade_id)
        )
        status = _parse_status_response(status_resp)
        last_status = status
        if status != STATUS_IDLE:
            saw_active = True

        # Stall detection: warm stall (have text, no growth for N seconds)
        if (
            saw_text
            and status != STATUS_IDLE
            and (now - last_growth) > _NO_GROWTH_STALL
        ):
            logger.warning(
                "[WindsurfCascade] Warm stall: no growth for %.1fs, accepting partial",
                _NO_GROWTH_STALL,
            )
            break

        if status == STATUS_IDLE:
            # Ignore early IDLE before warmup grace window
            elapsed = now - start_time
            if not saw_active and elapsed < _IDLE_GRACE:
                continue
            idle_count += 1
            # Require some text OR several consecutive IDLE polls before
            # accepting "done", so we don't race the first chunk.
            can_break = idle_count >= (2 if saw_text else 4)
            if can_break:
                # Final sweep: top up from modified_response if it's a strict
                # extension of what we've streamed.
                final_resp = await _unary_call(
                    credentials,
                    GET_STEPS_PATH,
                    _build_get_steps_request(cascade_id, 0),
                )
                final_steps = _parse_trajectory_steps(final_resp)
                for i, step in enumerate(final_steps):
                    resp_text = step["response_text"] or ""
                    mod_text = step["modified_text"] or ""
                    prev = yielded_by_step.get(i, 0)
                    if len(resp_text) > prev:
                        chunks.append(resp_text[prev:])
                        yielded_by_step[i] = len(resp_text)
                    cursor = yielded_by_step.get(i, 0)
                    if len(mod_text) > cursor and mod_text.startswith(resp_text):
                        chunks.append(mod_text[cursor:])
                        yielded_by_step[i] = len(mod_text)
                break
        else:
            idle_count = 0

    result = "".join(chunks)
    logger.debug(
        "[WindsurfCascade] Done: text_len=%d steps=%d last_status=%d saw_active=%s",
        len(result),
        last_step_count,
        last_status,
        saw_active,
    )
    return result
