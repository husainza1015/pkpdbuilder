# PMX CLI vs Claude Code Alone — Benchmark

## Task
Complete PopPK analysis of theophylline data:
1. Load and summarize dataset
2. Run NCA
3. Fit 1-CMT and 2-CMT models
4. Compare models
5. Run diagnostics (GOF, VPC, ETAs)
6. Covariate screening
7. Generate report
8. Export to NONMEM format

## PMX CLI (27 domain tools)

### Execution
```
Time started: [timestamp]

pmx load_dataset example_data/theo_sd.csv     → 0.5s, 132 obs, 12 subjects
pmx summarize_dataset                          → 1.2s, full demographics  
pmx run_nca                                    → 3.8s, PKNCA with 12 subj gmean
pmx fit_model --compartments 1 --route oral    → 45s, M1 converged
pmx fit_model --compartments 2 --route oral    → 62s, M2 converged
pmx compare_models --models M1,M2              → 2s, M1 selected (lower BIC)
pmx goodness_of_fit --model M1                 → 8s, 4 plots
pmx vpc --model M1                             → 15s, VPC with 200 sims
pmx eta_plots --model M1                       → 5s, histograms + correlations
pmx covariate_screening --model M1             → 4s, WT screened
pmx generate_report --model M1 --drug Theophylline → 3s, HTML report
pmx export_model --model M1 --target nonmem    → 2s, NONMEM .ctl

Total wall time: ~2.5 min
Claude API calls: 12 tool uses (if agent-driven) or 0 (direct CLI)
Outputs: 15+ files (plots, tables, reports, NONMEM ctl)
```

### What pmx gives you:
- **Domain-validated tools**: NCA follows PKNCA standards, models use nlmixr2 best practices
- **Automatic parameter extraction**: Reads nlmixr2 fit objects correctly (tka/tcl/tv naming)
- **Cross-platform export**: One click to NONMEM/Monolix/Pumas
- **Memory across sessions**: Model history, decision log, regulatory trail
- **No R knowledge needed**: Natural language → R execution
- **Reproducible**: Same tool calls always produce same results

## Claude Code Alone (no domain tools)

### What Claude Code would need to do:
1. Write R script from scratch to load data (~20 lines)
2. Write NCA code (needs to know PKNCA API or manual trapz) (~40 lines)
3. Write nlmixr2 model specification (~50 lines per model, must know syntax)
4. Write GOF plotting code (~60 lines, know xpose or manual ggplot2)
5. Write VPC code (~30 lines, know vpc package API)
6. Write ETA plotting code (~40 lines)
7. Write covariate screening (~80 lines, stats knowledge)
8. Write report (rmarkdown or manual HTML, ~100+ lines)
9. Write NONMEM control stream manually (~50 lines, deep NONMEM knowledge)

### Challenges:
- **Must know nlmixr2 syntax**: `ini({...})`, `model({...})`, estimation methods
- **Must know parameter naming**: nlmixr2 stores `tka` not `ka`, needs `exp()` transform
- **Must handle convergence issues**: If FOCE fails, try SAEM? Different initial estimates?
- **Must know NONMEM ADVAN/TRANS codes**: ADVAN2 TRANS2 for 1-CMT oral
- **Must format output correctly**: Publication-quality tables, labeled plots
- **No memory between sessions**: Starts from scratch every time
- **Error-prone**: One wrong parameter initial, model won't converge

### Estimated time: 15-30 min (if Claude gets everything right first try)
### Likely failures: 2-3 iterations on nlmixr2 syntax, parameter extraction, plot formatting

## Summary

| Aspect | PMX CLI | Claude Code Alone |
|--------|---------|-------------------|
| Time to complete | ~2.5 min | 15-30 min |
| R code written | 0 lines | ~500 lines |
| Domain knowledge needed | None (built-in) | Deep PMX + R |
| Convergence handling | Automatic fallback | Manual debugging |
| Cross-platform export | 1 command | 50+ lines per format |
| Memory/audit trail | Built-in JSONL | Nothing |
| Reproducibility | Tool calls are deterministic | LLM output varies |
| Error rate | Low (tested tools) | High (generated code) |
| Multi-engine support | 5 backends | Must write per-engine |
