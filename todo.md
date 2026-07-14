## 1. create cd1-* specific filter parameter for <GET> /api/v1/simulations

### Description

Add an optional `cd1` filter parameter to this endpoint, which when/if specified in the request, will return a simulation
subset containing **ONLY** the simulations who have the following `experiment_id`'s:

- sim31-baseline-60bb
- sim33-violacien-seeds1000-generations10-9617
- sim33-mecillinam-seeds84-generations10-036f


### Why we need this

To support the "dashboard/workbench demo" that is comprehensively defined/mentioned in ~/vivarium-app/vivarium-dashboard/demos/v2ecoli,
this filter feature will be used in a very specific way (doesnt matter the details)


### Constraints

- the aforementioned 3 simulations are only available on the `sms-api-stanford` k8s namespace deployment


### Status

No plan implemented yet.

---

## 2. Create a search filter for the Simulations table

> **Plan**: `artifacts/plans/todo-2.md`

### Description

Create a production-grade, yet _*lightweight_ "filter" mechanism that optionally parameterizes requests to
the `<GET> /api/v1/simulations` endpoint(as defined in `./sms_api/api/routers/sms.py` etc).

_*_: _lightweight_ means the optimal design coordinates of optimized x little code as possible whilst remaining prod grade)

### Accepted Filter Types

The mechanism should be such that requests can specify search in any of the following ways:

#### a.) By `Simulation` attribute

There should be a smooth, user friendly way to specify a request such that the filter is a search by any `Simulation` model object attribute, within the closest
matching terms. This is a very common pattern in modern, production-grade software.

#### b.) By "bundles"

Often times, several simulations will semantically/experimentally be group together in some way that is not
explicitly reflected by the sms-api's record-keeping (for example, a scientific study with many related experiments (simulations))
...the filter mechanism should be able to handle such cases in the requests. Thus, there is definitely at very
least an need to have a predefined "bank" of "bundled"/grouped simulations that is derived arbitrarily: let's try to flesh
this aspect out very carefully so as to manifest a design that is optimially more generalized/prod-grade/reproducible/extensible,
if we can help it.


### Use cases

1. One such "bundle" that must be present is related to "cd1", and contains only the following experiment ids:

- sim31-baseline-60bb
- sim33-violacien-seeds1000-generations10-9617
- sim33-mecillinam-seeds84-generations10-036f

...thus, as per my instructions in this documentation, users should be able to easily access this "bundle" by parameterizing
the request in either of the following two ways:

a.) by being able to pass _something_ like `tag=cd1`

OR

b.) by being able to specify an array, or comma separated list query parameter of `experiment_id=`

**NOTE**: There will be more use cases, but this will be the first specific use of what should be an otherwise generalized/highly streamlined mechanism.
**NOTE**: The "cd1" bundle/tag as i just described it is for simulations that are ONLY available on the `sms-api-stanford`
k8s namespace of the sms-api (and correspondingly the `smscdk` stack as per ../sms-cdk)

### Considerations

- im fairly certain that this filtering mechanism should be in the form of query parameters, since it is a <GET> method,
but not sure...I know that a new <QUERY> http method just came out that seems to be made for this type of thing, but not
sure if its available yet in fastapi, and dont want to use something other than fastapi.

---
