"""Azure AI Foundry V2 runner using Responses API with Containers."""

import os
import time
from pathlib import Path
from typing import cast

from helpers import Task, extract_json, retry_on_rate_limit

from .base import LLMResponse, OutputFile, categorize_input_files


BRAVE_SEARCH_TOOL = {
    "type": "function",
    "name": "web_search",
    "description": "Search the web for current information. Use this when you need up-to-date data, recent news, or information not in your training data.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query",
            }
        },
        "required": ["query"],
    },
}


class AzureAgentRunnerV2:
    """
    Run tasks against Azure AI Foundry using the v2 SDK (Responses API).

    Uses containers for code_interpreter, vector stores for file_search,
    and web_search for internet access. All three tools enabled by default.

    Web search defaults to Brave via function calling.
    Set web_search_mode="native" to use web_search_preview for OpenAI models.

    :param model: Deployment name in Azure AI Foundry (required)

    Environment variables:
        AZURE_AI_PROJECT_ENDPOINT: Project endpoint URL
        BRAVE_API_KEY: Required for non-OpenAI models
    """

    def __init__(self, model: str | None = None, web_search_mode: str = "brave"):
        if not model:
            raise ValueError(
                "model (deployment name) is required for AzureAgentRunnerV2"
            )

        self.model = model
        self._client = None
        self._openai = None

        self._endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
        if not self._endpoint:
            raise ValueError("AZURE_AI_PROJECT_ENDPOINT must be set")

        self._brave_api_key = os.environ.get("BRAVE_API_KEY")
        self._web_search_mode = web_search_mode.lower()
        if self._web_search_mode not in {"brave", "native"}:
            raise ValueError("web_search_mode must be 'brave' or 'native'")

        self._no_temperature_models = {"gpt-5.2-chat"}

    def _is_openai_model(self) -> bool:
        m = self.model.lower()
        return m.startswith(("gpt-", "o1", "o3", "o4"))

    def _use_native_web_search(self) -> bool:
        if self._web_search_mode != "native":
            return False
        if not self._is_openai_model():
            print(
                "  Warning: native web_search_preview requires an OpenAI model; "
                "falling back to Brave search."
            )
            return False
        return True

    def _supports_temperature(self) -> bool:
        return self.model.lower() not in self._no_temperature_models

    def _create_response(self, **kwargs):
        if self._supports_temperature():
            kwargs.setdefault("temperature", 0)
        else:
            kwargs.pop("temperature", None)
        return self.openai.responses.create(**kwargs)

    def _brave_search(self, query: str) -> str:
        import urllib.request
        import urllib.parse

        if not self._brave_api_key:
            return "Error: BRAVE_API_KEY not set"

        url = (
            "https://api.search.brave.com/res/v1/web/search?"
            + urllib.parse.urlencode({"q": query, "count": 5})
        )
        req = urllib.request.Request(url)
        req.add_header("X-Subscription-Token", self._brave_api_key)
        req.add_header("Accept", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                import json

                data = json.loads(resp.read().decode())
                results = []
                for item in data.get("web", {}).get("results", [])[:5]:
                    results.append(
                        f"Title: {item.get('title', '')}\n"
                        f"URL: {item.get('url', '')}\n"
                        f"Description: {item.get('description', '')}"
                    )
                return "\n\n".join(results) if results else "No results found"
        except Exception as e:
            return f"Search error: {e}"

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

    def _upload_to_container(self, container_id: str, path: Path) -> str:
        print(f"  Uploading {path.name} to container...")
        with open(path, "rb") as f:
            file = self.openai.containers.files.create(
                container_id=container_id,
                file=f,
            )
        return file.id

    def _delete_container(self, container_id: str) -> None:
        try:
            self.openai.containers.delete(container_id)
            print(f"  Deleted container: {container_id}")
        except Exception as e:
            print(f"  Warning: Failed to delete container {container_id}: {e}")

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

    def _extract_output_files_from_response(
        self, response, container_id: str
    ) -> list[OutputFile]:
        output_files = []
        file_counter = 0

        output = getattr(response, "output", None)
        if not output:
            return output_files

        for item in output:
            item_type = getattr(item, "type", None)

            if item_type == "message":
                content_list = getattr(item, "content", None)
                if not content_list:
                    continue

                for content in content_list:
                    content_type = getattr(content, "type", None)

                    if content_type == "output_text":
                        annotations = getattr(content, "annotations", None)
                        if annotations:
                            for ann in annotations:
                                ann_type = getattr(ann, "type", None)
                                if ann_type == "container_file_citation":
                                    file_id = getattr(ann, "file_id", None)
                                    filename = getattr(
                                        ann,
                                        "filename",
                                        f"output_{file_counter + 1}.xlsx",
                                    )
                                    if file_id:
                                        file_counter += 1
                                        try:
                                            print(
                                                f"  Downloading output file: {filename}"
                                            )
                                            resp = self.openai.containers.files.content.retrieve(
                                                container_id=container_id,
                                                file_id=file_id,
                                            )
                                            content_bytes = resp.read()
                                            ext = (
                                                Path(filename).suffix.lstrip(".")
                                                or "xlsx"
                                            )
                                            output_files.append(
                                                OutputFile(
                                                    filename=f"output_{file_counter}.{ext}",
                                                    content=content_bytes,
                                                    mime_type="application/octet-stream",
                                                )
                                            )
                                        except Exception as e:
                                            print(
                                                f"  Warning: Failed to download {filename}: {e}"
                                            )

        return output_files

    @retry_on_rate_limit(max_retries=3, initial_wait=60)
    def run(self, task: Task, input_files: list[Path] | None = None) -> LLMResponse:
        start = time.time()
        files = input_files or []

        code_files, search_files = categorize_input_files(files)

        container_id: str | None = None
        vector_store_id: str | None = None
        uploaded_file_ids: list[str] = []
        new_response_after_loop = False

        try:
            container_id = self._create_container(f"ib-bench-{task.id}")

            for f in code_files:
                self._upload_to_container(container_id, f)

            if search_files:
                for f in search_files:
                    fid = self._upload_file(f)
                    uploaded_file_ids.append(fid)
                vector_store_id = self._create_vector_store(
                    uploaded_file_ids, f"ib-bench-{task.id}-docs"
                )

            tools = []
            tools.append({"type": "code_interpreter", "container": container_id})

            if vector_store_id:
                tools.append(
                    {"type": "file_search", "vector_store_ids": [vector_store_id]}
                )

            use_native_web_search = self._use_native_web_search()
            if use_native_web_search:
                tools.append({"type": "web_search_preview"})
            else:
                tools.append(BRAVE_SEARCH_TOOL)

            print(f"  Running {self.model} via Responses API...")
            response = self._create_response(
                model=self.model,
                tools=cast(list, tools),
                input=task.prompt,
            )

            total_input_tokens = 0
            total_output_tokens = 0

            if not use_native_web_search:
                max_tool_calls = 10
                for _ in range(max_tool_calls):
                    usage = getattr(response, "usage", None)
                    total_input_tokens += (
                        getattr(usage, "input_tokens", 0) if usage else 0
                    )
                    total_output_tokens += (
                        getattr(usage, "output_tokens", 0) if usage else 0
                    )

                    function_call = None
                    output = getattr(response, "output", None)
                    if output:
                        for item in output:
                            if getattr(item, "type", None) == "function_call":
                                if getattr(item, "name", None) == "web_search":
                                    function_call = item
                                    break

                    if not function_call:
                        break

                    args = getattr(function_call, "arguments", "{}")
                    call_id = getattr(function_call, "call_id", "")
                    import json as _json

                    query = _json.loads(args).get("query", "")
                    print(f"  Brave search: {query}")
                    search_results = self._brave_search(query)

                    response = self._create_response(
                        model=self.model,
                        tools=cast(list, tools),
                        input=[
                            {
                                "type": "function_call_output",
                                "call_id": call_id,
                                "output": search_results,
                            }
                        ],
                        previous_response_id=response.id,
                    )

                output = getattr(response, "output", None)
                pending_call_id = None
                if output:
                    for item in output:
                        if getattr(item, "type", None) == "function_call":
                            pending_call_id = getattr(item, "call_id", None)
                            break

                if pending_call_id:
                    print("  Forcing final answer (max searches reached)...")
                    response = self._create_response(
                        model=self.model,
                        tools=cast(list, tools),
                        input=[
                            {
                                "type": "function_call_output",
                                "call_id": pending_call_id,
                                "output": "Search limit reached. Please provide your final answer based on the information gathered so far.",
                            }
                        ],
                        previous_response_id=response.id,
                    )
                    new_response_after_loop = True

            latency_ms = (time.time() - start) * 1000

            raw_text = ""
            output = getattr(response, "output", None)
            if output:
                for item in output:
                    item_type = getattr(item, "type", None)
                    if item_type == "message":
                        content = getattr(item, "content", None)
                        if content:
                            for c in content:
                                c_type = getattr(c, "type", None)
                                if c_type == "output_text":
                                    raw_text += getattr(c, "text", "")
                                elif c_type == "text":
                                    raw_text += getattr(c, "text", "")

            usage = getattr(response, "usage", None)
            if use_native_web_search:
                input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
                output_tokens = getattr(usage, "output_tokens", 0) if usage else 0
            else:
                if new_response_after_loop:
                    total_input_tokens += (
                        getattr(usage, "input_tokens", 0) if usage else 0
                    )
                    total_output_tokens += (
                        getattr(usage, "output_tokens", 0) if usage else 0
                    )
                input_tokens = total_input_tokens
                output_tokens = total_output_tokens

            stop_reason = "end_turn"
            status = getattr(response, "status", None)
            if status == "incomplete":
                incomplete_details = getattr(response, "incomplete_details", None)
                if incomplete_details:
                    reason = getattr(incomplete_details, "reason", None)
                    if reason == "max_output_tokens":
                        stop_reason = "max_tokens"
                    elif reason == "content_filter":
                        stop_reason = "content_filter"

            if stop_reason == "content_filter":
                print("  BLOCKED: Content filter triggered")
                return LLMResponse(
                    raw_text="",
                    parsed_json=None,
                    model=self.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    stop_reason="content_filter",
                    output_files=None,
                )

            output_files = self._extract_output_files_from_response(
                response, container_id
            )
            parsed_json = extract_json(raw_text)

            return LLMResponse(
                raw_text=raw_text.strip(),
                parsed_json=parsed_json,
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                stop_reason=stop_reason,
                output_files=output_files if output_files else None,
            )

        finally:
            if container_id:
                self._delete_container(container_id)
            if vector_store_id:
                self._delete_vector_store(vector_store_id)
            for fid in uploaded_file_ids:
                self._delete_file(fid)
