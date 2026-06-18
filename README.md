# Bennett v. University of Texas at Austin

**Bennett v. The University of Texas at Austin, et al., No. 1:26-cv-01601 (W.D. Tex. filed June 12, 2026).**

This repository contains the public filing package and build tools for a federal civil rights case against The University of Texas at Austin and several university officials.

The complaint alleges disability-access violations under ADA Title II and Section 504, ADA/Section 504 retaliation and interference, procedural due process violations and First Amendment retaliation under Section 1983.

The public filings are located in `Civil/Filing/`:

- [Civil complaint PDF](Civil/Filing/civil-complaint.pdf) ([source](Civil/Filing/civil-complaint.tex))
- [Complaint exhibits PDF](Civil/Filing/complaint-exhibits.pdf) ([source](Civil/Filing/complaint-exhibits.tex))

## Why this repository exists

The filed documents are public court materials on official record. Keeping the source files on GitHub makes it easier to inspect how these documents were prepared:

- the filed PDFs can be read directly;
- the LaTeX sources can be compared with the PDFs;
- the exhibit assembly tooling is documented and organized for reproduction.;
- other pro se litigants or public-interest projects can adapt the build workflow.

This repository contains public filing materials for the case as it develops. Official docket entries and filed documents may be obtained through [PACER](https://pacer.uscourts.gov/). For confidentiality reasons, all private drafts, raw source exhibits, and unrelated working notes remain outside this repository and are not tracked.

## What is tracked

`Civil/Filing/` contains the public filing documents:

- `civil-complaint.{tex,pdf}`
- `complaint-exhibits.{tex,pdf}`
- `motion-counsel-appointment.{tex,pdf}`
- `motion-restrict-ifp-affidavit.{tex,pdf}`
- `permission-file-electronically.{tex,pdf}`
- `proposed-summons.{tex,pdf}`

`Civil/Filing/Reference/` contains court forms, manuals, and complaint-review materials used while preparing the filing package.

The root directory contains shared build files:

- `filing-info.tex`: caption, party, date, and contact metadata used by the filing documents.
- `signatures.tex`: LaTeX helpers for inserting local signature PDFs.
- `extract-subexhibits.tex`: LaTeX macros for exhibit manifests, exhibit tables, and generated PDF previews.
- `_latex-workshop-build.py`: the main build entrypoint.
- `_extract-subexhibits.py`: creates cropped/generated exhibit PDFs from a LaTeX manifest.
- `_redactions.py`: applies literal text redactions to generated exhibit PDFs.
- `_extract-signatures.py`: extracts cropped signature PDFs from a source signature page.
- `_clean-latex-artifacts.py`: removes LaTeX auxiliary files after builds.
- `.vscode/settings.json` and `latexmkrc`: editor/build configuration.

`LICENSE` contains the BSD 3-Clause text for reusable tooling files marked with `SPDX-License-Identifier: BSD-3-Clause`.

## Local inputs that are not tracked

The repository depends on several local inputs that are not tracked for privacy reasons. These include:

- `Exhibits/Documents/` is where source exhibit PDFs and documents live. These files may contain private emails, medical or disability records, financial information, or other sensitive evidence.
- `Exhibits/_Generated/` is where extracted exhibit PDFs are written during a build.
- `Signatures/` is where local cropped signature PDFs live.
- `REDACTIONS.txt` can contain private literal text to redact from generated exhibit PDFs.

Use `REDACTIONS.example.txt` as the template for creating a local `REDACTIONS.txt`.

A fresh clone can read the tracked public PDFs and sources. Though it cannot rebuild every filing document unless the missing exhibits, signature PDFs, and REDACTION.txt files are supplied.

## Building

### Command line

You can build the filing documents with the included Python build script, which runs LaTeX and the PDF extraction/redaction helpers as needed. For example, to build the civil complaint:

```bash
python3 _latex-workshop-build.py Civil/Filing/civil-complaint.tex
```

If `uv` is installed, the build script uses `uv run --script` for helper scripts that declare PEP 723 dependencies.

### VS Code and LaTeX Workshop

The repository also includes VS Code integration for the [LaTeX Workshop](https://marketplace.visualstudio.com/items?itemName=James-Yu.latex-workshop) extension. `.vscode/settings.json` defines a LaTeX Workshop recipe that calls `_latex-workshop-build.py`, and `latexmkrc` keeps the command-line LaTeX build configuration aligned with that workflow.

After installing the LaTeX Workshop extension, you can open any `.tex` file and use the "Build LaTeX project" command (default `Ctrl+Alt+B`) to trigger the build process. By default, saving a `.tex` file will also trigger an automatic build, and no manual configuration of the extension is needed to get started.

The build script will automatically run LaTeX, extract exhibits, apply any redactions, and clean up auxiliary files as needed.

### Generated exhibits

For documents that include generated exhibits, the build script runs LaTeX and generates a manifest to extract or crop referenced PDFs, applies configured redactions, and re-runs LaTeX to embed generated exhibits as pages in the final PDF.

### Local requirements

The workflow expects:

- a working LaTeX installation with `latexmk`;
- PDF utilities such as `pdfinfo`, `pdfseparate`, `pdfunite`, and `pdfjam` available in the system path (e.g., via [poppler](https://poppler.freedesktop.org/));
- `uv` or `pymupdf>=1.24` installed in the active Python environment for text-based cropping or redactions;
- local source exhibits under `Exhibits/Documents/`;
- local signature PDFs under `Signatures/` for custom signatures.

## Reusing the tooling

The build system assumes a case-file layout like this one:

- public filing sources under `Civil/Filing/`;
- source exhibits in `Exhibits/Documents/`;
- shared filing metadata in `filing-info.tex`;
- optional signature PDFs under `Signatures/`;

For another case, start with customizing `filing-info.tex` and the source filing LaTeX sources. Then add the local exhibits and adjust `.gitignore` for any private files. The build script and helper scripts can be reused as-is, but the LaTeX sources may need to be adjusted for different document structure or exhibit referencing.

## License and legal note

Build tooling marked with `SPDX-License-Identifier: BSD-3-Clause` is licensed under the BSD 3-Clause License. The license text is located in [`LICENSE`](/LICENSE). This license allows for reuse and modification of the licensed files with attribution and without warranty, subject to the conditions outlined in the license.

That license covers only files carrying the BSD-3-Clause SPDX header, including the Python helper scripts, `extract-subexhibits.tex`, `signatures.tex`, and `latexmkrc`.

The filed pleadings, exhibits, case-specific allegations, court/reference forms, signature PDF assets, redaction files, and other case materials remain outside this repository license but available for reference. Official docket copies are available through [PACER](https://pacer.uscourts.gov/).

Nothing in this repository is legal advice. The allegations and legal positions are those stated in the filed case materials.
