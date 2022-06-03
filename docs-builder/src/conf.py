# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))

# -- Project information -----------------------------------------------------

project = 'pkm-cli'
copyright = '2022, Benny Lutati'
author = 'Benny Lutati'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.githubpages",
    'sphinx.ext.duration',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.viewcode',
    'utils.compile_scss',
    'utils.custom_roles',
    'utils.generate_api_docs',
    'sphinxarg.ext',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []
add_module_names = False
autodoc_typehints_format = "short"
master_doc = "master"

# -- Options for API generation ----------------------------------------------
build_apis = ["pkm_cli.api", "pkm.api"]

# -- Options for HTML output -------------------------------------------------

# import sphinx_pdj_theme
#
html_theme = 'agogo'
html_css_files = ["docs.css"]
pygments_style = "one-dark"
class_roles = ["program", "package", "file", "toml-table", "toml-key", "name"]
# htm_theme_path = [sphinx_pdj_theme.get_html_theme_path()]

# sets the darker appearence
html_theme_options = {
    'rightsidebar': False
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
