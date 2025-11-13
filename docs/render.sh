#!/bin/bash
export R_LIBS_USER=/Users/wolski/Library/R/4.5-arm64
export RETICULATE_PYTHON=/Users/wolski/projects/anndata_omics_bridge/.venv/bin/python
quarto render "$@"
