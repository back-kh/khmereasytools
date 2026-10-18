# OCR target development selection, 2026-10-18

Selected before running a new candidate on the 40-image comparison partition:
official best Khmer model with the existing automatic preprocessing and PSM 3.
Protocol SHA-256: 20491c15325ae4529f98e44280eab9188882ce8d8a3aaf3804892c95c644d044.

| Development configuration | Edits / reference code points | Compact CER |
| --- | ---: | ---: |
| Current fast / auto / PSM 3 | 6,566 / 34,617 | 18.9676% |
| Best / auto / PSM 3 | 6,554 / 34,617 | 18.9329% |
| Best / 3x gray / PSM 3 | 6,716 / 34,617 | 19.4009% |
| Best / auto / PSM 4 | 6,651 / 34,617 | 19.2131% |

The selected gain is only 12 edits on this development set. Do not infer
significance or a general advantage from it. The default remains unchanged.
Best model: 8,104,332 bytes; SHA-256
3d2d975e67a319bf1cd67626b12fdebc1e417a4ebef9c9afee01d9927b512815.

During development inspection, task-2/goc_3 and task-2/goc_4 were found to
have swapped images relative to their JSON transcripts. The former image
contains vaccination guidance, while its transcript describes an intellectual
property day letter; the latter has the converse mismatch. Both documents
are in the development partition. Original labels/scores are retained here;
the 40 comparison images do not include either ID. This finding invalidates
interpreting the development aggregate as a pure recognition error rate and
requires a separate corpus audit. It is not an OCR runtime improvement.

Run the selected candidate unchanged on the 40 comparison images. Results
remain an adaptive benchmark check rather than an independent test.
