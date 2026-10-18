# Exploratory small VLM evaluation

This research extension compares **Qwen2.5-VL-3B-Instruct** and
**Qwen3-VL-2B-Instruct** on the same 30 official CHURRO-DS Khmer test pages used
in the [150-page study](DOCUMENT_OCR.md). It does not add 60 independent pages
or extend the Qwen systems to the other 120 pages. The five original systems
still cover all 150 pages.

A subsequent [execution amendment](../benchmarks/accuracy/DOCUMENT_CUDA_EXECUTION.md)
moves the primary Paddle and DeepSeek profiles to MLX CUDA before either has
an evaluation prediction. The Qwen profile remains unchanged. The matched
comparison therefore includes Mac GGUF, MLX CUDA and Torch CUDA implementations.

The [protocol](../benchmarks/accuracy/SMALL_VLM_PROTOCOL.md) was written after
the primary experiment began, before any Qwen evaluation predictions. This is
an exploratory comparison. Neither model, prompt nor generation settings are
selected using its test outputs.

## Isolated GPU setup

The evaluated checkpoints are the original BF16 files, not their quantized
conversions. Their weight files occupy approximately 6.99 GiB and 3.96 GiB.
Qwen2.5-VL-3B uses the Qwen Research License Agreement; Qwen3-VL-2B lists
Apache 2.0. Model-family size labels do not measure download or memory size.
Kimi-VL-A3B has 16B total parameters despite 3B activated parameters and is not
included in this small-download comparison. DeepSeek-OCR is already evaluated
in the primary study.

The research environment uses Python 3.10, Torch 2.8.0, torchvision 0.23.0,
Transformers 5.20.1, Accelerate 1.10.1 and Pillow 10.4.0. It exposes one shared
A100 80 GB GPU, caps its Torch allocator at 20 percent of device memory, and
runs one model at a time. Existing server jobs are left running. These settings
are a recorded research profile, not general minimum hardware requirements.
No package or checkpoint is installed by KhmerEasyTools itself.

Download and verify the pinned original model files explicitly:

```bash
python scripts/fetch_small_vlm_models.py \
  --manifest benchmarks/accuracy/small-vlm/model-selection.json \
  --destination .evaluation/small_vlm/models \
  --inventory-out .evaluation/small_vlm/model-inventory.json
```

Create the input inventory from the frozen primary experiment, retaining all
30 official test identities and their exact RGB PNG hashes. Transfer only the
images, `inputs.json`, model inventories, checkpoint files, evaluator,
protocol, and setup controls to the inference machine. The inventory records
the primary evaluation token. **Do not transfer reference transcripts.**
The repository's `source-inventory.json` records the selected identities.

After validating the known-English and previously used KHOB development
controls, freeze the environment before evaluation. For the recorded server,
physical GPU 3 is exposed as the process's sole CUDA device:

```bash
CUDA_VISIBLE_DEVICES=3 python evaluate_small_vlm.py --data-root ./small-vlm --system qwen25-vl-3b --smoke
CUDA_VISIBLE_DEVICES=3 python evaluate_small_vlm.py --data-root ./small-vlm --system qwen3-vl-2b --smoke
CUDA_VISIBLE_DEVICES=3 python evaluate_small_vlm.py --data-root ./small-vlm --freeze
CUDA_VISIBLE_DEVICES=3 python evaluate_small_vlm.py --data-root ./small-vlm --system qwen25-vl-3b
CUDA_VISIBLE_DEVICES=3 python evaluate_small_vlm.py --data-root ./small-vlm --system qwen3-vl-2b
```

Use native processors, greedy decoding, a 4,096-token output cap, 240-second
per-page deadline and fixed image pixel budget. Resume only with the same
frozen token and input hashes. Retain errors, empty outputs and cap hits.
Bring `frozen.json` and the complete prediction directories back to
`.evaluation/small_vlm/server-run/`, then join references and score locally:

```bash
python scripts/report_small_vlm.py
```

The reporter checks the frozen input/evaluator identities and independently
recomputes edit counts using a separate standard-library implementation.
Compact NFC code-point CER and descriptive paired filename-group intervals
match the primary study. CUDA BF16, Mac GGUF and MLX CUDA profiles have different
implementations and precision; shared hardware and different batching prevent
a controlled speed ranking. Public test membership does not establish absence
from pretraining data.

## Recorded results

Both Qwen implementations completed the same **30 official source-test
images**, with **13,201 compact NFC reference code points**. The table retains
all seven implementations on that common subset. It does not combine the
Qwen subset with the other 120 historical pages.

| Frozen implementation | Edits | Compact CER | Empty | Runtime errors | Token caps |
| --- | ---: | ---: | ---: | ---: | ---: |
| Tesseract fast LSTM | 12,747 | 96.56% | 5 | 0 | N/A |
| KhmerEasyTools fast | 12,747 | 96.56% | 5 | 0 | N/A |
| Surya 2 first-pass GGUF on Mac | 71,713 | 543.24% | 0 | 0 | 21 |
| PaddleOCR-VL 1.6 MLX 4-bit on CUDA | 69,705 | 528.03% | 4 | 0 | 24 |
| DeepSeek-OCR MLX 4-bit on CUDA | 104,609 | 792.43% | 3 | 0 | 27 |
| Qwen2.5-VL-3B BF16 on CUDA | 72,308 | 547.75% | 0 | 0 | 11 |
| Qwen3-VL-2B BF16 on CUDA | 90,326 | 684.24% | 0 | 0 | 30 |

| Qwen comparison with Tesseract | CER difference in points | Descriptive 95% group interval |
| --- | ---: | ---: |
| Qwen2.5-VL-3B BF16 on CUDA | +451.19 | [+393.75, +495.89] |
| Qwen3-VL-2B BF16 on CUDA | +587.68 | [+544.51, +648.73] |

Negative differences favor the named Qwen implementation. Intervals use
5,000 paired resamples of 14 heuristic filename groups. They are descriptive
and do not establish pairwise significance among all seven systems.

The [complete Qwen results](../benchmarks/accuracy/small-vlm/local-results.json)
include frozen identities, all 60 per-page records and an independent audit
of 180 edit-distance projections. Errors, empty outputs and caps are retained.
CER can exceed 100% because of insertions. The
[generation diagnostic](../benchmarks/accuracy/document-ocr/generation-diagnostics.json)
describes lengths and repeated sequences without clipping or deduplicating
predictions. None of these checks independently validates the source labels.

Different precision, native image resizing and patch allocation, batching and
shared hardware prevent causal attribution to architecture or nominal model
size. These historical handwriting results do not certify modern printed
documents, phone scans or business-field extraction.

## Private business-image reference preparation

A separately supplied local folder has 148 images, with 146 distinct image
hashes after two duplicate pairs. No transcript or layout labels were supplied.
Mapping these files to the 158 documents described in the published KH-FUNSD
paper is unverified. Distinct hashes do not establish independent documents or
complete-page coverage.

The user explicitly requested Codex transcription. The research-only
`draft_khfunsd_codex.py` uses an already authenticated Codex CLI, one full image
per fresh call, strict JSON, literal text, uncertainty notes and no tools. It
sends these images to the configured Codex service. This is separate from the
local OCR backends and is never invoked by the installed toolkit.

After all drafts are generated, the compiler verifies their provenance and
prepares private JSONL and an offline review page:

```bash
python scripts/compile_business_reference_drafts.py
```

Every draft begins with `human_reviewed: false`. The review page preserves
source identities and prior browser edits, requires a reviewer name, and
blocks complete-reference export while `[ILLEGIBLE]` remains. Editing a
transcript clears its completeness approval. Export a backup of reviews;
browser storage alone is not an archival copy. When browser storage is
unavailable, edits remain in the current page session and should be exported
before closing.

**These model-generated drafts are not independent OCR gold.** No benchmark
CER is calculated against them. A Khmer reader must review every visible
character and reading order before a document can support a modern-document
accuracy claim. Images and full draft transcripts remain private; only
aggregate authoring counts and configuration are committed.

The [reference-review workflow](REFERENCE_REVIEW.md) specifies image coverage,
literal correction, independent second-pass review, document grouping and
reference freezing before future comparison predictions.
