# Additional mixed-language OCR candidate, 2026-10-18

This is a separate, post-hoc follow-up to OCR_TARGET_PROTOCOL.md, not one
of its four predeclared candidates. That experiment missed the target.
After inspecting comparison errors, the highest-error document (mef_4)
visibly contains substantial English job titles. Default OCR uses only khm.
The existing structured API and CLI already support lang="khm+eng".

Test exactly one additional configuration: pinned tessdata_fast Khmer plus
pinned tessdata_fast English from revision
87416418657359cb625c412a48b6e1d6d41c29bd, language order khm+eng, current
automatic preprocessing, PSM 3, engine order, minimum confidence zero.
No new framework, spelling corrections, page-specific selection, or model
training. Verify the English model byte size/SHA-256 before inference.

Measure the existing 20 development images first and record any regression.
Then evaluate this explicit mixed-language mode once on the same 40-image
comparison and the derived 15-page PDF. Retain all prior single-language
scores and labels. This evaluates an existing language choice, not a new
independent test: the candidate was motivated by comparison-set inspection.
Do not replace the lightweight Khmer-only default on this evidence. Any
target result applies only to the measured mixed mode/sample, pending a
fresh independent daily-document test. Data-pairing issues remain as recorded.
