# Claude API Summary

A comprehensive guide to using the Anthropic Claude API.

## Overview

The Claude API is a RESTful API at `https://api.anthropic.com` that provides
programmatic access to Claude models. The primary endpoint is the Messages API
(`POST /v1/messages`).

## Authentication

All requests require these headers:

| Header              | Value                            | Required |
| ------------------- | -------------------------------- | -------- |
| `x-api-key`         | Your API key from Console        | Yes      |
| `anthropic-version` | API version (e.g., `2023-06-01`) | Yes      |
| `content-type`      | `application/json`               | Yes      |

Get API keys from
[console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys).

## Available Models

### Current Models (Recommended)

| Model             | API ID                       | Context   | Max Output | Input Price | Output Price |
| ----------------- | ---------------------------- | --------- | ---------- | ----------- | ------------ |
| Claude Sonnet 4.5 | `claude-sonnet-4-5-20250929` | 200K/1M\* | 64K        | $3/MTok     | $15/MTok     |
| Claude Haiku 4.5  | `claude-haiku-4-5-20251001`  | 200K      | 64K        | $1/MTok     | $5/MTok      |
| Claude Opus 4.5   | `claude-opus-4-5-20251101`   | 200K      | 64K        | $5/MTok     | $25/MTok     |

\*1M context available with beta header `context-1m-2025-08-07`

**Model Aliases** (auto-update to latest):

- `claude-sonnet-4-5`
- `claude-haiku-4-5`
- `claude-opus-4-5`

### Legacy Models

| Model           | API ID                     | Context | Max Output | Input Price | Output Price |
| --------------- | -------------------------- | ------- | ---------- | ----------- | ------------ |
| Claude Opus 4.1 | `claude-opus-4-1-20250805` | 200K    | 32K        | $15/MTok    | $75/MTok     |
| Claude Sonnet 4 | `claude-sonnet-4-20250514` | 200K/1M | 64K        | $3/MTok     | $15/MTok     |
| Claude Opus 4   | `claude-opus-4-20250514`   | 200K    | 32K        | $15/MTok    | $75/MTok     |
| Claude Haiku 3  | `claude-3-haiku-20240307`  | 200K    | 4K         | $0.25/MTok  | $1.25/MTok   |

## Messages API

### Endpoint

```
POST https://api.anthropic.com/v1/messages
```

### Required Parameters

| Parameter    | Type   | Description                                |
| ------------ | ------ | ------------------------------------------ |
| `model`      | string | Model identifier                           |
| `max_tokens` | number | Maximum tokens to generate                 |
| `messages`   | array  | Array of message objects with role/content |

### Optional Parameters

| Parameter        | Type    | Description                           |
| ---------------- | ------- | ------------------------------------- |
| `system`         | string  | System prompt                         |
| `temperature`    | float   | Randomness (0.0-1.0, default: 1.0)    |
| `top_p`          | float   | Nucleus sampling threshold            |
| `top_k`          | number  | Sample from top K options             |
| `stop_sequences` | array   | Custom stop strings                   |
| `stream`         | boolean | Enable streaming responses            |
| `tools`          | array   | Tool definitions for function calling |
| `tool_choice`    | object  | Control tool selection behavior       |
| `metadata`       | object  | Request metadata (e.g., `user_id`)    |

### Basic Example

```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5",
    "max_tokens": 1024,
    "messages": [
      {"role": "user", "content": "Hello, Claude"}
    ]
  }'
```

### Response Format

```json
{
  "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "Hello! How can I assist you today?"
    }
  ],
  "model": "claude-sonnet-4-5",
  "stop_reason": "end_turn",
  "usage": {
    "input_tokens": 12,
    "output_tokens": 8
  }
}
```

### Stop Reasons

| Reason          | Description                         |
| --------------- | ----------------------------------- |
| `end_turn`      | Natural completion                  |
| `max_tokens`    | Reached token limit                 |
| `stop_sequence` | Hit custom stop sequence            |
| `tool_use`      | Model invoked a tool                |
| `refusal`       | Policy violation prevented response |

## Message Content Types

### Text Content

```json
{ "role": "user", "content": "Hello, Claude" }
```

Or as content block:

```json
{
  "role": "user",
  "content": [{ "type": "text", "text": "Hello, Claude" }]
}
```

### Image Content

Base64:

```json
{
  "type": "image",
  "source": {
    "type": "base64",
    "media_type": "image/jpeg",
    "data": "<base64_encoded_image>"
  }
}
```

URL:

```json
{
  "type": "image",
  "source": {
    "type": "url",
    "url": "https://example.com/image.jpg"
  }
}
```

Supported formats: `image/jpeg`, `image/png`, `image/gif`, `image/webp`

### Document Content

```json
{
  "type": "document",
  "source": {
    "type": "base64",
    "media_type": "application/pdf",
    "data": "<base64_encoded_pdf>"
  },
  "title": "Document Title"
}
```

## Tool Use

### Defining Tools

```json
{
  "tools": [
    {
      "name": "get_stock_price",
      "description": "Get the current stock price for a ticker symbol.",
      "input_schema": {
        "type": "object",
        "properties": {
          "ticker": {
            "type": "string",
            "description": "The stock ticker symbol"
          }
        },
        "required": ["ticker"]
      }
    }
  ]
}
```

### Tool Use Response

When Claude wants to use a tool:

```json
{
  "type": "tool_use",
  "id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
  "name": "get_stock_price",
  "input": { "ticker": "AAPL" }
}
```

### Providing Tool Results

```json
{
  "role": "user",
  "content": [
    {
      "type": "tool_result",
      "tool_use_id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
      "content": "AAPL is trading at $150.25"
    }
  ]
}
```

### Tool Choice Options

```json
{"type": "auto"}     // Let Claude decide (default)
{"type": "any"}      // Force tool use
{"type": "none"}     // Disable tools
{"type": "tool", "name": "specific_tool"}  // Force specific tool
```

## System Prompts

```json
{
  "system": "You are a helpful assistant specializing in Python.",
  "messages": [...]
}
```

With cache control:

```json
{
  "system": [
    {
      "type": "text",
      "text": "You are a helpful assistant.",
      "cache_control": { "type": "ephemeral" }
    }
  ]
}
```

## Extended Thinking

Enable Claude's reasoning process:

```json
{
  "thinking": {
    "type": "enabled",
    "budget_tokens": 10000
  }
}
```

## Streaming

Enable with `"stream": true`. Responses come as server-sent events:

```
event: message_start
event: content_block_start
event: content_block_delta
event: content_block_stop
event: message_delta
event: message_stop
```

## Other APIs

### Token Counting

```
POST /v1/messages/count_tokens
```

```json
{
  "model": "claude-sonnet-4-5",
  "messages": [{ "role": "user", "content": "Hello" }]
}
```

Response: `{"input_tokens": 10}`

### Message Batches (50% cost reduction)

```
POST /v1/messages/batches
GET /v1/messages/batches/{batch_id}
GET /v1/messages/batches/{batch_id}/results
```

### Models List

```
GET /v1/models
```

### Files API (Beta)

```
POST /v1/files
GET /v1/files
```

## Rate Limits

Limits are per-organization and increase with usage tiers.

### Tier Requirements

| Tier   | Credit Purchase | Max Purchase |
| ------ | --------------- | ------------ |
| Tier 1 | $5              | $100         |
| Tier 2 | $40             | $500         |
| Tier 3 | $200            | $1,000       |
| Tier 4 | $400            | $5,000       |

### Tier 4 Rate Limits (Example)

| Model             | RPM   | Input TPM | Output TPM |
| ----------------- | ----- | --------- | ---------- |
| Claude Sonnet 4.x | 4,000 | 2,000,000 | 400,000    |
| Claude Haiku 4.5  | 4,000 | 4,000,000 | 800,000    |
| Claude Opus 4.x   | 4,000 | 2,000,000 | 400,000    |

**Cache-aware limits**: Cached tokens don't count toward input TPM for most
models, effectively increasing throughput.

### Response Headers

- `retry-after`: Seconds to wait before retry
- `anthropic-ratelimit-requests-limit`: Max RPM
- `anthropic-ratelimit-requests-remaining`: Remaining requests
- `anthropic-ratelimit-tokens-limit`: Max tokens
- `anthropic-ratelimit-tokens-remaining`: Remaining tokens

## Client SDKs

### Python

```bash
pip install anthropic
```

```python
from anthropic import Anthropic

client = Anthropic()  # Reads ANTHROPIC_API_KEY from env
message = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello, Claude"}]
)
```
