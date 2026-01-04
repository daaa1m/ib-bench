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
