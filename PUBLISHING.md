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

## Publish an Existing Release

After configuring both trusted publishers, open the GitHub Actions **Publish** workflow, choose **Run workflow**, and enter the existing tag `v1.1.0`. Future published GitHub releases trigger the workflow automatically.

For stronger protection, configure the `pypi` and `npm` GitHub Environments with required reviewers before running a release. Keep any existing npm token only for an emergency manual publish, stored in your local npm login; revoke it after Trusted Publishing has succeeded.
