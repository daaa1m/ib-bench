"""Azure AI Foundry Agent Service runner for IB-bench evaluation pipeline."""

import os
import time
from pathlib import Path

from helpers import Task, extract_json, retry_on_rate_limit

from .base import (
    LLMResponse,
    OutputFile,
    categorize_input_files,
    is_content_filter_error,
)


def extract_text_from_messages(messages: list) -> str:
    """
    Extract text content from Azure agent messages.

    :param messages: List of agent message objects
    :returns: Concatenated text from assistant messages

    Handles: text_messages attribute on message objects.
    Does not handle: Complex nested content structures.
    """
    text_parts = []

    for msg in messages:
        if getattr(msg, "role", None) != "assistant":
            continue

        # Handle text_messages attribute (list of text message objects)
        text_messages = getattr(msg, "text_messages", None)
        if text_messages:
            for tm in text_messages:
                text_value = getattr(tm, "text", None)
                if text_value:
                    # text might be an object with .value or a string
                    if hasattr(text_value, "value"):
                        text_parts.append(text_value.value)
                    elif isinstance(text_value, str):
                        text_parts.append(text_value)

        # Handle content attribute (list of content blocks)
        content = getattr(msg, "content", None)
        if content and isinstance(content, list):
            for block in content:
                if hasattr(block, "text"):
                    text_obj = block.text
                    if hasattr(text_obj, "value"):
                        text_parts.append(text_obj.value)
                    elif isinstance(text_obj, str):
                        text_parts.append(text_obj)

    return "\n".join(text_parts)


def map_run_status_to_stop_reason(status: str, last_error: str | None) -> str:
    """
    Map Azure run status to standardized stop_reason.

    :param status: Azure run status (completed, failed, expired, etc.)
    :param last_error: Error message if run failed
    :returns: Normalized stop_reason string
    """
    status_lower = status.lower() if status else "unknown"

    if status_lower == "completed":
        return "end_turn"
    elif status_lower == "failed":
        if last_error and is_content_filter_error(last_error):
            return "content_filter"
        return "failed"
    elif status_lower == "expired":
        return "expired"
    elif status_lower == "cancelled":
        return "cancelled"
    else:
        return status_lower


class AzureAgentRunner:
    """
    Run tasks against Azure AI Foundry Agent Service.

    Supports multiple model providers (OpenAI, DeepSeek, Llama, Grok, etc.)
    via the unified Agent Service API. Uses code_interpreter for Excel/CSV
    and file_search for PDFs.

    :param api_key: Azure API key (optional if using DefaultAzureCredential)
    :param model: Deployment name in Azure AI Foundry (required)

    Environment variables:
        AZURE_AI_PROJECT_ENDPOINT: Project endpoint URL
        AZURE_AI_PROJECT_CONNECTION_STRING: Alternative to endpoint
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        if not model:
            raise ValueError("model (deployment name) is required for AzureAgentRunner")

        self.model = model
        self.api_key = api_key
        self._client = None

        self._endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
        self._connection_string = os.environ.get("AZURE_AI_PROJECT_CONNECTION_STRING")

        if not self._endpoint and not self._connection_string:
            raise ValueError(
                "AZURE_AI_PROJECT_ENDPOINT or AZURE_AI_PROJECT_CONNECTION_STRING must be set"
            )

    @property
    def client(self):
        """Lazy initialization of Azure AI Project client."""
        if self._client is None:
            from azure.ai.projects import AIProjectClient
            from azure.identity import DefaultAzureCredential

            if self._connection_string:
                self._client = AIProjectClient.from_connection_string(
                    credential=DefaultAzureCredential(),
                    conn_str=self._connection_string,
                )
            else:
                self._client = AIProjectClient(
                    endpoint=self._endpoint,
                    credential=DefaultAzureCredential(),
                )
        return self._client

    def _upload_file(self, path: Path, purpose: str) -> str:
        """
        Upload a file to Azure for use with agents.

        :param path: Local file path
        :param purpose: File purpose (e.g., "agents")
        :returns: Uploaded file ID
        """
        from azure.ai.agents.models import FilePurpose

        purpose_enum = FilePurpose.AGENTS if purpose == "agents" else FilePurpose.AGENTS
        print(f"  Uploading {path.name} to Azure...")
        file = self.client.agents.files.upload_and_poll(
            file_path=str(path), purpose=purpose_enum
        )
        return file.id

    def _create_vector_store(self, file_ids: list[str], name: str) -> str:
        """
        Create a vector store for file search.

        :param file_ids: List of uploaded file IDs
        :param name: Vector store name
        :returns: Vector store ID
        """
        print("  Creating vector store for file search...")
        vector_store = self.client.agents.vector_stores.create_and_poll(
            file_ids=file_ids, name=name
        )
        return vector_store.id

    def _delete_file(self, file_id: str) -> None:
        """Delete an uploaded file."""
        try:
            self.client.agents.files.delete(file_id)
        except Exception as e:
            print(f"  Warning: Failed to delete file {file_id}: {e}")

    def _delete_vector_store(self, vector_store_id: str) -> None:
        """Delete a vector store."""
        try:
            self.client.agents.vector_stores.delete(vector_store_id)
        except Exception as e:
            print(f"  Warning: Failed to delete vector store {vector_store_id}: {e}")

    def _delete_agent(self, agent_id: str) -> None:
        """Delete an agent."""
        try:
            self.client.agents.delete_agent(agent_id)
        except Exception as e:
            print(f"  Warning: Failed to delete agent {agent_id}: {e}")

    def _download_output_files(self, messages: list) -> list[OutputFile]:
        """
        Download files generated by the agent (charts, modified Excel, etc.).

        :param messages: List of agent messages
        :returns: List of OutputFile objects
        """
        output_files = []
        file_counter = 0

        for msg in messages:
            if getattr(msg, "role", None) != "assistant":
                continue

            # Check for image_contents
            image_contents = getattr(msg, "image_contents", None)
            if image_contents:
                for img in image_contents:
                    image_file = getattr(img, "image_file", None)
                    if image_file:
                        file_id = getattr(image_file, "file_id", None)
                        if file_id:
                            file_counter += 1
                            filename = f"output_{file_counter}.png"
                            try:
                                print(f"  Downloading output file: {filename}")
                                content = b"".join(
                                    self.client.agents.files.get_content(file_id)
                                )
                                output_files.append(
                                    OutputFile(
                                        filename=filename,
                                        content=content,
                                        mime_type="image/png",
                                    )
                                )
                            except Exception as e:
                                print(f"  Warning: Failed to download {file_id}: {e}")

            text_messages = getattr(msg, "text_messages", None)
            if text_messages:
                for tm in text_messages:
                    text_obj = getattr(tm, "text", None)
                    annotations = (
                        getattr(text_obj, "annotations", None) if text_obj else None
                    )
                    if annotations:
                        for ann in annotations:
                            file_path = (
                                ann.get("file_path")
                                if isinstance(ann, dict)
                                else getattr(ann, "file_path", None)
                            )
                            if file_path:
                                file_id = (
                                    file_path.get("file_id")
                                    if isinstance(file_path, dict)
                                    else getattr(file_path, "file_id", None)
                                )
                                if file_id:
                                    file_counter += 1
                                    ext = "xlsx"
                                    filename = f"output_{file_counter}.{ext}"
                                    try:
                                        print(f"  Downloading output file: {filename}")
                                        content = b"".join(
                                            self.client.agents.files.get_content(
                                                file_id
                                            )
                                        )
                                        output_files.append(
                                            OutputFile(
                                                filename=filename,
                                                content=content,
                                                mime_type="application/octet-stream",
                                            )
                                        )
                                    except Exception as e:
                                        print(
                                            f"  Warning: Failed to download {file_id}: {e}"
                                        )
                    if annotations:
                        for ann in annotations:
                            file_path = getattr(ann, "file_path", None)
                            if file_path:
                                file_id = getattr(file_path, "file_id", None)
                                if file_id:
                                    file_counter += 1
                                    ext = "xlsx"  # Default for file outputs
                                    filename = f"output_{file_counter}.{ext}"
                                    try:
                                        print(f"  Downloading output file: {filename}")
                                        content = b"".join(
                                            self.client.agents.files.get_content(
                                                file_id
                                            )
                                        )
                                        output_files.append(
                                            OutputFile(
                                                filename=filename,
                                                content=content,
                                                mime_type="application/octet-stream",
                                            )
                                        )
                                    except Exception as e:
                                        print(
                                            f"  Warning: Failed to download {file_id}: {e}"
                                        )

        return output_files

    @retry_on_rate_limit(max_retries=3, initial_wait=60)
    def run(self, task: Task, input_files: list[Path] | None = None) -> LLMResponse:
        """
        Execute a task using Azure AI Foundry Agent Service.

        :param task: Task object with prompt and metadata
        :param input_files: Optional list of input file paths
        :returns: LLMResponse with text, parsed JSON, and output files

        Uses code_interpreter for xlsx/csv files, file_search for PDFs.
        Agent and resources are cleaned up after execution.
        """
        from azure.ai.agents.models import (
            CodeInterpreterTool,
            FileSearchTool,
            ToolResources,
        )

        start = time.time()
        files = input_files or []

        code_files, search_files = categorize_input_files(files)

        uploaded_file_ids: list[str] = []
        vector_store_id: str | None = None
        agent_id: str | None = None

        try:
            code_file_ids = []
            for f in code_files:
                fid = self._upload_file(f, "agents")
                code_file_ids.append(fid)
                uploaded_file_ids.append(fid)

            search_file_ids = []
            for f in search_files:
                fid = self._upload_file(f, "agents")
                search_file_ids.append(fid)
                uploaded_file_ids.append(fid)

            if search_file_ids:
                vector_store_id = self._create_vector_store(
                    search_file_ids, "ib-bench-docs"
                )

            tools = []
            code_interpreter_resource = None
            file_search_resource = None

            if code_file_ids:
                code_interpreter = CodeInterpreterTool(file_ids=code_file_ids)
                tools.extend(code_interpreter.definitions)
                code_interpreter_resource = code_interpreter.resources.code_interpreter
            elif files:
                code_interpreter = CodeInterpreterTool()
                tools.extend(code_interpreter.definitions)

            if vector_store_id:
                file_search = FileSearchTool(vector_store_ids=[vector_store_id])
                tools.extend(file_search.definitions)
                file_search_resource = file_search.resources.file_search

            tool_resources = None
            if code_interpreter_resource or file_search_resource:
                tool_resources = ToolResources(
                    code_interpreter=code_interpreter_resource,
                    file_search=file_search_resource,
                )

            print(f"  Creating agent with model {self.model}...")
            agent = self.client.agents.create_agent(
                model=self.model,
                name="ib-bench-agent",
                instructions="You are an expert investment banking analyst. Analyze the provided files and respond precisely to the task.",
                tools=tools if tools else None,
                tool_resources=tool_resources if tool_resources else None,
                temperature=0,
            )
            agent_id = agent.id

            thread = self.client.agents.threads.create()

            self.client.agents.messages.create(
                thread_id=thread.id, role="user", content=task.prompt
            )

            print("  Running agent...")
            run = self.client.agents.runs.create_and_process(
                thread_id=thread.id, agent_id=agent_id
            )

            run_status = getattr(run, "status", "unknown")
            last_error = None
            if run_status == "failed":
                last_error_obj = getattr(run, "last_error", None)
                last_error = str(last_error_obj) if last_error_obj else None
                print(f"  Run failed: {last_error}")

            messages = list(self.client.agents.messages.list(thread_id=thread.id))

            usage = getattr(run, "usage", None)
            input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

            latency_ms = (time.time() - start) * 1000

            raw_text = extract_text_from_messages(messages)

            stop_reason = map_run_status_to_stop_reason(run_status, last_error)

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

            output_files = self._download_output_files(messages)

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
            if agent_id:
                self._delete_agent(agent_id)
            if vector_store_id:
                self._delete_vector_store(vector_store_id)
            for fid in uploaded_file_ids:
                self._delete_file(fid)
