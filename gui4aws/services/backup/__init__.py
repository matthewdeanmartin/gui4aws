"""AWS Backup service module.

Moto 5.2 supports a subset of AWS Backup: vaults and plans can be created/listed, but
``list_backup_jobs``, ``list_restore_jobs`` and ``list_recovery_points_by_backup_vault`` return
``Not yet implemented``. The action definitions still ship; tests that exercise the unsupported
operations are marked ``pytest.mark.integration`` and skipped by default.

See spec §17.3.
"""

from gui4aws.services.backup.service import SERVICE

__all__ = ["SERVICE"]
