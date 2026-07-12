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

## Publish an Existing Release

After configuring both trusted publishers, open the GitHub Actions **Publish** workflow, choose **Run workflow**, and enter the existing tag `v1.1.1`. Future published GitHub releases trigger the workflow automatically.

For stronger protection, configure the `pypi` and `npm` GitHub Environments with required reviewers before running a release. Keep any existing npm token only for an emergency manual publish, stored in your local npm login; revoke it after Trusted Publishing has succeeded.
