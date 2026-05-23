# Moto RDS/Aurora dashboard repro

## Summary

Moto's dashboard data endpoint crashes after creating an Aurora/RDS cluster with a master password.

The failing endpoint is:

```text
http://localhost:5005/moto-api/data.json
```

The browser dashboard at:

```text
http://localhost:5005/moto-api/
```

hits the same fragile serialization path.

## Minimal repro

Start Moto:

```bash
uv run moto_server -H localhost -p 5005
```

In another terminal:

```bash
bash spec/bugs_moto/repro.sh
```

## Expected

Moto should return JSON for `/moto-api/data.json`.

## Actual

Moto returns `HTTP/1.1 500 INTERNAL SERVER ERROR`.

The traceback ends with:

```text
File "...moto_api\\_internal\\responses.py", line 72, in model_data
    json.dumps(getattr(instance, attr))
File "...moto\\rds\\models.py", line 733, in master_user_password
    raise NotImplementedError("Password not retrievable.")
NotImplementedError: Password not retrievable.
```

## Root cause

Moto's internal dashboard serializer iterates model attributes and touches:

```python
@property
def master_user_password(self) -> str:
    raise NotImplementedError("Password not retrievable.")
```

That is reasonable for the public API surface, but it makes the internal dashboard crash when it tries to serialize the object.

## Proposed minimal fix

For the dashboard/debug serializer path, returning a sentinel password is enough to avoid the crash. A minimal proposal is in:

```text
spec/bugs_moto/models.py
```
