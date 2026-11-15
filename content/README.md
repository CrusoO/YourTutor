# Content (YAML)

`content/` is the production content root. It is a near-empty skeleton: **production serves nothing
until the content factory stamps content here.** Nobody hand-edits content in this folder; only the
factory CLI writes to the per-class folders.

```
content/
  curricula/            board definitions (chapters, sections). Read by the app at startup.
  rights/register.yaml  source register (licences). Read by `content validate` and `load`.
  sources/notes.yaml    approved sources for lessons (empty until the factory stamps lessons).
  copy/encouragement.yaml  tutor encouragement lines. Read at runtime by the lesson player.
  cbse/<class>/<subject>/{skills,templates,items,lessons,passages,overlays}/
                        class 9-12, subject maths or science; each folder holds only .gitkeep today
```

The loader and validator (`python -m app.content`) currently read `<root>/skills`, `<root>/items`,
`<root>/lessons` and so on. They do not yet descend into `cbse/<class>/<subject>/`; wiring that
belongs to the factory work.

## Check the production root

```
cd apps/api
python -m app.content validate ../../content    # OK: 0 skills, 0 items ...
python -m app.content load ../../content        # a no-op that syncs the registries
```

`load` of an empty root succeeds only when the database has no skills or items yet. If content is
already loaded it refuses, so an empty folder can never retire or delete what is in the database.

`validate` also warns (not an error) for every curriculum chapter whose `overlay_id` has no overlay
file. Those chapters cannot be served until the factory writes the overlay.

## Legacy pack (test fixture)

The frozen Class 9 linear-equations draft pack for the Bhutan and SEBA boards (12 skills, 406 items,
12 lessons, 13 passages, 35 templates, misconceptions, glossary, checkpoints, 2 overlays, the
`e2e_mini` chapter and its source notes) lives in
`apps/api/tests/fixtures/legacy_content/`. Everything in it is `status: draft`; none of it is
servable in production. It keeps the loader, validator, lesson player (including the number-line
pilot lesson `lessons/integers_operations.yaml`) and review tools under test.

* Tests import `LEGACY_CONTENT_ROOT` from `apps/api/tests/legacy_content.py`. Do not write the path
  anywhere else.
* CI gets the path with `python -m tests.legacy_content` (run from `apps/api`).
* To look at it in a local preview database:
  `cd apps/api && python -m app.content load tests/fixtures/legacy_content --database-url <preview url>`
  with `ALLOW_DRAFT_CONTENT=true`.
* The old seed scripts under `apps/api/scripts/` (`generate_seed.py`, `write_*`) still write to
  `content/`; point them at the fixture folder before using them.
* The pack is still `status: draft` with Nepali and Assamese reviewer placeholders. Do not mark it
  approved.
