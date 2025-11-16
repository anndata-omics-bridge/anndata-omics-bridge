# Omics Bridge Project - Proteomics Bridge Component

## Project Overview

The **Omics Bridge** project establishes a standardized data format to facilitate multi-step, multi-tool analysis workflows in quantitative omics. The project defines a common data container specification based on *AnnData* that enables seamless data exchange between diverse analysis packages and visualization tools.


## Key Concepts

### Self-Describing Data Objects
The core principle is to create **self-sufficient data objects** that carry both:
- Quantitative measurements (expression matrices, intensities, counts)
- Rich metadata describing how to interpret these measurements (column roles, experimental factors, analysis provenance)

### Column Roles Metadata
Instead of forcing specific column naming conventions, the specification uses **application-specific metadata** to define semantic roles:
- Column names remain **arbitrary** (preserving upstream tool outputs)
- Semantic meaning is defined in `uns['<app_name>']['column_roles']`
- Different tools can define their own requirements independently

## Project Structure

```
anndata_omics_bridge/
├── docs/                          # Documentation and specifications
│   ├── AnnData_Omics_Bridge_spec.qmd  # Main specification (Quarto)
│   ├── prolfqua_spec.qmd          # prolfqua-specific specification
│   ├── R/                         # R helper scripts
│   │   └── column_resolver.R      # R implementation of ColumnResolver
│   ├── deprecated/                # Archived old versions
│   ├── render.sh                  # Quarto rendering script
│   ├── omics_data_flow.png        # Workflow diagram
│   └── architecture_decision_column_annotation.md
├── src/omicsbridge/               # Python package
│   ├── __init__.py                # Package exports
│   ├── column_resolver.py         # Semantic column role resolver
│   └── exploreDE_validator.py     # exploreDE-specific AnnData validator
├── tests/                         # Test suite
│   ├── __init__.py
│   └── test_column_resolver.py   # ColumnResolver tests (19 tests, 100% coverage)
├── pyproject.toml                 # Python package configuration
├── .gitignore                     # Git ignore patterns
└── README.md                      # Project readme
```

## Participating Tools

The following tools and packages use this standardized format:

- **ezRun**: Workflow management and analysis orchestration
- **ezPyz**: Python-based quantification and analysis utilities
- **prolfqua**: Proteomics-focused differential expression and quality control (requires hierarchical data support)
- **exploreDE**: Interactive visualization and exploration of differential expression results
- **Mass spectrometry data generators**: Tools that produce quantification outputs from raw MS data

## Main Specification Documents

### AnnData Omics Bridge Specification

**Location**: `docs/AnnData_Omics_Bridge_spec.qmd`

This Quarto document contains:
1. **Introduction**: Project goals and participating tools
2. **Use Case**: Harmonizing omics quantification outputs
3. **Column Annotation Strategy**: Flexible metadata-based approach
4. **AnnData Structure Overview**: Component descriptions
5. **exploreDE Specification**: Complete tool-specific requirements
   - Column Roles Metadata Structure
   - X and Layers (abundance matrices)
   - var (feature annotations)
   - varm (DE results)
   - obs and obsm (sample metadata)
   - uns (unstructured metadata)
   - Validation and I/O
6. **prolfqua Specification**: Reference to separate document
7. **Working with Column Roles**: ColumnResolver usage
8. **Version History and References**

### prolfqua Specification

**Location**: `docs/prolfqua_spec.qmd`

This separate Quarto document contains:
1. **prolfqua Column Roles**: Hierarchical proteomics data requirements
   - var column roles (hierarchy, intensity, qvalue, etc.)
   - obs column roles (sample_id)
   - Metadata structure
2. **Example Code**: Python and R examples
3. **Annotation File Structure**: Separate experimental design file format

### Rendering the Specifications

```bash
cd docs
./render.sh AnnData_Omics_Bridge_spec.qmd
./render.sh prolfqua_spec.qmd
```

This generates:
- `AnnData_Omics_Bridge_spec.html` (Main specification with Python/R toggle buttons)
- `prolfqua_spec.html` (prolfqua-specific specification)

**Note**: Generated HTML files are `.gitignore`d - they should be regenerated from source.

## Python Package: omicsbridge

### Installation

Using uv (recommended):
```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

### Running Tests

The project uses pytest for testing:

```bash
# Install with dev dependencies
uv pip install -e ".[dev]"

# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run specific test file
pytest tests/test_column_resolver.py

# Run with coverage report
pytest --cov=omicsbridge --cov-report=term-missing

# Run a specific test
pytest tests/test_column_resolver.py::TestSimplifiedAPI::test_var_primary
```

**Current Test Coverage:**
- `test_column_resolver.py`: 19 tests, 100% code coverage

### Key Components

#### 1. ColumnResolver (`src/omicsbridge/column_resolver.py`)

Abstracts away column name differences by accessing columns via semantic roles:

```python
from omicsbridge import ColumnResolver

resolver = ColumnResolver(adata, app_name='exploreDE')

# Simple, clean API - get columns by role
desc_col = resolver.var('description')
effect_col = resolver.de('DE_treated_vs_control', 'effect')
```

**Simple API** (recommended):
- `var(role)`: Get primary column from var
- `obs(role)`: Get primary column from obs
- `de(de_test, role)`: Get primary column from DE test
- `var_all(role)`, `obs_all(role)`, `de_all(de_test, role)`: Get all columns for a role

#### 2. Validator (`src/omicsbridge/exploreDE_validator.py`)

Validates that AnnData objects meet the exploreDE specification:

```python
from omicsbridge import validate_anndata_omics

result = validate_anndata_omics(adata, app_name='exploreDE')
print(f"Status: {result['overall_status']}")  # 'PASS' or 'FAIL'
```

**Checks**:
- Basic structure (is AnnData instance)
- Index uniqueness
- Required metadata presence
- Application-specific requirements (e.g., 'description' role for exploreDE)
- DE test consistency

## Tool-Specific Requirements

### exploreDE Requirements

**Required in `var`**:
- `description`: Free-text searchable description (REQUIRED)
- `label`: Optional identifiers (gene symbols, protein IDs, etc.)

**Required in `obs`**:
- `factor`: At least one experimental factor (REQUIRED)

**DE Results Structure** (in `varm['DE_<contrast_name>']`):
- `effect`: Effect size columns (logFC, beta, etc.) - REQUIRED
- `score`: Significance columns (pvalue, padj, FDR) - REQUIRED
- `label`: Additional statistics (optional)

**Metadata** (in `uns['exploreDE']['de_tests'][<test_name>]`):
- `layer_used`: Which matrix was used for analysis
- `factor_used`: Which experimental factors were in the model
- `contrast_formula`: The contrast tested
- `model`: Statistical method used

### prolfqua Requirements

**Hierarchical Data**:
- `hierarchy`: Columns defining hierarchy (e.g., `['protein', 'peptide_seq']`)
- Stored in `uns['prolfqua']['hierarchy']`

**Note**: Hierarchy columns can contain duplicates, but combined they must uniquely identify each row.

## Development Workflow

### Code Organization Principle

- **Python code**: Lives in `src/omicsbridge/` as a proper Python package
- **R code**: Lives in `docs/R/` (sourced by Quarto documents)
- **Documentation**: Lives in `docs/` as Quarto (.qmd) documents

### Rendering Documents

The `docs/render.sh` script sets required environment variables:
- `R_LIBS_USER`: Path to R packages
- `RETICULATE_PYTHON`: Path to Python virtual environment

### Import Pattern in Quarto

Python blocks in `.qmd` files import from the package:
```python
from omicsbridge.column_resolver import ColumnResolver
from omicsbridge.validator import validate_anndata_omics
```

R blocks source from `docs/R/`:
```r
source('R/column_resolver.R')
```

## Recent Major Changes

### Project Scope Extension (2025-11-16)

1. **Repository renamed**: `anndata_omics_bridge` → `anndata_proteomics_bridge`
   - Clarifies this is the proteomics-focused component of the broader Omics Bridge project
   - Reflects extended scope beyond DIANN-only converter

2. **Multi-format support**: Now supports converting multiple proteomics quantification formats to AnnData
   - Reference points: ProteoBench test data (`ProteoBench/test/data/quant`) and I/O parsers (`projects/ProteoBench/proteobench/io`)

### Document Restructuring (2025-11-13)

1. **Reorganized hierarchy**:
   - Promoted exploreDE to top-level section
   - Made all exploreDE components (X/layers, var/varm, obs/obsm, uns, validation) subsections
   - Moved AnnData Structure Overview to appear early in document

2. **Code organization**:
   - Moved Python modules from `docs/src/` to `src/omicsbridge/`
   - Moved R scripts from `docs/src/` to `docs/R/`
   - Updated all imports and references

3. **Content improvements**:
   - Added comprehensive Introduction section
   - Removed all TODO comments
   - Fixed print statements to use row-by-row output for better readability
   - Removed redundant "exploreDE" mentions in subsections
   - Created standalone code examples (no variable reuse)

4. **Files removed/deprecated**:
   - Migration Guide section (removed)
   - Auto-Discovery section (removed)
   - Old specification versions moved to `docs/deprecated/`

## Version History

- **v2.0 (2025-11-12)**: Flexible column annotation with metadata-based roles
- **v1.0 (2025-11-12)**: Initial AnnData-focused specification

## References

- [AnnData documentation](https://anndata.readthedocs.io/)
- [Scanpy documentation](https://scanpy.readthedocs.io/)
- Architecture Decision: `docs/architecture_decision_column_annotation.md`
