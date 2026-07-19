# Publishing

Releases publish from GitHub Actions using short-lived OpenID Connect credentials. Do not add PyPI passwords, API tokens, npm tokens, or `.npmrc` files to this repository.

## PyPI Trusted Publisher

In PyPI's GitHub Trusted Publisher form, enter:

| Field | Value |
|---|---|
| Owner | `jeevesh2515` |
| Repository name | `readme-guardian` |
| Workflow name | `publish.yml` |
| Environment name | `pypi` |

The environment name must exactly match `.github/workflows/publish.yml`. No PyPI secret is needed: the workflow exchanges its GitHub OIDC identity for a short-lived PyPI credential.

## npm Trusted Publisher

In the npm package settings, add a GitHub Actions Trusted Publisher with:

| Field | Value |
|---|---|
| Owner | `jeevesh2515` |
| Repository | `readme-guardian` |
| Workflow filename | `publish.yml` |
| Environment | `npm` |
| Allowed action | `npm publish` |

This also needs no npm token. npm creates provenance automatically for a public package published through this workflow.

### First npm publication fallback

An npm Trusted Publisher can only be configured once the npm package exists. For the first npm publication, create a **short-lived granular access token** in the `jeevesh039` npm account with read/write access and 2FA bypass enabled. Store it only as the `NPM_TOKEN` **environment secret** in GitHub: repository **Settings** → **Environments** → **npm** → **Add environment secret**. The workflow uses it only when present.

After the first successful npm publication, configure the npm Trusted Publisher above, remove `NPM_TOKEN`, and rely on OIDC. Do not create repository-wide secrets, commit `.npmrc`, or paste a token into a terminal command or chat.

If the entire unscoped npm package was unpublished, npm blocks the name for 24 hours and never permits reuse of an unpublished version. Publish a new version after that cooldown; do not retry the unpublished version.

## Publish a New Release

1. Commit the version bump, create an annotated tag such as `v1.1.3`, and push that tag.
2. The **Publish** workflow starts from the tag, validates the source, then publishes npm before PyPI.
3. After the workflow succeeds, publish the matching GitHub Release and upload its release artifacts.

The workflow is deliberately idempotent. A manual rerun checks npm and PyPI first; versions already present in both registries are skipped successfully instead of being uploaded again. Use **Run workflow** with an existing tag only to resume a partial release, not to overwrite a published version.

For stronger protection, configure the `pypi` and `npm` GitHub Environments with required reviewers before running a release. Keep any existing npm token only for an emergency manual publish, stored in your local npm login; revoke it after Trusted Publishing has succeeded.
