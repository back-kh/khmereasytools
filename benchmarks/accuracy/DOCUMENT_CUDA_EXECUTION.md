# CUDA execution amendment for the remaining MLX profiles

This execution amendment follows the user's request to keep local research
files on Drive F and use the `.27` server for GPU work. It is recorded after
the CPU runs and some Surya predictions, **before any Paddle or DeepSeek
evaluation prediction**. It changes their execution platform, without using
test CER to select a checkpoint, prompt, or recognition option.

The original source and recognition protocol remains frozen in
`DOCUMENT_OCR_PROTOCOL.md`, at source revision
`85d0c7d74ddce198e83d5fba268dd586582d0a34` and evaluation token
`2b75fc64024edc9a9a64d92df22998ac21fb39886918a82797bd0dcd201bd9c3`.
Completed Tesseract and KhmerEasyTools predictions are retained. Surya finishes
its existing Mac first-pass profile. The originally planned Mac Paddle and
DeepSeek evaluation directories contain zero predictions when this amendment
is made; their setup controls remain available as setup history.

## Preserved recognition design

Both moved systems still cover **all 150 selected historical leaf images**:
30 official source-test pages and the same 120 source-training stress pages.
The source training partition is not relabeled as an official test set.
Input PNG bytes, source identities, image hashes, released reference hashes,
and filename groups are unchanged. The server receives no reference text.
Locally supplied business-image drafts are outside this experiment.

The exact pinned MLX community checkpoint files are unchanged:

- `mlx-community/PaddleOCR-VL-1.6-4bit`, revision
  `c8987b277bdd8aaec8bd265d154f391bd03ad165`.
- `mlx-community/DeepSeek-OCR-4bit`, revision
  `4958b6b0d46d7dc3cf27556989dab659996ea426`.

Use `mlx-vlm==0.7.8` and `mlx==0.32.4`, with their native load, image
processing, chat-template rendering and generation calls. Paddle receives
`OCR:` and DeepSeek receives `Free OCR.`. The DeepSeek rendered template must
contain exactly one image marker. Do not add word boxes, line crops, layout
labels, masks, translation, spelling repair, or reference text.

Other recognition settings remain batch one, seed 20261018, temperature 0.0,
4,096 output tokens and a 240-second per-page deadline. Clear the MLX cache
after each page. Retain all errors, empty outputs and token-cap hits. Failed
outputs retain their full reference denominator. Do not choose a device,
prompt or precision by comparing evaluation CER.

## Changed platform and software identity

Run these two MLX systems sequentially on physical GPU 2, a shared NVIDIA
A100 80 GB PCIe under Linux, using `mlx-cuda-12==0.32.4`. Expose only this GPU,
set the MLX allocator limit to 16 GiB, disable CUDA TF32 with
`MLX_ENABLE_TF32=0`, and use four CPU processing threads. Existing jobs remain
running. The Qwen extension separately uses physical GPU 3 under its own
already-frozen profile.

The MLX environment uses Python 3.10, Torch 2.14.1 CPU, torchvision 0.29.1 CPU,
Transformers 5.20.1, Pillow 10.4.0, and NumPy 2.2.6. Torch provides CPU image
processing; MLX performs GPU model inference. The Mac environment uses Python
3.11 and NumPy 2.4.6. Full framework archive hashes, NVIDIA component versions,
driver identity and generation settings are frozen before evaluation.
Different kernels and platform dependencies can change numerical behavior;
identical predictions or conversion fidelity across devices are not claimed.

Before freezing, check an actual CUDA matrix operation and both existing OCR
controls. Both GPU implementations return zero compact CER on the known-English
control and complete the KHOB development call without a runtime error. The
Paddle Khmer control still reaches the token cap. These are integration checks,
not new-corpus accuracy results or a selection of a better Khmer prompt.

The standalone Paddle VLM remains distinct from the complete Paddle document
pipeline. Surya remains the explicitly configured first-pass GGUF profile.
The MLX conversions remain distinct from the original unquantized models.
Shared GPUs, different backends, precisions and batching prevent a controlled
speed ranking or a general ranking of model families.

## Freeze, scoring and audit

`evaluate_mlx_cuda.py` freezes evaluator bytes, this amendment, the blinded
input inventory, exact checkpoint inventory, framework archive inventory,
software versions and hardware settings. Resume only with the same token and
image hashes. The server stores raw predictions with that CUDA token and the
original source-experiment token; it never scores against references.

Local reporting joins each output with the original released transcript,
applies the original frozen serializer and metrics, and combines the three
Mac profiles with the two CUDA profiles. Keep separate per-system environment
identities. Never relabel CUDA records with the old Mac environment token.
The final report requires all 150 records for every system.

Compact NFC code-point CER, source-split tables, descriptive paired filename-
group resampling, seed 20261018 and 5,000 bootstrap replicates remain unchanged.
The independent integer bit-vector auditor recomputes every edit count and
checks the composite profile bookkeeping. Native Windows, macOS and Linux
installation tests remain a separate claim from recognition accuracy on these
Mac and Linux GPU implementations.

The CUDA framework packages, model weights, images, transcripts and complete
predictions remain outside the installed KhmerEasyTools package. The runtime
source and daily-use defaults are unchanged.

Primary framework source: [MLX 0.32.4 CUDA installation documentation](https://ml-explore.github.io/mlx/build/html/install.html#cuda).
