# Architecture Decision: Column Annotation Strategy

**Date:** 2025-11-12  
**Status:** Accepted  
**Context:** exploreDE/DE apps need to work with AnnData from diverse sources (MaxQuant, DESeq2, FragPipe, etc.)

---

## Decision

**Use metadata-based column role mapping as the primary mechanism, with automatic fallback to prefix-based discovery.**

### AnnData Structure Overview

AnnData organizes omics data into distinct components:

```
AnnData
├── X: main data matrix (n_obs × n_vars)
├── obs: sample/observation annotations (DataFrame, n_obs rows)
├── var: feature/variable annotations (DataFrame, n_vars rows)
├── obsm: multi-dimensional observation annotations (dict of arrays)
├── varm: multi-dimensional variable annotations (dict of arrays/DataFrames)
├── layers: alternative data matrices (dict of arrays)
└── uns: unstructured metadata (dict)
```

**Our usage:**
- **`var`**: Shared feature annotations (gene symbols, protein IDs, hierarchy) - same across all DE tests
- **`obs`**: Sample metadata and experimental design factors (condition, batch, etc.)
- **`varm['DE_*']`**: Differential expression results as DataFrames - one per contrast
- **`uns['column_roles']`**: Metadata mapping column names to semantic roles

### Core Principle

The AnnData specification **does not require** column prefixes. Instead, column roles are defined in **application-specific metadata**, structured by location (var, obs, varm):

```python
# Application-specific column roles (each tool defines its own requirements)
adata.uns['exploreDE_column_roles'] = {
    'var': {
        # Feature annotations (shared across all DE tests)
        'description': ['description'],  # Required: free-text searchable description
        'label': ['gene_symbol', 'gene_name', 'protein_id'],  # Optional: identifiers
        # Note: 'hierarchy' not required for exploreDE (used by other tools)
    },
    'obs': {
        # Sample metadata and experimental design
        'factor': ['condition', 'treatment', 'batch'],
        'label': ['sample_name', 'sample_id']
    },
    'varm': {
        # DE results (one entry per contrast)
        'DE_treated_vs_control': {
            'effect': ['logFC', 'beta'],
            'score': ['pvalue', 'padj', 'fdr'],
            'label': ['t_statistic', 'base_mean', 'se']
        },
        'DE_timepoint_8h_vs_0h': {
            'effect': ['logFC'],
            'score': ['pvalue', 'padj']
        }
    }
}

# Other tools can define their own column roles
# adata.uns['prolfqua_column_roles'] = {...}
# adata.uns['proteobench_column_roles'] = {...}
```

**Key distinctions:**
- **`var`**: Feature-level annotations shared across all analyses
  - `description`: Required by exploreDE - free-text searchable field
  - `label`: Optional identifiers (gene symbols, protein IDs, etc.)
  - `hierarchy`: Not used by exploreDE (used by hierarchical analysis tools)
- **`obs`**: Sample-level metadata (experimental factors, batch info)
- **`varm["DE_*"]`**: Differential expression results for specific contrasts (effect sizes, p-values, statistics)

### Automatic Discovery Fallback

If `uns['exploreDE_column_roles']` is missing, the system attempts to auto-populate it by scanning for recognized prefix patterns:

```python
def discover_exploreDE_column_roles(adata):
    """Auto-populate exploreDE_column_roles from prefix patterns if not present"""
    if 'exploreDE_column_roles' in adata.uns:
        return  # Already defined, don't override
    
    roles = {'var': {}, 'obs': {}, 'varm': {}}
    
    # Scan var columns (feature annotations only - no effect/score here!)
    # Check for description (required for exploreDE)
    if 'description' in adata.var.columns:
        roles['var']['description'] = ['description']
    
    for role in ['label']:  # hierarchy not needed for exploreDE
        cols = [c for c in adata.var.columns if c.startswith(f'{role}_')]
        if cols:
            roles['var'][role] = cols
    
    # Scan obs columns (sample metadata)
    for role in ['factor', 'label']:
        cols = [c for c in adata.obs.columns if c.startswith(f'{role}_')]
        if cols:
            roles['obs'][role] = cols
    
    # Scan varm for DE results (effect/score live here!)
    for key in adata.varm.keys():
        if key.startswith('DE_'):
            de_df = adata.varm[key]
            de_roles = {}
            for role in ['effect', 'score', 'label']:
                cols = [c for c in de_df.columns if c.startswith(f'{role}_')]
                if cols:
                    de_roles[role] = cols
            if de_roles:
                roles['varm'][key] = de_roles
    
    adata.uns['exploreDE_column_roles'] = roles
```

---

## Rationale

### Why metadata-first?

1. **Maximum compatibility** - Accepts data with any column naming convention
2. **No forced renaming** - Original column names preserved
3. **Multi-tool interop** - Different apps can define their own role mappings
4. **Future-proof** - New roles can be added without changing column names

### Why keep prefix fallback?

1. **Convenience** - FGCZ native data can skip explicit metadata
2. **Self-documenting** - Prefixed columns are discoverable without docs
3. **Backward compatibility** - Works with existing sushi/exploreDE datasets
4. **Bootstrap mechanism** - Helps users who don't know about metadata requirement

### Why not prefix-only?

The meeting discussion identified key limitations:
- Forces external data providers to rename columns
- Creates brittleness when column names vary across tools
- Limits ecosystem growth

---

## Implementation Strategy

### 1. ColumnResolver (Core Abstraction)

```python
class ColumnResolver:
    """Resolves semantic column roles to actual column names"""
    
    def __init__(self, adata):
        self.adata = adata
        self._ensure_column_roles()
    
    def _ensure_column_roles(self):
        """Ensure exploreDE_column_roles exists, auto-discover if missing"""
        if 'exploreDE_column_roles' not in self.adata.uns:
            discover_exploreDE_column_roles(self.adata)
            if not self.adata.uns.get('exploreDE_column_roles'):
                raise ValueError(
                    "No column roles found. Please provide "
                    "adata.uns['exploreDE_column_roles'] mapping."
                )
    
    def get_columns(self, role, location='var', de_test=None):
        """
        Get all columns for a given role
        
        Args:
            role: Column role ('effect', 'score', 'label', 'factor', 'hierarchy')
            location: 'var', 'obs', or 'varm'
            de_test: Required if location='varm', e.g. 'DE_treated_vs_control'
        
        Returns:
            List of column names matching the role
        """
        roles = self.adata.uns['exploreDE_column_roles']
        
        if location not in roles:
            raise ValueError(
                f"Location '{location}' not found in column_roles. "
                f"Available: {list(roles.keys())}"
            )
        
        if location == 'varm':
            if de_test is None:
                raise ValueError(
                    "de_test required when location='varm'. "
                    f"Available DE tests: {list(roles['varm'].keys())}"
                )
            if de_test not in roles['varm']:
                raise ValueError(
                    f"DE test '{de_test}' not found. "
                    f"Available: {list(roles['varm'].keys())}"
                )
            return roles['varm'][de_test].get(role, [])
        
        return roles[location].get(role, [])
    
    def get_primary_column(self, role, location='var', de_test=None):
        """Get the primary/first column for a role"""
        cols = self.get_columns(role, location, de_test)
        if not cols:
            loc_str = f"{location}.{de_test}" if de_test else location
            raise ValueError(f"No columns found for role '{role}' in {loc_str}")
        return cols[0]
    
    def list_de_tests(self):
        """List all available DE tests"""
        roles = self.adata.uns.get('exploreDE_column_roles', {})
        return list(roles.get('varm', {}).keys())
    
    def get_de_columns(self, de_test, role):
        """Convenience method for accessing DE-specific columns"""
        return self.get_columns(role, location='varm', de_test=de_test)
```

### 2. Data Creation Workflow

**For FGCZ native data (option A - prefix-based):**
```python
# Feature annotations in var
adata.var['label_gene_symbol'] = ...
adata.var['label_protein_id'] = ...
adata.var['hierarchy_protein'] = ...
adata.var['hierarchy_peptide'] = ...

# Sample metadata in obs
adata.obs['factor_condition'] = ...
adata.obs['factor_batch'] = ...
adata.obs['label_sample_name'] = ...

# DE results in varm (one per contrast)
adata.varm['DE_treated_vs_control'] = pd.DataFrame({
    'effect_log2fc': ...,
    'score_pvalue': ...,
    'score_padj': ...,
    'label_t_statistic': ...
})

# On first access, resolver auto-populates:
# adata.uns['exploreDE_column_roles'] = {
#     'var': {
#         'description': ['description'],  # Required!
#         'label': ['label_gene_symbol', 'label_protein_id']
#     },
#     'obs': {
#         'factor': ['factor_condition', 'factor_batch'],
#         'label': ['label_sample_name']
#     },
#     'varm': {
#         'DE_treated_vs_control': {
#             'effect': ['effect_log2fc'],
#             'score': ['score_pvalue', 'score_padj'],
#             'label': ['label_t_statistic']
#         }
#     }
# }
```

**For FGCZ native data (option B - explicit metadata):**
```python
# Feature annotations with any names
adata.var['gene_symbol'] = ...
adata.var['protein_id'] = ...

# Sample metadata with any names
adata.obs['condition'] = ...
adata.obs['batch'] = ...

# DE results with any names
adata.varm['DE_treated_vs_control'] = pd.DataFrame({
    'log2fc': ...,
    'pvalue': ...,
    'padj': ...
})

# Provide explicit mapping
adata.uns['exploreDE_column_roles'] = {
    'var': {
        'description': ['description'],  # Required!
        'label': ['gene_symbol', 'protein_id']
    },
    'obs': {
        'factor': ['condition', 'batch']
    },
    'varm': {
        'DE_treated_vs_control': {
            'effect': ['log2fc'],
            'score': ['pvalue', 'padj']
        }
    }
}
```

**For external data:**
```python
# MaxQuant/DESeq2/etc output with original names
# Feature annotations
adata.var['Gene.names'] = ...  # MaxQuant style
adata.var['Protein.IDs'] = ...

# DE results (e.g., from DESeq2)
adata.varm['DE_treatment_vs_control'] = pd.DataFrame({
    'log2FoldChange': ...,  # DESeq2 style
    'pvalue': ...,
    'padj': ...
})

# User provides mapping once
adata.uns['exploreDE_column_roles'] = {
    'var': {
        'description': ['Protein.names'],  # Use Protein.names as description
        'label': ['Gene.names', 'Protein.IDs']
    },
    'obs': {
        'factor': ['condition']
    },
    'varm': {
        'DE_treatment_vs_control': {
            'effect': ['log2FoldChange'],
            'score': ['pvalue', 'padj']
        }
    }
}
```

### 3. Validator

```python
def validate_anndata(adata):
    """Check if AnnData conforms to exploreDE spec"""
    
    # Try to initialize resolver (triggers auto-discovery)
    try:
        resolver = ColumnResolver(adata)
    except ValueError as e:
        return {'status': 'FAIL', 'errors': [str(e)]}
    
    # Check required roles exist
    required_roles = ['effect', 'score']
    missing = []
    for role in required_roles:
        if not resolver.get_columns(role):
            missing.append(role)
    
    if missing:
        return {
            'status': 'FAIL',
            'errors': [f"Missing required roles: {missing}"]
        }
    
    return {'status': 'PASS'}
```

---

## Usage in Applications

### Before (direct column access):
```python
# Brittle - assumes specific column names and locations
volcano_plot(
    adata.var['effect_log2fc'],      # Wrong! Effect is in varm, not var
    adata.var['score_fdr']
)
```

### After (resolver-based):
```python
# Flexible - works with any column names
resolver = ColumnResolver(adata)

# Access feature annotations from var
gene_symbols = adata.var[resolver.get_primary_column('label', location='var')]
protein_col = adata.var[resolver.get_primary_column('hierarchy', location='var')]

# Access sample metadata from obs
conditions = adata.obs[resolver.get_primary_column('factor', location='obs')]

# Access DE results from varm (must specify which DE test)
de_test_name = 'DE_treated_vs_control'
effect_data = adata.varm[de_test_name][
    resolver.get_primary_column('effect', location='varm', de_test=de_test_name)
]
score_data = adata.varm[de_test_name][
    resolver.get_primary_column('score', location='varm', de_test=de_test_name)
]

# Create volcano plot
volcano_plot(effect_data, score_data)

# Convenience method for DE columns
effect_col = resolver.get_de_columns('DE_treated_vs_control', 'effect')[0]
score_col = resolver.get_de_columns('DE_treated_vs_control', 'score')[0]

# List all available DE tests
for de_test in resolver.list_de_tests():
    print(f"DE test: {de_test}")
    effects = resolver.get_de_columns(de_test, 'effect')
    scores = resolver.get_de_columns(de_test, 'score')
    print(f"  Effect columns: {effects}")
    print(f"  Score columns: {scores}")
```

---

## Migration Path

1. **Phase 1**: Implement ColumnResolver with auto-discovery
2. **Phase 2**: Update exploreDE to use resolver
3. **Phase 3**: Provide converter utilities for common external formats
4. **Phase 4**: Update spec documentation to recommend metadata approach

---

## Trade-offs Accepted

### Pros
✅ Maximum flexibility for data creators  
✅ No forced column renaming  
✅ Multi-tool ecosystem friendly  
✅ Backward compatible with prefix convention  

### Cons
⚠️ Requires resolver abstraction (~50 lines of code)  
⚠️ Two ways to specify roles (can be confusing)  
⚠️ Auto-discovery can be "magical" (but explicit override available)  

---

## Open Questions

1. **Priority rules**: If `uns['column_roles']` specifies multiple columns for a role, which is "primary"?
   - Current decision: First in list
   
2. **Naming conflicts**: What if auto-discovery finds prefixes AND metadata exists?
   - Current decision: Metadata always wins (explicit > implicit)

3. **Validation level**: Should validator require metadata, or accept auto-discoverable prefixes?
   - Current decision: Accept both, warn if relying on auto-discovery

4. **varm structure**: Should we support non-DataFrame varm entries, or only DataFrames for DE results?
   - Current assumption: `varm['DE_*']` entries are always DataFrames with columns
   - Alternative: Could be arrays/matrices (would need different access pattern)

5. **Multiple DE tests**: How to handle UI when multiple DE tests exist?
   - Need clear test selection mechanism
   - Consider default/primary test designation

---

## Next Steps

1. ✅ Document architecture decision
2. ⬜ Create Python implementation of ColumnResolver
3. ⬜ Build AnnData examples (gene expression, proteomics)
4. ⬜ Implement validator
5. ⬜ Update specification document
6. ⬜ Create converter utilities for common formats

---

**References:**
- Meeting summary: 2025-10-02 column annotation strategy discussion
- Original spec: `SE_spec_2025-10-02_restructured.md`
