# sms-api

[![Release](https://img.shields.io/github/v/release/vivarium-collective/sms-api)](https://img.shields.io/github/v/release/vivarium-collective/sms-api)
[![Build status](https://img.shields.io/github/actions/workflow/status/vivarium-collective/sms-api/main.yml?branch=main)](https://github.com/vivarium-collective/sms-api/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/vivarium-collective/sms-api/branch/main/graph/badge.svg)](https://codecov.io/gh/vivarium-collective/sms-api)
[![Commit activity](https://img.shields.io/github/commit-activity/m/vivarium-collective/sms-api)](https://img.shields.io/github/commit-activity/m/vivarium-collective/sms-api)
[![License](https://img.shields.io/github/license/vivarium-collective/sms-api)](https://img.shields.io/github/license/vivarium-collective/sms-api)

This is the api server for Vivarium simulation services.

- **Github repository**: <https://github.com/vivarium-collective/sms-api/>
- **Documentation** <https://vivarium-collective.github.io/sms-api/>

## install

Extensive setup instructions for minikube and services live in the `kustomize/cluster/README-Minikube.md`

## run

The Makefile contains several commands that can be used to interact with the various components of the system.

### make test

Ensures the python code runs for all the various components - if your system is set up correctly all tests will pass.

### make cycle

This command does a few things:
* Generates the OpenAPI spec
* Builds the latest container from the repository and uploads it to the biosimulators container registry
* Applies the local kubernetes overlay to minikube using kubectl