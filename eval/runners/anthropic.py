"""Anthropic Claude runner for IB-bench evaluation pipeline."""

import os
import time
from pathlib import Path
from typing import Any, cast

from helpers import Task, extract_json, retry_on_rate_limit

from .base import LLMResponse, OutputFile, is_content_filter_error, read_file_content


class AnthropicRunner:
    """Run tasks against Anthropic Claude models with code execution for Excel files."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        if not model:
            raise ValueError("model is required for AnthropicRunner")
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self.model = model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    @retry_on_rate_limit(max_retries=3, initial_wait=60)
    def run(self, task: Task, input_files: list[Path] | None = None) -> LLMResponse:
        """Execute a task against Claude with file upload via Files API."""
        files = input_files or []
        if files:
            return self._run_with_files(task, files)
        else:
            return self._run_text_only(task)

    def _run_text_only(self, task: Task) -> LLMResponse:
        """Run task with text prompt only (no Excel file)."""
        start = time.time()
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=16384,
                temperature=0,
                messages=[{"role": "user", "content": task.prompt}],
            )
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            if is_content_filter_error(str(e)):
                print("  BLOCKED: Content filter triggered")
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
            raise

        latency_ms = (time.time() - start) * 1000

        first_block = response.content[0]
        raw_text: str = getattr(first_block, "text", "")
        parsed_json = extract_json(raw_text)
        stop_reason = response.stop_reason or "unknown"

        if stop_reason == "max_tokens":
            print("  WARNING: Output truncated (hit max_tokens limit)")

        return LLMResponse(
            raw_text=raw_text,
            parsed_json=parsed_json,
            model=self.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_ms=latency_ms,
            stop_reason=stop_reason,
            output_files=None,
        )

    def _run_with_files(self, task: Task, input_files: list[Path]) -> LLMResponse:
        """Run with file upload - uploads files via Files API and uses code execution."""
        file_ids = []
        for input_file in input_files:
            print(f"Uploading {input_file.name} to Files API...")
            with open(input_file, "rb") as f:
                file_obj = self.client.beta.files.upload(file=f)
                file_ids.append(file_obj.id)

        content: list[Any] = []
        for file_id in file_ids:
            content.append({"type": "container_upload", "file_id": file_id})
        content.append({"type": "text", "text": task.prompt})

        start = time.time()
        content_filter_triggered = False
        messages: list[Any] = [{"role": "user", "content": content}]
        all_content_blocks: list[Any] = []
        total_input_tokens = 0
        total_output_tokens = 0
        final_stop_reason = "unknown"
        max_pause_continuations = 10
        container_id = None

        try:
            for continuation in range(max_pause_continuations + 1):
                try:
                    response = self.client.beta.messages.create(
                        model=self.model,
                        betas=["code-execution-2025-08-25", "files-api-2025-04-14"],
                        max_tokens=16384,
                        temperature=0,
                        messages=messages,
                        tools=[
                            {
                                "type": "code_execution_20250825",
                                "name": "code_execution",
                            }
                        ],
                    )
                except Exception as e:
                    if is_content_filter_error(str(e)):
                        print("  BLOCKED: Content filter triggered")
                        content_filter_triggered = True
                        break
                    raise

                all_content_blocks.extend(response.content)
                total_input_tokens += response.usage.input_tokens
                total_output_tokens += response.usage.output_tokens
                final_stop_reason = response.stop_reason or "unknown"

                resp_container = getattr(response, "container", None)
                if resp_container:
                    container_id = getattr(resp_container, "id", None) or container_id

                if final_stop_reason != "pause_turn":
                    break

                print(f"  Model paused (continuation {continuation + 1}), resuming...")
                messages.append({"role": "assistant", "content": response.content})

            if final_stop_reason == "pause_turn":
                print(
                    f"  WARNING: Model still paused after {max_pause_continuations} continuations"
                )

        finally:
            for file_id in file_ids:
                try:
                    self.client.beta.files.delete(file_id)
                except Exception as e:
                    print(f"  Warning: Failed to delete file {file_id}: {e}")

        latency_ms = (time.time() - start) * 1000

        if content_filter_triggered:
            return LLMResponse(
                raw_text="",
                parsed_json=None,
                model=self.model,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                latency_ms=latency_ms,
                stop_reason="content_filter",
                output_files=None,
            )

        raw_text = ""
        output_files: list[OutputFile] = []
        extracted_file_ids: list[str] = []

        for block in all_content_blocks:
            block_type = getattr(block, "type", None)

            if block_type == "text":
                block_text = getattr(block, "text", None)
                if block_text:
                    raw_text += block_text + "\n"

            elif block_type == "bash_code_execution_tool_result":
                block_content = getattr(block, "content", None)
                if block_content:
                    content_type = getattr(block_content, "type", None)
                    if content_type == "bash_code_execution_result":
                        stdout = getattr(block_content, "stdout", None)
                        if stdout:
                            raw_text += stdout + "\n"
                        inner_content = getattr(block_content, "content", []) or []
                        for item in inner_content:
                            file_id = getattr(item, "file_id", None)
                            if file_id:
                                extracted_file_ids.append(file_id)

            elif block_type == "text_editor_code_execution_tool_result":
                block_content = getattr(block, "content", None)
                if block_content:
                    content_text = getattr(block_content, "content", None)
                    if content_text and isinstance(content_text, str):
                        raw_text += content_text + "\n"

            elif block_type == "code_execution_result":
                container_id = getattr(block, "container_id", None) or container_id
                block_content = getattr(block, "content", None)
                if block_content:
                    for item in block_content:
                        stdout = getattr(item, "stdout", None)
                        item_text = getattr(item, "text", None)
                        if stdout:
                            raw_text += stdout + "\n"
                        elif item_text:
                            raw_text += item_text + "\n"

        for file_id in extracted_file_ids:
            try:
                file_metadata = self.client.beta.files.retrieve_metadata(file_id)
                print(f"  Downloading output file: {file_metadata.filename}")
                file_content = self.client.beta.files.download(file_id)
                output_files.append(
                    OutputFile(
                        filename=file_metadata.filename,
                        content=cast(bytes, read_file_content(file_content)),
                        mime_type=getattr(
                            file_metadata, "mime_type", "application/octet-stream"
                        ),
                    )
                )
            except Exception as e:
                print(f"  Warning: Failed to download file {file_id}: {e}")

        if not output_files and container_id:
            try:
                container_files = self.client.beta.files.list(
                    container_id=container_id  # type: ignore[call-arg]
                )
                for cf in container_files.data:
                    print(f"  Downloading output file: {cf.filename}")
                    file_content = self.client.beta.files.download(cf.id)
                    output_files.append(
                        OutputFile(
                            filename=cf.filename,
                            content=cast(bytes, read_file_content(file_content)),
                            mime_type=getattr(
                                cf, "mime_type", "application/octet-stream"
                            ),
                        )
                    )
            except Exception as e:
                print(f"  Warning: Failed to retrieve container files: {e}")

        parsed_json = extract_json(raw_text)

        if final_stop_reason == "max_tokens":
            print("  WARNING: Output truncated (hit max_tokens limit)")

        return LLMResponse(
            raw_text=raw_text,
            parsed_json=parsed_json,
            model=self.model,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            latency_ms=latency_ms,
            stop_reason=final_stop_reason,
            output_files=output_files if output_files else None,
        )
