"""Dataset QC and BLQ handling tools."""
import json
from .registry import register_tool
from .data import get_current_dataset


@register_tool(
    name="dataset_qc",
    description="""Run quality checks on the loaded PK dataset. Checks for:
- Duplicate records (same ID/TIME/EVID)
- Negative times
- Missing DV for observation records
- AMT/EVID inconsistency (AMT>0 but EVID=0, or EVID=1 but AMT=0)
- Dose before first observation per subject
- BLQ records (DV=0 or flagged via BLQ column)
- Subjects with <3 observations
- Extreme DV values (outliers >5 SD from mean)
Flags issues and returns a QC report. Run this before fitting models.""",
    parameters={
        "properties": {
            "lloq": {
                "type": "number",
                "description": "Lower limit of quantification. DV values below this are BLQ."
            }
        },
        "required": []
    }
)
def dataset_qc(lloq: float = None) -> dict:
    df = get_current_dataset()
    if df is None:
        return {"success": False, "error": "No dataset loaded."}
    
    import pandas as pd
    issues = []
    warnings = []
    
    # 1. Duplicates
    dup_cols = ["ID", "TIME"]
    if "EVID" in df.columns:
        dup_cols.append("EVID")
    dupes = df.duplicated(subset=dup_cols, keep=False)
    n_dupes = dupes.sum()
    if n_dupes > 0:
        issues.append(f"⚠️ {n_dupes} duplicate records (same {'/'.join(dup_cols)})")
    
    # 2. Negative times
    neg_time = (df["TIME"] < 0).sum()
    if neg_time > 0:
        issues.append(f"❌ {neg_time} records with negative TIME")
    
    # 3. Missing DV on observations
    if "EVID" in df.columns:
        obs = df[df["EVID"] == 0]
    else:
        obs = df[df.get("AMT", 0) == 0] if "AMT" in df.columns else df
    
    missing_dv = obs["DV"].isna().sum()
    if missing_dv > 0:
        issues.append(f"⚠️ {missing_dv} observation records with missing DV")
    
    # 4. AMT/EVID consistency
    if "AMT" in df.columns and "EVID" in df.columns:
        bad_dose = ((df["AMT"] > 0) & (df["EVID"] == 0)).sum()
        bad_evid = ((df["EVID"] == 1) & (df["AMT"].fillna(0) == 0)).sum()
        if bad_dose > 0:
            issues.append(f"❌ {bad_dose} records: AMT>0 but EVID=0 (dose not flagged)")
        if bad_evid > 0:
            issues.append(f"❌ {bad_evid} records: EVID=1 but AMT=0 (flagged as dose with no amount)")
    
    # 5. Dose before first observation
    if "EVID" in df.columns:
        no_dose_first = 0
        for subj in df["ID"].unique():
            subj_data = df[df["ID"] == subj].sort_values("TIME")
            doses = subj_data[subj_data["EVID"] == 1]
            observations = subj_data[subj_data["EVID"] == 0]
            if len(doses) > 0 and len(observations) > 0:
                if observations["TIME"].min() < doses["TIME"].min():
                    no_dose_first += 1
        if no_dose_first > 0:
            warnings.append(f"⚠️ {no_dose_first} subjects have observations before first dose")
    
    # 6. BLQ
    blq_count = 0
    if "BLQ" in df.columns:
        blq_count = (df["BLQ"] == 1).sum()
    elif lloq is not None:
        blq_count = (obs["DV"] < lloq).sum()
    elif (obs["DV"] == 0).sum() > 0:
        blq_count = (obs["DV"] == 0).sum()
        warnings.append(f"ℹ️ {blq_count} observations with DV=0 (possible BLQ — specify LLOQ to confirm)")
    
    if blq_count > 0:
        blq_pct = round(blq_count / len(obs) * 100, 1)
        warnings.append(f"ℹ️ {blq_count} BLQ records ({blq_pct}% of observations)")
        if blq_pct > 10:
            issues.append(f"⚠️ High BLQ rate ({blq_pct}%) — consider M3 or M4 method for handling")
    
    # 7. Sparse subjects
    obs_per_subj = obs.groupby("ID").size()
    sparse = (obs_per_subj < 3).sum()
    if sparse > 0:
        warnings.append(f"⚠️ {sparse} subjects with <3 observations (sparse sampling)")
    
    # 8. Outliers (>5 SD)
    dv_valid = obs["DV"].dropna()
    if len(dv_valid) > 10:
        mean_dv = dv_valid.mean()
        sd_dv = dv_valid.std()
        outliers = ((dv_valid - mean_dv).abs() > 5 * sd_dv).sum()
        if outliers > 0:
            issues.append(f"⚠️ {outliers} potential outliers (|DV - mean| > 5 SD)")
    
    # Summary
    n_issues = len(issues)
    n_warnings = len(warnings)
    status = "PASS" if n_issues == 0 else "FAIL" if any("❌" in i for i in issues) else "WARNING"
    
    return {
        "success": True,
        "status": status,
        "n_issues": n_issues,
        "n_warnings": n_warnings,
        "issues": issues,
        "warnings": warnings,
        "summary": {
            "n_subjects": int(df["ID"].nunique()),
            "n_observations": int(len(obs)),
            "n_blq": int(blq_count),
            "blq_pct": round(blq_count / max(len(obs), 1) * 100, 1),
            "obs_per_subject_range": [int(obs_per_subj.min()), int(obs_per_subj.max())],
        },
        "message": f"Dataset QC: {status}. {n_issues} issues, {n_warnings} warnings."
    }


@register_tool(
    name="handle_blq",
    description="""Handle below-limit-of-quantification (BLQ) data using standard methods:
- M1: Drop BLQ records (simplest, may bias if >10% BLQ)
- M3: Likelihood-based (treat BLQ as censored at LLOQ — recommended for PopPK)
- M4: Replace BLQ with LLOQ/2 (common but biased at high BLQ rates)
- M5: Replace first BLQ with LLOQ/2, drop subsequent BLQ in each subject
Creates a new processed dataset. Use dataset_qc first to assess BLQ prevalence.""",
    parameters={
        "properties": {
            "method": {
                "type": "string",
                "enum": ["M1", "M3", "M4", "M5"],
                "description": "BLQ handling method"
            },
            "lloq": {
                "type": "number",
                "description": "Lower limit of quantification"
            }
        },
        "required": ["method", "lloq"]
    }
)
def handle_blq(method: str, lloq: float) -> dict:
    import pandas as pd
    from .data import _current_dataset
    
    df = get_current_dataset()
    if df is None:
        return {"success": False, "error": "No dataset loaded."}
    
    df = df.copy()
    
    # Identify BLQ records
    if "BLQ" in df.columns:
        blq_mask = df["BLQ"] == 1
    elif "EVID" in df.columns:
        obs_mask = df["EVID"] == 0
        blq_mask = obs_mask & (df["DV"] < lloq)
    else:
        blq_mask = (df["DV"] < lloq) & (df.get("AMT", 0) == 0)
    
    n_blq = blq_mask.sum()
    n_total = len(df[(df.get("EVID", 0) == 0)])
    
    if method == "M1":
        # Drop all BLQ
        df_out = df[~blq_mask].copy()
        msg = f"M1: Dropped {n_blq} BLQ records. {len(df_out)} records remain."
    
    elif method == "M3":
        # Censored likelihood — set CENS=1 for BLQ, keep records
        df_out = df.copy()
        df_out["CENS"] = 0
        df_out.loc[blq_mask, "CENS"] = 1
        df_out.loc[blq_mask, "DV"] = lloq
        msg = f"M3: Flagged {n_blq} BLQ records as censored (CENS=1, DV=LLOQ={lloq})."
    
    elif method == "M4":
        # Replace BLQ with LLOQ/2
        df_out = df.copy()
        df_out.loc[blq_mask, "DV"] = lloq / 2
        msg = f"M4: Replaced {n_blq} BLQ records with LLOQ/2={lloq/2}."
    
    elif method == "M5":
        # First BLQ per subject → LLOQ/2, subsequent → drop
        df_out = df.copy()
        to_drop = []
        for subj in df_out["ID"].unique():
            subj_blq = df_out[(df_out["ID"] == subj) & blq_mask].index.tolist()
            if len(subj_blq) > 0:
                df_out.loc[subj_blq[0], "DV"] = lloq / 2  # Keep first
                to_drop.extend(subj_blq[1:])  # Drop rest
        df_out = df_out.drop(to_drop)
        msg = f"M5: Kept first BLQ as LLOQ/2 per subject, dropped {len(to_drop)} subsequent BLQ."
    
    else:
        return {"success": False, "error": f"Unknown method: {method}"}
    
    # Update current dataset
    import pkpdbuilder.tools.data as data_mod
    data_mod._current_dataset = df_out
    
    # Save processed data
    from ..config import load_config, ensure_output_dir
    config = load_config()
    out = ensure_output_dir(config)
    out_path = str(out / f"data_blq_{method.lower()}.csv")
    df_out.to_csv(out_path, index=False)
    
    return {
        "success": True,
        "method": method,
        "lloq": lloq,
        "n_blq_original": int(n_blq),
        "blq_pct": round(n_blq / max(n_total, 1) * 100, 1),
        "n_records_before": len(df),
        "n_records_after": len(df_out),
        "output_file": out_path,
        "message": msg
    }
