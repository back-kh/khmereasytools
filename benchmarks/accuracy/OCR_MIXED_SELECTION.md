# Mixed-language follow-up: development decision

Before mixed-language predictions on the 40 comparison images:

- Khmer-only fast, auto/PSM 3: 6,566 / 34,617 edits (18.9676%).
- Fast khm+eng, same preprocessing: 6,136 / 34,617 edits (17.7254%).
- Gain: 430 fewer edits on the 20 development images.

Proceed with the one predefined mixed-language mode unchanged on the
40 comparison images. Do not choose a mode per page or retune parameters.
The raw development scores include the two documented mismatched pairs.
This is a post-hoc experiment motivated by comparison-set inspection;
any resulting target success must be labeled adaptive, pending fresh data.
Keep the Khmer-only default regardless of this single benchmark.

Pinned fast English model: 4,113,088 bytes; SHA-256
7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2.
Khmer model unchanged: SHA-256
47f110575341b322052f3becbefee61a3ecf1ef549352b5d4d33d28afe30d099.
Combined model data: 5,560,014 bytes, stored outside the package.
