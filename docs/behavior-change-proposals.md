# Behavior Change Proposals

1. Expand input file detection in `eval/run.py` to include `.csv`, `.png`,
   `.jpg`, `.jpeg`.
   Why: Runners already support these file types, but they are currently ignored.

2. Treat `parsed_response == {}` as valid JSON in `score_task` instead of a
   JSON parse failure.
   Why: Some tasks may legitimately return an empty object.

3. Default missing `task.id` in `helpers.load_task` to the task directory name
   (and log a warning).
   Why: Avoids `None` task IDs propagating into run/score outputs.

4. Write a per-run `errors.json` log with structured API error details and next
   steps.
   Why: Makes failures auditable without changing response JSON schemas.

5. Add `--verbose` to `eval/run.py` and `eval/score.py` to print full API error
   details on failure.
   Why: Default output stays short, but detailed diagnostics are one flag away.

6. Improve error sections in `eval/run.py` with status/code/request ID and
   suggested next steps.
   Why: Helps users debug and recover faster when API calls fail.
