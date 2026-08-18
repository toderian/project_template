# Artifact Registry

Central registry for large, external, generated, encrypted, or reproducible artifacts in this
repository. Read this file before searching the tree: it says where each artifact lives, how to fetch
it, how to verify it, and whether it needs local decryption. Every artifact belongs here even when the
files are colocated with source, docs, or tests.

## Registry

Current status: no artifacts are registered yet.

| Slug | Backend | Repo path/pattern | Purpose | Encrypted? | Key path if encrypted | Fetch command | Verify command/checksum | Update notes |
|------|---------|-------------------|---------|------------|-----------------------|---------------|-------------------------|--------------|

## How to use it

- Default home for new Git LFS artifacts: `artifacts/lfs/<artifact-slug>/`. Decrypted working copies
  belong under ignored local paths such as `.local/artifacts/<artifact-slug>/`; private keys under
  `.creds/lfs/<artifact-slug>.agekey`, never committed or printed.
- Fetch only what you need: `git lfs install` once per machine, then
  `git lfs pull --include="<path-or-pattern>"` with the pattern from the row, then run the row's verify
  command.
- Check for drift with `git lfs ls-files --name-only` and confirm every tracked path has a row here.
- Adding or updating an artifact, encrypting with `age`, and the exact `.gitattributes` rules: follow
  the `artifacts-registry` skill. Keep LFS patterns narrow and per-artifact, and commit the
  `.gitattributes` change together with the registry row.
