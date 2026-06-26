"""NetworkSettingsDialog: configure HTTP proxy and TLS trust for AWS calls.

For users behind a corporate proxy and/or a TLS-inspecting firewall. Opened
from the toolbar's "Network…" button. Lets the user:

  * point the app at an HTTP/HTTPS proxy (or respect the env vars, or ignore
    them entirely — the "try without proxy despite the vars" escape hatch),
  * trust an enterprise/AWS CA bundle so cert verification stops failing,
  * pick a client certificate for mutual TLS,
  * disable verification entirely as a last-resort diagnostic.
"""

from __future__ import annotations

import os
import tkinter as tk
from collections.abc import Callable
from functools import partial
from tkinter import filedialog, ttk

from gui4aws.execution.network_config import PROXY_ENV_VARS, NetworkConfig

__all__ = ["NetworkSettingsDialog", "open_network_settings"]


def open_network_settings(
    parent: tk.Misc,
    current: NetworkConfig,
    on_apply: Callable[[NetworkConfig], None],
) -> NetworkSettingsDialog:
    """Open the dialog and return it (mostly for testing)."""
    return NetworkSettingsDialog(parent, current, on_apply)


class NetworkSettingsDialog(tk.Toplevel):
    """Modal-ish settings dialog for proxy + TLS trust."""

    def __init__(
        self,
        parent: tk.Misc,
        current: NetworkConfig,
        on_apply: Callable[[NetworkConfig], None],
    ) -> None:
        super().__init__(parent)
        self.title("Network & Proxy Settings")
        self.resizable(True, False)
        self.transient(parent.winfo_toplevel())
        self.on_apply = on_apply
        self.bind("<Escape>", lambda _e: self.destroy())

        # ── Tk variables seeded from the current config ───────────────────────
        self.use_env_proxy_var = tk.BooleanVar(value=current.use_env_proxy)
        self.http_proxy_var = tk.StringVar(value=current.http_proxy)
        self.https_proxy_var = tk.StringVar(value=current.https_proxy)
        self.no_proxy_var = tk.StringVar(value=current.no_proxy)
        self.ca_bundle_var = tk.StringVar(value=current.ca_bundle_path)
        self.client_cert_var = tk.StringVar(value=current.client_cert_path)
        self.verify_ssl_var = tk.BooleanVar(value=current.verify_ssl)

        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)
        outer.grid_columnconfigure(1, weight=1)
        row = 0

        ttk.Label(outer, text="Proxy", font=("", 11, "bold")).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(0, 4)
        )
        row += 1

        ttk.Checkbutton(
            outer,
            text="Respect HTTP_PROXY / HTTPS_PROXY environment variables",
            variable=self.use_env_proxy_var,
        ).grid(row=row, column=0, columnspan=3, sticky="w")
        row += 1
        ttk.Label(
            outer,
            text='Uncheck to ignore the proxy env vars — i.e. "try without the proxy despite the vars".',
            foreground="gray",
        ).grid(row=row, column=0, columnspan=3, sticky="w", pady=(0, 6))
        row += 1

        env_summary = self._env_proxy_summary()
        if env_summary:
            ttk.Label(outer, text=env_summary, foreground="#555").grid(
                row=row, column=0, columnspan=3, sticky="w", pady=(0, 6)
            )
            row += 1

        row = self._add_entry(outer, row, "HTTP proxy URL:", self.http_proxy_var, "http://proxy.corp:8080")
        row = self._add_entry(outer, row, "HTTPS proxy URL:", self.https_proxy_var, "http://proxy.corp:8080")
        row = self._add_entry(outer, row, "No-proxy hosts:", self.no_proxy_var, "169.254.169.254,localhost")
        ttk.Label(
            outer,
            text="Explicit URLs override the environment. Leave blank to use the env vars (if respected).",
            foreground="gray",
        ).grid(row=row, column=0, columnspan=3, sticky="w", pady=(0, 10))
        row += 1

        ttk.Separator(outer, orient="horizontal").grid(row=row, column=0, columnspan=3, sticky="ew", pady=6)
        row += 1

        ttk.Label(outer, text="TLS / Certificates", font=("", 11, "bold")).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(0, 4)
        )
        row += 1

        row = self._add_file_picker(
            outer, row, "Trusted CA bundle:", self.ca_bundle_var, "Trust an enterprise/AWS root CA (PEM)"
        )
        row = self._add_file_picker(
            outer, row, "Client certificate:", self.client_cert_var, "Client cert for mutual TLS (PEM, optional)"
        )

        ttk.Checkbutton(
            outer,
            text="Verify TLS certificates (recommended)",
            variable=self.verify_ssl_var,
            command=self._on_verify_toggled,
        ).grid(row=row, column=0, columnspan=3, sticky="w", pady=(4, 0))
        row += 1
        self.warn_label = ttk.Label(
            outer,
            text="⚠ Disabling verification is insecure — only use it to diagnose a cert problem.",
            foreground="#b00020",
        )
        self.warn_label.grid(row=row, column=0, columnspan=3, sticky="w")
        row += 1
        self._on_verify_toggled()

        # ── Buttons ───────────────────────────────────────────────────────────
        btns = ttk.Frame(outer)
        btns.grid(row=row, column=0, columnspan=3, sticky="e", pady=(12, 0))
        ttk.Button(btns, text="Reset", command=self._reset).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=4)
        ttk.Button(btns, text="Apply", command=self._apply).pack(side="left", padx=4)

        self.update_idletasks()
        self._center(parent)

    # ── Layout helpers ────────────────────────────────────────────────────────

    def _add_entry(self, parent: ttk.Frame, row: int, label: str, var: tk.StringVar, example: str) -> int:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        entry = ttk.Entry(parent, textvariable=var, width=44)
        entry.grid(row=row, column=1, sticky="ew", pady=2, padx=(6, 0))
        if example:
            ttk.Label(parent, text=f"e.g. {example}", foreground="gray").grid(
                row=row, column=2, sticky="w", padx=(6, 0)
            )
        return row + 1

    def _add_file_picker(self, parent: ttk.Frame, row: int, label: str, var: tk.StringVar, hint: str) -> int:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        ttk.Entry(parent, textvariable=var, width=36).grid(row=row, column=1, sticky="ew", pady=2, padx=(6, 0))
        ttk.Button(parent, text="Browse…", command=partial(self._browse, var)).grid(
            row=row, column=2, sticky="w", padx=(6, 0)
        )
        row += 1
        ttk.Label(parent, text=hint, foreground="gray").grid(row=row, column=1, columnspan=2, sticky="w")
        return row + 1

    def _browse(self, var: tk.StringVar) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Select certificate file",
            filetypes=[("Certificate / PEM", "*.pem *.crt *.cer *.cert"), ("All files", "*.*")],
        )
        if path:
            var.set(path)

    def _env_proxy_summary(self) -> str:
        """One-line summary of any proxy env vars currently set, for the user's awareness."""
        seen = {name: os.environ[name] for name in PROXY_ENV_VARS if os.environ.get(name)}
        if not seen:
            return "No proxy environment variables are currently set."
        # De-dupe lower/upper spellings by value.
        parts = sorted({f"{name}={value}" for name, value in seen.items()})
        return "Detected: " + ", ".join(parts)

    def _on_verify_toggled(self) -> None:
        # Emphasize the warning in red when verification is off; de-emphasize otherwise.
        verifying = self.verify_ssl_var.get()
        self.warn_label.configure(foreground="gray" if verifying else "#b00020")

    def _center(self, parent: tk.Misc) -> None:
        try:
            top = parent.winfo_toplevel()
            x = top.winfo_rootx() + 60
            y = top.winfo_rooty() + 60
            self.geometry(f"+{x}+{y}")
        except tk.TclError:
            pass

    # ── Actions ───────────────────────────────────────────────────────────────

    def to_config(self) -> NetworkConfig:
        """Read the current widget values into a NetworkConfig."""
        return NetworkConfig(
            use_env_proxy=self.use_env_proxy_var.get(),
            http_proxy=self.http_proxy_var.get().strip(),
            https_proxy=self.https_proxy_var.get().strip(),
            no_proxy=self.no_proxy_var.get().strip(),
            ca_bundle_path=self.ca_bundle_var.get().strip(),
            client_cert_path=self.client_cert_var.get().strip(),
            verify_ssl=self.verify_ssl_var.get(),
        )

    def _reset(self) -> None:
        defaults = NetworkConfig()
        self.use_env_proxy_var.set(defaults.use_env_proxy)
        self.http_proxy_var.set(defaults.http_proxy)
        self.https_proxy_var.set(defaults.https_proxy)
        self.no_proxy_var.set(defaults.no_proxy)
        self.ca_bundle_var.set(defaults.ca_bundle_path)
        self.client_cert_var.set(defaults.client_cert_path)
        self.verify_ssl_var.set(defaults.verify_ssl)
        self._on_verify_toggled()

    def _apply(self) -> None:
        self.on_apply(self.to_config())
        self.destroy()
