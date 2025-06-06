## ``gateway.routers``: Sub-package containing most of the actual endpoint logic for the VivariumAPI. 

The design choice to decouple the individual endpoint logic from the main module is deliberate. This architecture provides 3 "modes" in which
users can interact with Vivarium, outlined below. The distribution of endpoints have been grouped according to the app's routers. For clarity, the lower-level api endpoints have ``/api/v<VERSION>`` prepended to their definitions. This fosters reproducibility. The following abstract API "modes" are defined as such:

** = TODO: not yet implemented

3. _**``/api/v1/evolve``**_: The API which allows users to create, evolve, query, and parameterize a stateful vivarium instance, and thus a stateful simulation state which persists after runtime.  **NOTE**: This API requires filling out [This form](). TODO: Create a reference an application source here. Includes:
    - `/create`
    - `/evolve`
    - `/get/vivarium`
    - `/get/processes`
    - `/add/process`
    - `/add/object`

4. _**``/api/v1/community``**_: The Community API used by the `vEcoli` project requiring a screening-initiated secure API key for users' interaction. This API uses the UConn Health HPC runtime and is optimized for high-performance computing. **NOTE**: This API requires filling out [This form](). In addition to this form, applicants may be sujected to a screening processes as per [US DHC Guidelines](). TODO: Create a reference an application source here. Includes:
    - `/run`  (`document, duration`) -> `SecureResponse(sim_id: str, metadata: )--response_id`: this response is encrypted and its parsing depends on the `/get-results` method.
    - `/get-results`  (`response_id`) -> `SecureResults`: clients will use their private keys to decrypt this data behind the scenes.
    - `/get/processes`
    - `/get/types`
    - `/scan`  (`document`, `duration`, `n_threads`, `distribution_config`, `perturbation_config`) -> `dict[sim_id, SecureResults]`: launch `n_thread` of the same simulations in parallel. Optionally, users may perturb initial parameters across all threads according to `perturbation_config` and may also run it distributed according to `distribution_config`.

7. _**/api/v1/admin`**_: Private api not accessible to anyone other than maintainers.
