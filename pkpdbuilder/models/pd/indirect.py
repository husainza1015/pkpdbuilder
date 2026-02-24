"""Indirect Response (Turnover) PD Models — Monolix equivalents translated to nlmixr2."""
from pkpdbuilder.models import register_model

# ═══════════════════════════════════════════════════════════
# IDR Type I — Inhibition of production (kin)
# ═══════════════════════════════════════════════════════════

register_model(
    name="pd_idr1_imax",
    category="pd",
    description="Indirect response Type I — inhibition of production (kin), Imax model",
    pd_type="idr_type1",
    monolix_equivalent="turnover_kin_Imax",
    code=r"""
pd_idr1_imax <- function() {
  ini({
    lR0   <- log(100);   label("Baseline response")
    lkout <- log(0.1);   label("Response elimination rate (1/h)")
    lIC50 <- log(10);    label("IC50 (mg/L)")
    lImax <- logit(0.9); label("Maximum inhibition fraction")
    eta.R0   ~ 0.1
    eta.IC50 ~ 0.1
    add.sd <- 5
  })
  model({
    R0   <- exp(lR0   + eta.R0)
    kout <- exp(lkout)
    kin  <- R0 * kout
    IC50 <- exp(lIC50 + eta.IC50)
    Imax <- expit(lImax)
    d/dt(response) = kin * (1 - Imax * Cc / (IC50 + Cc)) - kout * response
    response(0) <- R0
    R = response
    R ~ add(add.sd)
  })
}
""")

register_model(
    name="pd_idr1_imax_sigmoid",
    category="pd",
    description="Indirect response Type I — inhibition of production (kin), sigmoidal Imax",
    pd_type="idr_type1",
    monolix_equivalent="turnover_kin_Imax_sigmoid",
    code=r"""
pd_idr1_imax_sigmoid <- function() {
  ini({
    lR0    <- log(100);   label("Baseline response")
    lkout  <- log(0.1);   label("Response elimination rate (1/h)")
    lIC50  <- log(10);    label("IC50 (mg/L)")
    lImax  <- logit(0.9); label("Maximum inhibition fraction")
    lgamma <- log(1.5);   label("Hill coefficient")
    eta.R0   ~ 0.1
    eta.IC50 ~ 0.1
    add.sd <- 5
  })
  model({
    R0    <- exp(lR0   + eta.R0)
    kout  <- exp(lkout)
    kin   <- R0 * kout
    IC50  <- exp(lIC50 + eta.IC50)
    Imax  <- expit(lImax)
    gamma <- exp(lgamma)
    d/dt(response) = kin * (1 - Imax * Cc^gamma / (IC50^gamma + Cc^gamma)) - kout * response
    response(0) <- R0
    R = response
    R ~ add(add.sd)
  })
}
""")

# ═══════════════════════════════════════════════════════════
# IDR Type II — Inhibition of degradation (kout)
# ═══════════════════════════════════════════════════════════

register_model(
    name="pd_idr2_imax",
    category="pd",
    description="Indirect response Type II — inhibition of degradation (kout), Imax model",
    pd_type="idr_type2",
    monolix_equivalent="turnover_kout_Imax",
    code=r"""
pd_idr2_imax <- function() {
  ini({
    lR0   <- log(100);   label("Baseline response")
    lkout <- log(0.1);   label("Response elimination rate (1/h)")
    lIC50 <- log(10);    label("IC50 (mg/L)")
    lImax <- logit(0.9); label("Maximum inhibition fraction")
    eta.R0   ~ 0.1
    eta.IC50 ~ 0.1
    add.sd <- 5
  })
  model({
    R0   <- exp(lR0   + eta.R0)
    kout <- exp(lkout)
    kin  <- R0 * kout
    IC50 <- exp(lIC50 + eta.IC50)
    Imax <- expit(lImax)
    d/dt(response) = kin - kout * (1 - Imax * Cc / (IC50 + Cc)) * response
    response(0) <- R0
    R = response
    R ~ add(add.sd)
  })
}
""")

register_model(
    name="pd_idr2_imax_sigmoid",
    category="pd",
    description="Indirect response Type II — inhibition of degradation (kout), sigmoidal Imax",
    pd_type="idr_type2",
    monolix_equivalent="turnover_kout_Imax_sigmoid",
    code=r"""
pd_idr2_imax_sigmoid <- function() {
  ini({
    lR0    <- log(100);   label("Baseline response")
    lkout  <- log(0.1);   label("Response elimination rate (1/h)")
    lIC50  <- log(10);    label("IC50 (mg/L)")
    lImax  <- logit(0.9); label("Maximum inhibition fraction")
    lgamma <- log(1.5);   label("Hill coefficient")
    eta.R0   ~ 0.1
    eta.IC50 ~ 0.1
    add.sd <- 5
  })
  model({
    R0    <- exp(lR0   + eta.R0)
    kout  <- exp(lkout)
    kin   <- R0 * kout
    IC50  <- exp(lIC50 + eta.IC50)
    Imax  <- expit(lImax)
    gamma <- exp(lgamma)
    d/dt(response) = kin - kout * (1 - Imax * Cc^gamma / (IC50^gamma + Cc^gamma)) * response
    response(0) <- R0
    R = response
    R ~ add(add.sd)
  })
}
""")

# ═══════════════════════════════════════════════════════════
# IDR Type III — Stimulation of production (kin)
# ═══════════════════════════════════════════════════════════

register_model(
    name="pd_idr3_emax",
    category="pd",
    description="Indirect response Type III — stimulation of production (kin), Emax model",
    pd_type="idr_type3",
    monolix_equivalent="turnover_kin_Emax",
    code=r"""
pd_idr3_emax <- function() {
  ini({
    lR0   <- log(100);  label("Baseline response")
    lkout <- log(0.1);  label("Response elimination rate (1/h)")
    lEmax <- log(2);    label("Maximum stimulation (fold-change)")
    lEC50 <- log(10);   label("EC50 (mg/L)")
    eta.R0   ~ 0.1
    eta.EC50 ~ 0.1
    add.sd <- 5
  })
  model({
    R0   <- exp(lR0   + eta.R0)
    kout <- exp(lkout)
    kin  <- R0 * kout
    Emax <- exp(lEmax)
    EC50 <- exp(lEC50 + eta.EC50)
    d/dt(response) = kin * (1 + Emax * Cc / (EC50 + Cc)) - kout * response
    response(0) <- R0
    R = response
    R ~ add(add.sd)
  })
}
""")

register_model(
    name="pd_idr3_emax_sigmoid",
    category="pd",
    description="Indirect response Type III — stimulation of production (kin), sigmoidal Emax",
    pd_type="idr_type3",
    monolix_equivalent="turnover_kin_Emax_sigmoid",
    code=r"""
pd_idr3_emax_sigmoid <- function() {
  ini({
    lR0    <- log(100);  label("Baseline response")
    lkout  <- log(0.1);  label("Response elimination rate (1/h)")
    lEmax  <- log(2);    label("Maximum stimulation (fold-change)")
    lEC50  <- log(10);   label("EC50 (mg/L)")
    lgamma <- log(1.5);  label("Hill coefficient")
    eta.R0   ~ 0.1
    eta.EC50 ~ 0.1
    add.sd <- 5
  })
  model({
    R0    <- exp(lR0   + eta.R0)
    kout  <- exp(lkout)
    kin   <- R0 * kout
    Emax  <- exp(lEmax)
    EC50  <- exp(lEC50 + eta.EC50)
    gamma <- exp(lgamma)
    d/dt(response) = kin * (1 + Emax * Cc^gamma / (EC50^gamma + Cc^gamma)) - kout * response
    response(0) <- R0
    R = response
    R ~ add(add.sd)
  })
}
""")

# ═══════════════════════════════════════════════════════════
# IDR Type IV — Stimulation of degradation (kout)
# ═══════════════════════════════════════════════════════════

register_model(
    name="pd_idr4_emax",
    category="pd",
    description="Indirect response Type IV — stimulation of degradation (kout), Emax model",
    pd_type="idr_type4",
    monolix_equivalent="turnover_kout_Emax",
    code=r"""
pd_idr4_emax <- function() {
  ini({
    lR0   <- log(100);  label("Baseline response")
    lkout <- log(0.1);  label("Response elimination rate (1/h)")
    lEmax <- log(2);    label("Maximum stimulation of degradation")
    lEC50 <- log(10);   label("EC50 (mg/L)")
    eta.R0   ~ 0.1
    eta.EC50 ~ 0.1
    add.sd <- 5
  })
  model({
    R0   <- exp(lR0   + eta.R0)
    kout <- exp(lkout)
    kin  <- R0 * kout
    Emax <- exp(lEmax)
    EC50 <- exp(lEC50 + eta.EC50)
    d/dt(response) = kin - kout * (1 + Emax * Cc / (EC50 + Cc)) * response
    response(0) <- R0
    R = response
    R ~ add(add.sd)
  })
}
""")

register_model(
    name="pd_idr4_emax_sigmoid",
    category="pd",
    description="Indirect response Type IV — stimulation of degradation (kout), sigmoidal Emax",
    pd_type="idr_type4",
    monolix_equivalent="turnover_kout_Emax_sigmoid",
    code=r"""
pd_idr4_emax_sigmoid <- function() {
  ini({
    lR0    <- log(100);  label("Baseline response")
    lkout  <- log(0.1);  label("Response elimination rate (1/h)")
    lEmax  <- log(2);    label("Maximum stimulation of degradation")
    lEC50  <- log(10);   label("EC50 (mg/L)")
    lgamma <- log(1.5);  label("Hill coefficient")
    eta.R0   ~ 0.1
    eta.EC50 ~ 0.1
    add.sd <- 5
  })
  model({
    R0    <- exp(lR0   + eta.R0)
    kout  <- exp(lkout)
    kin   <- R0 * kout
    Emax  <- exp(lEmax)
    EC50  <- exp(lEC50 + eta.EC50)
    gamma <- exp(lgamma)
    d/dt(response) = kin - kout * (1 + Emax * Cc^gamma / (EC50^gamma + Cc^gamma)) * response
    response(0) <- R0
    R = response
    R ~ add(add.sd)
  })
}
""")
