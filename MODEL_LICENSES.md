# Software and bundled model licenses

The Python software and independently authored rule-only tagger use the root
MIT [LICENSE](LICENSE). The MIT license does **not** cover these corpus-derived
research assets:

- `khmereasytools/data/research/ket_pos_v2.json.gz`
- `khmereasytools/data/research/manifest.json`

Those files, including trained weights, vocabulary and lexical counts, are
adapted from the khPOS corpus by Vichet Chea and Ye Kyaw Thu and distributed
under **Creative Commons Attribution-NonCommercial-ShareAlike 4.0**.
Retain attribution and adaptation notices. Commercial use of the model files
is not permitted by that license. See the [full model notice and legal text](khmereasytools/data/research/LICENSE.txt).

Default `khtag` uses the research model. `model="rules"` uses the independently
authored rules and does not load the corpus-derived weights. There is no
license change to software source code or the pre-existing dictionary assets;
their existing notices remain in their data files.
