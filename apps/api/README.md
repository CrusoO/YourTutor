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
