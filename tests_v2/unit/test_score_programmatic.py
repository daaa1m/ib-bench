import pytest

from eval.score import (
    evaluate_regex_pattern,
    evaluate_substring_one_of,
    get_evaluation_type,
    score_task,
)


@pytest.mark.unit
def test_evaluate_substring_one_of_matches():
    passed, details = evaluate_substring_one_of("The result is OK", ["OK"])
    assert passed is True
    assert "Found" in details


@pytest.mark.unit
def test_evaluate_substring_one_of_forbidden():
    passed, details = evaluate_substring_one_of("BAD", ["OK"], ["BAD"])
    assert passed is False
    assert "forbidden" in details


@pytest.mark.unit
def test_evaluate_regex_pattern_required_elements_missing():
    passed, details = evaluate_regex_pattern("value=10", [r"value=\\d+"], ["missing"])
    assert passed is False
    assert "Missing required" in details


@pytest.mark.unit
def test_get_evaluation_type_hybrid(sample_rubric):
    rubric = sample_rubric.copy()
    rubric["criteria"]["judge"] = {"type": "llm_judge"}
    assert get_evaluation_type(rubric) == "hybrid"


@pytest.mark.unit
def test_score_task_gates_llm_and_skips_judge(
    sample_rubric, task_factory, response_data_factory
):
    rubric = {
        "task_id": "e-000",
        "total_points": 100,
        "criteria": {
            "answer": {
                "type": "programmatic",
                "match_type": "substring_one_of",
                "accepted_values": ["OK"],
                "points": 50,
                "gates_llm": True,
            },
            "analysis": {
                "type": "llm_judge",
                "points": 50,
                "core_concepts": ["reason"],
            },
        },
    }
    task = task_factory(task_id="e-000", rubric=rubric)
    response_data = response_data_factory(parsed_response={"answer": "NO"})

    score = score_task(task, response_data, judge=None)

    assert score.llm_gated is True
    assert any(r.criterion_type == "llm_judge" for r in score.criteria_results)
