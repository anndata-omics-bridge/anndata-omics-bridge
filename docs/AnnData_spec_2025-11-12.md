---
title: "AnnData Structure Specification for Omics Data"
author:
  - "PL"
  - "WEW"
  - "Claude AI"
date: "2025-11-12"
format:
  html:
    toc: true
    toc-depth: 3
    number-sections: true
  pdf:
    toc: true
    toc-depth: 3
    number-sections: true
    geometry: margin=1in
    documentclass: article
    fontsize: 11pt
    colorlinks: true
    tbl-cap-location: top
    fig-pos: 'H'
editor:
  markdown:
    wrap: 72
---

# Use Case

### Use Case: Harmonizing Omics Quantification Outputs for Downstream Analysis

Proteomics identification and quantification software — such as **Spectronaut**, **DIA-NN**, **alphaDIA**, **MaxQuant**, and **FragPipe** — produce results at various levels of biological aggregation, including *ion*, *peptidoform*, *protein*, *PTM site*, or *multisite* level.
Similarly, **metabolomics** tools such as **MZmine** or **Compound Discoverer**, and **genomics** analysis pipelines, generate quantitative data tables with differing structures, column names, and metadata conventions.

For proteomics, specialized importers parse and normalize diverse table structures, transforming them into standardized data objects that enable robust differential expression analysis. However, changes in the upstream output formats can easily break compatibility, as importers depend on specific column naming and structure conventions.

Projects like **ProteoBench** provide parsers for many proteomics quantification tools, and could be extended to export data directly into **AnnData**.

Structural changes to data schemas can disrupt compatibility with visualization and downstream tools.

To summarize:

- Different omics technologies rely on diverse software ecosystems, and our goal is to interconnect them with analysis and visualization tools in a scalable way.
- It is unrealistic for every downstream application (for differential expression, enrichment, or visualization) to natively handle the idiosyncrasies of all upstream quantification tools and omics modalities.
- Maintaining extensive mapping tables between software packages becomes complex and fragile.

Therefore, an **intermediate data format** is needed—one that is both:

- **flexible enough** to represent omics- and tool-specific features,
- yet **simple enough** to be generated easily, in a preprocessing step.

The guiding principle for this format is to minimize requirements imposed on tool developers when writing into this format, while maintaining semantic richness for downstream interoperability.

**Workflow:**

1. **Convert** raw quantification outputs into a multi-assay data container (AnnData).
2. **Add conversion support** for various quantification applications to ensure integration.
3. **Run the DE application**, starting from the multi-assay container and appending differential expression results.
4. **Run the GSEA/ORA application**, which adds functional enrichment results.
5. **Visualize** integrated quantitative and functional data in applications such as *exploreDE*.

This modular architecture allows interoperability across tools, omics domains, and institutions, ensuring long-term sustainability and reproducibility of quantitative omics analyses.

## Contract: "Essential Data" for Tool Interoperability

To make multiple omics tools work on a common container without brittle per-exporter adapters/importers, each downstream tool (exploreDE, prolfquaDE) that operates on **AnnData** must publish an **essential set** of required data, **column decorations** and metadata (uns).

The goal is a **minimal, stable contract**: enough information to fully support the tool's features, while **abstaining from non-essential requirements** that complicate AnnData creation.

Each tool also implements a Validator function, tool, or script, which allows easily checking if the multi-assay container file will work.

**Principles**

1. **Essential-only**: Keep the required fields to the minimum needed for the tool's core functionality. Avoid nice-to-haves.
   - Some additional metadata, e.g. additional sample annotation, contrasts, can be added when using a tool, therefore no need to add it to the AnnData at the beginning.

2. **Decorate `obs`/`var` first**: Encode semantics using **column decorations** `<role>__<name>`.
   - Use `uns` **only** when a concept cannot be expressed as column-level decorations (e.g., contrast definitions, global settings).

3. **Tool-specific contracts**: Each tool (e.g., exploreDE, prolfqua DE) documents its **essential contract**. Upstream writers and importers target the contract—**not** tool-internal structures.
   - Validation function

---

## AnnData Structure Overview

AnnData components:

| Component | AnnData Slot | Description |
|-----------|--------------|-------------|
| Features  | `var/varm`   | Annotation of Variables/Features (Gene/protein/Metabolite annotations and DE results) |
| Samples   | `obs/obsm`   | Annotation of Observations (Sample metadata and experimental factors) |
| Counts    | `X`/`layers` | Raw/normalized/transformed abundance matrices |
| Other     | `uns`        | Unstructured metadata (pathways, settings) |

**Example: Creating a minimal AnnData object**

```python
import anndata as ad
import numpy as np
import pandas as pd

# Create example data: 100 samples x 50 proteins
np.random.seed(42)
intensities = np.random.lognormal(mean=10, sigma=2, size=(100, 50))

# Sample metadata (observations)
obs = pd.DataFrame({
    'sample_id': [f'sample_{i:03d}' for i in range(100)],
    'factor_condition': ['control'] * 50 + ['treated'] * 50,
    'factor_batch': np.random.choice(['batch1', 'batch2'], 100)
}, index=[f'sample_{i:03d}' for i in range(100)])

# Feature metadata (proteins)
var = pd.DataFrame({
    'protein_id': [f'P{i:05d}' for i in range(50)],
    'description': [f'Protein {i}' for i in range(50)],
    'label_gene_symbol': [f'GENE{i}' for i in range(50)]
}, index=[f'P{i:05d}' for i in range(50)])

# Create AnnData object
adata = ad.AnnData(X=intensities, obs=obs, var=var)

# Set index names (critical for clarity)
adata.obs.index.name = 'sample_id'
adata.var.index.name = 'protein_id'

print(f"Created AnnData: {adata.n_obs} samples × {adata.n_vars} proteins")
```

---

# X and Layers (Counts / Abundances / Intensities)

Abundance matrices are stored in AnnData `X` and `layers`. In AnnData, rows = observations (samples), columns = variables (features).

Layer names should be descriptive of the data type or transformation applied (e.g., `counts`, `tpm`, `vst`, `log2_tpm`).

The distribution of the data (exponential, Poisson, normal) is **not encoded in the layer name**. Instead, tools can determine the sampling distribution statistically when needed for visualization or analysis.

**Important:** Annotate in `adata.uns` which layer was used for each DE test.

| Layer Type | Description | Examples |
|:-----------|:------------|:---------|
| Numeric abundance | Raw, normalized, or transformed abundance data | `counts`, `tpm`, `fpkm`, `intensities` |
| Transformed abundance | Log-transformed or variance-stabilized data | `log2_tpm`, `vst`, `voom`, `vsn` |
| Metadata matrices | Feature-specific annotations per sample | `nr_peptides`, `stdev`, `retention_time` |

**Common Layer Name Examples**

| Layer Name | Description |
|:-----------|:------------|
| `counts` | Raw read counts (RNA-seq) |
| `tpm` | Transcripts per million |
| `fpkm` | Fragments per kilobase per million |
| `intensities` | Raw MS intensities (proteomics/metabolomics) |
| `log2_tpm` | Log2-transformed TPM |
| `vst` | Variance stabilizing transformation (DESeq2) |
| `voom` | Voom transformation (limma) |
| `vsn` | Variance stabilizing normalization |
| `nr_peptides` | Number of peptides quantified per protein per sample |
| `stdev` | Standard deviation of technical replicates |
| `retention_time` | Chromatographic retention time (metabolomics) |

## Determining Data Distribution

Tools can determine the sampling distribution of data statistically using moment-based classification. This approach uses skewness and kurtosis to classify data and suggest appropriate visualization scales.

This approach allows visualization tools to automatically select appropriate scales (linear vs. log) and statistical methods based on the empirical distribution of the data, without requiring distribution information to be encoded in layer names.

**Example: Adding multiple data layers**

```python
# Store raw intensities in a layer
adata.layers['intensities'] = adata.X.copy()

# Log2-transform for main analysis
adata.X = np.log2(adata.X)

# Add variance-stabilized version
from scipy.stats import zscore
adata.layers['vst'] = zscore(adata.X, axis=0)

# Add peptide counts per protein (metadata matrix)
adata.layers['nr_peptides'] = np.random.randint(1, 20, size=adata.X.shape)

print(f"Available layers: {list(adata.layers.keys())}")
```

---

# var and varm (Features)

Feature annotations and differential expression results are stored in `var` and `varm`.

We can store genes, proteins, peptides, metabolites etc. in the `var` container.
To identify which type of data is stored, use: `adata.var.index.name = 'gene_id'` (or `protein_id`, `peptide_id`, etc.)

## Feature Annotation Table

**Single table shared across all DE tests in the AnnData object.**

All columns can be used for filtering and subsetting. Column types (string, integer, numeric) determine available filter operations.

| Column Name |  Type | Required? | Distinct? | Description |
|-------------|-------|-----------|-----------|-------------|
| `<index>` | string | Yes | Yes | Row identifier for each feature (e.g., gene ID, protein ID, Ensembl ID) |
| `description` | string | Yes | Yes? | Free-text description (searchable) |
| `label_gene_symbol` | string | No | No | Human-readable gene symbol |
| `label_entrez_id` | string | No | No | NCBI Entrez Gene ID |
| `label_ensembl_gene_id` | string | No | No | Ensembl gene identifier |
| `label_uniprot_id` | string | No | No | UniProt accession |
| `label_flydb_id` | string | No | No | FlyBase identifier |
| `label_nr_peptides` | numeric | No | No | Number of peptides quantifying this protein |
| `label_global_base_mean` | numeric | No | No | Mean abundance across all samples |
| `label_assignment_method` | string | No | No | Annotation method (MS1, MS2, manual) |

The description column is used to store free-text description of the feature e.g. "Amyloid-beta precursor protein", "BRCA1 DNA repair", "EGFR receptor", or for metabolomics compounds "Caffeine", "Theobromine", "Theophylline", etc. This information is primarily used for searching using names used by biologists.

**Example: Adding feature annotations**

```python
# Add additional protein annotations
adata.var['label_uniprot_id'] = [f'UNI{i:05d}' for i in range(adata.n_vars)]
adata.var['label_nr_peptides'] = np.random.randint(2, 50, adata.n_vars)
adata.var['label_global_base_mean'] = adata.X.mean(axis=0)

# Verify all features have descriptions
assert adata.var['description'].notna().all(), "All features must have descriptions"
print(f"Feature annotations: {list(adata.var.columns)}")
```

## Hierarchical Data Columns (prefix: `hierarchy_`)

For proteomics and other hierarchical omics data, use `hierarchy_` columns to encode multi-level relationships. Individual hierarchy columns do not need to be distinct, but **all hierarchy columns combined must ensure distinct rows** (matching the feature identifiers).

- Each `hierarchy_*` column alone may contain duplicates
- The **combination** of all `hierarchy_*` columns must uniquely identify each row
- This allows rollup/aggregation from lower to higher levels (e.g., peptide -> protein)
- The hierarchy levels should be ordered left-to-right from coarsest to finest granularity

**Representing Hierarchies**

Store hierarchy data in columns in `var`, define structure in `uns`.

**Peptide-level hierarchy:**

| Column Name | Type | Description | Example Values |
|-------------|------|-------------|----------------|
| `<index>` | string | Distinct row identifier | "PEPTIDE_001", "PEPTIDE_002", "PEPTIDE_003" |
| `hierarchy_protein` | string | Protein identifier | "P53_HUMAN", "P53_HUMAN", "P53_HUMAN" |
| `hierarchy_peptide` | string | Peptide sequence | "SVTEQGAELSNEER", "ALPNNTSSSPQPK", "CSDSDGLAPPQHLIR" |

Store hierarchy definition in `adata.uns['hierarchy_definition'] = ['protein', 'peptide']`

**Example: Creating hierarchical peptide-level data**

```python
# Create peptide-level AnnData (multiple peptides per protein)
n_peptides = 200
peptide_intensities = np.random.lognormal(mean=8, sigma=2, size=(100, n_peptides))

# Peptide annotations with hierarchy
peptide_var = pd.DataFrame({
    'peptide_id': [f'PEP_{i:05d}' for i in range(n_peptides)],
    'description': [f'Peptide sequence {i}' for i in range(n_peptides)],
    'hierarchy_protein': np.random.choice([f'P{i:05d}' for i in range(50)], n_peptides),
    'hierarchy_peptide': [f'PEPTIDE{i}K' for i in range(n_peptides)]
}, index=[f'PEP_{i:05d}' for i in range(n_peptides)])

# Create peptide-level AnnData
adata_peptide = ad.AnnData(X=peptide_intensities, obs=obs.copy(), var=peptide_var)
adata_peptide.obs.index.name = 'sample_id'
adata_peptide.var.index.name = 'peptide_id'

# Store hierarchy definition
adata_peptide.uns['hierarchy_definition'] = ['protein', 'peptide']

print(f"Peptide data: {adata_peptide.n_vars} peptides mapping to ~50 proteins")
print(f"Hierarchy levels: {adata_peptide.uns['hierarchy_definition']}")
```

**Peptidoform and ion-level hierarchy:**

| Column Name | Type | Description | Example Values |
|-------------|------|-------------|----------------|
| `<index>` | string | Distinct row identifier | "ION_001", "ION_002" |
| `hierarchy_protein` | string | Protein identifier | "P53_HUMAN" |
| `hierarchy_peptide` | string | Peptide sequence | "SVTEQGAELSNEER" |
| `hierarchy_peptidoform` | string | Modified peptide sequence | "SVTEQGAELSNEER[Phospho]" |
| `hierarchy_ion` | string | Precursor ion (m/z, charge) | "762.3442_2", "508.5628_3" |

**Phosphoproteomics - site-level hierarchy:**

For phosphorylation site analysis (single site):

| Column Name | Type | Description | Example Values |
|-------------|------|-------------|----------------|
| `<index>` | string | Distinct row identifier | "PHOSPHO_001", "PHOSPHO_002", "PHOSPHO_003" |
| `hierarchy_protein` | string | Protein identifier | "P53_HUMAN", "P53_HUMAN", "TAU_HUMAN" |
| `hierarchy_site` | string | Single phosphorylation site | "S15", "S20", "S199" |

**Phosphoproteomics - site with multiplicity:**

When tracking phosphorylation multiplicity (multiple phosphorylation events on the same peptide):

| Column Name | Type | Description | Example Values |
|-------------|------|-------------|----------------|
| `<index>` | string | Distinct row identifier | "PHOSPHO_001", "PHOSPHO_002", "PHOSPHO_003", "PHOSPHO_004" |
| `hierarchy_protein` | string | Protein identifier | "TAU_HUMAN", "TAU_HUMAN", "TAU_HUMAN", "TAU_HUMAN" |
| `hierarchy_site` | string | Single phosphorylation site | "S199", "S199", "S199", "S396" |
| `hierarchy_multiplicity` | integer | Number of phosphorylations on peptide | 1, 2, 3, 2 |

---

## Differential Expression Results (varm)

**One set of columns per DE test performed.**

Each DE test is stored in `varm` as a **pandas DataFrame**, accessed by a distinct name. The DataFrame must have the same index as `adata.var` (same length and order).

The DE table name format is: `DE_<name_of_contrast>` where `<name_of_contrast>` is a distinct identifier for this comparison.

### Required DE Columns

| Column Name | Type | Distinct? | Alternative Names | Description |
|-------------|------|-----------|-------------------|-------------|
| `<index>` | string | Yes | | Row identifier matching feature annotation table and all layers |
| `effect_*` | numeric | No | `log2Ratio`, `log2FC`, `lfc` | Log2 fold change or other effect size |
| `score_*` | numeric | No | `score_pvalue`, `score_adjusted_p_val`, `score_q_value` | Raw p-value, adjusted p-value / FDR / q-value |
| `label_*` | numeric/string | No | `label_model_name`, `label_de_base_mean`, `label_t_statistic`, `label_n_missing`, `label_ci_upper`, `label_ci_lower` | Additional statistics or metadata, either numeric or string |

- `effect_*`: Used for volcano plot x-axis
- `score_*`: Used for volcano plot y-axis. At least one score column required
- `label_*`: Additional statistics or metadata, either numeric or string

For each DE test, the following information should be stored in `adata.uns['de_tests'][<name_of_contrast>]`:

| Field | Required? | Type | Description | Example |
|-------|-----------|------|-------------|---------|
| `layer_used` | Yes | string | Which layer was used for DE | `"vst"` |
| `factor_used` | Yes | list | Which `factor_*` column(s) from `obs` were used | `["factor_treatment", "factor_batch"]` |
| `contrast_formula` | No | string | Exact mathematical formula | `"factor_treatment_B - factor_treatment_control"` |
| `model` | No | string | Statistical model used | `"DESeq2"`, `"limma"`, `"prolfqua"` |

**Example: Storing DE results in varm**

```python
# Simulate differential expression analysis results
de_results = pd.DataFrame({
    'effect_log2FC': np.random.randn(adata.n_vars),
    'score_pvalue': np.random.uniform(0, 1, adata.n_vars),
    'score_adjusted_pval': np.random.uniform(0, 1, adata.n_vars),
    'label_base_mean': np.random.uniform(100, 10000, adata.n_vars),
    'label_t_statistic': np.random.randn(adata.n_vars)
}, index=adata.var_names)

# Store in varm as DataFrame
adata.varm['DE_treated_vs_control'] = de_results

# Store metadata in uns
if 'de_tests' not in adata.uns:
    adata.uns['de_tests'] = {}

adata.uns['de_tests']['treated_vs_control'] = {
    'layer_used': 'vst',
    'factor_used': ['factor_condition'],
    'contrast_formula': 'treated - control',
    'model': 'limma'
}

print(f"DE results stored: {adata.varm['DE_treated_vs_control'].shape}")
print(f"DE columns: {list(adata.varm['DE_treated_vs_control'].columns)}")
```

---

# obs and obsm (Samples/Observations)

Sample metadata and experimental design information stored in `obs`.

TODO: How to accommodate different sample types: e.g. QC samples, and differentiate them from biological samples etc.

| Column Name | Type | Required? | Distinct? | Description |
|-------------|------|-----------|-----------|-------------|
| `<index>` | string | Yes | Yes | Sample identifier (typically same as `sample_id`) |
| `sample_label` | string | No | Yes | Human-readable sample name |
| `bfabric_sample_id` | string | No | No | B-Fabric database ID |
| `factor_*` | categorical or numeric | No | No | Experimental factors (condition, sex, treatment, batch, timepoint, genotype) |
| `organism` | string | No | No | Species name |
| `feature_level` | string | No | No | Feature type (isoform/gene, peptide/protein) |
| `label_*` | string or numeric | No | No | Sample-level annotations (read counts, creatinine concentration, etc.) |

**Factors:** Categorical or continuous covariates used in experimental design.

- `factor_condition` (e.g., "control", "treated")
- `factor_sex` (e.g., "M", "F")
- `factor_batch` (e.g., "batch1", "batch2")
- `factor_timepoint` (numeric, e.g., 0, 2, 4, 8 hours)
- `factor_genotype` (e.g., "WT", "KO")

**Example: Adding sample annotations and factors**

```python
# Add additional sample-level metadata
adata.obs['label_total_intensity'] = adata.X.sum(axis=1)
adata.obs['label_n_proteins_detected'] = (adata.X > 0).sum(axis=1)
adata.obs['organism'] = 'Homo sapiens'
adata.obs['feature_level'] = 'protein'

# Verify factor columns exist
factor_cols = [col for col in adata.obs.columns if col.startswith('factor_')]
print(f"Experimental factors: {factor_cols}")
```

---

# uns (Unstructured Metadata)

Unstructured metadata stored in `adata.uns`

- To represent differential expression analysis annotations not stored in the DE tables (see section Differential Expression Results)
- To represent hierarchical data structures not stored in the var tables (see section Hierarchical Data Columns)

**Example: Storing metadata in uns**

```python
# Store global experiment metadata
adata.uns['experiment_info'] = {
    'date': '2025-11-12',
    'instrument': 'Orbitrap Fusion',
    'software': 'Spectronaut 18.0',
    'normalization': 'global median'
}

# Store analysis parameters
adata.uns['analysis_params'] = {
    'log_transform': True,
    'missing_value_threshold': 0.5,
    'filter_min_peptides': 2
}

print(f"Metadata in uns: {list(adata.uns.keys())}")
```

## TODO: Pathway Analysis Results

Pathway enrichment and gene set analysis results.

If native objects are not used, store pathway results as data frames with the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `category` | string | Pathway database (GO, KEGG, Reactome, etc.) |
| `id` | string | Pathway identifier (GO:0008150, hsa04110, etc.) |
| `description` | string | Pathway name/description |
| `n_genes_mapped` | integer | Number of genes from input mapping to this pathway |
| `n_genes_in_set` | integer | Total genes in pathway |
| `enrichment_score` | numeric | Enrichment score (varies by method) |
| `fdr` | numeric | False discovery rate |
| `method` | string | Analysis method (ORA, GSEA, etc.) |
| `feature_ids` | list | List of mapped feature IDs (matching var index) |
| `feature_labels` | list | List of human-readable feature labels |

---

# TODO: Dimensionality Reduction Results

## Storage of PCA, UMAP, and Other Embeddings

Dimensionality reduction analyses (PCA, UMAP, t-SNE) are computationally intensive and should be cached to avoid re-computation.

### Use Case: PCA for Missing Value Imputation

**Problem:** PCA-based imputation is computationally expensive, especially with:
- Large feature sets (genes, proteins)
- Multiple missing values
- Iterative imputation algorithms (e.g., NIPALS, EM-based)

---

# Validation

## Validating AnnData Objects

A validation function should check if an AnnData object conforms to this specification.

The validator should perform the following checks:

1. **Basic Structure**: Confirms object is an AnnData instance
2. **Required Components**: Verifies presence of X/layers, var, obs, uns
3. **Index Uniqueness** (Critical):
   - **Observation indices must be unique**: `adata.obs.index.is_unique == True`
   - **Variable indices must be unique**: `adata.var.index.is_unique == True`
   - AnnData requires unique indices for proper subsetting and merging operations
4. **Layers**:
   - Checks for at least one numeric layer
   - Ensures consistent dimensions across all layers
5. **obs**:
   - Verifies index is present and distinct
   - Checks for `factor_*` columns
   - Validates column naming conventions
6. **var**:
   - Looks for feature annotation columns
   - Identifies DE tables in varm (`DE_*`)
   - Validates required columns (description, `effect_*`, `score_*`)
   - Checks naming conventions (`label_*`, `hierarchy_*`, `effect_*`, `score_*`)
7. **uns**:
   - Validates DE test metadata structure (`adata.uns['de_tests']`)
   - Checks required fields (`layer_used`, `factor_used`)
   - Validates optional fields (`contrast_formula`, `model`)
8. **Consistency**:
   - Ensures row/column dimensions match across components
   - Validates DE table names match uns keys
   - Verifies layer names referenced in uns exist
   - Confirms varm DataFrames have same index as var

## Validation Result Structure

The validation function should return a structure with:

- `overall_status`: "PASS" or "FAIL"
- `errors`: Critical issues preventing use
- `warnings`: Non-critical issues or recommendations
- `checks`: Detailed per-check results with status and messages

**Example: Basic validation checks**

```python
def validate_anndata_omics(adata):
    """Validate AnnData object against omics specification."""
    errors = []
    warnings = []
    
    # Check basic structure
    if not isinstance(adata, ad.AnnData):
        errors.append("Object is not an AnnData instance")
        return {"overall_status": "FAIL", "errors": errors, "warnings": warnings}
    
    # Critical: Check index uniqueness
    if not adata.obs.index.is_unique:
        errors.append("Observation indices are not unique")
    if not adata.var.index.is_unique:
        errors.append("Variable indices are not unique")
    
    # Check required var columns
    if 'description' not in adata.var.columns:
        warnings.append("Missing 'description' column in var")
    
    # Check for at least one factor
    factor_cols = [col for col in adata.obs.columns if col.startswith('factor_')]
    if len(factor_cols) == 0:
        warnings.append("No factor_* columns found in obs")
    
    # Check DE results consistency
    de_varm_keys = [k for k in adata.varm.keys() if k.startswith('DE_')]
    de_uns_keys = list(adata.uns.get('de_tests', {}).keys())
    
    for varm_key in de_varm_keys:
        # Check varm DE result is a DataFrame
        if not isinstance(adata.varm[varm_key], pd.DataFrame):
            errors.append(f"varm['{varm_key}'] must be a DataFrame")
        # Check index matches var
        elif not adata.varm[varm_key].index.equals(adata.var.index):
            errors.append(f"varm['{varm_key}'] index doesn't match var index")
    
    # Overall status
    overall_status = "FAIL" if errors else "PASS"
    
    return {
        "overall_status": overall_status,
        "errors": errors,
        "warnings": warnings
    }

# Run validation
validation_result = validate_anndata_omics(adata)
print(f"Validation: {validation_result['overall_status']}")
if validation_result['errors']:
    print(f"Errors: {validation_result['errors']}")
if validation_result['warnings']:
    print(f"Warnings: {validation_result['warnings']}")
```

## Saving and Loading AnnData Objects

The standard format for AnnData is HDF5-based `.h5ad` files, which efficiently store all components.

**Example: File I/O**

```python
# Save AnnData object
adata.write('proteomics_experiment.h5ad')

# Load AnnData object
import anndata as ad
adata_loaded = ad.read_h5ad('proteomics_experiment.h5ad')

# Verify loaded data
assert adata_loaded.n_obs == adata.n_obs
assert adata_loaded.n_vars == adata.n_vars
print(f"Loaded: {adata_loaded.n_obs} samples × {adata_loaded.n_vars} features")
```

---

# Version History

| Date | Version | Changes |
|------|---------|---------|
| 2025-11-12 | 1.0 | Initial AnnData-focused specification |

---

# References

- [AnnData documentation](https://anndata.readthedocs.io/)
- [scanpy documentation](https://scanpy.readthedocs.io/)
- [ClusterProfiler enrichResult objects](https://yulab-smu.top/biomedical-knowledge-mining-book/)
- [STRING-DB API](https://string-db.org/help/api/)
