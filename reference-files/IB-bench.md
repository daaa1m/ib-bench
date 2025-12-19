# IB-bench: Can LLM's really replace a junior investment banker?

- IB-bench is an LLM benchmark focused on testing an LLM's ability to handle actual day-to-day tasks of an IB analyst

## Tasks

- IB-bench will test the LLM's ability on tasks that will be representative of the daily work of an IB analyst
- This is in contrast to other benchmarks focused on testing an LLM's ability to score well in exams like the CFA or to perform RAG-type information look-ups

### Easy

- broadly defined as tasks where an analyst would need less than 1 hour to perform
- fixing 1-2 unrelated errors in an already made Excel sheet
- summarising documents, and creating a 1-pager (RLAIF)
- answering subjective questions (RLAIF)
- data extraction of GAAP / straightforward metrics e.g., find the average capex as a % of revenue in the last 3 years
- updating the model on new quarter without breaking the model

### Medium

- broadly defined as tasks where a human analyst would need multiple hours to perform. e
- examples
  - data extraction of tricky / derived metrics e.g., find the average ARPU, CAC of a company
  - building a model, given very clear inputs
  - fixing a model with multiple errors

### Hard

- broadly defined as tasks where a human analyst would need days to perform examples:
  - building a model with messy inputs

## Flow

- LLM gets tested on a corpus of 50-100 (for the launch, we use 50 tasks and keep 50 in private eval / dripfeed to the public slowly) tasks and will be judged on a scale of: 1 point for easy tasks, 2.5 points for medium tasks and 5 points for hard tasks
- model gets given 40% easy and medium tasks, each, with the remaining 20% of tasks allocated to hard tasks
- tasks will primarily be assessed by either a verifiable reward, another LLM or sometimes by expert human judgement

## Future work

- ppt tasks
- refinement and increase of Excel test data
- testing of more LLM's
