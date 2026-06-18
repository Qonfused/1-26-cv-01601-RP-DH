## @file
# Copyright (c) 2026, Cory Bennett. All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause
##
# latexmkrc - workspace LaTeX defaults
#
# Exhibit extraction is orchestrated by _latex-workshop-build.py so it can pass
# a document-scoped generated-output directory into both LaTeX and the extractor.

# Allow latexmk cleanup to recognize transient manifest files.
push @generated_exts, 'exhibit-manifest.txt';

# Do not remove generated exhibit packets during latexmk cleanup.
$clean_ext = "";
