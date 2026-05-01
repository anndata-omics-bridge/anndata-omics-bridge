# anndata_omics_bridge

Documentation repo for the Omics Bridge — a standardised AnnData-based interchange format for multi-tool quantitative omics workflows.

This repo also ships a small Python package, `omicsbridge`, with the `ColumnResolver` and validators referenced from the spec. Tool-specific converters (DIA-NN, MaxQuant, Spectronaut, …) live in the sibling repo [anndata_proteomics_bridge](../anndata_proteomics_bridge/).

## Key design

Tool requirements are declared **per tool** in `uns['<app_name>']['column_roles']` — column names stay arbitrary (preserving upstream tool outputs), and semantic meaning is carried by metadata. See:

- [docs/adr_tool_specific_views.md](docs/adr_tool_specific_views.md) — authoritative ADR
- [docs/roles_and_separation_of_concerns.md](docs/roles_and_separation_of_concerns.md) — operational roles
- [docs/conventions.md](docs/conventions.md) — naming sanitisation rules for `obs`/`var`/layer columns
- [docs/proteomics_rationale.md](docs/proteomics_rationale.md) — why AnnData for proteomics

## Project structure

- `src/omicsbridge/` — `column_resolver.py`, `exploreDE_validator.py`
- `tests/` — pytest suite (`test_column_resolver.py`)
- `docs/` — specifications and ADRs (Quarto `.qmd` for renderable specs, plain `.md` for ADRs and conventions)

## Environment & development

- Create env: `uv venv` then `source .venv/bin/activate`
- Install: `uv pip install -e ".[dev]"`
- Format: `black src/ tests/` (line length 100) or `ruff format src/ tests/`
- Lint: `ruff check src/ tests/`
- Type check: `mypy src/`
- Tests: `pytest` or `pytest --cov=omicsbridge`

## Coding style

- Python 3.10+; typed function signatures and explicit return types
- Black/Ruff defaults (100-char lines, sorted imports)
- Naming: modules `snake_case.py`, classes `CapWords`, functions/vars `snake_case`; tests `test_*.py`, fixtures `sample_*`
- Raise clear `ValueError` when resolver contracts are violated, mirroring existing patterns
- Keep public APIs minimal

## Testing

- Extend `tests/` with `test_*` functions; mirror the `sample_adata` fixture pattern
- Cover happy-path resolution and error cases (missing roles, empty mappings, invalid app namespaces)
- Run `pytest` before pushing; include `--cov` when touching resolver or validator logic

## Commits & PRs

- Commit messages: concise, present-tense (e.g. "update Readme.md", "add roles"); no long prefixes
- One logical change per PR; describe intent, files touched, validation (`pytest`, `ruff`, `mypy`) results
- Note any AnnData metadata schema adjustments

## Documentation notes

- Align code with `docs/AnnData_Omics_Bridge_spec.qmd` and `docs/roles_and_separation_of_concerns.md`
- When adding metadata roles or validators, document the expected `uns['<app_name>']['column_roles']` structure and update examples if semantics change
- Quarto specs render via `docs/render.sh` (which sets `R_LIBS_USER` and `RETICULATE_PYTHON`); generated HTML/PDF are gitignored
