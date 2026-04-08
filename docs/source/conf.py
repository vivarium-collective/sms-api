# Configuration file for the Sphinx documentation builder.

import os
import sys

sys.path.insert(0, os.path.abspath("../../sms_api"))
sys.path.insert(0, os.path.abspath("../.."))

# Detect ReadTheDocs environment (sms_api not installable due to Python pin)
on_rtd = os.environ.get("READTHEDOCS") == "True"

# -- Project information -----------------------------------------------------

project = "Atlantis API (SMS API)"
copyright = "2025-2026, Alexander Patrie, Jim Schaff, Ryan Spangler"
author = "Alexander Patrie, Jim Schaff, Ryan Spangler"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "myst_parser",
]

if not on_rtd:
    extensions += [
        "sphinx.ext.autodoc",
        "sphinx.ext.autosummary",
        "sphinx.ext.viewcode",
    ]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

if on_rtd:
    exclude_patterns += ["api/*"]

# MyST (Markdown) settings
myst_enable_extensions = [
    "colon_fence",
    "deflist",
]
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# Autodoc settings (only used in local builds)
autoclass_content = "both"
autosummary_generate = True
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}

# Napoleon settings (Google/NumPy docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = True

# Intersphinx
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_logo = "_static/wholecellecoli.png"
html_theme_options = {
    "logo_only": False,
    "navigation_depth": 3,
}
pygments_style = "sphinx"
