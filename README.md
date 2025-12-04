# sms-api: Simulating Microbial Systems

[![Homepage](https://img.shields.io/badge/Homepage-Visit-blue)](https://sms.cam.uchc.edu/home)
[![API Documentation](https://img.shields.io/badge/docs-REST%20API-blue)](https://sms.cam.uchc.edu/documentation)
[![Swagger UI](https://img.shields.io/badge/swagger_docs-Swagger_UI-green?logo=swagger)](https://sms.cam.uchc.edu/docs)
[![Build status](https://img.shields.io/github/actions/workflow/status/vivarium-collective/sms-api/main.yml?branch=main)](https://github.com/vivarium-collective/sms-api/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/vivarium-collective/sms-api/branch/main/graph/badge.svg)](https://codecov.io/gh/vivarium-collective/sms-api)
[![Commit activity](https://img.shields.io/github/commit-activity/m/vivarium-collective/sms-api)](https://img.shields.io/github/commit-activity/m/vivarium-collective/sms-api)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)
[![Documentation](https://img.shields.io/badge/documentation-online-blue.svg)](https://sms-api.readthedocs.io/en/latest/)

<p align="center">
  <img src="https://github.com/vivarium-collective/sms-api/blob/main/documentation/source/_static/wholecellecoli.png?raw=true" width="400" />
</p>

- **Github repository**: <https://github.com/vivarium-collective/sms-api/>
- **REST API Documentation**: [View Docs](https://sms.cam.uchc.edu/documentation)
- **Documentation(In progress, not complete)** <https://sms-api.readthedocs.io/en/latest/>

#### SMS API (otherwise known as _Atlantis API_):

Design, run, and analyze reproducible simulations of dynamic cellular processes in Escherichia coli. SMS API uses the vEcoli model. Please refer to [the vEcoli documentation](https://covertlab.github.io/vEcoli/) for more details.
The vEcoli documentation is very well written and we highly recommend that users become familiar with it.

## Getting Started

### The SMS API uniquely acts as both a server _and_ client:

This project uses FastAPI, Uvicorn, and Marimo to serve a REST API as well as host Marimo user interfaces. For more information
on Marimo, please [refer to their documentation](https://docs.marimo.io/).

#### Server:

A kubernetes cluster containing an ASGI application (FastAPI) is hosted and available at [https://sms.cam.uchc.edu/](https://sms.cam.uchc.edu/)
An API router of endpoints is assigned for each API in this project's scope and available by name in the request url. For example the
primary multigeneration, multiseed cell simulation endpoints are hosted at [https://sms.cam.uchc.edu/v1/ecoli](https://sms.cam.uchc.edu/v1/ecoli). Other APIs include
the Antibiotic and Biomanufacturing and Core (single cell).

#### Client:

This project uses the Marimo web app functionality to act as a client to the aforementioned server. There is a client for each
API router (or simply, API). This ui is accessible within a "splash page" by navigating to [https://sms.cam.uchc.edu/home](https://sms.cam.uchc.edu/home). Please contact
our organization for authentication, if needed.
