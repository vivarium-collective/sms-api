# sms-api

[![Release](https://img.shields.io/github/v/release/vivarium-collective/sms-api)](https://img.shields.io/github/v/release/vivarium-collective/sms-api)
[![Build status](https://img.shields.io/github/actions/workflow/status/vivarium-collective/sms-api/main.yml?branch=main)](https://github.com/vivarium-collective/sms-api/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/vivarium-collective/sms-api/branch/main/graph/badge.svg)](https://codecov.io/gh/vivarium-collective/sms-api)
[![Commit activity](https://img.shields.io/github/commit-activity/m/vivarium-collective/sms-api)](https://img.shields.io/github/commit-activity/m/vivarium-collective/sms-api)
[![License](https://img.shields.io/github/license/vivarium-collective/sms-api)](https://img.shields.io/github/license/vivarium-collective/sms-api)

This is the api server for Vivarium simulation services.

- **Github repository**: <https://github.com/vivarium-collective/sms-api/>
- **Documentation** <https://vivarium-collective.github.io/sms-api/>

## Getting started with your project

First, create a repository on GitHub with the same name as this project, and then run the following commands:

```bash
git init -b main
git add .
git commit -m "init commit"
git remote add origin git@github.com:vivarium-collective/sms-api.git
git push -u origin main
```

Finally, install the environment and the pre-commit hooks with

```bash
make install
```

You are now ready to start development on your project!
The CI/CD pipeline will be triggered when you open a pull request, merge to main, or when you create a new release.

To finalize the set-up for publishing to PyPI or Artifactory, see [here](https://fpgmaas.github.io/cookiecutter-poetry/features/publishing/#set-up-for-pypi).
For activating the automatic documentation with MkDocs, see [here](https://fpgmaas.github.io/cookiecutter-poetry/features/mkdocs/#enabling-the-documentation-on-github).
To enable the code coverage reports, see [here](https://fpgmaas.github.io/cookiecutter-poetry/features/codecov/).

---

Repository initiated with [fpgmaas/cookiecutter-poetry](https://github.com/fpgmaas/cookiecutter-poetry).
