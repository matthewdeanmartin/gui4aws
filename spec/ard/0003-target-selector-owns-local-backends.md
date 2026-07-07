# ADR 0003: target selector owns local backends

The toolbar Target selector is the source of truth for AWS, Moto, Robotocore, and Custom endpoints.

Moto and Robotocore are mutually exclusive. Selecting one starts or switches to it; switching away stops the managed backend.

When a managed emulator is active, the profile selector is disabled and shown as not applicable.

This prevents mixing live AWS credentials with emulator state in normal use.
