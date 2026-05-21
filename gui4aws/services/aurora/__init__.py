"""RDS Aurora service module.

Aurora is cluster-centered. The user-facing navigation surfaces clusters first, then snapshots
and member instances. See spec §17.2.
"""

from gui4aws.services.aurora.service import SERVICE

__all__ = ["SERVICE"]
