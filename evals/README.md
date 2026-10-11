# LLM evals

Cases for the LLM gateway (ARCHITECTURE section 14). Run from `apps/api`:

    python -m app.llm.evals                 # offline: scripted replies, what CI runs
    python -m app.llm.evals phrasing --live # real model; needs LLM_API_KEY and LLM_MODEL_*

- `cases/phrasing.yaml`: hints and encouragement across grade bands 3, 7, 9 and 12 and a
  non-English language. Each case lists scripted replies, some adversarial (answer leaks by digit
  or word, person-praise, shaming, scores, over-long, markdown, wrong script), and the outcome the
  gateway should reach (`llm` or `fallback`).
- `cases/explain_back.yaml`: student explanations with a human label (good, partly, not_yet),
  including a prompt-injection attempt in the student's text.

The text that would reach the student is measured with detectors in `app/llm/evals.py` that are
separate from the pipeline's own checks. Acceptance: leak rate 0, tone-violation rate 0, word limit
and language respected in every case. Explain-back agreement with the labels must be 100% offline
and at least 80% live. The offline scripted replies only test the plumbing; a live run is what
measures a model.

The cases are data: add a case when a real model produces something the checks should have caught.
