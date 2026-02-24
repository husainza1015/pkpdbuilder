#!/usr/bin/env python3
"""Benchmark: PKPDBuilder CLI full PopPK workflow with timing."""
import time
import json
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pkpdbuilder.tools import data, nlmixr2, diagnostics, nca, simulation, literature, report, shiny, covariate, presentation, backends, memory

results = []

def timed(name, fn, **kwargs):
    t0 = time.time()
    try:
        r = fn(**kwargs)
        dt = time.time() - t0
        success = r.get("success", True) if isinstance(r, dict) else True
        msg = r.get("message", "OK") if isinstance(r, dict) else "OK"
        results.append({"step": name, "time_s": round(dt, 1), "success": success, "message": msg[:100]})
        print(f"  {'✅' if success else '❌'} {name}: {dt:.1f}s — {msg[:80]}")
        return r
    except Exception as e:
        dt = time.time() - t0
        results.append({"step": name, "time_s": round(dt, 1), "success": False, "error": str(e)[:100]})
        print(f"  ❌ {name}: {dt:.1f}s — ERROR: {e}")
        return None

print("=" * 60)
print("PKPDBuilder CLI BENCHMARK — Full PopPK Workflow")
print("=" * 60)
print()

t_total = time.time()

# 1. Load dataset
timed("load_dataset", data.load_dataset, file_path="example_data/theo_sd.csv")

# 2. Summarize
timed("summarize_dataset", data.summarize_dataset)

# 3. Plot data  
timed("plot_data", data.plot_data)

# 4. NCA
timed("run_nca", nca.run_nca)

# 5. Fit 1-CMT
timed("fit_model_1cmt", nlmixr2.fit_model, model_type="1cmt_oral", model_name="M1")

# 6. Fit 2-CMT
timed("fit_model_2cmt", nlmixr2.fit_model, model_type="2cmt_oral", model_name="M2")

# 7. Compare models
timed("compare_models", nlmixr2.compare_models, model_names=["M1", "M2"])

# 8. GOF
timed("goodness_of_fit", diagnostics.goodness_of_fit, model_name="M1")

# 9. VPC
timed("vpc", diagnostics.vpc, model_name="M1", n_sim=200)

# 10. ETA plots
timed("eta_plots", diagnostics.eta_plots, model_name="M1")

# 11. Parameter table
timed("parameter_table", diagnostics.parameter_table, model_name="M1")

# 12. Covariate screening
timed("covariate_screening", covariate.covariate_screening, model_name="M1", covariates=["WT"])

# 13. Simulate regimen
timed("simulate_regimen", simulation.simulate_regimen, model_name="M1", dose=320, interval=24, n_doses=7, sim_duration=168)

# 14. Generate report
timed("generate_report", report.generate_report, model_name="M1", drug_name="Theophylline", author="PKPDBuilder Benchmark")

# 15. Generate Beamer slides
timed("generate_beamer_slides", presentation.generate_beamer_slides, drug_name="Theophylline", model_name="M1")

# 16. Export to NONMEM
timed("export_nonmem", backends.export_model, model_name="M1", target="nonmem")

# 17. Export to Pumas
timed("export_pumas", backends.export_model, model_name="M1", target="pumas")

# 18. Export to mrgsolve
timed("export_mrgsolve", backends.export_model, model_name="M1", target="mrgsolve")

# 19. List backends
timed("list_backends", backends.list_backends)

total = time.time() - t_total
n_success = sum(1 for r in results if r["success"])
n_total = len(results)

print()
print("=" * 60)
print(f"TOTAL: {total:.1f}s ({n_success}/{n_total} steps passed)")
print("=" * 60)

# Count output files
import os
out_dir = "./pkpdbuilder_output"
files = [f for f in os.listdir(out_dir) if os.path.isfile(os.path.join(out_dir, f))]
print(f"\nOutput files: {len(files)}")
for f in sorted(files):
    size = os.path.getsize(os.path.join(out_dir, f))
    print(f"  {f} ({size:,} bytes)")

# Save results
with open("benchmark/results.json", "w") as fh:
    json.dump({"total_s": round(total, 1), "steps": results, "n_success": n_success, "n_total": n_total}, fh, indent=2)
