# Publishing releases

The release workflow uses PyPI Trusted Publishing, scoped to this repository and the `pypi` GitHub Actions environment. It does not require a stored PyPI API token.

PyPI publisher identity:

- Owner: `back-kh`
- Repository: `khmereasytools`
- Workflow: `publish.yml`
- Environment: `pypi`

The GitHub environment restricts deployment to tags matching `v*`. The workflow checks that a tag matches the package version and that its commit belongs to `main`. It tests the source and installed wheel, builds/checks the distributions, and uploads only those build artifacts. The separate publishing job alone has `id-token: write` permission.

For each release, update both version declarations and the changelog, merge passing changes, then push the matching tag (for example, `v0.4.0`). Check the publishing workflow, confirm the PyPI file hashes, and install the version from PyPI in a fresh environment. Never replace or reuse an existing published version.

The initial trusted-publisher configuration requires the project owner's approval because it gives this workflow permission to publish future releases of this PyPI project.
