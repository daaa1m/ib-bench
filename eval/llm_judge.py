"""LLM-as-judge scorer for IB-bench evaluation pipeline."""

import os
import re
import time
from pathlib import Path
from typing import Any

from helpers import Rubric, extract_json, retry_on_rate_limit


class LLMJudge:
    """LLM-as-judge scorer using Claude with Files API."""

    def __init__(self, model: str = "claude-sonnet-4-5"):
        """
        Initialize the LLM judge.

        :param model: Anthropic model identifier
        :raises ValueError: If ANTHROPIC_API_KEY environment variable not set
        """
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self.model = model
        self._client = None

    @property
    def client(self):
        """Lazy-initialized Anthropic client."""
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def _build_prompt(
        self,
        criteria: dict,
        response_text: str,
        file_names: list[str],
        task_prompt: str,
    ) -> str:
        """
        Build the evaluation prompt for the judge.

        :param criteria: Dict of criterion_id -> criterion spec
        :param response_text: The LLM response to evaluate
        :param file_names: Names of source files for context
        :param task_prompt: The ## Task section from prompt.md (not full prompt)
        :returns: Formatted prompt string
        """
        prompt_path = Path(__file__).parent / "prompts" / "llm_judge.md"
        template = prompt_path.read_text()

        criteria_text = "\n".join(
            f"- **{cid}** ({spec.get('points', 0)} points): {spec.get('description', '')}"
            for cid, spec in criteria.items()
        )
        criteria_ids = list(criteria.keys())
        files_list = ", ".join(file_names)

        # WARNING: {} in task_prompt/response_text/criteria_text will cause
        # KeyError since str.format() interprets them as placeholders
        return template.format(
            task_prompt=task_prompt,
            files_list=files_list,
            response_text=response_text,
            criteria_text=criteria_text,
            example_criterion=criteria_ids[0],
            criteria_ids=criteria_ids,
        )

    def _extract_response_text(self, response: Any) -> str:
        """
        Extract text content from API response (LLM judge's API call).

        Handles both direct text blocks and code execution stdout.

        :param response: Raw API response object
        :returns: Extracted text, prioritizing blocks containing JSON scores
        """
        text_blocks = []
        for block in response.content:
            if hasattr(block, "text") and block.text:
                text_blocks.append(block.text)
            if hasattr(block, "type") and block.type == "code_execution_result":
                if hasattr(block, "content"):
                    for item in block.content:
                        if hasattr(item, "stdout") and item.stdout:
                            text_blocks.append(item.stdout)
                        elif hasattr(item, "text") and item.text:
                            text_blocks.append(item.text)

        for text in text_blocks:
            if '{"scores"' in text or '"scores":' in text:
                return text

        return "\n".join(text_blocks)

    def _parse_prose_scores(self, text: str, criteria_ids: list[str]) -> dict | None:
        """
        Fallback parser for prose format scores if _parse_response() fails.

        :param text: Raw response text
        :param criteria_ids: List of criterion IDs to look for
        :returns: Dict with "scores" key, or None if parsing fails

        Handles formats: "**accuracy: 0.95/1.0**", "accuracy - 0.85", etc.
        Does not handle: Scores embedded in complex prose or tables.
        """
        scores = {}
        text_lower = text.lower()

        for cid in criteria_ids:
            cid_variants = [
                cid.lower(),
                cid.lower().replace("_", " "),
                cid.lower().replace("_", ""),
            ]

            for cid_variant in cid_variants:
                patterns = [
                    rf"\*?\*?{re.escape(cid_variant)}\*?\*?[:\s]+(\d+\.?\d*)\s*/\s*1\.?0?",
                    rf"\*?\*?{re.escape(cid_variant)}\*?\*?[:\s]+(\d+\.?\d*)(?:/|\s|$)",
                    rf"{re.escape(cid_variant)}[:\-\s]+(\d+\.?\d*)",
                    rf"{re.escape(cid_variant)}[^0-9]*(\d+\.?\d*)\s*/\s*1",
                ]

                for pattern in patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        try:
                            score_val = float(match.group(1))
                            if score_val > 1:
                                score_val = score_val / 100
                            scores[cid] = {
                                "score": min(score_val, 1.0),
                                "reasoning": "Parsed from prose",
                            }
                            break
                        except ValueError:
                            continue
                if cid in scores:
                    break

        return {"scores": scores} if scores else None

    def _parse_response(self, raw_text: str, criteria_ids: list[str]) -> dict | None:
        """
        Parse scores from judge response text.

        :param raw_text: Raw response text from the judge
        :param criteria_ids: List of criterion IDs to extract
        :returns: Dict with "scores" key, or None if parsing fails

        Tries JSON extraction first, falls back to prose parsing in
        _parse_prose_scores().
        """
        parsed = extract_json(raw_text)
        if parsed and parsed.get("scores"):
            return parsed

        print("  Warning: JSON parse failed, trying prose fallback...")
        return self._parse_prose_scores(raw_text, criteria_ids)

    def _calculate_weighted(self, scores: dict, criteria: dict) -> float:
        """
        Calculate weighted average score.

        :param scores: Dict of criterion_id -> {"score": float, "reasoning": str}
        :param criteria: Dict of criterion_id -> criterion spec with "points"
        :returns: Weighted average as float 0.0-1.0
        """
        weighted_total = 0.0
        total_weight = 0.0

        for cid, criterion in criteria.items():
            points = criterion.get("points", 0)
            if cid in scores:
                score_val = scores[cid].get("score", 0)
                weighted_total += score_val * points
                total_weight += points

        return weighted_total / total_weight if total_weight > 0 else 0.0

    @retry_on_rate_limit(max_retries=3, initial_wait=60)
    def _call_api(self, content: list[dict[str, Any]]) -> Any:
        """
        Make the API call with retry logic.

        :param content: List of content blocks for the message
        :returns: Raw API response
        :raises: API errors after retries exhausted
        """
        return self.client.beta.messages.create(
            model=self.model,
            betas=["code-execution-2025-08-25", "files-api-2025-04-14"],
            max_tokens=16384,
            temperature=0,
            messages=[{"role": "user", "content": content}],  # type: ignore[list-item]
            tools=[{"type": "code_execution_20250825", "name": "code_execution"}],
        )

    def _call_judge(self, source_files: list[Path], prompt: str) -> str:
        """
        Upload files, call the judge API, and return response text.

        :param source_files: List of source document paths
        :param prompt: The evaluation prompt
        :returns: Raw response text from the judge

        Handles file upload/cleanup. Files are deleted after the call.
        """
        file_objects = []
        print(f"  Uploading {len(source_files)} file(s) to Files API for judging...")

        for source_file in source_files:
            with open(source_file, "rb") as f:
                file_obj = self.client.beta.files.upload(file=f)
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
                    print(f"  Warning: Failed to delete judge file {fo.id}: {e}")

        latency_ms = (time.time() - start) * 1000
        print(f"  Judge completed in {latency_ms:.0f}ms")

        return self._extract_response_text(response)

    def score(
        self,
        rubric: Rubric,
        source_files: list[Path],
        response_text: str,
        task_prompt: str,
    ) -> dict[str, Any]:
        """
        Score a response against rubric criteria.

        :param rubric: Rubric dict with "criteria" key
        :param source_files: List of source document paths (PDF, xlsx, etc.)
        :param response_text: The LLM response to evaluate
        :param task_prompt: The original task prompt given to the LLM
        :returns: Dict with "scores" (per-criterion) and "weighted_total" (0.0-1.0)

        Pipeline: build_prompt -> call_judge -> parse_response -> calculate_weighted
        """
        criteria = rubric.get("criteria", {})
        criteria_ids = list(criteria.keys())
        file_names = [f.name for f in source_files]

        prompt = self._build_prompt(criteria, response_text, file_names, task_prompt)
        raw_text = self._call_judge(source_files, prompt)
        parsed = self._parse_response(raw_text, criteria_ids)

        if not parsed:
            print("  Warning: Could not parse judge response")
            print(f"  Preview: {raw_text[:200] if raw_text else '(empty)'}...")
            return {"scores": {}, "weighted_total": 0.0, "raw_response": raw_text}

        scores = parsed.get("scores", {})
        parsed["weighted_total"] = self._calculate_weighted(scores, criteria)
        return parsed
