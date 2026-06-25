"""AppContext: the single source of truth for runtime selections.

The GUI binds widget values to fields on AppContext and asks AppContext for the right executor.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from gui4aws.execution.action_cache import ActionCache
from gui4aws.execution.action_history import ActionHistory
from gui4aws.execution.aws_cli_executor import AwsCliExecutor
from gui4aws.execution.boto3_executor import Boto3Executor
from gui4aws.execution.endpoint_config import EndpointConfig, EndpointMode
from gui4aws.execution.execution_mode import ExecutionMode
from gui4aws.execution.network_config import NetworkConfig
from gui4aws.services.service_registry import ServiceRegistry, default_registry

__all__ = ["AWS_PARTITIONS", "AppContext"]

logger = logging.getLogger(__name__)

# AWS partitions with their default region for region enumeration.
# Keys are partition names; values are a (default_region, display_label) tuple.
AWS_PARTITIONS: dict[str, tuple[str, str]] = {
    "aws": ("us-east-1", "AWS Standard"),
    "aws-us-gov": ("us-gov-west-1", "AWS GovCloud (US)"),
    "aws-cn": ("cn-north-1", "AWS China"),
    "aws-iso": ("us-iso-east-1", "AWS ISO"),
    "aws-iso-b": ("us-isob-east-1", "AWS ISO-B"),
}


@dataclass
class AppContext:
    """Holds profile/region/mode/endpoint plus the action history and registry."""

    profile_name: str | None = None
    region_name: str = "us-east-1"
    partition: str = "aws"
    mode: ExecutionMode = ExecutionMode.BOTO3
    endpoint_config: EndpointConfig = field(default_factory=EndpointConfig)
    network_config: NetworkConfig = field(default_factory=NetworkConfig)
    history: ActionHistory = field(default_factory=ActionHistory)
    registry: ServiceRegistry = field(default_factory=default_registry)
    action_cache: ActionCache = field(default_factory=ActionCache)

    def set_mode(self, mode: ExecutionMode) -> None:
        """Change execution mode (AWS CLI vs boto3)."""
        logger.info("execution mode -> %s", mode)
        self.mode = mode
        self.action_cache.clear()

    def set_region(self, region_name: str) -> None:
        """Change region; resource lists should refresh after this."""
        logger.info("region -> %s", region_name)
        self.region_name = region_name
        self.action_cache.clear()

    def set_partition(self, partition: str) -> None:
        """Change AWS partition (aws, aws-us-gov, aws-cn, aws-iso, aws-iso-b)."""
        logger.info("partition -> %s", partition)
        self.partition = partition
        self.action_cache.clear()

    def set_profile(self, profile_name: str | None) -> None:
        """Change AWS profile (None means rely on environment)."""
        logger.info("profile -> %s", profile_name)
        self.profile_name = profile_name
        self.action_cache.clear()

    def set_endpoint(self, mode: EndpointMode, endpoint_url: str | None = None) -> None:
        """Change endpoint mode + URL."""
        self.endpoint_config = EndpointConfig.for_mode(mode, endpoint_url)
        logger.info("endpoint -> %s url=%s", mode, endpoint_url)
        self.action_cache.clear()

    def set_network_config(self, network_config: NetworkConfig) -> None:
        """Replace the proxy/TLS settings used for every call."""
        self.network_config = network_config
        logger.info(
            "network -> use_env_proxy=%s http=%s https=%s ca_bundle=%s verify_ssl=%s",
            network_config.use_env_proxy,
            bool(network_config.http_proxy),
            bool(network_config.https_proxy),
            bool(network_config.ca_bundle_path),
            network_config.verify_ssl,
        )
        # Connectivity/trust changes can flip calls between success and failure,
        # so drop cached results that were captured under the old settings.
        self.action_cache.clear()

    def boto3_executor(self) -> Boto3Executor:
        """Build a fresh Boto3Executor that reflects current selections."""
        return Boto3Executor(
            profile_name=self.profile_name,
            region_name=self.region_name,
            endpoint_config=self.endpoint_config,
            network_config=self.network_config,
        )

    def aws_cli_executor(self) -> AwsCliExecutor:
        """Build a fresh AwsCliExecutor that reflects current selections."""
        return AwsCliExecutor(
            profile_name=self.profile_name,
            region_name=self.region_name,
            endpoint_config=self.endpoint_config,
            network_config=self.network_config,
        )

    def execute(self, action: Any, inputs: dict[str, str]) -> Any:
        """Dispatch to whichever executor matches the current mode."""
        cache_key = self.action_cache.build_key(
            action,
            inputs,
            mode=self.mode,
            profile_name=self.profile_name,
            region_name=self.region_name,
            endpoint_config=self.endpoint_config,
        )
        cached = self.action_cache.get(cache_key)
        if cached is not None:
            return cached
        result: Any
        if self.mode is ExecutionMode.BOTO3:
            result = self.boto3_executor().execute(action, inputs)
        else:
            result = self.aws_cli_executor().execute(action, inputs)
        if self.action_cache.should_cache(action, result):
            self.action_cache.put(cache_key, result)
        return result

    def invalidate_read_cache(self, service_id: str | None = None) -> None:
        """Drop cached read-only results globally or for one service."""
        if service_id is None:
            self.action_cache.clear()
            return
        self.action_cache.invalidate_service(service_id)
