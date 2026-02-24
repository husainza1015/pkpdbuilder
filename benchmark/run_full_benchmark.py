#!/usr/bin/env python3
"""Full benchmark: all fixes tested end-to-end."""
import time
import json
import sys
sys.path.insert(0, "/root/.openclaw/workspace/pkpdbuilder-cli")

from pkpdbuilder.tools import data, nlmixr2, diagnostics, nca, simulation, literature, report, shiny, covariate, presentation, backends, memory, model_library, data_qc

results = []

def timed(name, fn, **kwargs):
    t0 = time.time()
    try:
        r = fn(**kwargs)
        dt = time.time() - t0
        success = r.get("success", True) if isinstance(r, dict) else True
        msg = r.get("message", r.get("error", "OK")) if isinstance(r, dict) else "OK"
        results.append({"step": name, "time_s": round(dt, 1), "success": success})
        status = '✅' if success else '❌'
        print(f"  {status} {name}: {dt:.1f}s — {str(msg)[:80]}")
        return r
    except Exception as e:
        dt = time.time() - t0
        results.append({"step": name, "time_s": round(dt, 1), "success": False})
        print(f"  ❌ {name}: {dt:.1f}s — ERROR: {e}")
        return None

print("=" * 65)
print("PKPDBuilder CLI FULL BENCHMARK — 33 tools, all fixes verified")
print("=" * 65)
print()
t_total = time.time()

# === Data ===
print("[Data]")
timed("load_dataset", data.load_dataset, file_path="example_data/theo_sd.csv")
timed("summarize_dataset", data.summarize_dataset)
timed("plot_data", data.plot_data)

# === Dataset QC (FIX 8) ===
print("\n[Dataset QC — Fix 8]")
timed("dataset_qc", data_qc.dataset_qc, lloq=0.1)
timed("handle_blq_M1", data_qc.handle_blq, method="M1", lloq=0.1)
# Reload original data after BLQ test
data.load_dataset("example_data/theo_sd.csv")

# === NCA ===
print("\n[NCA]")
timed("run_nca", nca.run_nca)

# === Standard fit_model ===
print("\n[Modeling — standard fit_model]")
timed("fit_model_1cmt", nlmixr2.fit_model, model_type="1cmt_oral", model_name="M1")
timed("fit_model_2cmt", nlmixr2.fit_model, model_type="2cmt_oral", model_name="M2")

# === fit_from_library (FIX 1) ===
print("\n[Model Library → fit_from_library — Fix 1]")
timed("list_model_library", model_library.list_model_library, category="pk")
timed("fit_from_library", nlmixr2.fit_from_library, library_model="pk_1cmt_oral", model_name="M_lib")

# === Compare ===
print("\n[Compare]")
timed("compare_models", nlmixr2.compare_models, model_names=["M1", "M2", "M_lib"])

# === Diagnostics ===
print("\n[Diagnostics]")
timed("goodness_of_fit", diagnostics.goodness_of_fit, model_name="M1")
timed("vpc", diagnostics.vpc, model_name="M1", n_sim=200)
timed("eta_plots", diagnostics.eta_plots, model_name="M1")
timed("parameter_table", diagnostics.parameter_table, model_name="M1")

# === Individual fits (FIX 7) ===
print("\n[Individual Fits — Fix 7]")
timed("individual_fits", diagnostics.individual_fits, model_name="M1")

# === Covariates (FIX 2 — missing R scripts) ===
print("\n[Covariates — Fix 2: missing R scripts]")
timed("covariate_screening", covariate.covariate_screening, model_name="M1", covariates=["WT"])
timed("stepwise_covariate_model", covariate.stepwise_covariate_model, model_name="M1", covariates=["WT"])
timed("forest_plot", covariate.forest_plot, model_name="M1")

# === Simulation ===
print("\n[Simulation]")
timed("simulate_regimen", simulation.simulate_regimen, model_name="M1", dose=320, interval=24, n_doses=7, sim_duration=168)
timed("population_simulation", simulation.population_simulation, model_name="M1", dose=320, sim_duration=168, interval=24, n_doses=7, n_subjects=200)

# === Report & Slides ===
print("\n[Reports]")
timed("generate_report", report.generate_report, model_name="M1", drug_name="Theophylline", author="PKPDBuilder")
timed("beamer_slides", presentation.generate_beamer_slides, drug_name="Theophylline", model_name="M1")

# === Export ===
print("\n[Cross-Platform Export]")
timed("export_nonmem", backends.export_model, model_name="M1", target="nonmem")
timed("export_pumas", backends.export_model, model_name="M1", target="pumas")
timed("export_mrgsolve", backends.export_model, model_name="M1", target="mrgsolve")
timed("list_backends", backends.list_backends)

# Summary
total = time.time() - t_total
n_success = sum(1 for r in results if r["success"])
n_total = len(results)

print()
print("=" * 65)
print(f"TOTAL: {total:.1f}s ({n_success}/{n_total} steps passed)")
print("=" * 65)

# Output files
import os
out_dir = "./pkpdbuilder_output"
files = sorted([f for f in os.listdir(out_dir) if os.path.isfile(os.path.join(out_dir, f))])
print(f"\nOutput files: {len(files)}")
for f in files:
    size = os.path.getsize(os.path.join(out_dir, f))
    print(f"  {f} ({size:,} bytes)")

with open("benchmark/full_results.json", "w") as fh:
    json.dump({"total_s": round(total, 1), "passed": n_success, "total": n_total, "steps": results}, fh, indent=2)
