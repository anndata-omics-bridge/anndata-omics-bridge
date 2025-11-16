# ColumnResolver: Abstract away column name differences using semantic roles
#
# This R6 class allows tools to work with AnnData objects without hard-coding
# specific column names. Instead, columns are accessed by their semantic role
# (e.g., 'description', 'effect', 'factor').

library(R6)

ColumnResolver <- R6Class("ColumnResolver",
    public = list(
        #' @field adata The AnnData object
        adata = NULL,

        #' @field app_name The application name (e.g., 'exploreDE')
        app_name = NULL,

        #' @description Initialize the ColumnResolver
        #' @param adata AnnData object to resolve columns from
        #' @param app_name Application name (default: 'exploreDE')
        initialize = function(adata, app_name = 'exploreDE') {
            self$adata <- adata
            self$app_name <- app_name
            if (!(app_name %in% names(adata$uns))) {
                stop(sprintf("No %s config found in adata$uns", app_name))
            }
            if (!('column_roles' %in% names(adata$uns[[app_name]]))) {
                stop(sprintf("No column_roles found in adata$uns$%s", app_name))
            }
        },

        #' @description Get all columns for a given role
        #' @param role The semantic role (e.g., 'description', 'effect', 'factor')
        #' @param location Either 'var' or 'obs' (default: 'var')
        #' @param de_test Name of the DE test (if accessing DE results)
        #' @return Character vector of column names matching the role
        get_columns = function(role, location = 'var', de_test = NULL) {
            roles <- self$adata$uns[[self$app_name]]$column_roles

            # DE test results are stored at the top level of column_roles
            if (!is.null(de_test)) {
                return(unlist(roles[[de_test]][[role]]))
            }

            return(unlist(roles[[location]][[role]]))
        },

        #' @description Get the primary (first) column for a role
        #' @param role The semantic role
        #' @param location Either 'var' or 'obs' (default: 'var')
        #' @param de_test Name of the DE test (if accessing DE results)
        #' @return The primary column name for this role
        get_primary_column = function(role, location = 'var', de_test = NULL) {
            cols <- self$get_columns(role, location, de_test)
            if (length(cols) == 0) {
                loc_str <- ifelse(!is.null(de_test), de_test, location)
                stop(sprintf("No columns found for role '%s' in %s", role, loc_str))
            }
            return(cols[1])
        },

        # Convenience methods for cleaner API
        #' @description Get primary column from var by role
        var = function(role) {
            self$get_primary_column(role, location = 'var')
        },

        #' @description Get all columns from var by role
        var_all = function(role) {
            self$get_columns(role, location = 'var')
        },

        #' @description Get primary column from obs by role
        obs = function(role) {
            self$get_primary_column(role, location = 'obs')
        },

        #' @description Get all columns from obs by role
        obs_all = function(role) {
            self$get_columns(role, location = 'obs')
        },

        #' @description Get primary column from DE test by role
        de = function(de_test, role) {
            self$get_primary_column(role, de_test = de_test)
        },

        #' @description Get all columns from DE test by role
        de_all = function(de_test, role) {
            self$get_columns(role, de_test = de_test)
        }
    )
)
