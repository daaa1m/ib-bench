import sys
from types import SimpleNamespace

import pytest

from judge_runners import AnthropicJudge, AzureJudge  # type: ignore


def _build_fake_anthropic(response):
    class FakeMessages:
        def __init__(self):
            self.calls = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            return response

    class FakeFiles:
        def __init__(self):
            self.uploaded_ids = []
            self.deleted_ids = []

        def upload(self, file):
            file_id = f"file_{len(self.uploaded_ids) + 1}"
            self.uploaded_ids.append(file_id)
            return SimpleNamespace(id=file_id)

        def delete(self, file_id):
            self.deleted_ids.append(file_id)

    class FakeBeta:
        def __init__(self):
            self.messages = FakeMessages()
            self.files = FakeFiles()

    class FakeAnthropicClient:
        instances = []

        def __init__(self, api_key):
            self.api_key = api_key
            self.beta = FakeBeta()
            FakeAnthropicClient.instances.append(self)

    return SimpleNamespace(Anthropic=FakeAnthropicClient), FakeAnthropicClient


@pytest.mark.unit
def test_anthropic_judge_tools_and_cleanup(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    response = SimpleNamespace(
        content=[
            SimpleNamespace(text="noise"),
            SimpleNamespace(
                type="code_execution_result",
                content=[
                    SimpleNamespace(text='{"scores": {"accuracy": {"score": 1}}}')
                ],
            ),
        ]
    )
    fake_module, fake_client_cls = _build_fake_anthropic(response)
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)

    files = [tmp_path / "input.xlsx", tmp_path / "input.pdf"]
    for path in files:
        path.write_text("fixture")

    judge = AnthropicJudge(model="claude-test")
    output = judge.judge("prompt", files)

    assert '"scores"' in output
    client = fake_client_cls.instances[0]
    tool_types = {tool["type"] for tool in client.beta.messages.calls[0]["tools"]}
    assert "code_execution_20250825" in tool_types
    assert "web_search_20250305" in tool_types
    assert len(client.beta.files.uploaded_ids) == len(files)
    assert client.beta.files.deleted_ids == client.beta.files.uploaded_ids


class _FakeResponses:
    def __init__(self, response):
        self.calls = []
        self._response = response

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


class _FakeContainerFiles:
    def __init__(self):
        self.created = []

    def create(self, container_id, file):
        self.created.append(container_id)
        return SimpleNamespace(id=f"container_file_{len(self.created)}")


class _FakeContainers:
    def __init__(self):
        self.created_ids = []
        self.deleted_ids = []
        self.files = _FakeContainerFiles()

    def create(self, name):
        container_id = f"container_{len(self.created_ids) + 1}"
        self.created_ids.append(container_id)
        return SimpleNamespace(id=container_id)

    def delete(self, container_id):
        self.deleted_ids.append(container_id)


class _FakeFiles:
    def __init__(self):
        self.created = []
        self.deleted_ids = []

    def create(self, file, purpose):
        file_id = f"file_{len(self.created) + 1}"
        self.created.append((file_id, purpose))
        return SimpleNamespace(id=file_id)

    def delete(self, file_id):
        self.deleted_ids.append(file_id)


class _FakeVectorStores:
    def __init__(self):
        self.created = []
        self.deleted_ids = []

    def create(self, name, file_ids):
        vector_store_id = f"vs_{len(self.created) + 1}"
        self.created.append((vector_store_id, name, list(file_ids)))
        return SimpleNamespace(id=vector_store_id)

    def delete(self, vector_store_id):
        self.deleted_ids.append(vector_store_id)


class _FakeOpenAI:
    def __init__(self, response):
        self.containers = _FakeContainers()
        self.files = _FakeFiles()
        self.vector_stores = _FakeVectorStores()
        self.responses = _FakeResponses(response)


@pytest.mark.unit
def test_azure_judge_tools_and_cleanup(monkeypatch, tmp_path):
    monkeypatch.setenv("AZURE_AI_PROJECT_ENDPOINT", "https://example.com")
    response = SimpleNamespace(
        output=[
            SimpleNamespace(
                type="message",
                content=[
                    SimpleNamespace(
                        type="output_text",
                        text='{"scores": {"accuracy": {"score": 1}}}',
                    )
                ],
            )
        ]
    )
    fake_openai = _FakeOpenAI(response)
    judge = AzureJudge(model="gpt-5.2-chat")
    judge._openai = fake_openai

    code_file = tmp_path / "input.xlsx"
    search_file = tmp_path / "input.pdf"
    code_file.write_text("fixture")
    search_file.write_text("fixture")

    output = judge.judge("prompt", [code_file, search_file])

    assert '"scores"' in output
    call = fake_openai.responses.calls[0]
    tool_types = {tool["type"] for tool in call["tools"]}
    assert {"code_interpreter", "file_search", "web_search_preview"} <= tool_types
    assert len(fake_openai.containers.files.created) == 1
    assert fake_openai.containers.deleted_ids == fake_openai.containers.created_ids
    assert fake_openai.vector_stores.deleted_ids == [
        fake_openai.vector_stores.created[0][0]
    ]
    assert fake_openai.files.deleted_ids == [fake_openai.files.created[0][0]]
