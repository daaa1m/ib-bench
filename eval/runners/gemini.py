"""Google Gemini runner for IB-bench evaluation pipeline."""

import os
import time
from pathlib import Path

from helpers import Task, extract_json, retry_on_rate_limit

from .base import LLMResponse, OutputFile, is_content_filter_error


class GeminiRunner:
    """Run tasks against Google Gemini models using Files API + Code Execution."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        if not model:
            raise ValueError("model is required for GeminiRunner")
        self.api_key = (
            api_key
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not set")
        self.model = model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _upload_file(self, path: Path) -> object:
        """Upload file to Gemini Files API."""
        print(f"Uploading {path.name} to Gemini Files API...")
        return self.client.files.upload(file=str(path))

    @retry_on_rate_limit(max_retries=3, initial_wait=60)
    def run(self, task: Task, input_files: list[Path] | None = None) -> LLMResponse:
        """Execute a task using Gemini with file upload and code execution."""
        from google.genai import types

        start = time.time()

        uploaded_files = []
        files_to_upload = input_files or []
        for f in files_to_upload:
            if f and f.exists():
                uploaded_file = self._upload_file(f)
                uploaded_files.append(uploaded_file)

        contents = uploaded_files + [task.prompt]

        config = types.GenerateContentConfig(
            tools=[types.Tool(code_execution=types.ToolCodeExecution())],
            temperature=0,
            max_output_tokens=16384,
        )

        print("  Running Gemini model...")
        content_filter_triggered = False
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
                response = None
            else:
                raise
        finally:
            for uploaded_file in uploaded_files:
                try:
                    self.client.files.delete(name=uploaded_file.name)
                except Exception as e:
                    print(f"  Warning: Failed to delete file {uploaded_file.name}: {e}")

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
                prompt_tokens = usage.prompt_token_count if usage else None
                return LLMResponse(
                    raw_text="",
                    parsed_json=None,
                    model=self.model,
                    input_tokens=prompt_tokens or 0,
                    output_tokens=0,
                    latency_ms=latency_ms,
                    stop_reason="content_filter",
                    output_files=None,
                )

        response_text = ""
        output_files = []
        file_counter = 0

        content = response.candidates[0].content if response.candidates else None
        parts = content.parts if content else []
        if parts:
            for part in parts:
                if hasattr(part, "text") and part.text is not None:
                    response_text += part.text + "\n"
                if hasattr(part, "inline_data") and part.inline_data:
                    file_counter += 1
                    mime_type = getattr(
                        part.inline_data, "mime_type", "application/octet-stream"
                    )
                    ext = mime_type.split("/")[-1] if "/" in mime_type else "bin"
                    if ext == "vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                        ext = "xlsx"
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
