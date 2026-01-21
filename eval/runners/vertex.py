"""Google Vertex AI runner for IB-bench evaluation pipeline.

Uses the unified google-genai SDK with Vertex AI backend for enterprise
deployments. Requires Google Cloud authentication (ADC or service account).

Environment variables:
    GOOGLE_CLOUD_PROJECT: GCP project ID
    GOOGLE_CLOUD_LOCATION: Region (default: us-central1)
    GOOGLE_APPLICATION_CREDENTIALS: Path to service account key (optional)
"""

import os
import time
from pathlib import Path

from helpers import Task, extract_json, retry_on_rate_limit

from .base import LLMResponse, OutputFile, is_content_filter_error


class VertexAIRunner:
    """Run tasks against Google Vertex AI using the unified genai SDK.

    Features:
        - Code execution (sandboxed Python environment)
        - Google Search grounding (web search)
        - File uploads via Files API
        - Support for Gemini and Model Garden models

    :param model: Model name (e.g., 'gemini-2.0-flash', 'gemini-1.5-pro')
    :param project: GCP project ID (defaults to GOOGLE_CLOUD_PROJECT env var)
    :param location: GCP region (defaults to GOOGLE_CLOUD_LOCATION or us-central1)
    """

    def __init__(
        self,
        model: str | None = None,
        project: str | None = None,
        location: str | None = None,
    ):
        if not model:
            raise ValueError("model is required for VertexAIRunner")

        self.model = model
        self.project = project or os.environ.get("GOOGLE_CLOUD_PROJECT")
        self.location = location or os.environ.get(
            "GOOGLE_CLOUD_LOCATION", "us-central1"
        )

        if not self.project:
            raise ValueError(
                "project is required: pass it directly or set GOOGLE_CLOUD_PROJECT"
            )

        self._client = None

    @property
    def client(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(
                vertexai=True,
                project=self.project,
                location=self.location,
            )
        return self._client

    def _upload_file(self, path: Path) -> object:
        """Upload file to Vertex AI Files API."""
        print(f"  Uploading {path.name} to Vertex AI Files API...")
        return self.client.files.upload(file=str(path))

    def _delete_file(self, file_obj) -> None:
        """Delete uploaded file."""
        try:
            self.client.files.delete(name=file_obj.name)
        except Exception as e:
            print(f"  Warning: Failed to delete file {file_obj.name}: {e}")

    @retry_on_rate_limit(max_retries=3, initial_wait=60)
    def run(self, task: Task, input_files: list[Path] | None = None) -> LLMResponse:
        """Execute a task using Vertex AI with code execution and grounding.

        Tools enabled:
            - code_execution: For Excel/CSV analysis and computations
            - google_search: For real-time web information (grounding)
        """
        from google.genai import types

        start = time.time()

        uploaded_files = []
        files_to_upload = input_files or []
        for f in files_to_upload:
            if f and f.exists():
                uploaded_file = self._upload_file(f)
                uploaded_files.append(uploaded_file)

        contents = uploaded_files + [task.prompt]

        tools = [
            types.Tool(code_execution=types.ToolCodeExecution()),
            types.Tool(google_search=types.GoogleSearch()),
        ]

        config = types.GenerateContentConfig(
            tools=tools,
            temperature=0,
            max_output_tokens=16384,
        )

        print(f"  Running Vertex AI model: {self.model}...")
        content_filter_triggered = False
        response = None

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
        except Exception as e:
            if is_content_filter_error(str(e)):
                print("  BLOCKED: Content filter triggered")
                content_filter_triggered = True
            else:
                raise
        finally:
            for uploaded_file in uploaded_files:
                self._delete_file(uploaded_file)

        latency_ms = (time.time() - start) * 1000

        if content_filter_triggered:
            return LLMResponse(
                raw_text="",
                parsed_json=None,
                model=self.model,
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                stop_reason="content_filter",
                output_files=None,
            )

        assert response is not None

        if response.candidates:
            finish_reason = getattr(response.candidates[0], "finish_reason", None)
            if finish_reason and "safety" in str(finish_reason).lower():
                print(
                    f"  BLOCKED: Content filter triggered (finish_reason={finish_reason})"
                )
                usage = response.usage_metadata
                prompt_tokens = (
                    usage.prompt_token_count
                    if usage and usage.prompt_token_count
                    else 0
                )
                return LLMResponse(
                    raw_text="",
                    parsed_json=None,
                    model=self.model,
                    input_tokens=prompt_tokens,
                    output_tokens=0,
                    latency_ms=latency_ms,
                    stop_reason="content_filter",
                    output_files=None,
                )

        response_text = ""
        output_files = []
        file_counter = 0

        content = response.candidates[0].content if response.candidates else None
        parts = list(content.parts) if content and content.parts else []
        for part in parts:
            if hasattr(part, "text") and part.text is not None:
                response_text += part.text + "\n"

            if hasattr(part, "executable_code") and part.executable_code:
                code = getattr(part.executable_code, "code", None)
                if code:
                    print(f"  Executed code: {len(code)} chars")

            if hasattr(part, "code_execution_result") and part.code_execution_result:
                result = getattr(part.code_execution_result, "output", None)
                if result:
                    response_text += result + "\n"

            if hasattr(part, "inline_data") and part.inline_data:
                file_counter += 1
                mime_type = getattr(
                    part.inline_data, "mime_type", "application/octet-stream"
                )
                ext = mime_type.split("/")[-1] if "/" in mime_type else "bin"
                if ext == "vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                    ext = "xlsx"
                elif ext == "vnd.ms-excel":
                    ext = "xls"
                filename = f"output_{file_counter}.{ext}"
                print(f"  Found output file: {filename} ({mime_type})")
                inline_data = getattr(part.inline_data, "data", None)
                output_files.append(
                    OutputFile(
                        filename=filename,
                        content=inline_data or b"",
                        mime_type=mime_type,
                    )
                )

        usage = response.usage_metadata
        input_tokens = (usage.prompt_token_count if usage else None) or 0
        output_tokens = (usage.candidates_token_count if usage else None) or 0

        stop_reason = "unknown"
        if response.candidates:
            finish_reason = getattr(response.candidates[0], "finish_reason", None)
            if finish_reason:
                stop_reason = str(finish_reason).lower().replace("finishreason.", "")
                if stop_reason == "max_tokens":
                    print("  WARNING: Output truncated (hit max_tokens limit)")

        parsed_json = extract_json(response_text)

        return LLMResponse(
            raw_text=response_text.strip(),
            parsed_json=parsed_json,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            stop_reason=stop_reason,
            output_files=output_files if output_files else None,
        )
