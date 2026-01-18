"""Judge runners for LLM-as-judge scoring."""

import os
import sys
import time
from pathlib import Path
from typing import Any, Literal, Protocol

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers import retry_on_rate_limit

JudgeProvider = Literal["anthropic", "openai", "azure"]


class JudgeRunner(Protocol):
    """Protocol for judge runners that send prompts with files and return text."""

    model: str

    def judge(self, prompt: str, files: list[Path]) -> str:
        """Send prompt with optional files, return response text."""
        ...


class AnthropicJudge:
    """Judge runner using Anthropic's Claude with Files API."""

    def __init__(self, model: str = "claude-sonnet-4-5"):
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
            messages=[{"role": "user", "content": content}],
            tools=[{"type": "code_execution_20250825", "name": "code_execution"}],
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
    """Judge runner using Azure AI Foundry Agent Service."""

    def __init__(self, model: str):
        if not model:
            raise ValueError("model (deployment name) required for AzureJudge")
        self.model = model
        self._client = None

        self._endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
        self._connection_string = os.environ.get("AZURE_AI_PROJECT_CONNECTION_STRING")

        if not self._endpoint and not self._connection_string:
            raise ValueError(
                "AZURE_AI_PROJECT_ENDPOINT or AZURE_AI_PROJECT_CONNECTION_STRING required"
            )

    @property
    def client(self):
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

    def _extract_text(self, messages: list) -> str:
        text_parts = []
        for msg in messages:
            if getattr(msg, "role", None) != "assistant":
                continue
            text_messages = getattr(msg, "text_messages", None)
            if text_messages:
                for tm in text_messages:
                    text_value = getattr(tm, "text", None)
                    if text_value:
                        if hasattr(text_value, "value"):
                            text_parts.append(text_value.value)
                        elif isinstance(text_value, str):
                            text_parts.append(text_value)
        return "\n".join(text_parts)

    @retry_on_rate_limit(max_retries=3, initial_wait=60)
    def judge(self, prompt: str, files: list[Path]) -> str:
        from azure.ai.agents.models import (
            CodeInterpreterTool,
            FilePurpose,
            ToolResources,
        )

        start = time.time()
        uploaded_file_ids: list[str] = []
        agent_id: str | None = None

        try:
            if files:
                print(f"  Uploading {len(files)} file(s) for judging...")
                for f in files:
                    file_obj = self.client.agents.files.upload_and_poll(
                        file_path=str(f), purpose=FilePurpose.AGENTS
                    )
                    uploaded_file_ids.append(file_obj.id)

            tools = []
            tool_resources = None
            if uploaded_file_ids:
                ci = CodeInterpreterTool(file_ids=uploaded_file_ids)
                tools = ci.definitions
                tool_resources = ToolResources(
                    code_interpreter=ci.resources.code_interpreter
                )

            agent = self.client.agents.create_agent(
                model=self.model,
                name="ib-bench-judge",
                instructions="You are an expert evaluator. Score responses precisely according to the rubric.",
                tools=tools if tools else None,
                tool_resources=tool_resources,
                temperature=0,
            )
            agent_id = agent.id

            thread = self.client.agents.threads.create()
            self.client.agents.messages.create(
                thread_id=thread.id, role="user", content=prompt
            )

            run = self.client.agents.runs.create_and_process(
                thread_id=thread.id, agent_id=agent_id
            )

            if run.status == "failed":
                error = getattr(run, "last_error", None)
                print(f"  Warning: Judge run failed: {error}")

            messages = list(self.client.agents.messages.list(thread_id=thread.id))
            response_text = self._extract_text(messages)

            print(f"  Judge completed in {(time.time() - start) * 1000:.0f}ms")
            return response_text

        finally:
            if agent_id:
                try:
                    self.client.agents.delete_agent(agent_id)
                except Exception:
                    pass
            for fid in uploaded_file_ids:
                try:
                    self.client.agents.files.delete(fid)
                except Exception:
                    pass


def get_judge_runner(provider: JudgeProvider, model: str) -> JudgeRunner:
    """Factory function to get the appropriate judge runner."""
    runners = {
        "anthropic": AnthropicJudge,
        "azure": AzureJudge,
    }

    runner_class = runners.get(provider)
    if runner_class is None:
        raise ValueError(
            f"Unknown judge provider: {provider}. Available: {list(runners.keys())}"
        )

    return runner_class(model=model)
