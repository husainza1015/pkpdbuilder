"""Direct PD Models — Monolix equivalents translated to nlmixr2."""
from pkpdbuilder.models import register_model

register_model(
    name="pd_direct_emax",
    category="pd",
    description="Direct Emax model — stimulatory drug effect",
    route="", elimination="", compartments=0,
    pd_type="direct_emax",
    monolix_equivalent="direct_Emax",
    code=r"""
pd_direct_emax <- function() {
  ini({
    lE0   <- log(10);  label("Baseline effect")
    lEmax <- log(50);  label("Maximum drug effect")
    lEC50 <- log(5);   label("Concentration for 50% effect (mg/L)")
    eta.E0   ~ 0.1
    eta.Emax ~ 0.1
    add.sd <- 2
  })
  model({
    E0   <- exp(lE0   + eta.E0)
    Emax <- exp(lEmax + eta.Emax)
    EC50 <- exp(lEC50)
    E = E0 + Emax * Cc / (EC50 + Cc)
    E ~ add(add.sd)
  })
}
""")

register_model(
    name="pd_direct_emax_sigmoid",
    category="pd",
    description="Direct sigmoidal Emax model — with Hill coefficient",
    route="", elimination="", compartments=0,
    pd_type="direct_emax_sigmoid",
    monolix_equivalent="direct_Emax_sigmoid",
    code=r"""
pd_direct_emax_sigmoid <- function() {
  ini({
    lE0    <- log(10);  label("Baseline effect")
    lEmax  <- log(50);  label("Maximum drug effect")
    lEC50  <- log(5);   label("Concentration for 50% effect (mg/L)")
    lgamma <- log(1.5); label("Hill coefficient")
    eta.E0   ~ 0.1
    eta.Emax ~ 0.1
    add.sd <- 2
  })
  model({
    E0    <- exp(lE0   + eta.E0)
    Emax  <- exp(lEmax + eta.Emax)
    EC50  <- exp(lEC50)
    gamma <- exp(lgamma)
    E = E0 + Emax * Cc^gamma / (EC50^gamma + Cc^gamma)
    E ~ add(add.sd)
  })
}
""")

register_model(
    name="pd_direct_imax",
    category="pd",
    description="Direct Imax model — full inhibitory drug effect",
    route="", elimination="", compartments=0,
    pd_type="direct_imax",
    monolix_equivalent="direct_Imax",
    code=r"""
pd_direct_imax <- function() {
  ini({
    lE0   <- log(100); label("Baseline effect")
    lIC50 <- log(5);   label("Concentration for 50% inhibition (mg/L)")
    eta.E0 ~ 0.1
    add.sd <- 5
  })
  model({
    E0   <- exp(lE0 + eta.E0)
    IC50 <- exp(lIC50)
    E = E0 * (1 - Cc / (IC50 + Cc))
    E ~ add(add.sd)
  })
}
""")

register_model(
    name="pd_direct_imax_partial",
    category="pd",
    description="Direct partial Imax model — inhibition bounded by Imax < 1",
    route="", elimination="", compartments=0,
    pd_type="direct_imax_partial",
    monolix_equivalent="direct_Imax_partial",
    code=r"""
pd_direct_imax_partial <- function() {
  ini({
    lE0   <- log(100);    label("Baseline effect")
    lImax <- logit(0.8);  label("Maximum fractional inhibition")
    lIC50 <- log(5);      label("Concentration for 50% inhibition (mg/L)")
    eta.E0 ~ 0.1
    add.sd <- 5
  })
  model({
    E0   <- exp(lE0 + eta.E0)
    Imax <- expit(lImax)
    IC50 <- exp(lIC50)
    E = E0 * (1 - Imax * Cc / (IC50 + Cc))
    E ~ add(add.sd)
  })
}
""")

register_model(
    name="pd_direct_imax_sigmoid",
    category="pd",
    description="Direct sigmoidal Imax model — with Hill coefficient",
    route="", elimination="", compartments=0,
    pd_type="direct_imax_sigmoid",
    monolix_equivalent="direct_Imax_sigmoid",
    code=r"""
pd_direct_imax_sigmoid <- function() {
  ini({
    lE0    <- log(100);    label("Baseline effect")
    lImax  <- logit(0.9);  label("Maximum fractional inhibition")
    lIC50  <- log(5);      label("Concentration for 50% inhibition (mg/L)")
    lgamma <- log(1.5);    label("Hill coefficient")
    eta.E0 ~ 0.1
    add.sd <- 5
  })
  model({
    E0    <- exp(lE0 + eta.E0)
    Imax  <- expit(lImax)
    IC50  <- exp(lIC50)
    gamma <- exp(lgamma)
    E = E0 * (1 - Imax * Cc^gamma / (IC50^gamma + Cc^gamma))
    E ~ add(add.sd)
  })
}
""")

register_model(
    name="pd_linear",
    category="pd",
    description="Linear PD model — effect proportional to concentration",
    route="", elimination="", compartments=0,
    pd_type="linear",
    monolix_equivalent="linear",
    code=r"""
pd_linear <- function() {
  ini({
    lE0    <- log(10); label("Baseline effect")
    lslope <- log(2);  label("Slope (effect/concentration)")
    eta.E0 ~ 0.1
    add.sd <- 2
  })
  model({
    E0    <- exp(lE0 + eta.E0)
    slope <- exp(lslope)
    E = E0 + slope * Cc
    E ~ add(add.sd)
  })
}
""")
