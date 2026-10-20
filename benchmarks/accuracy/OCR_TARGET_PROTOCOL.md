# Sub-10% Khmer OCR target: protocol, 2026-10-18

Freeze this protocol before inspecting new candidate scores. Baseline runtime:
0603c9d5346a4d6263c9e3d61cf27888d44c487d. Keep the earlier measurements.

The target is micro-averaged compact Unicode-code-point CER < 0.10 over
the same 40 KHOB images, without changing references or scoring. This is an
adaptive benchmark comparison: those pages have already been evaluated.
It cannot establish a universal guarantee or replace a new independent test.
The 40 images represent only 10 underlying printed documents, each acquired
four ways. Report all four acquisition categories and page-level variation.

Use the same five development document IDs (20 images) as
IMPROVEMENT_PROTOCOL.md. Do not inspect reserved candidate results before
selecting one configuration from development data. Do not use gold crops,
gold-based spelling corrections, per-page best-of runs, or altered labels.

Compare four predetermined configurations on development pages:

1. Current fast model, automatic 2x grayscale/autocontrast, PSM 3.
2. Official tessdata_best Khmer model, same preprocessing, PSM 3.
3. Same best model, 3x grayscale/autocontrast on small images, PSM 3.
4. Same best model, current automatic preprocessing, PSM 4 (single column).

Pin tessdata_best revision e12c65a915945e4c28e237a9b52bc4a8f39a0cec.
Record downloaded bytes and SHA-256 before inference. Neither model is
trained or modified here. Select the lowest development CER; if a tie,
prefer the existing preprocessing and smaller/faster configuration. If best
does not improve over fast, retain fast. Run only the selected configuration
on the 40-image comparison partition and the existing 15-page image-only
PDF transport fixture. The latter is derived from the same images, not an
independent corpus. Preserve original image coordinates in any shipped API.

Keep the default lightweight model and zero-dependency core. An improved
model must be opt-in, downloaded only by an explicit setup action, verified,
and kept outside the package/system Tesseract directory. Record speed and
disk tradeoffs. Test the shipped public image/PDF API in fresh Windows,
macOS, and Linux installations with pinned fast and best model checksums.
Live translation remains pending at the user's request.
