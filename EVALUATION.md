# Evaluation

`MERCURY-MEM-20` runs 20 deterministic incidents across six categories against six persisted historical lessons. It compares FORGET to REMEMBER using the same decision and policy code as the API.

Current measured results are generated in `evals/results/mercury-mem-20.md` and the case-level JSON beside it. The current run measured:

- correct mitigation: 0% baseline vs 100% with Sibyl;
- repeated failure: 100% baseline vs 0% with Sibyl;
- mean simulated recovery: 50.6 vs 12.8 minutes;
- policy violations: 0% in both modes;
- decision change and memory use: 100% in applicable Sibyl cases.

These are simulator measurements, not production effectiveness claims. Re-run `python evals/run_benchmark.py`; never hand-edit the generated results.

