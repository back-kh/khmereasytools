# Public full page Khmer OCR evaluation

This study adds **150 complete historical manuscript page images**, using
SleukRith pages distributed in CHURRO-DS. It is a handwriting stress test outside
the toolkit's printed-page design scope. It does not replace the small KHOB
printed-document comparison or supply a new modern phone-scan benchmark.

The toolkit implementation is unchanged. Heavy baseline packages, model weights,
page images and transcripts remain outside the installed package.

The recorded execution design uses **three Mac profiles and two Linux CUDA
profiles**. The [CUDA execution amendment](../benchmarks/accuracy/DOCUMENT_CUDA_EXECUTION.md)
moves Paddle and DeepSeek before either system has an evaluation prediction.
It preserves the selected images, checkpoint files and recognition arguments.
The [per-system identity record](../benchmarks/accuracy/document-ocr/execution-amendment.json)
retains both frozen tokens. The independent [Qwen extension](SMALL_VLM.md)
covers only the 30 official test pages.

## Data availability and source quality

The [source survey](../benchmarks/accuracy/document-ocr/data-survey.json) records
public resources and exclusion reasons. CHURRO-DS supplies 622 Khmer pages at
revision `cbeaba69179d5de122fbbc9e97b2a7d97942f688`: 562 train, 30 development and
30 test. We use all 30 official test pages and 120 train pages selected by fixed
SHA-256 ordering. The source training pages are explicitly identified as an
external stress test for this untrained toolkit; they are not relabeled as
CHURRO's official test set. No development page enters the experiment.

The complete Hugging Face viewer-delivered JPEG page is converted to upright RGB
PNG. Released `original_transcription` supplies the reference; generated XML
descriptions and metadata are excluded. These are not certified byte-identical
original SleukRith image files. The selected set has 150 distinct image and raw
reference hashes and 27 conservative filename groups. Group identities are not
independently verified book identities. Pretrained-model overlap and inherited
transcription errors remain possible.

KH-FUNSD describes 158 business documents but its public repository currently
provides no image/annotation download. Khmer Document Corpus version 0.1 lacks
OCR gold. A separate survey found 11 Wikisource pages marked proofread among 294
Khmer page candidates; visual inspection found missing printed header text and
stray markup. The entire candidate collection was excluded before inference.
Its images do not count toward the 150 scored pages.

## Protocol and inference profiles

The [protocol](../benchmarks/accuracy/DOCUMENT_OCR_PROTOCOL.md) records source
selection, image handling, model profiles, deadlines, output normalization and
uncertainty. The [amendment](../benchmarks/accuracy/document-ocr/protocol-amendment.json)
explains a Surya integration correction: its default transport retries repetitive
responses at higher temperatures, and RecognitionPredictor can invoke additional
layout/block inference. The intended first-pass comparison explicitly disables
those paths. The incomplete initial attempt remains recorded. CPU profiles are
rerun and Surya uses the amended first-pass transport. The later CUDA execution
amendment changes the remaining MLX hosts and platform dependencies before
their evaluation calls, retaining source selection, references, checkpoint
bytes, prompts and scalar generation limits.

| System | Evaluated profile |
| --- | --- |
| Tesseract fast | `khm+eng`, PSM 3, OEM 1; original integer LSTM models |
| KhmerEasyTools fast | Same engine/models, auto preprocessing, engine reading order, no downstream segmentation |
| Surya OCR 2 | Official GGUF, native full-page prompt/image processing, first pass, zero retries and no layout/block fallback |
| PaddleOCR-VL 1.6 | Pinned MLX community 4-bit conversion on CUDA, standalone VLM, `OCR:` prompt |
| DeepSeek-OCR | Pinned MLX community 4-bit conversion on CUDA, native processor and free-OCR prompt |

All VLMs use greedy decoding with a 4,096-token output cap. Surya batches four
independent requests; other VLMs use batch one. Tesseract uses four CPU workers
with `OMP_THREAD_LIMIT=1`. These concurrent local timings do not establish a
controlled speed ranking. Surya's per-page time is amortized batch time. The
MLX variants do not establish accuracy of their
unquantized originals or the complete Paddle document pipeline.

Model and setup identities appear in the [model inventory](../benchmarks/accuracy/document-ocr/model-inventory.json)
and [setup controls](../benchmarks/accuracy/document-ocr/setup-controls.json).
Paddle's known-English image control and a control sent to the active Surya
backend both have zero compact CER. This confirms that the installed variants
recognize that control; it does not establish reliable Khmer handwriting.
Surya and DeepSeek setup checks also use a KHOB development page.

## Reproduction

Tesseract and Surya use **macOS on Apple Silicon**, Python 3.11 and a local
Metal-enabled `llama-server`. Paddle and DeepSeek use **Linux CUDA**, Python 3.10
and a shared A100 80 GB GPU. These accuracy profiles are separate from the
toolkit's Windows/macOS/Linux installation tests. External checkpoint and
framework downloads are explicit and research-only.

The recorded environment uses `surya-ocr==0.22.1`, `mlx-vlm==0.7.8`,
`mlx==0.32.4`, `torch==2.14.1`, `transformers==5.20.1`, `Pillow==10.4.0`,
`pytesseract==0.3.13`, `pypdfium2==5.14.0`, `rapidfuzz==3.14.6`,
`numpy==2.4.6`, and `beautifulsoup4==4.15.0`. Full package and executable
versions are recorded in the environment manifest. Build and install the wheel
in an isolated research environment before executing with `python -I`.

```bash
python -m pip install build
python -m build --wheel --outdir .evaluation/document-wheel
python -m venv .evaluation/document-env
.evaluation/document-env/bin/python -m pip install .evaluation/document-wheel/*.whl
.evaluation/document-env/bin/python -m pip install \
  surya-ocr==0.22.1 mlx-vlm==0.7.8 mlx==0.32.4 \
  torch==2.14.1 transformers==5.20.1 Pillow==10.4.0 \
  pytesseract==0.3.13 pypdfium2==5.14.0 rapidfuzz==3.14.6 \
  numpy==2.4.6 beautifulsoup4==4.15.0 requests
.evaluation/document-env/bin/python scripts/fetch_document_ocr_models.py --model all
.evaluation/document-env/bin/python scripts/fetch_document_ocr.py --workers 3
.evaluation/document-env/bin/python -I scripts/evaluate_document_ocr.py --freeze
.evaluation/document-env/bin/python -I scripts/evaluate_document_ocr.py --system tesseract-fast
.evaluation/document-env/bin/python -I scripts/evaluate_document_ocr.py --system khmereasytools-fast
.evaluation/document-env/bin/python -I scripts/evaluate_document_ocr.py --system surya-2
```

Install the local Tesseract executable and `llama-server` separately. The harness
requires toolkit runtime source bytes matching `b062be0`. It verifies checkpoint
and input hashes. Freeze a new run only after setup controls; a changed
environment receives a new token and cannot reuse an incompatible prediction
cache. Retain any old frozen experiment rather than overwriting it.

The CUDA environment retains the same MLX and MLX-VLM versions, with
`mlx-cuda-12==0.32.4`, Torch 2.14.1 CPU, torchvision 0.29.1 CPU, Transformers
5.20.1, Pillow 10.4.0 and NumPy 2.2.6. Its [95-archive framework inventory](../benchmarks/accuracy/document-ocr/cuda-execution/framework-inventory.json)
records exact wheel hashes and original registry/vendor URLs. Download those
archives explicitly and install them into a fresh Python 3.10 environment;
`pip check` must pass. Keep it separate from the Qwen Torch/CUDA environment.

The [blinded inventory](../benchmarks/accuracy/document-ocr/cuda-execution/source-inventory.json)
contains the same 150 image identities without transcript text. For a fresh
replication, derive this inventory from the newly frozen primary experiment,
removing each page's `reference` field and recording its new source token.
Copy only the selected PNGs, pinned Paddle/DeepSeek checkpoint files, inventory,
framework inventory, evaluator and CUDA amendment to the inference host.
Do not transfer `prepared.json` or released transcript files. Preserve the
recorded image and checkpoint hashes.

After checking the matrix and existing English/KHOB development calls, freeze
the CUDA profile and run both complete 150-page profiles. Zero English control
CER does not establish Khmer accuracy; the Paddle Khmer control remains capped.
The recorded run
uses physical GPU 2, a 16 GiB MLX allocator limit and disabled TF32. Existing
server jobs remain running.

```bash
CUDA_VISIBLE_DEVICES=2 python scripts/evaluate_mlx_cuda.py --data-root .evaluation/document_mlx_cuda --device-control
CUDA_VISIBLE_DEVICES=2 python scripts/evaluate_mlx_cuda.py --data-root .evaluation/document_mlx_cuda --system paddleocr-vl-1.6-4bit --smoke
CUDA_VISIBLE_DEVICES=2 python scripts/evaluate_mlx_cuda.py --data-root .evaluation/document_mlx_cuda --system deepseek-ocr-4bit --smoke
CUDA_VISIBLE_DEVICES=2 python scripts/evaluate_mlx_cuda.py --data-root .evaluation/document_mlx_cuda --freeze
CUDA_VISIBLE_DEVICES=2 python scripts/evaluate_mlx_cuda.py --data-root .evaluation/document_mlx_cuda --system paddleocr-vl-1.6-4bit
CUDA_VISIBLE_DEVICES=2 python scripts/evaluate_mlx_cuda.py --data-root .evaluation/document_mlx_cuda --system deepseek-ocr-4bit
```

Return `frozen.json` and all CUDA prediction directories to
`.evaluation/document_mlx_cuda/server-run/`. Retain the matching local blinded
input, model, framework and protocol files. The execution amendment records
which systems use each token; a fresh replication must record its own tokens
and zero prior Mac predictions for the moved systems before test calls.
Then score locally and run the independent audit:

```bash
python -I scripts/report_document_ocr_cuda.py
python -I scripts/audit_document_ocr.py
```

After the separate Qwen report is also complete, run the optional post hoc
generation diagnostic:

```bash
python -I scripts/analyze_document_generation.py
```

This requires both completed studies and their edit-count audits. It records
compact output/reference length ratios and an explicitly defined overlapping
eight-code-point reuse fraction. Reuse describes repeated text and is not an
accuracy measure. The analysis leaves all predictions, token limits and CER
unchanged; it does not report a clipped or deduplicated alternative score.

The reporter refuses incomplete profiles and checks the original frozen files,
blinded selection, model identities, generation settings and execution order.
It preserves per-system environments and writes no composite results until
all five systems have 150 outputs. Different CUDA/Metal kernels and platform
dependencies can change numerical behavior; cross-device prediction identity
and conversion fidelity are not claimed.

The optional `--with-wikisource` acquisition flag repeats the exclusion audit.
Its live page inventory can change; use the pinned revisions and PDF hashes in
the committed excluded-page records to inspect the original audit. Numerical
comparison uses only the fixed 150 manuscript pages. Compare their image and
reference hashes with the committed inventory when reproducing.

Compact CER is a micro edit ratio after NFC, Unicode-whitespace and ZWSP removal.
It can exceed 100% and is not grapheme accuracy or linguistic word error rate.
Empty and failed calls retain full denominators. Tables separate the official
30-page test partition from the 120 source-train pages. Descriptive paired
intervals use 5,000 manuscript-group resamples and no multiplicity correction.

## Sources and terms

- [CHURRO-DS paper](https://aclanthology.org/2025.emnlp-main.1763/)
  and [dataset](https://huggingface.co/datasets/stanford-oval/churro-dataset).
- [Original SleukRith dataset](https://github.com/donavaly/SleukRith-Set).
- [Surya software](https://github.com/datalab-to/surya) and
  [official GGUF model](https://huggingface.co/datalab-to/surya-ocr-2-gguf).
- [Evaluated Paddle conversion](https://huggingface.co/mlx-community/PaddleOCR-VL-1.6-4bit).
- [Evaluated DeepSeek conversion](https://huggingface.co/mlx-community/DeepSeek-OCR-4bit).
- [Tesseract LSTM model documentation](https://tesseract-ocr.github.io/tessdoc/Data-Files.html).

CHURRO-DS permits research use and its paper records SleukRith research
permission. Source images, transcripts and full predictions are not redistributed.
External baseline licenses remain separate from the toolkit license. These
five historical OCR backends run locally and no model is trained. A separate
user-requested Codex workflow drafts references for locally supplied business
images through the authenticated model service; those drafts are not gold
labels. Live translation remains pending by user choice.
