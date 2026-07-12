# Contributing

Thanks for helping make README freshness dependable.

Open an issue before large changes so the workflow stays focused. For a pull request, keep the change small, add or update a regression test, run `python -m unittest discover -v`, and run `python -m readme_sync --check`.

Do not add telemetry, network access, automatic package installation, hidden git mutations, or broad filesystem writes. The core promise is a local, reviewable tool that changes only its managed README sections and badge.

Use conventional commit subjects where practical, such as `fix:`, `feat:`, `docs:`, or `test:`.
