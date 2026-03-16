"""Test Windsurf gRPC flow: InitializeCascadePanelState + RawGetChatMessage.

Run this test with Windsurf IDE open:
    cd apps/backend && python test_windsurf_flow.py
"""
import asyncio
import sys

sys.path.insert(0, ".")


async def test():
    from integrations.windsurf_proxy.auth import discover_credentials
    from integrations.windsurf_proxy.grpc_client import stream_chat
    from integrations.windsurf_proxy.models import resolve_model

    print("=== Windsurf gRPC Flow Test ===\n")

    # Step 1: Discover credentials (CSRF from process env, API key, port)
    print("1. Discovering credentials...")
    creds = discover_credentials()
    print(f"   Port: {creds.port}")
    print(f"   Version: {creds.version}")
    print(f"   CSRF: {creds.csrf_token[:12]}...")
    print(f"   API Key: {creds.api_key[:12]}...")

    # Step 2: Resolve model
    model_name = "claude-4-sonnet"
    model_enum, model_grpc_name = resolve_model(model_name)
    print(f"\n2. Model: {model_name} → enum={model_enum}, grpc_name={model_grpc_name}")

    # Step 3: Send chat via gRPC (Connect protocol)
    # This will: InitializeCascadePanelState → RawGetChatMessage (streaming)
    print("\n3. Sending chat request...")
    messages = [{"role": "user", "content": "Say hello in one word."}]

    text_parts = []
    try:
        async for chunk in stream_chat(
            credentials=creds,
            messages=messages,
            model_enum=model_enum,
            model_name=model_grpc_name,
        ):
            text_parts.append(chunk)
            print(f"   Chunk: {chunk!r}")
    except Exception as e:
        print(f"   Error: {e}")
        return

    full_text = "".join(text_parts)
    print(f"\n4. Full response ({len(full_text)} chars): {full_text[:200]}")

    if full_text:
        print("\n✓ SUCCESS — Windsurf gRPC flow is working!")
    else:
        print("\n✗ FAILED — Empty response from Windsurf")


asyncio.run(test())
