# ADR: Tool-Specific Column Roles Metadata

**Status**: Accepted

**Date**: 2025-11-19

**Authors**: Project team

---

## Decision

Tool requirements live in **tool-specific namespaces** under `uns`:

```
adata.uns['<app_name>']['column_roles']
```

Each consumer (exploreDE, prolfqua, ProteoBench, …) gets its own namespace. Column names in `obs` and `var` stay arbitrary (preserving upstream tool outputs); semantic meaning is carried by the per-tool metadata mapping. This is **Option A** below; alternatives B (shared namespace) and C (core + extensions) were considered and rejected — see *Rejected alternatives* at the end.

---

## Context

The Omics Bridge defines a standardised AnnData-based format for multi-tool omics workflows. The architectural question: should column-role metadata be **shared across all tools** (single namespace) or **tool-specific** (separate namespaces per application)?

Two kinds of tool need to work with the same AnnData object:

1. **Visualisation/exploration tools** (e.g. exploreDE) — consume pre-computed results, need feature descriptions and DE statistics.
2. **Hierarchical analysis workflows** (e.g. bottom-up proteomics with prolfqua) — aggregate lower-level features to higher levels, perform statistical analysis.

The decision affects how tools discover and interpret data columns, the integration burden for new tools, the flexibility for tools to evolve independently, and the complexity of validation.

---

## Option A: Tool-Specific Metadata Namespaces (chosen)

Each application defines its column roles in a separate namespace under `uns['<app_name>']['column_roles']`.

```python
# exploreDE defines its view of the data
adata.uns['exploreDE'] = {
    'column_roles': {
        'var': {
            'description': ['Protein.Names'],
            'label': ['gene_symbol'],
        },
        'obs': {
            'factor': ['condition', 'batch'],
            'label': ['sample_id'],
        },
        'DE_treated_vs_control': {
            'effect': ['log2FoldChange'],
            'score': ['pvalue', 'padj'],
        },
    },
}

# bottom_up_proteomics defines its own view (different requirements)
adata.uns['bottom_up_proteomics'] = {
    'column_roles': {
        'var': {
            'hierarchy': ['Protein.Group', 'Stripped.Sequence'],
            'intensity': ['Peptide.Quantity'],
            'qvalue': ['qValue'],
        },
        'obs': {
            'sample_id': ['raw.file'],
        },
    },
}
```

### Why A wins

1. **Complete isolation.** Tools evolve independently without coordination — exploreDE can add a `go_terms` role without checking other tools, with no risk of name collisions.
2. **Clear ownership.** Each tool documents and validates its own requirements (`validate_anndata_omics(adata, app_name='exploreDE')`); error messages are specific (`"exploreDE requires 'description' role in var"`).
3. **Workflow composition.** Data flows naturally through multi-tool pipelines — an upstream producer can write metadata for itself AND for downstream tools.
4. **Database-view pattern alignment.** Multiple views over the same table is a standard, well-understood pattern. The physical schema (the `obs`/`var` columns) stays one; multiple logical schemas project from it.

### Trade-offs accepted

1. **Duplicated column references.** When two tools need the same column, both namespaces reference it. We treat this as explicit dependency declaration rather than waste — the cost is one line per tool per column, paid willingly to keep tools isolated.
2. **Coordination burden on data exporters.** A converter that wants to support exploreDE *and* prolfqua must populate both namespaces. The fix is to make this routine in converter libraries — `anndata_proteomics_bridge` does it for the proteomics consumers it knows about.
3. **No automatic "list compatible tools".** Discovery requires running each tool's validator. Acceptable: the alternatives that offer auto-discovery come with worse evolution properties.

---

## Rejected alternatives

### Option B — Shared namespace (`uns['column_roles']`)

All tools read from a single shared structure. **Rejected.** Different tools genuinely want the same role name to mean different things (`identifier` = gene symbol for exploreDE, protein group for prolfqua), forcing namespacing to come back through naming convention. Validation logic ends up tool-specific anyway, and adding a role becomes an ecosystem-wide governance problem rather than a single tool's decision. The "single source of truth" benefit is undermined the moment two tools disagree on semantics.

### Option C — Shared core + tool-specific extensions

A common `uns['core']['column_roles']` plus per-tool extensions. **Rejected.** AnnData itself already provides the shared core (X, obs, var, layers, obsm, varm, uns) — adding another shared metadata layer adds complexity without clear benefit. Tools have fundamentally different needs (exploreDE doesn't aggregate, bottom_up_proteomics uses external annotation rather than `obs.factor`), so finding common ground for the core is hard. The hybrid keeps the worst of both worlds: governance burden of B plus duplication of A, with extra precedence rules for resolving core/extension conflicts.

---

## Consequences

- New tools join by writing their own `uns['<app_name>']['column_roles']` and a validator. They do not need to coordinate with existing tools.
- Data converters (`anndata_proteomics_bridge` and friends) own the mapping from vendor columns to per-tool roles. Adding a tool means adding namespace-population logic, not changing AnnData layout.
- The optional `uns['generic_semantics']` glossary (see [roles_and_separation_of_concerns.md](roles_and_separation_of_concerns.md)) is a *human* helper for writing tool-specific roles; applications never read it.
- Backwards compatibility: existing tools (ezRun, ezPyz, prolfquapp) already use tool-specific namespaces, so no migration is required.
