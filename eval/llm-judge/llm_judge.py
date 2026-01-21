"""LLM-as-judge scorer for IB-bench evaluation pipeline."""

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers import Rubric, extract_json
from judge_runners import JudgeProvider, JudgeRunner, get_judge_runner


class LLMJudge:
    """LLM-as-judge scorer using configurable provider."""

    def __init__(
        self,
        model: str | None = None,
        provider: JudgeProvider = "azure-v2",
        runner: JudgeRunner | None = None,
    ):
        if runner is not None:
            self.runner = runner
            return

        self.runner = get_judge_runner(provider, model)

    def _build_prompt(
        self,
        criteria: dict,
        response_text: str,
        file_names: list[str],
        task_prompt: str,
    ) -> str:
        prompt_path = Path(__file__).parent / "llm_judge.md"
        template = prompt_path.read_text()

        criteria_text = "\n".join(
            f"- **{cid}** ({spec.get('points', 0)} points): {spec.get('description', '')}"
            for cid, spec in criteria.items()
        )
        criteria_ids = list(criteria.keys())
        files_list = ", ".join(file_names)

        return template.format(
            task_prompt=task_prompt,
            files_list=files_list,
            response_text=response_text,
            criteria_text=criteria_text,
            example_criterion=criteria_ids[0],
            criteria_ids=criteria_ids,
        )

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
        parsed = extract_json(raw_text)
        if parsed and parsed.get("scores"):
            return parsed

        print("  Warning: JSON parse failed, trying prose fallback...")
        return self._parse_prose_scores(raw_text, criteria_ids)

    def _calculate_weighted(self, scores: dict, criteria: dict) -> float:
        weighted_total = 0.0
        total_weight = 0.0

        for cid, criterion in criteria.items():
            points = criterion.get("points", 0)
            if cid in scores:
                score_val = scores[cid].get("score", 0)
                weighted_total += score_val * points
                total_weight += points

        return weighted_total / total_weight if total_weight > 0 else 0.0

    def score(
        self,
        rubric: Rubric,
        source_files: list[Path],
        response_text: str,
        task_prompt: str,
    ) -> dict[str, Any]:
        criteria = rubric.get("criteria", {})
        criteria_ids = list(criteria.keys())
        file_names = [f.name for f in source_files]

        prompt = self._build_prompt(criteria, response_text, file_names, task_prompt)
        raw_text = self.runner.judge(prompt, source_files)
        parsed = self._parse_response(raw_text, criteria_ids)

        if not parsed:
            print("  Warning: Could not parse judge response")
            print(f"  Preview: {raw_text[:200] if raw_text else '(empty)'}...")
            return {"scores": {}, "weighted_total": 0.0, "raw_response": raw_text}

        scores = parsed.get("scores", {})
        parsed["weighted_total"] = self._calculate_weighted(scores, criteria)
        return parsed
