# ADR 0004: secret fields are placeholders in scripts

Secret inputs use `InputField.is_secret`.

The form masks them. History and diagnostics redact them. Generated CLI/Python scripts use environment-variable placeholders instead of literal values.

Generated scripts should be safe to paste into a project without accidentally committing passwords or secret strings.
