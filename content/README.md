# Content (YAML)

Authoring root for skills, items, misconceptions, overlays, glossaries, and checkpoint forms.

```
cd apps/api
python -m app.content.validate ../../content
python -m app.content.load ../../content --database-url sqlite:///content.db
```

The Class 9 linear-equations seed is `status: draft` with Nepali/Assamese reviewer placeholders. Do not mark approved until a human reviewer edits the translations. Regenerate (overwrites YAML) with `python scripts/generate_seed.py`.
