# Public grammatical-role adapter amendment

After the first reserved evaluation, inspection of the authored development
checks found that the public adapter suppressed existing aspect/discourse
roles whenever the trained corpus POS label differed from the v1 rule label.
For example, khPOS can call a modal VERB while the authored helper calls it
AUX. Dropping the independent ability/aspect role was an adapter limitation.

The adapter now retains the existing fixed aspect/discourse role hypotheses
across that tagset difference. It introduces no new lexical rule, training
example, weight, frequency or vocabulary entry. POS labels, token boundaries,
native predictions and the copula-to-NOVA projection remain unchanged. User
overrides and the conservative personal/demonstrative/location roles retain
their previous handling. Reasons still identify roles as heuristics.

This is **adapted development** of the role interface after seeing the authored
cases, not an independent role-accuracy gain. `tagger-v2/results-initial.json`
preserves the first public evaluation (24/37 authored assertions). The rerun
must verify identical native/public POS and span counts on CLOSE, OPEN and ALT
before accepting the new role output. Fine roles have no independent gold in
these corpora. The selected 244,666-byte research model and its SHA-256 remain
frozen; no training or model selection is repeated.
