---
title: "AnnData for Proteomics: From Prolfquapp to ProteoBench"
author: "Witold Wolski"
date: 2026-03-27
---

# What is AnnData?

AnnData is a matrix-centric data container originating from the single-cell genomics ecosystem (scverse). It stores a samples-by-features matrix (`X`) together with rich, structured metadata in dedicated slots:

- **X** — primary data matrix, dimensioned **samples x features** (obs x var). All `layers` share this same shape.
- **layers** — alternative quantifications with the same dimensions as `X` (e.g., raw intensities, normalized intensities, imputed values)
- **obs** — sample annotation table (one row per sample). Example columns: condition, replicate, batch, instrument.
- **var** — feature annotation table (one row per protein or precursor). Example columns: gene name, species, protein group.
- **obsm / varm** — multi-column annotations aligned to obs or var. For example, `varm` can store per-feature statistics across contrasts (fold changes, p-values).
- **uns** — unstructured metadata (nested dictionaries for configuration, thresholds, column role conventions)

The on-disk format is HDF5 (`.h5ad`) — efficient, portable, and language-agnostic. Native libraries exist for both Python (`anndata`) and R (`anndataR`, pure R without reticulate dependency).


# Why AnnData for Proteomics?

Proteomics analysis pipelines typically scatter their outputs across CSVs, Excel sheets, RDS files, and custom formats. AnnData addresses this by providing:

**Single structured object.** One `.h5ad` file replaces dozens of loose files. Experimental design, quantification matrices, statistical results, and analysis parameters all travel together.

**Bilingual by design.** The same `.h5ad` file is readable from R (via `anndataR`) and Python (via `anndata`) without format conversion. This is critical for ecosystems like ours where the statistical engine is in R and downstream consumers increasingly use Python.

**Metadata travels with the data.** Analysis results, quality scores, and benchmark metrics are stored alongside the quantification matrix — not in separate files that can drift out of sync. For example, ProteoBench scores (CV, epsilon, fold-change accuracy) travel with the precursor intensities they were computed from.


**Ecosystem leverage.** Any tool that reads AnnData — scanpy, cellxgene, or Bioconductor tools via anndataR/zellkonverter conversion — can consume the output without custom adapters.


## Why Not Parquet or Arrow?

Parquet and Arrow are excellent for flat tabular data but lack the multi-slot structure proteomics needs. Storing intensities, sample metadata, feature annotations, condition-level statistics, and analysis parameters in Parquet requires multiple separate files — and the burden of keeping them in sync falls on the user. AnnData bundles all of these into a single HDF5 file with typed, named slots (`X`, `obs`, `var`, `varm`, `uns`) — a more natural fit for self-contained analytical objects.


# anndata_proteomics_bridge — The Converter Library

`anndata_proteomics_bridge` is the planned standalone Python library for converting raw proteomics software output into AnnData. Its core functionality will be extracted from ProteoBench's existing 15+ format parsers and restructured as a reusable, pip-installable package.

The library will provide both a programmatic API and a CLI entry point (`prot2ad`). A typical invocation would take a vendor quantification file, a sample annotation table, and optionally a FASTA file:

```bash
prot2ad convert report.tsv annotation.csv file.fasta diann-log.txt -o output.h5ad
prot2ad convert evidence.txt annotation.csv file.fasta mqpar.xml -o output.h5ad --software MaxQuant
```

The FASTA file serves a standardization role: it provides protein lengths, description lines, and species annotations that some software tools include in their output but others omit. Parsing the FASTA produces a uniform `var` annotation regardless of which software generated the quantification data.

Beyond quantification tables and software-specific parameter files (e.g., MaxQuant `mqpar.xml`, Sage `.json`, FragPipe `.workflow`, DIA-NN logs), the library will extract **upstream search engine parameters** — FDR thresholds, mass tolerances, enzyme settings, modifications, charge states, and flags like match-between-runs. ProteoBench already parses these from 15+ software tools into a standardized `ProteoBenchParameters` dataclass; the bridge library will consolidate this extraction and store the result in `uns`.

```bash
prot2ad convert report.tsv annotation.csv file.fasta mqpar.xml -o output.h5ad
```


# ProteoBench

## Current Architecture and Limitations

ProteoBench is a multi-tool benchmarking platform for proteomics quantification, supporting 15+ software tools across DDA and DIA acquisition modes. It ingests diverse software outputs via TOML-driven column mappings, normalizes them into a standardized tabular representation, and computes benchmark metrics (coefficient of variation, log2 fold change accuracy, epsilon deviation, ROC-AUC).

The intermediate format — a wide pandas DataFrame with one row per precursor — is serialized to CSV. Aggregate results and submission metadata are stored as JSON files in GitHub (one per submission). This means the intensity matrix, per-precursor annotations, and benchmark scores are flattened into a single table and the JSON results are disconnected from the data they summarize.

## ProteoBench on AnnData: The Synergies

The ProteoBench intermediate format encodes two dimensions in its DataFrame columns: per-sample intensities and per-condition summary statistics. AnnData separates these cleanly into dedicated slots:

| Aspect | Current (pandas + JSON) | With AnnData |
|--------|-------------------------|--------------|
| Intensity data | Per-sample columns mixed into wide DataFrame | `X` matrix (runs x precursors) |
| Sample metadata | Encoded in column names | `obs` table with condition, replicate, instrument |
| Precursor annotation | Extra columns per row | `var` table: sequence, proteins, species, expected ratio |
| Condition-level stats | Columns like `CV_A`, `log2_A_vs_B` | `varm` entries per condition comparison |
| Aggregate metrics | Nested dicts (cutoff -> metric -> value) | `uns` with consistent schema |
| Submission storage | One-off JSON per submission | Self-contained `.h5ad` per submission |
| Downstream access | Custom export code | Standard AnnData API for slicing and filtering |

Notably, `uns` also stores the **software search parameters** that ProteoBench already parses from search engine outputs — keeping full analysis provenance alongside the quantification data.

## ProteoBench Pipeline

The refactored ProteoBench pipeline has three distinct stages:

1. **prot2ad** — converts raw vendor output to `.h5ad`. Runs once per submission.
2. **ProteoBench Benchmark** — reads the `.h5ad` and computes benchmark metrics: group averages and CVs are stored in `varm`; aggregate scores (epsilon, ROC-AUC, fold-change accuracy across cutoffs) and software parameters are written into `uns`.
3. **ProteoBench Streamlit application** — visualizes the scored `.h5ad` for the leaderboard. Since the AnnData already contains all metrics, the visualization layer performs no recomputation.

# Prolfquapp: Adding DEA Results to AnnData

The pipeline has three stages:

1. **prot2ad** — writes a precursor-level `.h5ad`.
2. **prolfqua_dea** (extended with a new `-a` flag) — accepts either the `.h5ad` from step 1 or the existing raw-data flags. Runs aggregation and differential expression analysis. Writes a protein-level `.h5ad` enriched with DEA results.
3. **prolfqua_export** — reads the protein-level `.h5ad` and generates all deliverables: 14-sheet XLSX, ORA text files, GSEA rank files, HTML reports and per-protein boxplots.

# Shared Infrastructure

Prolfquapp and ProteoBench share the same upstream problem: converting diverse proteomics software outputs into a structured, queryable object. Both currently solve this independently — prolfquapp in R, ProteoBench in Python. With `anndata_proteomics_bridge` as the shared conversion layer, both would become consumers of a single parsing library rather than maintaining parallel implementations.

The migration plan is to move **all 15+ ProteoBench parsers** into the bridge library. Parsing-specific information — column mappings, modification handling, format quirks — moves to the bridge's Strategy classes. Benchmark-specific configuration (e.g., file-name-to-condition-group mapping) stays in ProteoBench. Since ProteoBench stores the original vendor data alongside its submissions, historical results can be re-converted from the originals.

Prolfquapp's R-based preprocessors would likewise be replaced by the bridge library. These currently handle: DIA-NN (`report.tsv`), MaxQuant (`peptides.txt`), FragPipe TMT (`psm.tsv`), Spectronaut (`BGS Factory Report.tsv`), and FragPipe DIA via MSstats format (`msstats.csv`). The prolfquappPTMreaders package adds site-level PTM parsing for FragPipe (single-site and multi-site) and Spectronaut (site-level factory report).


# Publication and Library Goals

**Standalone library.** `anndata_proteomics_bridge` will be an independent, pip-installable Python package with no dependency on prolfquapp or ProteoBench, usable by any project that needs to convert proteomics quantification output into AnnData.

**Application note.** The target venue is the *Journal of Proteome Research* (JPR) Software Tools and Resources special issue 2027. The note would focus on:

- The case for a standardized AnnData representation in proteomics
- The Builder pattern for extensible software support (a `ConverterBuilder` that returns instances of specialized parser strategies)
- R/Python interoperability via anndataR/scverse
- Demonstration of utility through two independent consumers (prolfquapp for differential expression analysis, ProteoBench for multi-tool benchmarking)

**Community impact.** Any tool that reads AnnData gains access to results from any supported quantification software — without writing format-specific parsing code.


# Multi-Level Quantification: Future Directions

Proteomics workflows produce quantification at multiple levels: precursor, peptidoform, modification site, and protein. The planned design produces separate `.h5ad` files for each level — e.g., a precursor-level AnnData from `prot2ad` and a protein-level AnnData from `prolfqua_dea`. Cross-level links (which precursors roll up to which protein) are not formally encoded.

MuData — the multi-modal extension of AnnData from the scverse ecosystem — is a potential fit for bundling multiple quantification levels into a single object. QFeatures from Bioconductor provides prior art for this kind of hierarchical linking in R. Whether MuData or a similar structure is the right formalization for proteomics multi-level data is an open question worth investigating.


# Schema Versioning

If multiple tools (ProteoBench, prolfquapp, and future consumers) rely on the same `.h5ad` structure, there must be a schema contract. The bridge library should include a `schema_version` field in `uns` along with standardized column names in `obs` and `var` that consumers can rely on. Defining the precise required columns, layer names, `varm` keys, and `uns` structure is an open design task for the upcoming hackathon.


# Summary

1. **AnnData** provides a mature, bilingual, metadata-rich container that proteomics currently lacks as a standard interchange format.
2. **anndata_proteomics_bridge** will consolidate ProteoBench's 15+ format parsers into a reusable library with a clean, extensible architecture.
3. **Prolfquapp** gains a single-file DEA output that decouples analysis from export, with a fully specified schema for round-trip fidelity.
4. **ProteoBench** gains structured storage, reuses the same converter library, and opens its benchmark results to the broader scverse ecosystem.
5. **One library, two consumers** — a strong case for a standalone package and a JPR application note.


# Open Questions (carried over from review)

The vision above incorporates resolutions for most reviewer concerns. The following are explicitly left open and should be addressed before publication / hackathon kickoff.

- **QC metric storage.** Where do per-sample QC metrics (proteins identified, missing-value counts, CV distributions) live? Candidates: pre-computed values in `uns` vs. on-the-fly computation from `X` and `varm`. Worth exploring scverse QC tooling (`scanpy.pp.calculate_qc_metrics`).
- **Performance characteristics.** HDF5 vs. Parquet/Arrow at the data sizes proteomics produces (5-10 GB DIA-NN reports). Memory footprint of the conversion path. No benchmarks yet.
- **Boundary between generic conversion and benchmark-specific enrichment.** The bridge handles raw format conversion. ProteoBench currently also resolves species labels (HUMAN/YEAST/ECOLI), computes expected ratios, and flags shared peptides. The exact split between bridge responsibilities and ProteoBench post-processing needs to be defined precisely.
- **Dependency compatibility.** Adding the bridge to ProteoBench means inheriting `anndata`, `h5py`, etc. Version-conflict surface against ProteoBench's existing dependency tree has not been verified.

Reviews resolved during the document update: see the previous `annData_Proteobench_review.md` (now removed) for the full Q&A history. Residual items above are the only ones still in flight.
