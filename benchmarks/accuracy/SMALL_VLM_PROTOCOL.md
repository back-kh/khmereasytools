# Exploratory small vision language model comparison

This addition evaluates two user-requested small VLMs on **all 30 official
CHURRO-DS Khmer test pages** already selected by the full-page protocol. The
five-system comparison still covers all 150 historical pages. This addition
does not expand the two Qwen systems to the 120 source-training pages.

The addition was specified after the original experiment began and after
completed CPU and initial Surya outputs existed. It is exploratory, not a
preregistered extension or an independent confirmation of a selected prompt.
No Qwen evaluation prediction is used to choose a checkpoint or prompt.

## Models and resource boundary

- `Qwen/Qwen2.5-VL-3B-Instruct`, revision
  `66285546d2b821cf421d4f5eb2576359d3770cd3`.
- `Qwen/Qwen3-VL-2B-Instruct`, revision
  `89644892e4d85e24eaac8bacfd4f463576704203`.

Use the original BF16 checkpoints, native Transformers processors and SDPA
attention, sequentially on one shared A100 80 GB GPU. The process exposes only
one GPU and caps its Torch allocator at 20 percent of that GPU's memory.
Existing jobs are not stopped. These are research comparators, with no new
KhmerEasyTools runtime dependency or installation-time download.

The model names give nominal family sizes. Record actual weight file bytes
separately. Kimi-VL-A3B has 16B total parameters and 3B activated parameters;
it is excluded from this small-download comparison. DeepSeek-OCR is already
part of the five-system experiment. No unrun model is assigned an accuracy
score.

## Inputs and generation

Use the exact upright RGB PNG bytes from the frozen full-page study. The
inference server receives images, source identities and hashes, **without
reference transcripts**. Local scoring later joins outputs with the original
released references. No box coordinates, line crops, masks or OCR outputs
are supplied to either Qwen model.

The native image processor has a fixed 112,896 to 1,003,520 pixel budget.
Record each actual image grid. Other settings are batch one, greedy decoding,
4,096 new tokens, a 240-second per-page deadline, seed 20261018, repetition
penalty 1.0, and no repeated-ngram filter. Use this prompt unchanged:

> Transcribe all visible text in this image exactly as written. Preserve Khmer
> and Latin characters, digits and punctuation. Read blocks from top to bottom
> and tables row by row, left to right. Do not translate, explain, summarize,
> correct spelling or invent missing text. Return only the transcription,
> without Markdown or formatting labels.

Verify integration on the existing known-English image and a previously used
KHOB development page before freezing the environment. These controls do not
enter the 30-page comparison. Freeze model file digests, evaluator bytes,
input inventory, software versions and generation settings before test calls.
Resume only with the same token and input hashes. Keep failures and cap hits.

## Scoring and interpretation

Use the same fixed serializer and compact NFC code-point CER as the full-page
study. Retain hallucinated prose, empty outputs and failed-page denominators.
Compare all seven systems on the same 30 official test pages, and keep the
150-page five-system results separate. CER may exceed 100 percent.

Paired differences against Tesseract use the existing conservative filename
groups, 5,000 bootstrap resamples and seed 20261018. Intervals are descriptive;
group identities are not verified independent books and there is no
multiplicity correction. Public reports contain per-page edit counts and
provenance, without redistributing page images or complete recognized text.

The Qwen runs use Linux/CUDA BF16, while the other VLM profiles use local
Mac implementations and different precision. Report these implementation
differences. Shared-GPU contention and different batching prevent a controlled
speed ranking. Unknown pretraining overlap and the small historical test
partition limit generalization to modern Khmer business documents.

## Separately supplied KH FUNSD images

The user later supplied a local folder containing 148 business-document
images, with 146 distinct source-byte and upright-RGB hashes. No transcript
or layout annotation files were supplied. They are separate from publicly
released KH-FUNSD annotations and are not part of the 30-page Qwen benchmark.
Without an official identity/annotation mapping, correspondence to the 158
documents described in the KH-FUNSD paper is not verified. Distinct image
hashes also do not establish independent documents or complete-page coverage.

Codex transcription drafts are reference-authoring material, not human-reviewed
OCR gold. Keep source hashes, the literal transcription prompt, model/CLI
configuration, uncertainty notes and a false human-review flag with each
draft. Do not report agreement with these drafts as independently established
OCR accuracy. The images and draft transcripts remain private research files.

## Primary sources

- https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct
- https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct
- https://huggingface.co/moonshotai/Kimi-VL-A3B-Instruct
- https://huggingface.co/datasets/stanford-oval/churro-dataset
- https://github.com/back-kh/KH-FUNSD
