"""Judge runners for LLM-as-judge scoring."""

import os
import sys
import time
from pathlib import Path
from typing import Any, Literal, Protocol, cast

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers import retry_on_rate_limit
from runners.base import categorize_input_files

JudgeProvider = Literal["anthropic", "azure-v2"]

DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-5"
DEFAULT_AZURE_MODEL = "gpt-5.2-chat"


class JudgeRunner(Protocol):
    """Protocol for judge runners that send prompts with files and return text."""

    model: str

    def judge(self, prompt: str, files: list[Path]) -> str:
        """Send prompt with optional files, return response text."""
        ...


class AnthropicJudge:
    """Judge runner using Anthropic's Claude with Files API."""

    def __init__(self, model: str = DEFAULT_ANTHROPIC_MODEL):
        self.model = model
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    # Expected output: raw JSON text containing a top-level "scores" key.
    # Output parsed by _parse_response() in llm-judge/llm_judge.py
    def _extract_text(self, response: Any) -> str:
        text_blocks = []
        for block in response.content:
            if hasattr(block, "text") and block.text:
                text_blocks.append(block.text)
            elif hasattr(block, "type") and block.type == "code_execution_result":
                for item in getattr(block, "content", []):
                    stdout = getattr(item, "stdout", None)
                    text = getattr(item, "text", None)
                    if stdout:
                        text_blocks.append(stdout)
                    elif text:
                        text_blocks.append(text)

        for text in text_blocks:
            if '{"scores"' in text or '"scores":' in text:
                return text

        return "\n".join(text_blocks)

    @retry_on_rate_limit(max_retries=3, initial_wait=60)
    def _call_api(self, content: list[dict[str, Any]]) -> Any:
        return self.client.beta.messages.create(
            model=self.model,
            betas=["code-execution-2025-08-25", "files-api-2025-04-14"],
            max_tokens=16384,
            temperature=0,
            messages=cast(Any, [{"role": "user", "content": content}]),
            tools=[
                {"type": "code_execution_20250825", "name": "code_execution"},
                {"type": "web_search_20250305", "name": "web_search", "max_uses": 5},
            ],
        )

    def judge(self, prompt: str, files: list[Path]) -> str:
        file_objects = []
        if files:
            print(f"  Uploading {len(files)} file(s) for judging...")
            for f in files:
                with open(f, "rb") as fp:
                    file_obj = self.client.beta.files.upload(file=fp)
                    file_objects.append(file_obj)

        content: list[dict[str, Any]] = [
            {"type": "container_upload", "file_id": fo.id} for fo in file_objects
        ]
        content.append({"type": "text", "text": prompt})

        start = time.time()
        try:
            response = self._call_api(content)
        finally:
            for fo in file_objects:
                try:
                    self.client.beta.files.delete(fo.id)
                except Exception as e:
                    print(f"  Warning: Failed to delete file {fo.id}: {e}")

        print(f"  Judge completed in {(time.time() - start) * 1000:.0f}ms")
        return self._extract_text(response)


class AzureJudge:
    """Judge runner using Azure AI Foundry Responses API."""

    def __init__(self, model: str):
        if not model:
            raise ValueError("model (deployment name) required for AzureJudge")
        self.model = model
        self._client = None
        self._openai = None

        self._endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
        if not self._endpoint:
            raise ValueError("AZURE_AI_PROJECT_ENDPOINT must be set")
        self._endpoint = cast(str, self._endpoint)

    @property
    def client(self):
        if self._client is None:
            from azure.ai.projects import AIProjectClient
            from azure.identity import DefaultAzureCredential

            assert self._endpoint is not None
            self._client = AIProjectClient(
                endpoint=self._endpoint,
                credential=DefaultAzureCredential(),
            )
        return self._client

    @property
    def openai(self):
        if self._openai is None:
            self._openai = self.client.get_openai_client()
        return self._openai

    def _create_container(self, name: str) -> str:
        print(f"  Creating container: {name}")
        container = self.openai.containers.create(name=name)
        return container.id

    def _upload_to_container(self, container_id: str, path: Path) -> None:
        print(f"  Uploading {path.name} to container...")
        with open(path, "rb") as f:
            self.openai.containers.files.create(container_id=container_id, file=f)

    def _upload_file(self, path: Path) -> str:
        print(f"  Uploading {path.name} for file search...")
        with open(path, "rb") as f:
            file = self.openai.files.create(file=f, purpose="assistants")
        return file.id

    def _create_vector_store(self, file_ids: list[str], name: str) -> str:
        print(f"  Creating vector store: {name}")
        vector_store = self.openai.vector_stores.create(name=name, file_ids=file_ids)
        return vector_store.id

    def _delete_vector_store(self, vector_store_id: str) -> None:
        try:
            self.openai.vector_stores.delete(vector_store_id)
            print(f"  Deleted vector store: {vector_store_id}")
        except Exception as e:
            print(f"  Warning: Failed to delete vector store {vector_store_id}: {e}")

    def _delete_file(self, file_id: str) -> None:
        try:
            self.openai.files.delete(file_id)
        except Exception as e:
            print(f"  Warning: Failed to delete file {file_id}: {e}")

    def _delete_container(self, container_id: str) -> None:
        try:
            self.openai.containers.delete(container_id)
            print(f"  Deleted container: {container_id}")
        except Exception as e:
            print(f"  Warning: Failed to delete container {container_id}: {e}")

    @retry_on_rate_limit(max_retries=3, initial_wait=60)
    def judge(self, prompt: str, files: list[Path]) -> str:
        start = time.time()
        container_id: str | None = None
        vector_store_id: str | None = None
        uploaded_file_ids: list[str] = []

        try:
            tools = []
            code_files, search_files = categorize_input_files(files)

            if code_files:
                container_id = self._create_container(
                    f"ib-bench-judge-{int(time.time())}"
                )
                for f in code_files:
                    self._upload_to_container(container_id, f)
                tools.append({"type": "code_interpreter", "container": container_id})

            if search_files:
                for f in search_files:
                    fid = self._upload_file(f)
                    uploaded_file_ids.append(fid)
                vector_store_id = self._create_vector_store(
                    uploaded_file_ids, f"ib-bench-judge-{int(time.time())}-docs"
                )
                tools.append(
                    {"type": "file_search", "vector_store_ids": [vector_store_id]}
                )

            tools.append({"type": "web_search_preview"})
            # default model gpt-5.2-chat does not take temperature
            create_params: dict[str, Any] = {
                "model": self.model,
                "input": prompt,
            }
            if tools:
                create_params["tools"] = tools

            response = self.openai.responses.create(**create_params)
            # raw_text parsed by _parse_response() in llm-judge/llm_judge.py
            raw_text = ""
            output = getattr(response, "output", None)
            if output:
                for item in output:
                    if getattr(item, "type", None) == "message":
                        content = getattr(item, "content", None)
                        if content:
                            for c in content:
                                c_type = getattr(c, "type", None)
                                if c_type in {"output_text", "text"}:
                                    raw_text += getattr(c, "text", "")

            print(f"  Judge completed in {(time.time() - start) * 1000:.0f}ms")
            return raw_text

        finally:
            if container_id:
                self._delete_container(container_id)
            if vector_store_id:
                self._delete_vector_store(vector_store_id)
            for file_id in uploaded_file_ids:
                self._delete_file(file_id)


def get_judge_runner(provider: JudgeProvider, model: str | None = None) -> JudgeRunner:
    """Factory function to get the appropriate judge runner."""
    runners = {
        "anthropic": AnthropicJudge,
        "azure-v2": AzureJudge,
    }

    runner_class = runners.get(provider)
    if runner_class is None:
        raise ValueError(
            f"Unknown judge provider: {provider}. Available: {list(runners.keys())}"
        )

    if model is None:
        if provider == "anthropic":
            return runner_class()
        if provider == "azure-v2":
            return runner_class(model=DEFAULT_AZURE_MODEL)

    return runner_class(model=model)
