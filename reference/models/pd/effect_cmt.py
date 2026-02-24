"""Effect Compartment PD Models — Monolix equivalents translated to nlmixr2."""
from pkpdbuilder.models import register_model

register_model(
    name="pd_effect_cmt_emax",
    category="pd",
    description="Effect compartment Emax model — hysteresis via Ce delay",
    pd_type="effect_compartment",
    monolix_equivalent="effectCpt_Emax",
    code=r"""
pd_effect_cmt_emax <- function() {
  ini({
    lke0  <- log(0.5);  label("Effect compartment equilibration rate (1/h)")
    lE0   <- log(50);   label("Baseline effect")
    lEmax <- log(100);  label("Maximum drug effect")
    lEC50 <- log(10);   label("EC50 for effect compartment conc (mg/L)")
    eta.E0   ~ 0.1
    eta.Emax ~ 0.1
    add.sd <- 5
  })
  model({
    ke0  <- exp(lke0)
    E0   <- exp(lE0   + eta.E0)
    Emax <- exp(lEmax + eta.Emax)
    EC50 <- exp(lEC50)
    d/dt(Ce) = ke0 * (Cc - Ce)
    E = E0 + Emax * Ce / (EC50 + Ce)
    E ~ add(add.sd)
  })
}
""")

register_model(
    name="pd_effect_cmt_emax_sigmoid",
    category="pd",
    description="Effect compartment sigmoidal Emax model — with Hill coefficient",
    pd_type="effect_compartment",
    monolix_equivalent="effectCpt_Emax_sigmoid",
    code=r"""
pd_effect_cmt_emax_sigmoid <- function() {
  ini({
    lke0   <- log(0.5);  label("Effect compartment equilibration rate (1/h)")
    lE0    <- log(50);   label("Baseline effect")
    lEmax  <- log(100);  label("Maximum drug effect")
    lEC50  <- log(10);   label("EC50 (mg/L)")
    lgamma <- log(1.5);  label("Hill coefficient")
    eta.E0   ~ 0.1
    eta.Emax ~ 0.1
    add.sd <- 5
  })
  model({
    ke0   <- exp(lke0)
    E0    <- exp(lE0   + eta.E0)
    Emax  <- exp(lEmax + eta.Emax)
    EC50  <- exp(lEC50)
    gamma <- exp(lgamma)
    d/dt(Ce) = ke0 * (Cc - Ce)
    E = E0 + Emax * Ce^gamma / (EC50^gamma + Ce^gamma)
    E ~ add(add.sd)
  })
}
""")

register_model(
    name="pd_effect_cmt_imax",
    category="pd",
    description="Effect compartment Imax model — inhibition via Ce",
    pd_type="effect_compartment",
    monolix_equivalent="effectCpt_Imax",
    code=r"""
pd_effect_cmt_imax <- function() {
  ini({
    lke0  <- log(0.5);  label("Effect compartment equilibration rate (1/h)")
    lE0   <- log(100);  label("Baseline effect")
    lIC50 <- log(10);   label("IC50 (mg/L)")
    eta.E0 ~ 0.1
    add.sd <- 5
  })
  model({
    ke0  <- exp(lke0)
    E0   <- exp(lE0 + eta.E0)
    IC50 <- exp(lIC50)
    d/dt(Ce) = ke0 * (Cc - Ce)
    E = E0 * (1 - Ce / (IC50 + Ce))
    E ~ add(add.sd)
  })
}
""")

register_model(
    name="pd_effect_cmt_imax_partial",
    category="pd",
    description="Effect compartment partial Imax model — bounded inhibition via Ce",
    pd_type="effect_compartment",
    monolix_equivalent="effectCpt_Imax_partial",
    code=r"""
pd_effect_cmt_imax_partial <- function() {
  ini({
    lke0  <- log(0.5);    label("Effect compartment equilibration rate (1/h)")
    lE0   <- log(100);    label("Baseline effect")
    lImax <- logit(0.8);  label("Maximum fractional inhibition")
    lIC50 <- log(10);     label("IC50 (mg/L)")
    eta.E0 ~ 0.1
    add.sd <- 5
  })
  model({
    ke0  <- exp(lke0)
    E0   <- exp(lE0 + eta.E0)
    Imax <- expit(lImax)
    IC50 <- exp(lIC50)
    d/dt(Ce) = ke0 * (Cc - Ce)
    E = E0 * (1 - Imax * Ce / (IC50 + Ce))
    E ~ add(add.sd)
  })
}
""")
