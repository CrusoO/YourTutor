"""Authoring pipeline for model-drafted (machine-unchecked) practice items.

A drafter writes one compact YAML file per chapter (see `schema.DraftFile`). This package checks it
against the syllabus map, lints it with deterministic rules (no model), and compiles it into full
Item YAML at tier C, status draft. Nothing here produces a verification record: only the factory
may do that, so a compiled item is never labelled as machine-checked.
"""
