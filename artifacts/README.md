# Artifact Registry

This file is the central registry for large, external, generated, encrypted, or reproducible
artifacts in this repository. Before searching the repo for artifacts, agents and humans should read
this file to discover where artifacts live, how to fetch them, how to verify them, and whether they
need local decryption.

Git LFS is the first supported backend. Future systems such as DVC should be added as additional
backend values in the same registry instead of creating a parallel discovery path.

## Default Layout

- `artifacts/README.md` lists every artifact or artifact group, even when the files are colocated
  elsewhere for clarity.
- `artifacts/lfs/<artifact-slug>/` is the default home for new Git LFS-managed artifacts.
- Artifacts may live outside `artifacts/lfs/` only when colocating with source, docs, or tests is
  materially clearer; the registry entry remains mandatory.
- Decrypted or plaintext working copies belong under ignored local paths such as
  `.local/artifacts/<artifact-slug>/`.
- Private decryption keys belong under `.creds/lfs/<artifact-slug>.agekey` and must never be
  committed, printed, copied into docs, or summarized.

## Registry

Current status: no artifacts are registered yet.

| Slug | Backend | Repo path/pattern | Purpose | Encrypted? | Key path if encrypted | Fetch command | Verify command/checksum | Update notes |
|------|---------|-------------------|---------|------------|-----------------------|---------------|-------------------------|--------------|

## Using Git LFS Artifacts

Run this once per machine before using Git LFS-backed artifacts:

```bash
git lfs install
```

Fetch only the specific artifact path or pattern listed in the registry:

```bash
git lfs pull --include="<path-or-pattern>"
```

Then run the registry entry's verify command. Prefer artifact-specific checks such as
`sha256sum --check <checksum-file>` or a reproducible build/test command over broad manual
inspection.

To check registry drift, list Git LFS-managed files and confirm every tracked path is represented in
the registry table:

```bash
git lfs ls-files --name-only
```

## Adding Or Updating Git LFS Artifacts

1. Choose a stable slug such as `sample-dataset-v1`.
2. Place new LFS-managed artifacts under `artifacts/lfs/<artifact-slug>/` unless another repo path is
   materially clearer.
3. Track the narrowest path or pattern that describes that artifact:

   ```bash
   git lfs track "<path-or-pattern>"
   ```

4. Keep `.gitattributes` LFS rules narrow and per-artifact. Add project-specific LFS rules outside
   the managed agents-template block, preferably after `# END agents-template merge rules`.
5. Add or update the registry row in this file in the same change as the `.gitattributes` update and
   artifact pointer files.
6. Include update notes that explain the source, regeneration command, checksum procedure, and any
   compatibility constraints.
7. Before committing, run:

   ```bash
   git lfs ls-files --name-only
   git diff --check
   ```

Do not add broad repository-wide LFS patterns such as `*.zip` or `*.bin` unless every matching file is
part of the same intentional artifact group and the registry entry says so.

## Encrypted Artifacts

Use `age` by default for encrypted artifacts.

- Commit only encrypted files, such as `*.age`, through Git LFS.
- Store private keys under `.creds/lfs/<artifact-slug>.agekey`.
- Keep decrypted outputs under ignored local paths such as `.local/artifacts/<artifact-slug>/`.
- Document exact artifact-specific decrypt and encrypt commands in the registry row's update notes.

Example decrypt command to adapt in a registry entry:

```bash
mkdir -p .local/artifacts/<artifact-slug>
age --decrypt \
  --identity .creds/lfs/<artifact-slug>.agekey \
  --output .local/artifacts/<artifact-slug>/<plaintext-name> \
  artifacts/lfs/<artifact-slug>/<encrypted-name>.age
```

Example encrypt command to adapt in a registry entry:

```bash
age --encrypt \
  --recipient-file artifacts/lfs/<artifact-slug>/recipients.txt \
  --output artifacts/lfs/<artifact-slug>/<encrypted-name>.age \
  .local/artifacts/<artifact-slug>/<plaintext-name>
```

For encrypted artifacts, the registry verify command should state whether it validates the encrypted
file, the decrypted plaintext, or both.
