# IB-bench

IB-bench is an automated benchmark for evaluating Large Language Models (LLMs)
on tasks typical of Investment Banking (IB) analysts. Inspired by SWE-bench,
IB-bench focuses on high-stakes financial workflows including Excel modeling,
complex document analysis, and precise data extraction.

## Features & Scope

- **Real-world IB Tasks**: Benchmarking across financial analysis, due
  diligence, document review, and data extraction.
- **Multimodal Inputs**: Supports complex Excel spreadsheets (`.xlsx`),
  financial reports (`.pdf`), and web-based tasks.
- **Advanced Scoring**: Hybrid evaluation combining deterministic programmatic
  checks with LLM-as-a-judge for nuanced analysis.
- **Human-in-the-Loop**: Integrated workflow for manual verification and expert
  human scoring.
- **Rich Diagnostics**: Detailed analysis of model failure patterns, credit
  tiers, and leaderboard generation.

## Installation & Setup

IB-bench uses `uv` for package management.

1. **Clone the repository**:

   ```bash
   git clone https://github.com/daaa1m/ib-bench.git
   cd ib-bench
   ```

2. **Install dependencies**:

   ```bash
   uv sync
   ```

3. **Configure environment**: Create a `.env` file with your API keys
   (Anthropic, OpenAI, Gemini, Azure):
   ```bash
   cp .env.example .env
   # Edit .env with your keys
   ```

   Supported providers:
   - **Anthropic**: Claude models via Anthropic API
   - **OpenAI**: GPT models via OpenAI API  
   - **Gemini**: Gemini models via Google AI API
   - **Azure**: Any model via Azure AI Foundry (GPT, Mistral, DeepSeek, Llama, etc.)

## Configuration

Evaluation runs are controlled by YAML configuration files.

1. **Initialize local configs**:

   ```bash
   cp -R eval/configs.example eval/configs
   ```

2. **Edit configs**: Customize files in `eval/configs/` (copied from
   `eval/configs.example/`).

   Optional Azure v2 settings:
   - `web_search_mode`: `brave` (default) or `native`

## Usage

### 1. Run Evaluation (Generation)

Run models against tasks. This phase is expensive as it calls LLM APIs. Results
are cached in `eval/responses/`.

```bash
# Run using a specific config
uv run eval/run.py --config configs/quick-run.yaml

# Resume a partially completed run
uv run eval/run.py --config configs/full-easy-example.yaml --resume MODEL/RUN_ID
```

### 2. Score Responses

Score the generated outputs. This phase is fast and can be re-run whenever
rubrics are updated.

```bash
# Score the latest run for a model
uv run eval/score.py MODEL

# Score a specific run
uv run eval/score.py MODEL/RUN_ID

# Score specific tasks only
uv run eval/score.py MODEL/RUN_ID --tasks e-001 e-002

# Force rescore (ignore cached scores)
uv run eval/score.py MODEL/RUN_ID --rescore

# Score with a specific judge model
uv run eval/score.py MODEL/RUN_ID --judge-model claude-3-5-sonnet-20241022

# (Optional) Regenerate summary.json from score files
uv run eval/scripts/regenerate_score_summary.py eval/scores/MODEL/RUN_ID
```

### 3. Human Scoring Workflow

For criteria requiring expert judgment or when LLM parsing fails:

1. Generate templates: `uv run eval/score.py MODEL/RUN_ID --human`
2. Review the generated `*_human.md` files in the score directory.
3. Edit the corresponding JSON score files (provide `score` 0.0-1.0 and
   `reasoning`).
4. Finalize by running without the flag: `uv run eval/score.py MODEL/RUN_ID`

### 4. Analyze & Export

```bash
# Analyze run health and failure patterns
uv run eval/results/analyze.py MODEL/RUN_ID

# Compare two models
uv run eval/results/analyze.py MODEL --compare MODEL2

# Update the benchmark leaderboard
uv run eval/results/leaderboard.py

# Export task results for external analysis
uv run eval/export-scripts/export_task_results.py

# Export leaderboard for external analysis
uv run eval/export-scripts/export_leaderboard.py
```

## Task Anatomy

Each task in `eval/tasks/{id}/` consists of:

- `prompt.md`: Instructions provided to the LLM.
- `input.*`: One or more input files (Excel, PDF, etc.).
- `rubric.json`: Evaluation criteria (Programmatic, LLM Judge, or Human).
- `meta.yaml`: Task metadata (difficulty, category, expected values).

## Directory Structure

- `eval/tasks/`: Task definitions and source files.
- `eval/responses/`: LLM outputs and generated files (expensive, preserve).
- `eval/scores/`: Scoring results, logs, and human templates (regenerable). Optional
  `summary.json` can be generated via `eval/scripts/regenerate_score_summary.py`.
- `eval/configs.example/`: Example run and leaderboard configurations (copy to
  `eval/configs/`).
- `eval/configs/`: Local run and leaderboard configurations (gitignored).
- `tests/`: Project test suite (`uv run pytest`).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file
for details.

## Citation

If you use IB-bench in your research, please cite:

```bibtex
@software{ib_bench2026,
  author = {IB-bench contributors},
  title = {IB-bench: A Benchmark for Investment Banking LLM Agents},
  year = {2026},
  url = {https://github.com/daaa1m/ib-bench}
}
```

## Support

For issues or questions, please open a GitHub issue or contact the maintainers.
