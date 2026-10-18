# OCR target reports

See [interpretation](../../../docs/OCR_TARGET.md), the frozen
[protocol](../OCR_TARGET_PROTOCOL.md) and
[selection](../OCR_TARGET_SELECTION.md). No production algorithm changed.
The sub-10% target is not met on the 40-image comparison.

development/ preserves the original four prototype measurements on 20
images. These records preceded the final installed-wheel harness. The fast
prototype did not record its model hash; the pinned baseline/model is
identified in the protocol and final reports. The prototype explicitly
prepared best-profile pixels before recognition with preprocessing disabled.
The final harness calls the existing public automatic preprocessing directly
for auto profiles, verifies actual model checksums, and records runtime/input
hashes. The fixed auto predictions reproduce the prototype comparison.

local/ contains the final public-API comparison and derived PDF transport
check on macOS. Native CI artifacts additionally record the exact source
revision and built wheel hash. Within each workflow the same wheel is used
on all OSes. The install-test and accuracy workflows build independently.

The two mismatched development pairings are retained in raw records. Their
IDs are excluded from the 40-image comparison. Gold references and full
predictions are not stored here or packaged; .evaluation keeps them ignored.
Acquisition variants are correlated, and possible label/reading-order issues
remain. A successful workflow does not establish a successful accuracy target.
