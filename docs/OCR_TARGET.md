# Khmer OCR below 10% character error

The overall target is **not met** on the current printed-document comparison.
Keep the lightweight default. A larger official model and two additional
settings did not justify changing everyday behavior or adding a new option.

## Fixed comparison

The baseline is runtime commit 0603c9d5346a4d6263c9e3d61cf27888d44c487d.
The existing five-document development partition selected best/auto/PSM 3
from four predefined settings. Development gains were only 12 character
edits; 3x enlargement and PSM 4 were worse. The selected configuration then
ran unchanged on the 40-image comparison partition. No spelling correction,
reference editing, gold crops, or best-of selection per image was used.

Local macOS, Tesseract 5.5.2, same input images and transcripts:

| Model, same auto preprocessing | Edits / reference code points | Compact CER |
| --- | ---: | ---: |
| Existing fast Khmer | 9,215 / 80,606 | 11.4322% |
| Optional best Khmer | 9,261 / 80,606 | 11.4892% |

Half the default-model pages are below 10%, but individual page CER ranges
from 2.16% to 25.02%. This variation prevents a consistent sub-10% claim.
The derived 15-page scan PDF scores 11.8582% with fast and 11.5265% with
best: a small PDF improvement, still above target and using the same images.

The larger model made 46 more edits on this sample. Its 8,104,332-byte
download remains an evaluation dependency, outside the package and the
system model directory. No automatic model download, extra runtime package,
or production model change was introduced. The zero-dependency core stays
the same. The existing installed image/PDF APIs are used for both models;
model selection is isolated in each evaluation subprocess.

To get strictly below 10% on these fixed references, the default would need
at least 1,155 fewer edits. Neither passing integration tests nor the name
"best" establishes that improvement. Successful CI means the experiment
ran correctly; its JSON separately reports `target_met: false`.

These 40 images represent only 10 underlying government documents in four
correlated acquisition variants. They were previously evaluated, so this is
an adaptive benchmark comparison, not new independent evidence. CER applies
NFC and removes Unicode whitespace/ZWSP; it counts code points, not Khmer
grapheme clusters. Keep the supplementary whitespace-sensitive metric and
all page scores. OCR confidence is not a substitute for labeled evaluation.

## Corpus issue found during development

In the pinned KHOB archive, task-2/goc_3.jpg shows the vaccination-guidance
document, while its JSON transcript describes the intellectual-property-day
letter. task-2/goc_4.jpg shows that letter but is paired with the guidance
transcript. Visual inspection and the development predictions identify the
swapped document pair. Their annotation `imagePath` fields use those names.

The archive SHA-256 is
976b050d5e8a24e9654223bab2520b9cd750f5ebaa7024e7c594adf02886a703.
Image SHA-256 values:

- task-2/goc_3.jpg: 2fc406c95d8f987f564ac47bd7e169ba3213417c68e2737644a49a67cb892672
- task-2/goc_4.jpg: 9a36d413699e053670c7d6bfffc9b33015fbabd18c473aaec03dc951ffcacdaf

Both IDs belong to development, so the 40-image comparison above excludes
them. The published raw development/historical scores remain preserved;
their aggregates include this mismatch and cannot be interpreted as pure
recognition error. This discovery does not reduce the reported 40-image
error rate. References are unchanged in this experiment. A separate audit
and independently checked transcripts are needed before stronger claims.

## Reproduce and inspect

See the frozen [protocol](../benchmarks/accuracy/OCR_TARGET_PROTOCOL.md),
[development selection](../benchmarks/accuracy/OCR_TARGET_SELECTION.md), and
[count reports](../benchmarks/accuracy/ocr-target/README.md). External gold,
images and predictions stay in ignored .evaluation. Models are official
Tesseract data under [Apache 2.0](https://github.com/tesseract-ocr/tessdata_best).

~~~bash
python -m pip install '.[all]' -r requirements-evaluation.txt
python scripts/fetch_accuracy_data.py
# Prepare isolated CI model directories, with printed locations and SHA checks:
python scripts/prepare_ocr_ci.py
python scripts/prepare_ocr_ci.py --best
python scripts/evaluate_ocr_target.py --profile fast-auto --partition reserved --tessdata-dir /path/to/ket-tessdata --pdf-transport
python scripts/evaluate_ocr_target.py --profile best-auto --partition reserved --tessdata-dir /path/to/ket-tessdata-best --pdf-transport
~~~

The native accuracy workflow installs the built wheel in a fresh venv on
Windows, macOS and Linux. It runs both fixed model profiles and a 15-page
PDF made losslessly from the physical scans at their source pixel size.
This PDF is a transport test using the same images, not a separate corpus.
Artifacts identify the wheel, runtime sources, model, engine and input hashes.
Core/all-extras installation tests also exercise the real OCR/POS backends.
Live translation stays pending by user choice.

For a defensible sub-10% release claim, collect new representative daily
documents with independently reviewed transcripts, keep all variants of
one document in the same split, and freeze the test set before further
tuning. Report overall error and variation by document, not just a selected
easy subset. Higher-resolution, upright, evenly lit input is worth measuring:
[Tesseract's quality guide](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html)
suggests at least 300 DPI and explains scale/skew/binarization effects. That
is input guidance, not evidence that a particular document will meet 10%.
