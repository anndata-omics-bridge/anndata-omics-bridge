# AnnData Omics Bridge

This repository contains the format specification for representing quantitative omics results in [AnnData](https://anndata.readthedocs.io/). It defines how converters and analysis tools record the roles of source columns without renaming those columns.

## Problem

Omics tools use different column names and data structures. For example, MaxQuant uses `Protein.Names`, DESeq2 uses `log2FoldChange`, and limma uses `logFC`. Connecting these outputs requires tool-specific parsing and column mappings.

## Design

Column names remain as reported by the source tool. Application-specific metadata maps those columns to roles needed by a consumer.

Each application, such as exploreDE or prolfqua, defines a metadata namespace for the columns it uses. Data converters and analysis workflows populate that mapping.

## Column-role rules

- Each application has its own complete namespace under `uns['<app_name>']['column_roles']`.
- Generic semantic annotations are optional.
- Each consumer declares only the columns it requires.

## Documentation

- **[Tool-specific views ADR](docs/adr_tool_specific_views.md)** — authoritative decision: per-tool `uns['<app_name>']['column_roles']`
- **[Roles and separation of concerns](docs/roles_and_separation_of_concerns.md)** — workflow architecture and responsibilities
- **[Naming conventions](docs/conventions.md)** — sanitisation rules for `obs`/`var`/layer column names
- **[Proteomics rationale](docs/proteomics_rationale.md)** — why AnnData for proteomics (ProteoBench / prolfquapp context)
- **[Main specification](docs/AnnData_Omics_Bridge_spec.qmd)** — complete spec with examples (Quarto, renders to HTML/PDF)
- **[AnnData API reference](docs/anndata_api_reference.md)** — cheat sheet for the AnnData library

Implementation: the current proteomics converter is [APB2](https://github.com/anndata-omics-bridge/apb2).

## Status

Active development - specification and architecture under refinement.

## FGCZ context

The [Functional Genomics Center Zurich (FGCZ)](https://fgcz.ch/service_and_support/bioinformatics_services.html) supports genomics, transcriptomics, proteomics, metabolomics/lipidomics, and other omics data. AnnData is already used on the genomics side. Proteomics results still arrive as tool-specific tables, so downstream applications need parsers and column mappings for each upstream tool. This repository records the data model used for those mappings. Support for metabolomics data is planned.
