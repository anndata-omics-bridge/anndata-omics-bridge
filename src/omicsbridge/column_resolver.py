"""
ColumnResolver: Abstract away column name differences using semantic roles

This class allows tools to work with AnnData objects without hard-coding
specific column names. Instead, columns are accessed by their semantic role
(e.g., 'description', 'effect', 'factor').
"""

class ColumnResolver:
    """Resolves semantic column roles to actual column names for any application."""

    def __init__(self, adata, app_name='exploreDE'):
        """
        Initialize the ColumnResolver.

        Parameters
        ----------
        adata : AnnData
            The AnnData object to resolve columns from
        app_name : str
            The application name (default: 'exploreDE')
        """
        self.adata = adata
        self.app_name = app_name
        if self.app_name not in adata.uns:
            raise ValueError(f"No {self.app_name} config found in adata.uns")
        if 'column_roles' not in adata.uns[self.app_name]:
            raise ValueError(f"No column_roles found in adata.uns['{self.app_name}']")

    def get_columns(self, role, location='var', de_test=None):
        """
        Get all columns for a given role.

        Parameters
        ----------
        role : str
            The semantic role (e.g., 'description', 'effect', 'factor')
        location : str
            Either 'var' or 'obs' (default: 'var')
        de_test : str, optional
            Name of the DE test (if accessing DE results)

        Returns
        -------
        list
            List of column names matching the role
        """
        roles = self.adata.uns[self.app_name]['column_roles']

        # DE test results are stored at the top level of column_roles
        if de_test is not None:
            return roles.get(de_test, {}).get(role, [])

        return roles[location].get(role, [])

    def get_primary_column(self, role, location='var', de_test=None):
        """
        Get the primary (first) column for a role.

        Parameters
        ----------
        role : str
            The semantic role
        location : str
            Either 'var' or 'obs' (default: 'var')
        de_test : str, optional
            Name of the DE test (if accessing DE results)

        Returns
        -------
        str
            The primary column name for this role

        Raises
        ------
        ValueError
            If no columns are found for the specified role
        """
        cols = self.get_columns(role, location, de_test)
        if not cols:
            loc_str = de_test if de_test else location
            raise ValueError(f"No columns found for role '{role}' in {loc_str}")
        return cols[0]
