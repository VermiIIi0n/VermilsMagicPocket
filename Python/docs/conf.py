# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import toml
import os
import sys

project = 'Vermils Magic Pocket .Python'
copyright = '2023, VermiIIi0n'
author = 'VermiIIi0n'

sys.path.insert(0, os.path.abspath('..'))

# Load the project version from pyproject.toml
with open("../pyproject.toml") as f:
    metadata = toml.load(f)["tool"]["poetry"]
version = metadata["version"]
release = version
# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx_autodoc_typehints',
    'sphinx.ext.coverage',
    'sphinx.ext.napoleon',
    'autoapi.extension',
]

autoapi_options = ['members', 'undoc-members', 'show-inheritance']
autoapi_add_toctree_entry = False
autodoc_typehints = 'description'
autoapi_dirs = ['../vermils']
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'classic'
html_static_path = ['_static']
