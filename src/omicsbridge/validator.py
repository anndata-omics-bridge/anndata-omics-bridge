"""
AnnData Validator for exploreDE Specification

This validator checks if an AnnData object conforms to the exploreDE specification.
"""

import anndata as ad


def validate_anndata_omics(adata, app_name='exploreDE'):
    """
    Validate AnnData object against omics specification.

    Parameters
    ----------
    adata : AnnData
        The AnnData object to validate
    app_name : str
        Application name to validate for (default: 'exploreDE')

    Returns
    -------
    dict
        Dictionary with keys:
        - 'overall_status': 'PASS' or 'FAIL'
        - 'errors': List of error messages
        - 'warnings': List of warning messages
    """
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

    # Check for application configuration
    if app_name not in adata.uns:
        errors.append(f"No {app_name} config found in adata.uns['{app_name}']")
        return {"overall_status": "FAIL", "errors": errors, "warnings": warnings}

    # Check application structure
    if 'column_roles' not in adata.uns[app_name]:
        errors.append(f"{app_name} missing 'column_roles' section")
    if 'de_tests' not in adata.uns[app_name]:
        warnings.append(f"{app_name} missing 'de_tests' section (OK if no DE has been performed)")

    if 'column_roles' in adata.uns[app_name]:
        required_locations = ['var', 'obs']
        for loc in required_locations:
            if loc not in adata.uns[app_name]['column_roles']:
                errors.append(f"{app_name} column_roles missing '{loc}' section")

        # Check required roles for var (exploreDE-specific)
        if app_name == 'exploreDE' and 'var' in adata.uns[app_name]['column_roles']:
            if 'description' not in adata.uns[app_name]['column_roles']['var']:
                errors.append(f"{app_name} requires 'description' role in var")

        # Check required roles for obs
        if 'obs' in adata.uns[app_name]['column_roles']:
            if 'factor' not in adata.uns[app_name]['column_roles']['obs']:
                warnings.append(f"{app_name} has no 'factor' role in obs (required for DE analysis)")

    # Check DE results consistency (DE tests are at top level of column_roles)
    if 'column_roles' in adata.uns[app_name]:
        for key, roles in adata.uns[app_name]['column_roles'].items():
            # Skip var and obs, look for DE test entries
            if key.startswith('DE_') and isinstance(roles, dict):
                if key not in adata.varm:
                    errors.append(f"column_roles references '{key}' but it doesn't exist in varm")

                # Check required roles
                if 'effect' not in roles or not roles['effect']:
                    errors.append(f"DE test '{key}' missing 'effect' columns")
                if 'score' not in roles or not roles['score']:
                    errors.append(f"DE test '{key}' missing 'score' columns")

    # Overall status
    overall_status = "FAIL" if errors else "PASS"

    return {
        "overall_status": overall_status,
        "errors": errors,
        "warnings": warnings
    }
