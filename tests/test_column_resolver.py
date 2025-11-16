"""Tests for ColumnResolver class."""

import pytest
import anndata as ad
import numpy as np
import pandas as pd
from omicsbridge.column_resolver import ColumnResolver


@pytest.fixture
def sample_adata():
    """Create a sample AnnData object with column roles for testing."""
    np.random.seed(42)
    adata = ad.AnnData(X=np.random.randn(10, 5))

    # Add var with column roles
    adata.var = pd.DataFrame({
        'protein_id': [f'P{i:05d}' for i in range(5)],
        'description': [f'Protein {i}' for i in range(5)],
        'gene_symbol': [f'GENE{i}' for i in range(5)],
        'uniprot_id': [f'UNI{i:05d}' for i in range(5)]
    }, index=[f'P{i:05d}' for i in range(5)])

    # Add obs with column roles
    adata.obs = pd.DataFrame({
        'sample_id': [f'S{i}' for i in range(10)],
        'treatment': ['control'] * 5 + ['treated'] * 5,
        'batch': [1, 2] * 5
    }, index=[f'S{i}' for i in range(10)])

    # Add DE results to varm
    adata.varm['DE_treated_vs_control'] = pd.DataFrame({
        'logFC': np.random.randn(5),
        'pvalue': np.random.uniform(0, 1, 5),
        'padj': np.random.uniform(0, 1, 5),
        'baseMean': np.random.uniform(100, 10000, 5)
    }, index=adata.var_names)

    # Define column roles for exploreDE
    adata.uns['exploreDE'] = {
        'column_roles': {
            'var': {
                'description': ['description'],
                'label': ['gene_symbol', 'protein_id', 'uniprot_id']
            },
            'obs': {
                'factor': ['treatment', 'batch'],
                'label': ['sample_id']
            },
            'DE_treated_vs_control': {
                'effect': ['logFC'],
                'score': ['pvalue', 'padj'],
                'label': ['baseMean']
            }
        },
        'de_tests': {}
    }

    return adata


class TestColumnResolverInit:
    """Test ColumnResolver initialization."""

    def test_init_success(self, sample_adata):
        """Test successful initialization."""
        resolver = ColumnResolver(sample_adata, app_name='exploreDE')
        assert resolver.adata is sample_adata
        assert resolver.app_name == 'exploreDE'

    def test_init_missing_app_config(self, sample_adata):
        """Test initialization fails when app config is missing."""
        with pytest.raises(ValueError, match="No nonexistent config found"):
            ColumnResolver(sample_adata, app_name='nonexistent')

    def test_init_missing_column_roles(self, sample_adata):
        """Test initialization fails when column_roles is missing."""
        sample_adata.uns['exploreDE'] = {}
        with pytest.raises(ValueError, match="No column_roles found"):
            ColumnResolver(sample_adata, app_name='exploreDE')


class TestSimplifiedAPI:
    """Test the new simplified API methods."""

    def test_var_primary(self, sample_adata):
        """Test var() returns primary column from var."""
        resolver = ColumnResolver(sample_adata, app_name='exploreDE')
        assert resolver.var('description') == 'description'
        assert resolver.var('label') == 'gene_symbol'

    def test_var_all(self, sample_adata):
        """Test var_all() returns all columns from var."""
        resolver = ColumnResolver(sample_adata, app_name='exploreDE')
        assert resolver.var_all('description') == ['description']
        assert resolver.var_all('label') == ['gene_symbol', 'protein_id', 'uniprot_id']

    def test_obs_primary(self, sample_adata):
        """Test obs() returns primary column from obs."""
        resolver = ColumnResolver(sample_adata, app_name='exploreDE')
        assert resolver.obs('factor') == 'treatment'
        assert resolver.obs('label') == 'sample_id'

    def test_obs_all(self, sample_adata):
        """Test obs_all() returns all columns from obs."""
        resolver = ColumnResolver(sample_adata, app_name='exploreDE')
        assert resolver.obs_all('factor') == ['treatment', 'batch']
        assert resolver.obs_all('label') == ['sample_id']

    def test_de_primary(self, sample_adata):
        """Test de() returns primary column from DE test."""
        resolver = ColumnResolver(sample_adata, app_name='exploreDE')
        assert resolver.de('DE_treated_vs_control', 'effect') == 'logFC'
        assert resolver.de('DE_treated_vs_control', 'score') == 'pvalue'

    def test_de_all(self, sample_adata):
        """Test de_all() returns all columns from DE test."""
        resolver = ColumnResolver(sample_adata, app_name='exploreDE')
        assert resolver.de_all('DE_treated_vs_control', 'effect') == ['logFC']
        assert resolver.de_all('DE_treated_vs_control', 'score') == ['pvalue', 'padj']
        assert resolver.de_all('DE_treated_vs_control', 'label') == ['baseMean']


class TestLegacyAPI:
    """Test the legacy verbose API still works."""

    def test_get_primary_column_var(self, sample_adata):
        """Test get_primary_column() with location='var'."""
        resolver = ColumnResolver(sample_adata, app_name='exploreDE')
        assert resolver.get_primary_column('description', location='var') == 'description'

    def test_get_columns_obs(self, sample_adata):
        """Test get_columns() with location='obs'."""
        resolver = ColumnResolver(sample_adata, app_name='exploreDE')
        assert resolver.get_columns('factor', location='obs') == ['treatment', 'batch']

    def test_get_primary_column_de_test(self, sample_adata):
        """Test get_primary_column() with de_test."""
        resolver = ColumnResolver(sample_adata, app_name='exploreDE')
        result = resolver.get_primary_column('effect', de_test='DE_treated_vs_control')
        assert result == 'logFC'

    def test_get_columns_de_test(self, sample_adata):
        """Test get_columns() with de_test."""
        resolver = ColumnResolver(sample_adata, app_name='exploreDE')
        result = resolver.get_columns('score', de_test='DE_treated_vs_control')
        assert result == ['pvalue', 'padj']


class TestErrorHandling:
    """Test error handling."""

    def test_var_missing_role(self, sample_adata):
        """Test var() raises error for missing role."""
        resolver = ColumnResolver(sample_adata, app_name='exploreDE')
        with pytest.raises(ValueError, match="No columns found for role 'nonexistent'"):
            resolver.var('nonexistent')

    def test_obs_missing_role(self, sample_adata):
        """Test obs() raises error for missing role."""
        resolver = ColumnResolver(sample_adata, app_name='exploreDE')
        with pytest.raises(ValueError, match="No columns found for role 'nonexistent'"):
            resolver.obs('nonexistent')

    def test_de_missing_role(self, sample_adata):
        """Test de() raises error for missing role."""
        resolver = ColumnResolver(sample_adata, app_name='exploreDE')
        with pytest.raises(ValueError, match="No columns found for role 'nonexistent'"):
            resolver.de('DE_treated_vs_control', 'nonexistent')


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_role_list(self, sample_adata):
        """Test behavior when role exists but is empty list."""
        sample_adata.uns['exploreDE']['column_roles']['var']['empty'] = []
        resolver = ColumnResolver(sample_adata, app_name='exploreDE')

        # var_all should return empty list
        assert resolver.var_all('empty') == []

        # var should raise error
        with pytest.raises(ValueError, match="No columns found"):
            resolver.var('empty')

    def test_single_column_role(self, sample_adata):
        """Test role with single column."""
        resolver = ColumnResolver(sample_adata, app_name='exploreDE')
        # description has only one column
        assert resolver.var('description') == 'description'
        assert resolver.var_all('description') == ['description']

    def test_multiple_column_role(self, sample_adata):
        """Test role with multiple columns."""
        resolver = ColumnResolver(sample_adata, app_name='exploreDE')
        # label has multiple columns
        assert resolver.var('label') == 'gene_symbol'  # Returns first
        assert len(resolver.var_all('label')) == 3  # Returns all three
