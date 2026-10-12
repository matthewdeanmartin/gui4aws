# gui4aws

Is the web console for AWS slow and annoying? Do you have python? You could have a nice GUI for most services.

Design goals

- minimal dependencies
- safety guardrails
- fast

![png](https://raw.githubusercontent.com/matthewdeanmartin/gui4aws/main/docs/img/main_page.png)

<!-- TODO (generated from template — delete this block once done)
  - [ ] Replace this description with a real one-paragraph summary
  - [ ] Add a PyPI badge: https://badge.fury.io/py/gui4aws
  - [ ] Add a CI badge from your GitHub Actions build.yml
  - [ ] Fill in docs/overview/README.md with a real project overview
  - [ ] Add real AWS service panels to gui4aws/ and update scripts/basic_checks.sh
  - [ ] Register project on Read the Docs and point it at mkdocs.yml
  - [ ] Run `make pre-commit-install` to install git hooks
  - [ ] Run `make gha-upgrade` after first push to pin GHA action SHAs
  - [ ] Add project-specific words to private_dictionary.txt
  - [ ] Update SECURITY.md scope section with what's actually in scope for this project
  - [ ] Update CHANGELOG.md 0.1.0 entry with real release notes
  - [ ] Configure AWS credentials / profile for local development (AWS_PROFILE or ~/.aws/credentials)
-->

Tkinter GUI for AWS

## Installation

```bash
pipx install gui4aws
```

Or with pip:

```bash
pip install gui4aws
```

## Usage

```bash
gui4aws --help
```

## Contributing

See [CONTRIBUTING.md](https://github.com/matthewdeanmartin/gui4aws/blob/main/docs/extending/CONTRIBUTING.md).

## License

MIT — see [LICENSE](https://github.com/matthewdeanmartin/gui4aws/blob/main/LICENSE).

## Changelog

See [CHANGELOG.md](https://github.com/matthewdeanmartin/gui4aws/blob/main/CHANGELOG.md).


## Python 3.15 verification — 2026-10-04

Core wheels install on 3.15.0rc3 with stable or prerelease dependencies. 271 tests pass in both RC3 modes with base Moto; 17 tests using Moto HTTP server, CloudFormation or SSM remain unverified there because PyYAML has no matching published wheel. The complete 288-test suite passes on Python 3.14.7, including the local Moto server and actual Tk widgets. SQL drivers are tested from wheels. Existing Route53 work was preserved.

Dependencies were installed only from published wheels; the project's own pure-Python wheel was built locally without build isolation. `uv lock --upgrade` refreshed the lock. No GitHub builds, releases or upstream reports were sent. Upstream bug filing is the human operator's job.
