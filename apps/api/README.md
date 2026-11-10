# YourTutor API

FastAPI service. From this directory:

```
pip install -r requirements-dev.txt
pytest
ruff check .
mypy app
python -m app.content.validate ../../content
python -m app.content.load ../../content --database-url sqlite:///content.db
```

CI and the Docker image install from the pinned `requirements.lock` and `requirements-dev.lock` (Linux, Python 3.12). To refresh them after changing a requirements file or to take upgrades, run from this directory with [uv](https://docs.astral.sh/uv/):

```
uv pip compile requirements.txt --python-version 3.12 --python-platform linux --no-header -o requirements.lock
uv pip compile requirements-dev.txt --python-version 3.12 --python-platform linux --no-header -o requirements-dev.lock
```
