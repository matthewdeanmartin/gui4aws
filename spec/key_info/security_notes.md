# Security notes

The app is a local desktop tool. A user who runs it can already call AWS and launch local subprocesses. The security goal is not to stop the local user; it is to avoid surprising credential/secret leakage and avoid turning viewed data into executed code.

## Current decisions

AWS credentials are not stored by the app. boto3 and the AWS CLI use their normal credential chains.

App config stores preferences, endpoint URLs, and network settings. It should not store AWS secrets.

SQL connection secrets are stored through the OS keyring.

Generated scripts may contain resource names and ARNs. Secret values must be placeholders.

Subprocess calls use argv lists, not `shell=True`.

Moto and Robotocore are local developer targets. Fake credential injection for Moto is process-global and intentionally scoped to the GUI session.

TLS verification can be disabled in network settings as a diagnostic escape hatch. That is insecure and should remain explicit.

## Future watch points

Do not reintroduce plaintext secret values into history, diagnostics, clipboard flows, script previews, or exports.

Keep Bandit shell-injection checks enabled globally. Use targeted `# nosec` comments only when a subprocess call is intentional and reviewed.

Release/publish jobs should run dependency audits even if a release-helper commit uses `[skip ci]`.

Optional SQL drivers and keyring backends touch credentials. Keep an eye on their supply-chain posture before wider distribution.
