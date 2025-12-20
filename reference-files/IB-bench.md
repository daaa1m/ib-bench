# IB-bench: Can LLM's really replace a junior investment banker?

- IB-bench is an LLM benchmark focused on testing an LLM's ability to handle actual day-to-day tasks of an IB analyst

## Tasks

- IB-bench will test the LLM's ability on tasks that will be representative of the daily work of an IB analyst
- This is in contrast to other benchmarks focused on testing an LLM's ability to score well in exams like the CFA or to perform RAG-type information look-ups

### Easy

- broadly defined as tasks where an analyst would need less than 1 hour to perform
- examples include but not limited to:
  - fixing 1-2 unrelated errors in an already made Excel sheet
  - summarising documents, and creating a 1-pager
  - answering subjective questions
  - data extraction of GAAP / straightforward metrics e.g., find the average capex as a % of revenue in the last 3 years
  - updating the model on new quarter without breaking the model
  - creating a Public Information Book
  - turning comments
  - updating model on share count / currency etc.

### Medium

- broadly defined as tasks where a human analyst would need multiple hours to perform
- examples include but not limited to:
  - data extraction of tricky / derived metrics e.g., find the average ARPU, CAC of a company
  - building a model, given very clear inputs
  - fixing a model with multiple errors
  - making single well defined slides from scratch
  - raw data dump to structured data - but single focus

### Hard

- broadly defined as tasks where a human analyst would need days to perform
- examples include but not limited to:
  - building a model with messy inputs
  - QOE work
  - full slides

## Flow

- model gets given 40% easy and medium tasks, each, with the remaining 20% of tasks allocated to hard tasks
- tasks will primarily be assessed by either a verifiable reward, another LLM, hybrid or sometimes by expert human judgement

## Future work

- refinement and increase of Excel test data
- testing of more LLM's
- testing with different harnesses
