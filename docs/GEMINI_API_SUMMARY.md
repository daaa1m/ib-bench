# Gemini API Summary

A comprehensive guide to using the Google Gemini API.

## Overview

The Gemini API provides access to Google's multimodal AI models. Access via:

- **Gemini Developer API** - Direct API with API key authentication
- **Vertex AI** - Enterprise GCP integration with IAM authentication

## Installation

```bash
pip install google-genai
# or
uv pip install google-genai
```

## Client Initialization

### Gemini Developer API

```python
from google import genai
from google.genai import types

client = genai.Client(api_key='GEMINI_API_KEY')
```

### Vertex AI

```python
client = genai.Client(
    vertexai=True,
    project='your-project-id',
    location='us-central1'
)
```

### Environment Variables

| Variable                     | Description                    |
| ---------------------------- | ------------------------------ |
| `GEMINI_API_KEY`             | API key for Gemini Developer API |
| `GOOGLE_API_KEY`             | Alternative API key variable   |
| `GOOGLE_GENAI_USE_VERTEXAI`  | Set `true` for Vertex AI       |
| `GOOGLE_CLOUD_PROJECT`       | GCP project ID                 |
| `GOOGLE_CLOUD_LOCATION`      | GCP region                     |

### Resource Management

```python
client.close()  # Sync client
await client.aclose()  # Async client

# Context manager (auto-close)
with genai.Client() as client:
    response = client.models.generate_content(...)
```

## Available Models

### Current Generation (2.5+)

| Model                | ID                      | Context   | Max Output | Input Price | Output Price |
| -------------------- | ----------------------- | --------- | ---------- | ----------- | ------------ |
| Gemini 3 Pro         | `gemini-3-pro-preview`  | 1M        | 65K        | $2.00/MTok  | $12.00/MTok  |
| Gemini 3 Flash       | `gemini-3-flash-preview`| 1M        | 65K        | $0.50/MTok  | $3.00/MTok   |
| Gemini 2.5 Pro       | `gemini-2.5-pro`        | 1M        | 65K        | $1.25/MTok  | $10.00/MTok  |
| Gemini 2.5 Flash     | `gemini-2.5-flash`      | 1M        | 65K        | $0.30/MTok  | $2.50/MTok   |
| Gemini 2.5 Flash-Lite| `gemini-2.5-flash-lite` | 1M        | 65K        | $0.10/MTok  | $0.40/MTok   |

### Previous Generation (2.0)

| Model                | ID                      | Context   | Max Output | Input Price | Output Price |
| -------------------- | ----------------------- | --------- | ---------- | ----------- | ------------ |
| Gemini 2.0 Flash     | `gemini-2.0-flash`      | 1M        | 8K         | $0.10/MTok  | $0.40/MTok   |
| Gemini 2.0 Flash-Lite| `gemini-2.0-flash-lite` | 1M        | 8K         | $0.075/MTok | $0.30/MTok   |

**Notes:**
- Prices double for inputs >200K tokens (Pro models)
- Batch API provides 50% discount
- Audio input typically costs more than text/image/video

### Specialized Models

| Model                | ID                           | Purpose              |
| -------------------- | ---------------------------- | -------------------- |
| Gemini 2.5 Flash Image | `gemini-2.5-flash-image`   | Image generation     |
| Gemini Embedding     | `gemini-embedding-001`       | Text embeddings      |
| Imagen 4             | `imagen-4.0-generate-001`    | Image generation     |
| Veo 2                | `veo-2.0-generate-001`       | Video generation     |

## Generate Content

### Basic Usage

```python
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='Why is the sky blue?'
)
print(response.text)
```

### With Configuration

```python
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='Explain quantum computing',
    config=types.GenerateContentConfig(
        system_instruction='You are a physics teacher',
        temperature=0,           # 0-2, lower = more deterministic
        top_p=0.95,              # Nucleus sampling threshold
        top_k=20,                # Top-k sampling
        max_output_tokens=8192,  # Limit output length
        stop_sequences=['END'],  # Stop generation triggers
        candidate_count=1,       # Number of responses
        seed=42,                 # For reproducibility
    ),
)
```

### Configuration Parameters

| Parameter            | Type    | Description                              |
| -------------------- | ------- | ---------------------------------------- |
| `temperature`        | float   | Randomness (0-2, default varies by model)|
| `top_p`              | float   | Nucleus sampling threshold               |
| `top_k`              | int     | Top-k sampling                           |
| `max_output_tokens`  | int     | Maximum tokens to generate               |
| `stop_sequences`     | list    | Strings that stop generation             |
| `candidate_count`    | int     | Number of response candidates            |
| `seed`               | int     | Random seed for reproducibility          |
| `presence_penalty`   | float   | Penalize repeated topics                 |
| `frequency_penalty`  | float   | Penalize repeated tokens                 |
| `system_instruction` | str     | System prompt                            |
| `response_mime_type` | str     | Force output format (e.g., `application/json`) |
| `response_schema`    | dict    | JSON schema for structured output        |

### With Files

```python
# Upload file
file = client.files.upload(file='document.pdf')

# Use in generation
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=['Summarize this document:', file]
)
```

### Multimodal Input

```python
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[
        'What is in this image?',
        types.Part.from_uri(
            file_uri='gs://bucket/image.jpg',
            mime_type='image/jpeg',
        ),
    ],
)
```

## Streaming

### Synchronous

```python
for chunk in client.models.generate_content_stream(
    model='gemini-2.5-flash',
    contents='Tell me a story'
):
    print(chunk.text, end='')
```

### Asynchronous

```python
async for chunk in await client.aio.models.generate_content_stream(
    model='gemini-2.5-flash',
    contents='Tell me a story'
):
    print(chunk.text, end='')
```

## Chat Sessions

```python
chat = client.chats.create(model='gemini-2.5-flash')

response = chat.send_message('Tell me a story')
print(response.text)

response = chat.send_message('Summarize it in one sentence')
print(response.text)

# Streaming
for chunk in chat.send_message_stream('Continue the story'):
    print(chunk.text, end='')
```

## Function Calling

### Automatic (Python Functions)

```python
def get_weather(location: str) -> str:
    """Get current weather for a location.

    Args:
        location: City and state, e.g., San Francisco, CA

    Returns:
        Weather description.
    """
    return 'sunny, 72°F'

response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='What is the weather in Boston?',
    config=types.GenerateContentConfig(
        tools=[get_weather],
    ),
)
print(response.text)  # Automatically calls function and uses result
```

### Manual Declaration

```python
function = types.FunctionDeclaration(
    name='get_weather',
    description='Get current weather for a location',
    parameters_json_schema={
        'type': 'object',
        'properties': {
            'location': {
                'type': 'string',
                'description': 'City and state'
            }
        },
        'required': ['location'],
    },
)
tool = types.Tool(function_declarations=[function])

response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='What is the weather in Boston?',
    config=types.GenerateContentConfig(tools=[tool]),
)

# Handle function call manually
if response.function_calls:
    call = response.function_calls[0]
    result = get_weather(**call.args)

    # Send result back
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            response.candidates[0].content,
            types.Part.from_function_response(
                name=call.name,
                response={'result': result}
            )
        ],
        config=types.GenerateContentConfig(tools=[tool]),
    )
```

### Function Calling Modes

```python
config=types.GenerateContentConfig(
    tools=[...],
    tool_config=types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(
            mode='AUTO'  # AUTO, ANY, NONE, VALIDATED
        )
    ),
)
```

| Mode        | Description                                    |
| ----------- | ---------------------------------------------- |
| `AUTO`      | Model decides (default)                        |
| `ANY`       | Always call a function                         |
| `NONE`      | Disable function calling                       |
| `VALIDATED` | Schema compliance guaranteed (preview)         |

### Disable Automatic Calling

```python
config=types.GenerateContentConfig(
    tools=[get_weather],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(
        disable=True
    ),
)
```

## Code Execution

Enable the model to write and run Python code:

```python
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='Calculate the first 10 prime numbers',
    config=types.GenerateContentConfig(
        tools=[types.Tool(code_execution=types.ToolCodeExecution)]
    ),
)
```

### Limitations

- Python only
- 30 second timeout per execution
- Max 5 code regenerations per response
- Cannot install custom libraries
- Pre-installed: NumPy, pandas, Matplotlib, scikit-learn, TensorFlow, SymPy, etc.

## Structured Output (JSON)

### With JSON Schema

```python
schema = {
    'type': 'object',
    'properties': {
        'name': {'type': 'string'},
        'age': {'type': 'integer'},
    },
    'required': ['name', 'age'],
}

response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='Create a user profile',
    config=types.GenerateContentConfig(
        response_mime_type='application/json',
        response_json_schema=schema,
    ),
)
print(response.parsed)  # Parsed dict
```

### With Pydantic

```python
from pydantic import BaseModel

class UserProfile(BaseModel):
    name: str
    age: int

response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='Create a user profile',
    config=types.GenerateContentConfig(
        response_mime_type='application/json',
        response_schema=UserProfile,
    ),
)
```

### Enum Response

```python
from enum import Enum

class Sentiment(Enum):
    POSITIVE = 'positive'
    NEGATIVE = 'negative'
    NEUTRAL = 'neutral'

response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='Classify: "I love this product"',
    config=types.GenerateContentConfig(
        response_mime_type='text/x.enum',
        response_schema=Sentiment,
    ),
)
```

## Files API

```python
# Upload
file = client.files.upload(file='document.pdf')

# Get info
file_info = client.files.get(name=file.name)

# Delete
client.files.delete(name=file.name)
```

## Context Caching

Cache large content for reuse (reduces costs):

```python
# Create cache
cached = client.caches.create(
    model='gemini-2.5-flash',
    config=types.CreateCachedContentConfig(
        contents=[
            types.Content(
                role='user',
                parts=[
                    types.Part.from_uri(
                        file_uri='gs://bucket/large-doc.pdf',
                        mime_type='application/pdf'
                    ),
                ],
            )
        ],
        system_instruction='Summarize documents',
        ttl='3600s',  # 1 hour
    ),
)

# Use cache
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='What are the key points?',
    config=types.GenerateContentConfig(
        cached_content=cached.name,
    ),
)
```

## Token Counting

```python
response = client.models.count_tokens(
    model='gemini-2.5-flash',
    contents='Why is the sky blue?',
)
print(response.total_tokens)
```

## Embeddings

```python
response = client.models.embed_content(
    model='gemini-embedding-001',
    contents='Why is the sky blue?',
)
print(response.embeddings)

# Multiple with config
response = client.models.embed_content(
    model='gemini-embedding-001',
    contents=['query 1', 'query 2'],
    config=types.EmbedContentConfig(output_dimensionality=256),
)
```

## Batch Processing

```python
# Create batch job
job = client.batches.create(
    model='gemini-2.5-flash',
    src='bq://project.dataset.table',  # BigQuery source
)

# Or with inline requests
job = client.batches.create(
    model='gemini-2.5-flash',
    src=[{
        'contents': [{'parts': [{'text': 'Hello!'}], 'role': 'user'}],
    }],
)

# Monitor
while job.state not in {'JOB_STATE_SUCCEEDED', 'JOB_STATE_FAILED'}:
    job = client.batches.get(name=job.name)
    time.sleep(30)
```

## Rate Limits

### Tiers

| Tier   | Qualification                                |
| ------ | -------------------------------------------- |
| Free   | Available in eligible countries              |
| Tier 1 | Paid billing account linked                  |
| Tier 2 | >$250 spend + 30 days since first payment    |
| Tier 3 | >$1,000 spend + 30 days since first payment  |

### Dimensions

- **RPM** - Requests per minute
- **TPM** - Tokens per minute
- **RPD** - Requests per day

Rate limits apply per project (not per API key). RPD resets at midnight Pacific.

### Free Tier Limits (December 2025)

| Model             | RPM | RPD   |
| ----------------- | --- | ----- |
| Gemini 2.5 Pro    | 5   | 25    |
| Gemini 2.5 Flash  | 15  | 500   |

### Paid Tier 1 Limits

| Model             | RPM  | TPM       |
| ----------------- | ---- | --------- |
| Gemini 2.5 Flash  | 300  | 1,000,000 |

## Safety Settings

```python
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='...',
    config=types.GenerateContentConfig(
        safety_settings=[
            types.SafetySetting(
                category='HARM_CATEGORY_HATE_SPEECH',
                threshold='BLOCK_ONLY_HIGH',
            ),
            types.SafetySetting(
                category='HARM_CATEGORY_DANGEROUS_CONTENT',
                threshold='BLOCK_MEDIUM_AND_ABOVE',
            ),
        ]
    ),
)
```

### Categories

- `HARM_CATEGORY_HATE_SPEECH`
- `HARM_CATEGORY_DANGEROUS_CONTENT`
- `HARM_CATEGORY_HARASSMENT`
- `HARM_CATEGORY_SEXUALLY_EXPLICIT`

### Thresholds

- `BLOCK_NONE`
- `BLOCK_ONLY_HIGH`
- `BLOCK_MEDIUM_AND_ABOVE`
- `BLOCK_LOW_AND_ABOVE`

## Error Handling

```python
from google.genai import errors

try:
    response = client.models.generate_content(
        model='invalid-model',
        contents='Hello',
    )
except errors.APIError as e:
    print(f'Error {e.code}: {e.message}')
```

## Async Operations

```python
import asyncio

async def main():
    async with genai.Client().aio as client:
        response = await client.models.generate_content(
            model='gemini-2.5-flash',
            contents='Hello!'
        )
        print(response.text)

asyncio.run(main())
```

## Best Practices

1. **Use `temperature=0`** for deterministic/analytical tasks
2. **Use function calling mode `ANY`** when you need guaranteed function calls
3. **Cache large documents** with context caching for cost savings
4. **Use batch API** for non-time-sensitive bulk processing (50% savings)
5. **Limit tools to 10-20** for optimal performance
6. **Write detailed function descriptions** for better tool selection
7. **Use Pydantic models** for type-safe structured output
8. **Close clients** or use context managers to release connections

## Resources

- **Python SDK Docs**: [googleapis.github.io/python-genai](https://googleapis.github.io/python-genai/)
- **API Reference**: [ai.google.dev/api](https://ai.google.dev/api)
- **Models**: [ai.google.dev/gemini-api/docs/models](https://ai.google.dev/gemini-api/docs/models)
- **Pricing**: [ai.google.dev/gemini-api/docs/pricing](https://ai.google.dev/gemini-api/docs/pricing)
- **Rate Limits**: [ai.google.dev/gemini-api/docs/rate-limits](https://ai.google.dev/gemini-api/docs/rate-limits)
