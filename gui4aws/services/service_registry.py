"""Registry of ServiceDefinition objects.

The registry is intentionally explicit: services are added by listing them here, not by
filesystem scanning or entry-point discovery. This keeps imports predictable.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from gui4aws.models import ServiceDefinition

__all__ = ["ServiceRegistry", "default_registry"]


class ServiceRegistry:
    """Holds the ServiceDefinitions visible in the sidebar."""

    def __init__(self, services: Iterable[ServiceDefinition] = ()) -> None:
        self.services: list[ServiceDefinition] = list(services)

    def register(self, service: ServiceDefinition) -> None:
        """Add a service; raises if the service_id is already registered."""
        if any(existing.service_id == service.service_id for existing in self.services):
            raise ValueError(f"Service already registered: {service.service_id!r}")
        self.services.append(service)

    def get(self, service_id: str) -> ServiceDefinition:
        """Return the service with the given id."""
        for service in self.services:
            if service.service_id == service_id:
                return service
        raise KeyError(f"No service {service_id!r} in registry")

    def __iter__(self) -> Iterator[ServiceDefinition]:
        return iter(self.services)

    def __len__(self) -> int:
        return len(self.services)


def default_registry() -> ServiceRegistry:
    """Build the registry with all currently-supported services.

    Phase 2 / Phase 3 services are added here as they come online.
    """
    registry = ServiceRegistry()
    try:
        from gui4aws.services.aurora.service import SERVICE as AURORA_SERVICE

        registry.register(AURORA_SERVICE)
    except ImportError:
        pass
    try:
        from gui4aws.services.backup.service import SERVICE as BACKUP_SERVICE

        registry.register(BACKUP_SERVICE)
    except ImportError:
        pass
    try:
        from gui4aws.services.ecs.service import SERVICE as ECS_SERVICE

        registry.register(ECS_SERVICE)
    except ImportError:
        pass
    try:
        from gui4aws.services.secrets.service import SERVICE as SECRETS_SERVICE

        registry.register(SECRETS_SERVICE)
    except ImportError:
        pass
    try:
        from gui4aws.services.ssm.service import SERVICE as SSM_SERVICE

        registry.register(SSM_SERVICE)
    except ImportError:
        pass
    try:
        from gui4aws.services.networking.service import SERVICE as NETWORKING_SERVICE

        registry.register(NETWORKING_SERVICE)
    except ImportError:
        pass
    return registry
