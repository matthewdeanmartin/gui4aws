# ADR 0001: explicit service registry

`gui4aws` registers services in `gui4aws.services.service_registry.default_registry()`.

We do not scan the filesystem or auto-load entry points in the app core.

This keeps imports predictable, startup understandable, and the sidebar order intentional.

Adding a service means adding its `SERVICE` constant and registering it explicitly.
