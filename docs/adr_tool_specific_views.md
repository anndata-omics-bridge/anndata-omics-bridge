# ADR: Tool-Specific vs. Shared Column Roles Metadata

**Status**: Under Discussion

**Date**: 2025-11-19

**Authors**: Project team

---

## Context

The **Omics Bridge** project creates a standardized AnnData-based format for multi-tool omics analysis workflows. A critical architectural question arose: should column role metadata be **shared across all tools** (single namespace) or **tool-specific** (separate namespaces per application)?

This decision affects:

- How tools discover and interpret data columns
- The integration burden for new tools joining the ecosystem
- The flexibility for tools to evolve independently
- The complexity of validation and error handling

Two primary types of tools need to work with the same AnnData objects:

1. **Visualization and exploration tools** (e.g., exploreDE) - consume pre-computed results, need feature descriptions and DE statistics
2. **Hierarchical analysis workflows** (e.g., bottom-up proteomics with prolfqua) - aggregate lower-level features to higher levels, perform statistical analysis

The question: Should both tools share a single `uns['column_roles']` structure, or should each have its own namespace like `uns['exploreDE']` and `uns['bottom_up_proteomics']`?

---

## Options Under Consideration

### Option A: Tool-Specific Metadata Namespaces

Each application defines its column roles in a separate namespace under `uns['<app_name>']['column_roles']`.

**Example**:
```python
# exploreDE defines its view of the data
adata.uns['exploreDE'] = {
    'column_roles': {
        'var': {
            'description': ['Protein.Names'],
            'label': ['gene_symbol']
        },
        'obs': {
            'factor': ['condition', 'batch'],
            'label': ['sample_id']
        },
        'DE_treated_vs_control': {
            'effect': ['log2FoldChange'],
            'score': ['pvalue', 'padj']
        }
    }
}

# bottom_up_proteomics defines its own view (different requirements)
adata.uns['bottom_up_proteomics'] = {
    'column_roles': {
        'var': {
            'hierarchy': ['Protein.Group', 'Stripped.Sequence'],
            'intensity': ['Peptide.Quantity'],
            'qvalue': ['qValue']
        },
        'obs': {
            'sample_id': ['raw.file']
        }
    }
}
```

### Option B: Shared Column Roles (Single Namespace)

All tools share the same metadata location, with column roles defined once for all consumers:

```python
# All tools share same metadata location
adata.uns['column_roles'] = {
    'var': {
        'description': ['Protein.Names'],
        'hierarchy': ['Protein.Group', 'Stripped.Sequence'],
        'label': ['gene_symbol'],
        'intensity': ['Peptide.Quantity']
    },
    'obs': {
        'factor': ['condition', 'batch'],
        'sample_id': ['raw.file']
    }
}

# Tools query the shared structure
# exploreDE looks for 'description', 'label', 'factor'
# bottom_up_proteomics looks for 'hierarchy', 'intensity', 'sample_id'
```

### Option C: Shared Core + Tool-Specific Extensions

Hybrid approach with common roles defined in a shared core, supplemented by tool-specific extensions:

```python
# Shared core metadata
adata.uns['core']['column_roles'] = {
    'var': {'description': ['Protein.Names'], 'identifier': ['Protein.Group']},
    'obs': {'factor': ['condition', 'batch'], 'sample_id': ['raw.file']}
}

# Tool-specific extensions
adata.uns['exploreDE']['column_roles'] = {
    'var': {'label': ['gene_symbol']}  # exploreDE-specific
}
adata.uns['bottom_up_proteomics']['column_roles'] = {
    'var': {'hierarchy': ['Protein.Group', 'Stripped.Sequence']}  # bottom_up_proteomics-specific
}
```

---

## Comparison: Option A (Tool-Specific)

### Arguments For

1. **Complete isolation**: Tools evolve independently without coordination
   - exploreDE can add `go_terms` role without checking bottom_up_proteomics
   - No risk of name collisions

2. **Clear ownership**: Each tool documents and validates its own requirements
   - `validate_anndata_omics(adata, app_name='exploreDE')` checks only exploreDE needs
   - Specific error messages: "exploreDE requires 'description' role in var"

3. **Workflow composition**: Data flows naturally through multi-tool pipelines
   ```python
   # bottom_up_proteomics writes metadata for both itself AND downstream tools
   adata.uns['bottom_up_proteomics'] = {...}  # For its own use
   adata.uns['exploreDE'] = {...}  # Enable downstream visualization
   ```

4. **Database view pattern alignment**: Multiple views over same table is standard in databases
   - Each view has its own projection and constraints
   - Physical schema (columns) unchanged, multiple logical schemas (views)

### Arguments Against

1. **Duplication**: Same column referenced in multiple namespaces
   ```python
   adata.uns['exploreDE']['column_roles']['var']['description'] = ['Protein.Names']
   adata.uns['bottom_up_proteomics']['column_roles']['var']['description'] = ['Protein.Names']
   ```
   - Is this explicit dependency declaration (good) or wasteful duplication (bad)?

2. **Coordination burden**: Data exporters must know all downstream tool requirements
   - MaxQuant exporter must write both `uns['exploreDE']` and `uns['bottom_up_proteomics']`
   - What if they miss a tool? Breaks silently for that tool

3. **Discovery complexity**: How do users know which tools work with their data?
   - Must run validator for each tool individually
   - No automatic "list compatible tools" function

4. **Fragmentation risk**: Could lead to tool silos if metadata not written properly

---

## Comparison: Option B (Shared Namespace)

### Arguments For

1. **Single source of truth**: All role definitions in one place
   - No duplication of column mappings
   - Easier to see complete picture of data semantics

2. **Simpler for data producers**: Write metadata once, works for all tools
   - Don't need to know about every downstream tool
   - Less chance of missing a tool's requirements

3. **Easier discovery**: Check `uns['column_roles']` to see what's available
   - Could implement: "You have 'description' and 'factor' → exploreDE compatible"

4. **Less metadata bloat**: Fewer nested structures in AnnData object

### Arguments Against

1. **Name collision risk**: What if two tools want `'identifier'` to mean different things?
   - exploreDE wants gene symbols
   - bottom_up_proteomics wants protein groups
   - Need naming coordination or namespacing anyway

2. **Unclear validation**: Who checks what?
   - Is `description` required by all tools or just some?
   - If exploreDE requires it but bottom_up_proteomics doesn't, how to validate?
   - Need tool-specific validation logic anyway

3. **Evolution friction**: Adding roles requires coordination
   - Check if role name conflicts with existing roles
   - Need governance process for shared namespace
   - Breaking changes affect all tools

4. **Loss of isolation**: Tools can't experiment independently
   - Hard to add experimental features
   - Must coordinate with tool ecosystem

5. **Coupling**: All tools share fate of shared namespace
   - Changes ripple across tools
   - Unclear ownership of shared structure

6. **Violates minimal interface principle**: Tool providers must understand entire shared namespace to use it
   - Unclear which roles each application actually needs/uses
   - Must learn all available roles to know which ones to populate
   - No way to know minimal requirements for a specific tool
   - Higher cognitive load for implementers (view users)

---

## Comparison: Option C (Core + Extensions)

### Arguments For

1. **Balance**: Gets benefits of both approaches
   - Common roles avoid duplication
   - Tool-specific extensions provide flexibility

2. **Reduced duplication**: Core roles like `description` defined once

3. **Some isolation**: Tools can extend without full coupling

### Arguments Against

1. **Common core already exists**: AnnData itself provides the shared structure
   - X, obs, var, layers, obsm, varm, uns are the common core
   - Tools already share this physical schema
   - Additional "core" metadata layer adds complexity without clear benefit

2. **Who defines core?**: Tools have fundamentally different needs
   - exploreDE doesn't need hierarchy (single aggregation level)
   - bottom_up_proteomics doesn't need factors in obs (uses external annotation)
   - Hard to find common ground

3. **Governance burden**: Requires coordination on what belongs in core
   - Who decides?
   - How to handle disputes?
   - Versioning complexity

4. **Validation complexity**: Must validate both core and extensions
   - Two validation paths
   - Precedence rules unclear (what if core and extension conflict?)

5. **Forced dependencies**: Tools must populate core even if they don't use it
   - bottom_up_proteomics forced to write `obs['factor']` even though it uses external annotation
   - exploreDE forced to write `var['hierarchy']` even though it doesn't aggregate

6. **Breaking change**: Existing tools (ezRun, ezPyz, bottom_up_proteomicspp) use tool-specific namespaces
   - Would require migration
   - Backwards compatibility issues

---

## Next Steps

This document presents the architectural trade-offs without making a final decision. Discussion points:

1. **Prioritize concerns**: Which issues matter most? Duplication? Coordination? Evolution flexibility?

2. **Prototype comparison**: Implement simple examples with both approaches to see practical differences

3. **Stakeholder input**: Gather perspectives from:

   - Tool developers (ezRun, ezPyz, bottom_up_proteomicspp teams)
   - Data producers (MS core facilities)
   - End users (researchers using multiple tools)

4. **Backwards compatibility analysis**: What's the cost of migrating existing tools if we choose differently?

5. **Hybrid experiments**: Could we support both patterns temporarily to evaluate?

