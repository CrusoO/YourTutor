# Removed

A log of everything deleted from this repo. A deletion needs evidence: no references (grep), no imports, no routes, no tests depending on it, and no flag that turns it on in any environment. One category per PR. Anything uncertain is asked about first. See [docs/RELEASES.md](docs/RELEASES.md).

| What | Why | Evidence | Restore commit |
|---|---|---|---|
| Groq, Gemini and OpenRouter support: their keys and routing in `app/config.py`, the OpenAI-style HTTP path in `app/explain/service.py` and `service_chat.py` (`ENDPOINTS`, `_chat_request`, `_reply_text`, `_stream_piece`, `RETRY_CODES`, Groq token budgets), and their tests | Owner decision (2026-11-11): focus on Anthropic; Claude is the only LLM provider (ADR-004). | Claude already served all chat and lesson calls through the SDK; no code path outside the removed branches needed the other providers. Tests rewritten to cover the Anthropic path and to check that other model names are refused. | `a1a8e7e` (last commit with the code) |
| `litellm` (`LiteLLMProvider`) and the packages only it pulled in (aiohttp, boto3, openai, tiktoken, huggingface-hub, tokenizers, jinja2 and others; the full list is the diff of `apps/api/requirements.lock` and `requirements-dev.lock`) | Same owner decision. The gateway now uses `AnthropicProvider` (SDK). | Dependencies checked from the lock files' `via` graph: only packages whose every requirer was removed were dropped. | `a1a8e7e` |
| `LLM_API_KEY` setting (renamed: `ANTHROPIC_API_KEY` is the one key) | Same owner decision; a second shared key had no use with one provider. | Every reader moved to `anthropic_api_key`. Deployments that set `LLM_API_KEY` must set `ANTHROPIC_API_KEY` instead. | `a1a8e7e` |
