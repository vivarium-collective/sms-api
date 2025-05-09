## `gateway`

#### This package servers to provide 4 primary components:

1. ~4 different APIs (core, community, evolve, types, etc)

2. specialized/secure endpoint routers for community, evolve, and types apis

3. main modules for each api (base(/), core, community, evolve)

4. api key headers (api auth input) for community, evolve, and types, etc/


#### The CoreAPI is the standard, free, unauthenticated "standard-use" API.

#### The purpose of such a design is that each api can behave atomically, and thus spun up seperately as nanoservices with a larger gateway microservice. The need for authentication also comes into this design choice.