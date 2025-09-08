# sms-api: Simulating Microbial Systems

[![Documentation](https://img.shields.io/badge/documentation-online-blue.svg)](https://sms-api.readthedocs.io/en/latest/)
[![Swagger UI](https://img.shields.io/badge/swagger_docs-Swagger_UI-green?logo=swagger)](https://sms.cam.uchc.edu/docs)
[![Build status](https://img.shields.io/github/actions/workflow/status/vivarium-collective/sms-api/main.yml?branch=main)](https://github.com/vivarium-collective/sms-api/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/vivarium-collective/sms-api/branch/main/graph/badge.svg)](https://codecov.io/gh/vivarium-collective/sms-api)
[![Commit activity](https://img.shields.io/github/commit-activity/m/vivarium-collective/sms-api)](https://img.shields.io/github/commit-activity/m/vivarium-collective/sms-api)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)

<p align="center">
  <img src="https://github.com/vivarium-collective/sms-api/blob/main/documentation/source/_static/wholecellecoli.png?raw=true" width="400" />
</p>

- **Github repository**: <https://github.com/vivarium-collective/sms-api/>
- **Documentation** <https://sms-api.readthedocs.io/en/latest/>
- **REST API Documentation**: [View Docs](./sms_api/api/README.md)

#### SMS API (otherwise known as _Atlantis API_):

Design, run, and analyze reproducible simulations of dynamic cellular processes in Escherichia coli. SMS API uses the vEcoli model. Please refer to [the vEcoli documentation](https://covertlab.github.io/vEcoli/) for more details.

## Getting Started

### The SMS API uniquely acts as both a server _and_ client:

This project uses FastAPI, Uvicorn, and Marimo to serve a REST API as well as host Marimo user interfaces. For more information
on Marimo, please [refer to their documentation](https://docs.marimo.io/).

#### Server:

A kubernetes cluster containing an ASGI application (FastAPI) is hosted and available at [https://sms.cam.uchc.edu/](https://sms.cam.uchc.edu/)
An API router of endpoints is assigned for each API in this project's scope and available by name in the request url. For example the
primary single-cell API ("core") endpoints are hosted at [https://sms.cam.uchc.edu/core](https://sms.cam.uchc.edu/core). Other APIs include
the Antibiotic and Biomanufacturing.

#### Client:

This project uses the Marimo web app functionality to act as a client to the aforementioned server. There is a client for each
API router (or simply, API). This ui is accessible by navigating to [https://sms.cam.uchc.edu/](https://sms.cam.uchc.edu/). Please contact
our organization for authentication, if needed.


#### In Detail:
The SMS(Simulating Microbial Systems) API allows users to design, run, and analyze reproducible simulations of dynamic cellular processes in Escherichia coli.
This tool aims to allow users to configure, run, and introspect simulations of the vEcoli(Vivarium-Ecoli) model. The SMS API uniquely acts as both a server
and client, using FastAPI, Uvicorn, and Marimo to serve a REST API as well as host Marimo user interfaces. The full comprehensive REST API documentation is
available at https://sms.cam.uchc.edu/redoc. Please refer to the aforementioned documentation for the complete details of the request query parameters and
body data required for each outlined endpoint.

Server-side sits kubernetes cluster containing a containerized ASGI(Asynchronous Server Gateway Interface) application using Python and FastAPI which is hosted and
available at https://sms.cam.uchc.edu/. An API router of endpoints is assigned for each API in this project's scope and available by name in the request url. The
primary modes of interaction exist within the "/wcm" and "/core" endpoint routers. For example, the primary single-cell API ("core") endpoints are hosted at https://sms.cam.uchc.edu/core.
A more generalized, Nextflow-based group of endpoints that is actively being developed is available at https://sms.cam.uchc.edu/wcm. Internally it uses a simulation service
that dynamically creates and dispatches SLURM job scripts which are executed through an authenticated connection with a given HPC(High Performance Computing) environment.

The /wcm endpoint router enables the design, execution, and introspection of simulations using vEcoli's Nextflow API. This is the preferred mode of interaction with
the SMS API, as it enables users to customize simulation configurations, create variants, run analysis, and execute a "batch" of one or many ecoli simulation jobs.
A typical end-to-end SMS API /wcm workflow consists of the following:

1. Run a simulation and generate a vEcoli experiment:

    POST https://sms.cam.uchc.edu/wcm/simulation/run

    Query Parameters:
    config_id: Config Id (string) or Config Id (null) (Config Id). Use "sms_single" to run a single cell vEcoli simulation and analysis.

    Request Body schema: application/json
    overrides: Overrides (object) or null
    variants: Variants (object) or null
    config: SimulationConfig (object) or null

    Responses:
    200 Successful Response
    Response Schema: application/json
    Response Type: EcoliExperiment

    experiment_id: string (Experiment Id)
    simulation: EcoliSimulation (object) or EcoliWorkflowSimulation (object) or AntibioticSimulation (object) (Simulation)
    last_updated: string (Last Updated)
    metadata: object (Metadata)
    experiment_tag: Experiment Tag (string) or Experiment Tag (null) (Experiment Tag)

    422 Validation Error
    Response Schema: application/json
    detail: Array of objects (Detail)

2. Check the simulation's status:

    GET https://sms.cam.uchc.edu/wcm/simulation/run/status

    Query Parameters:
    experiment_tag: string (Experiment Tag)

    Responses:
    200 Successful Response
    Response Schema: application/json
    id: string (Id)
    status: string (JobStatus)
    Enum: "waiting" "queued" "running" "completed" "failed"

    422 Validation Error
    Response Schema: application/json
    detail: Array of objects (Detail)


3. Once complete, get an overview of the available simulation outputs, for example: analysis outputs.

    GET https://sms.cam.uchc.edu/wcm/analysis/outputs

    Query Parameters:
    experiment_id: string (Experiment Id)

    Responses:
    200 Successful Response
    Response Schema: application/json

    422 Validation Error
    Response Schema: application/json
    detail: Array of objects (Detail)

4. The data generated by step #3 will inform the query parameters required to fetch the actual simulation analysis outputs
as follows:

    GET https://sms.cam.uchc.edu/wcm/analysis/download

    Query Parameters:
    experiment_id: string (Experiment Id)
    variant_id: integer (Variant Id). Default: 0
    lineage_seed_id: integer (Lineage Seed Id). Default: 0
    generation_id: integer (Generation Id). Default: 1
    agent_id: integer (Agent Id). Default: 0
    filename: string (Filename)
    Examples: filename=mass_fraction_summary.html

    Responses:
    200 Successful Response
    Response Schema: application/json

    422 Validation Error
    Response Schema: application/json
    detail: Array of objects (Detail)



This project’s “client” behavior is leveraged by the utilization of Marimo(python) components rather than a traditional javascript-based frontend framework. A
static HTML Jinja template is served as an extension of the FastAPI/Uvicorn backend server enabling interactive simulation introspection. There exists a user
interface for each router within the set of routers exposed by the REST API. The user interface makes calls to the REST API to enable non-programmatic interaction
with the aforementioned endpoints. This UI is accessible by navigating to https://sms.cam.uchc.edu/.
