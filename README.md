# Bennett v. University of Texas at Austin

**Bennett v. The University of Texas at Austin, et al., No. 1:26-cv-01601 (W.D. Tex. filed June 12, 2026).**

This repository contains the public filing package and build tools for a federal civil rights case against The University of Texas at Austin and several university officials.

The complaint alleges disability-access violations under ADA Title II and Section 504, ADA/Section 504 retaliation and interference, procedural due process violations, and First Amendment retaliation. The public filings are in `Civil/Filing/`.

## Why this repository exists

The filed documents are public court materials. Keeping the source files on GitHub makes it easier to inspect how the PDFs were prepared:

- the filed PDFs can be read directly;
- the LaTeX sources can be compared with the PDFs;
- the exhibit assembly tooling is documented instead of hidden in local scripts;
- other pro se litigants or public-interest projects can adapt the build workflow.

This is not the full working case file. All private drafts, sealed financial materials, raw source exhibits, attorney-consultation materials, and unrelated working notes are excluded.

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

## Local inputs that are not tracked

The repository keeps placeholder `.gitkeep` files for several local input directories, but the real contents are excluded.

- `Exhibits/Documents/` is where source exhibit PDFs and documents live. These files may contain private emails, medical or disability records, financial information, or other sensitive evidence.
- `Exhibits/_Generated/` is where extracted exhibit PDFs are written during a build.
- `Signatures/` is where local cropped signature PDFs live.
- `REDACTIONS.txt` can contain private literal text to redact from generated exhibit PDFs.

Use `REDACTIONS.example.txt` as the template for creating a local `REDACTIONS.txt`.

A fresh clone can read the tracked public PDFs and sources. It cannot rebuild every filing document unless the missing local exhibit sources, signature PDFs, and redaction terms are supplied.

## Building

### Command line

The main command is:

```bash
python3 _latex-workshop-build.py Civil/Filing/civil-complaint.tex
```

### VS Code and LaTeX Workshop

The repository also includes VS Code integration for the [LaTeX Workshop](https://marketplace.visualstudio.com/items?itemName=James-Yu.latex-workshop) extension. `.vscode/settings.json` defines a LaTeX Workshop recipe that calls `_latex-workshop-build.py`, and `latexmkrc` keeps the command-line LaTeX build configuration aligned with that workflow.

### Generated exhibits

For documents that include generated exhibits, the build script runs LaTeX, reads the generated manifest, extracts or crops referenced PDFs, applies configured redactions, and runs LaTeX again so generated exhibit previews are available.

### Local requirements

The workflow expects:

- a working LaTeX installation with `latexmk`;
- PDF utilities such as `pdfinfo`, `pdfseparate`, `pdfunite`, and `pdfjam`;
- PyMuPDF when using the Python PDF cropping and redaction helpers;
- local source exhibits under `Exhibits/Documents/`;
- local signature PDFs under `Signatures/` when a filing uses `signatures.tex`.

## Reusing the tooling

The build system assumes a case-file layout like this one:

- public filing sources under `Civil/Filing/`;
- source exhibits outside the tracked filing package;
- generated exhibit PDFs under `Exhibits/_Generated/`;
- shared filing metadata in `filing-info.tex`;
- optional signature helpers in `signatures.tex`.

For another case, replace `filing-info.tex`, update the filing documents, provide local exhibit sources, and revise `.gitignore` to match that case's privacy boundary.

## License and legal note

This repository is public for inspection, citation, and reuse of the workflow where legally permitted. No separate license file is currently included, so add a license before treating the repository as granting broad reuse rights.

Nothing in this repository is legal advice. The allegations and legal positions are those stated in the filed case materials.
