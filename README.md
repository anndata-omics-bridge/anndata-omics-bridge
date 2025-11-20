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

- **[Main Specification](docs/AnnData_Omics_Bridge_spec.qmd)**: Complete specification with examples
- **[Roles and Separation of Concerns](docs/roles_and_separation_of_concerns.md)**: Workflow architecture and responsibilities
- **[Architecture Decisions](docs/adr_tool_specific_views.md)**: Design rationale

## Status

Active development - specification and architecture under refinement.