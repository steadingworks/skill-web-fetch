---
name: web-fetch
description: Fetch web pages or search the internet. Use when the user asks to fetch, read, look up, search for, or find information on the web. Returns clean extracted content ready for synthesis. TRIGGER on "fetch", "get page", "read url", "look up", "search for", "find on web".
allowed-tools: Bash(curl:*), Bash(grep:*)
user-invocable: true
---

# web-fetch

Fetch web pages and search the internet via the skill-web-fetch API. The API handles
HTTP fetching and HTML-to-text extraction — you receive clean markdown or plain text.

You do NOT fetch URLs directly. All web access goes through the API.

## Setup: Acquire a Token

Run once per session. Re-run if any API call returns 401.

```bash
SKILL_WEB_TOKEN=$(curl -s -X POST https://<your-auth-host>/token \
  -H "X-API-Key: $(grep '^key=' ~/.config/homelab/skill-apis.api | cut -d= -f2-)" \
  | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
```

Never print or echo `$SKILL_WEB_TOKEN`.

## Endpoints

All requests require: `-H "Authorization: Bearer $SKILL_WEB_TOKEN"`

### Fetch a URL

```bash
curl -s -G "https://<your-api-host>/v1/fetch" \
  -H "Authorization: Bearer $SKILL_WEB_TOKEN" \
  --data-urlencode "url=https://example.com" \
  --data-urlencode "format=markdown"
```

Parameters:
- `url` (required) — must be http or https
- `format` — `markdown` (default) or `text`

Response: `{"url": "...", "format": "...", "content": "..."}` — content capped at 50,000 chars.

### Search

```bash
curl -s -G "https://<your-api-host>/v1/search" \
  -H "Authorization: Bearer $SKILL_WEB_TOKEN" \
  --data-urlencode "q=your query here" \
  -d "limit=10"
```

Response: `{"query": "...", "results": [{"title": "...", "url": "...", "snippet": "...", "engine": "..."}]}`

If search returns 503, the backend is not yet configured — use fetch on known URLs instead.

### Health (no auth)

```bash
curl -s https://<your-api-host>/health
```

## How to approach tasks

**Direct URL** — call `/v1/fetch` with that URL.

**Open-ended search** — call `/v1/search`, review titles and snippets, pick the 2–3 most
relevant URLs, call `/v1/fetch` on each, then synthesise the content into an answer.

**401 response** — re-acquire the token (re-run the setup command) then retry the request once.

**4xx response (other than 401)** — do not retry. These are client errors that will not resolve on retry. Report the status code and detail to the user.

**503 on /v1/search** — fall back to `/v1/fetch` on any known relevant URLs.

**Content too long** — the API truncates at 50,000 chars. Focus on the portion most relevant
to the user's question; consider requesting `format=text` for denser content.

## Must NOT

- Do not use `curl`, `wget`, or any tool to fetch URLs directly — all web access via the API
- Do not print or echo `$SKILL_WEB_TOKEN`
- Do not crawl recursively — fetch only what the task requires
- Do not invent content — all facts must come from API responses
- Do not attempt to fetch non-http/https URLs (file://, ftp://, etc.)
