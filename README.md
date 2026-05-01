# AnnData Omics Bridge

A standardized data format specification for multi-tool omics analysis workflows. Defines a common [AnnData](https://anndata.readthedocs.io/)-based container that enables seamless integration between quantification tools, statistical analysis packages, and visualization applications.

## The Challenge

Omics workflows involve multiple tools with different column naming conventions and data structures. MaxQuant uses `Protein.Names`, DESeq2 outputs `log2FoldChange`, limma outputs `logFC`. Integrating these tools traditionally requires brittle, tool-specific adapters.

## Our Approach

**Metadata-driven semantics**: Instead of forcing standardized column names, we preserve original names and use application-specific metadata to map columns to semantic roles. This separates the physical data structure from the logical interpretation, allowing tools to evolve independently while maintaining interoperability.

Each application (exploreDE, prolfqua, etc.) defines its own metadata namespace specifying which columns it needs. Data converters and analysis workflows populate this metadata, creating self-describing data objects that work across the entire tool ecosystem.

## Key Design Principles

- **Tool-specific metadata is required and self-sufficient**: Each application has its own namespace
- **Generic semantics are optional helpers**: Data converters may document vendor format semantics to aid downstream metadata creation
- **Minimal interface contracts**: Tools specify only essential requirements, reducing integration burden

## Documentation

- **[Tool-specific views ADR](docs/adr_tool_specific_views.md)** — authoritative decision: per-tool `uns['<app_name>']['column_roles']`
- **[Roles and separation of concerns](docs/roles_and_separation_of_concerns.md)** — workflow architecture and responsibilities
- **[Naming conventions](docs/conventions.md)** — sanitisation rules for `obs`/`var`/layer column names
- **[Proteomics rationale](docs/proteomics_rationale.md)** — why AnnData for proteomics (ProteoBench / prolfquapp context)
- **[Main specification](docs/AnnData_Omics_Bridge_spec.qmd)** — complete spec with examples (Quarto, renders to HTML/PDF)
- **[AnnData API reference](docs/anndata_api_reference.md)** — cheat sheet for the AnnData library

Implementation: tool-specific converters live in [anndata_proteomics_bridge](../anndata_proteomics_bridge/).

## Status

Active development - specification and architecture under refinement.