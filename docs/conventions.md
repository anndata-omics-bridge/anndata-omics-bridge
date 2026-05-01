# Naming conventions

This document defines naming rules for AnnData objects produced by Omics Bridge converters. They apply uniformly across tools (DIA-NN, MaxQuant, Spectronaut, FragPipe, etc.) so that downstream consumers can rely on the same shape regardless of the upstream proteomics software.

## Where the per-tool config lives

Each consumer (e.g. `exploreDE`, `prolfqua`, `proteobench`) has its own namespace under `uns`:

```
uns
├── exploreDE
│   ├── column_roles
│   │   ├── var: { description: "...", label: "...", ... }
│   │   ├── obs: { factor: ["..."], ... }
│   │   └── de:  { ... }
│   └── ...
├── prolfqua
│   └── column_roles
│       ├── var: { hierarchy: ["protein", "peptide_seq"], intensity: "...", ... }
│       └── obs: { sample_id: "..." }
└── <other_app>
    └── column_roles { ... }
```

Column names referenced by these roles **stay arbitrary** — they preserve whatever the upstream tool wrote. Semantic meaning is carried by the `column_roles` mapping. Rationale and alternatives considered: see [adr_tool_specific_views.md](adr_tool_specific_views.md).

## Sanitisation of column and layer names

The following sanitisation is applied to **`obs.columns`**, **`var.columns`**, and **layer names** before they are written to AnnData. It is **not** applied to:

- row IDs (`obs_names` / `var_names`) — these preserve original identifiers (e.g. DIA-NN's `Modified.Sequence`)
- `uns` keys — these are namespaces and structural keys, not data column names

### Rule

Treat names like Linux filenames: case-preserving, dot-allowed, no whitespace, no special characters.

```python
import re
import unicodedata

def sanitize_name(name: str) -> str:
    """Linux-filename-style sanitiser for AnnData column / layer names.

    - Case is preserved (Linux filesystems are case-sensitive).
    - Dots are kept (DIA-NN's 'Protein.Group' stays 'Protein.Group').
    - Whitespace and other special characters are replaced with '_'.
    - Repeated underscores are collapsed; leading/trailing '_' and '.' are stripped.
    - Empty results fall back to 'col'.
    """
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^A-Za-z0-9_.]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_.")
    return name or "col"
```

### Examples

| Original                | Sanitised             |
|-------------------------|-----------------------|
| `Protein.Group`         | `Protein.Group`       |
| `Modified.Sequence`     | `Modified.Sequence`   |
| `Sample 01`             | `Sample_01`           |
| `Run #5`                | `Run_5`               |
| `log2(A vs B)`          | `log2_A_vs_B`         |
| `% missing`             | `missing`             |
| `.value`                | `value`               |
| `abc__def`              | `abc_def`             |
| `naïve`                 | `naive`               |

### Conflict policy

If two distinct original names sanitise to the same string, the converter **must raise** rather than silently de-duplicate (e.g. by suffixing `_1`, `_2`). The right place to resolve a collision is at the upstream renaming layer — not by hiding it behind a generated suffix.

Implementations should raise `ValueError` with both colliding originals and the shared sanitised result, e.g.:

```
ValueError: column-name collision after sanitisation:
  'Sample 01' -> 'Sample_01'
  'Sample-01' -> 'Sample_01'
```
