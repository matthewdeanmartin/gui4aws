"""Network configuration: HTTP(S) proxy and TLS trust for AWS calls.

This exists for users behind a corporate HTTP proxy and/or a TLS-inspecting
firewall. In those environments two things commonly break:

  * AWS calls can't reach the internet without going through the proxy.
  * The AWS endpoint's certificate is re-signed by an enterprise CA, so the
    default trust store rejects it ("certificate verify failed") and the app
    looks broken.

``NetworkConfig`` lets the user point the app at a proxy and/or a CA bundle
that trusts the enterprise/AWS cert. It is intentionally separate from
``EndpointConfig`` (which decides *where* calls go); this decides *how* the
connection is made.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

__all__ = ["PROXY_ENV_VARS", "NetworkConfig"]

# Environment variables botocore/requests consult for proxy settings. Both the
# lower- and upper-case spellings are honored by the underlying libraries; we
# surface them so the dialog can show the user what's currently set.
PROXY_ENV_VARS: tuple[str, ...] = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "no_proxy",
)


@dataclass(frozen=True)
class NetworkConfig:
    """Proxy and TLS-trust settings applied to every AWS call.

    Attributes:
        use_env_proxy: When True (default), proxy environment variables
            (HTTP_PROXY/HTTPS_PROXY/NO_PROXY) are respected by botocore and the
            AWS CLI as usual. When False, those env vars are ignored for this
            app's calls — this is the "try without the proxy despite the vars"
            escape hatch.
        http_proxy: Explicit HTTP proxy URL (e.g. ``http://proxy.corp:8080``).
            Overrides the environment when set.
        https_proxy: Explicit HTTPS proxy URL. Overrides the environment when set.
        no_proxy: Comma-separated hosts that should bypass the proxy.
        ca_bundle_path: Path to a PEM CA bundle to trust (e.g. the enterprise
            proxy's root CA, or an AWS cert you must trust). Maps to botocore's
            ``verify`` / the ``AWS_CA_BUNDLE`` env var / ``--ca-bundle``.
        client_cert_path: Optional path to a client certificate (PEM) for mutual
            TLS, if the proxy requires one.
        verify_ssl: When False, TLS certificate verification is disabled. This
            is insecure and intended only as a last-resort diagnostic — the
            dialog warns about it.
    """

    use_env_proxy: bool = True
    http_proxy: str = ""
    https_proxy: str = ""
    no_proxy: str = ""
    ca_bundle_path: str = ""
    client_cert_path: str = ""
    verify_ssl: bool = True

    def is_default(self) -> bool:
        """True when nothing has been customized (real AWS / no proxy / default trust)."""
        return self == NetworkConfig()

    def explicit_proxies(self) -> dict[str, str]:
        """Return the explicit proxy map for botocore's ``Config(proxies=...)``.

        Empty when no explicit proxy URLs are set (so the environment, if
        honored, still applies).
        """
        proxies: dict[str, str] = {}
        if self.http_proxy.strip():
            proxies["http"] = self.http_proxy.strip()
        if self.https_proxy.strip():
            proxies["https"] = self.https_proxy.strip()
        return proxies

    def botocore_verify(self) -> bool | str | None:
        """Value for a boto3 client's ``verify`` argument.

        ``False`` disables verification; a path string points at a custom CA
        bundle; ``None`` means "use botocore's default", letting us avoid
        passing the argument at all when nothing is customized.
        """
        if not self.verify_ssl:
            return False
        if self.ca_bundle_path.strip():
            return self.ca_bundle_path.strip()
        return None

    def env_overlay(self) -> dict[str, str]:
        """Environment-variable overlay for subprocesses (the AWS CLI).

        The returned dict is merged onto a copy of ``os.environ`` by the caller.
        A value of empty string means "unset this variable in the child".
        """
        overlay: dict[str, str] = {}

        if not self.use_env_proxy:
            # Strip inherited proxy vars so the CLI ignores the environment.
            for name in PROXY_ENV_VARS:
                overlay[name] = ""

        http = self.http_proxy.strip()
        https = self.https_proxy.strip()
        no_proxy = self.no_proxy.strip()
        if http:
            overlay["HTTP_PROXY"] = http
            overlay["http_proxy"] = http
        if https:
            overlay["HTTPS_PROXY"] = https
            overlay["https_proxy"] = https
        if no_proxy:
            overlay["NO_PROXY"] = no_proxy
            overlay["no_proxy"] = no_proxy

        ca = self.ca_bundle_path.strip()
        if ca:
            overlay["AWS_CA_BUNDLE"] = ca

        return overlay

    def apply_to_environ(self, base: dict[str, str] | None = None) -> dict[str, str]:
        """Build a child-process environment with this config applied.

        Starts from ``base`` (defaults to ``os.environ``), removes any variable
        the overlay maps to empty string, and sets the rest.
        """
        env = dict(os.environ if base is None else base)
        for name, value in self.env_overlay().items():
            if value == "":
                env.pop(name, None)
            else:
                env[name] = value
        return env
