"""OpenAI runner for IB-bench evaluation pipeline."""

import os
import time
from pathlib import Path
from typing import cast

from helpers import Task, extract_json, retry_on_rate_limit

from .base import LLMResponse, OutputFile, is_content_filter_error, read_file_content


class OpenAIRunner:
    """Run tasks against OpenAI models using Responses API."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        if not model:
            raise ValueError("model is required for OpenAIRunner")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")
        self.model = model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import openai

            self._client = openai.OpenAI(api_key=self.api_key)
        return self._client

    def _upload_file(self, path: Path) -> str:
        """Upload file to OpenAI Files API for use with Responses API."""
        with open(path, "rb") as f:
            file = self.client.files.create(file=f, purpose="user_data")
        return file.id

    # OpenAI's file_search tool requires files to be indexed in a vector store
    # before querying. We create a temp store, add files, then poll until
    # indexing completes (async on their end).
    def _create_vector_store(self, file_ids: list[str]) -> str:
        """Create a vector store with uploaded files for file_search."""
        vs = self.client.vector_stores.create(name="ib-bench-temp")
        for fid in file_ids:
            self.client.vector_stores.files.create(vector_store_id=vs.id, file_id=fid)
        print("Waiting for vector store indexing...")
        while True:
            vs_status = self.client.vector_stores.retrieve(vs.id)
            if vs_status.file_counts.completed == len(file_ids):
                break
            if vs_status.file_counts.failed > 0:
                print(
                    f"  Warning: {vs_status.file_counts.failed} file(s) failed to index"
                )
                break
            time.sleep(1)
        return vs.id

    @retry_on_rate_limit(max_retries=3, initial_wait=60)
    def run(self, task: Task, input_files: list[Path] | None = None) -> LLMResponse:
        """Execute a task using Responses API with tools."""
        import base64

        start = time.time()
        files = input_files or []
        tools: list[dict] = [{"type": "web_search"}]
        vector_store_id = None
        uploaded_file_ids = []

        pdf_files = [f for f in files if f.suffix.lower() == ".pdf"]
        code_files = [f for f in files if f.suffix.lower() in [".xlsx", ".xls", ".csv"]]
        image_files = [
            f for f in files if f.suffix.lower() in [".png", ".jpg", ".jpeg"]
        ]

        if pdf_files:
            print(f"Uploading {len(pdf_files)} PDF(s) for file search...")
            pdf_file_ids = []
            for pdf in pdf_files:
                fid = self._upload_file(pdf)
                pdf_file_ids.append(fid)
                uploaded_file_ids.append(fid)
            vector_store_id = self._create_vector_store(pdf_file_ids)
            tools.append(
                {
                    "type": "file_search",
                    "vector_store_ids": [vector_store_id],
                }
            )

        code_file_ids = []
        if code_files:
            print(f"Uploading {len(code_files)} file(s) for code interpreter...")
            for cf in code_files:
                fid = self._upload_file(cf)
                code_file_ids.append(fid)
                uploaded_file_ids.append(fid)
            tools.append(
                {
                    "type": "code_interpreter",
                    "container": {"type": "auto", "file_ids": code_file_ids},
                }
            )

        input_content = []

        for img in image_files:
            print(f"Encoding {img.name} as base64...")
            with open(img, "rb") as f:
                img_data = base64.b64encode(f.read()).decode("utf-8")
            ext = img.suffix.lower().replace(".", "")
            mime = f"image/{ext}" if ext != "jpg" else "image/jpeg"
            input_content.append(
                {
                    "type": "input_image",
                    "image_url": {"url": f"data:{mime};base64,{img_data}"},
                }
            )

        input_content.append(
            {
                "type": "input_text",
                "text": task.prompt,
            }
        )

        if len(input_content) == 1:
            api_input = task.prompt
        else:
            api_input = [{"role": "user", "content": input_content}]

        print("Running Responses API...")
        content_filter_triggered = False
        try:
            response = self.client.responses.create(
                model=self.model,
                input=api_input,  # type: ignore[arg-type]
                tools=tools if tools else None,  # type: ignore[arg-type]
                temperature=0,
                max_output_tokens=16384,
            )
        except Exception as e:
            if is_content_filter_error(str(e)):
                print("  BLOCKED: Content filter triggered")
                content_filter_triggered = True
                response = None
            else:
                raise
        finally:
            if vector_store_id:
                try:
                    self.client.vector_stores.delete(vector_store_id)
                except Exception as e:
                    print(f"  Warning: Failed to delete vector store: {e}")

            for fid in uploaded_file_ids:
                try:
                    self.client.files.delete(fid)
                except Exception as e:
                    print(f"  Warning: Failed to delete file {fid}: {e}")

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
        response_text = response.output_text or ""

        # Extract files from container - list all files and filter out uploaded inputs
        output_files: list[OutputFile] = []
        container_id = None
        if hasattr(response, "output") and response.output:
            for item in response.output:
                if getattr(item, "type", None) == "code_interpreter_call":
                    container_id = getattr(item, "container_id", None)
                    if container_id:
                        break

        if container_id:
            try:
                container_files = self.client.containers.files.list(
                    container_id=container_id
                )
                uploaded_names = {f.name for f in (input_files or [])}
                for idx, cf in enumerate(container_files.data):
                    fid = getattr(cf, "id", None)
                    fpath = getattr(cf, "path", None) or f"output_{idx + 1}.bin"
                    fname = fpath.split("/")[-1] if "/" in fpath else fpath
                    is_uploaded = any(uname in fname for uname in uploaded_names)
                    if fid and not is_uploaded:
                        print(f"  Downloading output file: {fname}")
                        file_content = self.client.containers.files.content.retrieve(
                            fid, container_id=container_id
                        )
                        output_files.append(
                            OutputFile(
                                filename=fname,
                                content=cast(bytes, read_file_content(file_content)),
                                mime_type="application/octet-stream",
                            )
                        )
            except Exception as e:
                print(f"  Warning: Failed to retrieve container files: {e}")

        usage = response.usage
        input_tokens = usage.input_tokens if usage else 0
        output_tokens = usage.output_tokens if usage else 0

        stop_reason = getattr(response, "stop_reason", None) or "unknown"
        if stop_reason == "length":
            stop_reason = "max_tokens"
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
