"""Minimal proposed patch for moto.rds.models."""


class DBCluster:
    """Patch excerpt for the failing property used by Moto's dashboard serializer."""

    @property
    def master_user_password(self) -> str:
        """Return a sentinel value so /moto-api/data.json can serialize the model."""
        return "testing"
