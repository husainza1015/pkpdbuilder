"""1-Compartment PK Models — all Monolix equivalents translated to nlmixr2."""
from pkpdbuilder.models import register_model

# ═══════════════════════════════════════════════════════════
# 1-CMT ORAL — First-order absorption, linear elimination
# ═══════════════════════════════════════════════════════════

register_model(
    name="pk_1cmt_oral",
    category="pk",
    description="1-compartment, first-order oral absorption, linear elimination",
    route="oral", elimination="linear", compartments=1,
    monolix_equivalent="oral1_1cpt_kaVCl",
    code=r"""
pk_1cmt_oral <- function() {
  ini({
    lka  <- log(1);    label("Absorption rate constant (1/h)")
    lcl  <- log(5);    label("Clearance (L/h)")
    lv   <- log(50);   label("Volume of distribution (L)")
    eta.ka ~ 0.3
    eta.cl ~ 0.1
    eta.v  ~ 0.1
    prop.sd <- 0.2;    label("Proportional error")
  })
  model({
    ka <- exp(lka + eta.ka)
    cl <- exp(lcl + eta.cl)
    v  <- exp(lv  + eta.v)
    Cc <- linCmt()
    Cc ~ prop(prop.sd)
  })
}
""")

register_model(
    name="pk_1cmt_oral_tlag",
    category="pk",
    description="1-compartment, first-order oral absorption with lag time, linear elimination",
    route="oral", elimination="linear", compartments=1,
    monolix_equivalent="oral1_1cpt_TlagkaVCl",
    code=r"""
pk_1cmt_oral_tlag <- function() {
  ini({
    ltlag <- log(0.5); label("Absorption lag time (h)")
    lka   <- log(1);   label("Absorption rate constant (1/h)")
    lcl   <- log(5);   label("Clearance (L/h)")
    lv    <- log(50);  label("Volume of distribution (L)")
    eta.ka ~ 0.3
    eta.cl ~ 0.1
    eta.v  ~ 0.1
    prop.sd <- 0.2
  })
  model({
    tlag <- exp(ltlag)
    ka   <- exp(lka + eta.ka)
    cl   <- exp(lcl + eta.cl)
    v    <- exp(lv  + eta.v)
    alag(depot) <- tlag
    d/dt(depot)   = -ka * depot
    d/dt(central) =  ka * depot - cl/v * central
    Cc = central / v
    Cc ~ prop(prop.sd)
  })
}
""")

register_model(
    name="pk_1cmt_oral_zero_order",
    category="pk",
    description="1-compartment, zero-order oral absorption, linear elimination",
    route="oral", elimination="linear", compartments=1,
    monolix_equivalent="oral0_1cpt_TkVCl",
    code=r"""
pk_1cmt_oral_zero_order <- function() {
  ini({
    lTk  <- log(2);   label("Absorption duration (h)")
    lcl  <- log(5);   label("Clearance (L/h)")
    lv   <- log(50);  label("Volume of distribution (L)")
    eta.cl ~ 0.1
    eta.v  ~ 0.1
    prop.sd <- 0.2
  })
  model({
    Tk <- exp(lTk)
    cl <- exp(lcl + eta.cl)
    v  <- exp(lv  + eta.v)
    dur(depot) <- Tk
    d/dt(depot)   = -depot / Tk
    d/dt(central) =  depot / Tk - cl/v * central
    Cc = central / v
    Cc ~ prop(prop.sd)
  })
}
""")

register_model(
    name="pk_1cmt_oral_mm",
    category="pk",
    description="1-compartment, first-order oral absorption, Michaelis-Menten elimination",
    route="oral", elimination="michaelis-menten", compartments=1,
    monolix_equivalent="oral1_1cpt_kaVVmKm",
    code=r"""
pk_1cmt_oral_mm <- function() {
  ini({
    lka  <- log(1);    label("Absorption rate constant (1/h)")
    lVm  <- log(10);   label("Maximum elimination rate (mg/h)")
    lKm  <- log(5);    label("Michaelis-Menten constant (mg/L)")
    lv   <- log(50);   label("Volume of distribution (L)")
    eta.ka ~ 0.3
    eta.Vm ~ 0.1
    eta.v  ~ 0.1
    prop.sd <- 0.2
  })
  model({
    ka <- exp(lka + eta.ka)
    Vm <- exp(lVm + eta.Vm)
    Km <- exp(lKm)
    v  <- exp(lv  + eta.v)
    d/dt(depot)   = -ka * depot
    d/dt(central) =  ka * depot - (Vm * central/v) / (Km + central/v)
    Cc = central / v
    Cc ~ prop(prop.sd)
  })
}
""")

register_model(
    name="pk_1cmt_oral_mm_tlag",
    category="pk",
    description="1-compartment, first-order oral absorption with lag time, Michaelis-Menten elimination",
    route="oral", elimination="michaelis-menten", compartments=1,
    monolix_equivalent="oral1_1cpt_TlagkaVVmKm",
    code=r"""
pk_1cmt_oral_mm_tlag <- function() {
  ini({
    ltlag <- log(0.5); label("Absorption lag time (h)")
    lka   <- log(1);   label("Absorption rate constant (1/h)")
    lVm   <- log(10);  label("Maximum elimination rate (mg/h)")
    lKm   <- log(5);   label("Michaelis-Menten constant (mg/L)")
    lv    <- log(50);  label("Volume of distribution (L)")
    eta.ka ~ 0.3
    eta.Vm ~ 0.1
    eta.v  ~ 0.1
    prop.sd <- 0.2
  })
  model({
    tlag <- exp(ltlag)
    ka   <- exp(lka + eta.ka)
    Vm   <- exp(lVm + eta.Vm)
    Km   <- exp(lKm)
    v    <- exp(lv  + eta.v)
    alag(depot) <- tlag
    d/dt(depot)   = -ka * depot
    d/dt(central) =  ka * depot - (Vm * central/v) / (Km + central/v)
    Cc = central / v
    Cc ~ prop(prop.sd)
  })
}
""")

register_model(
    name="pk_1cmt_oral_mixed_elim",
    category="pk",
    description="1-compartment, first-order oral absorption, mixed linear + Michaelis-Menten elimination",
    route="oral", elimination="mixed", compartments=1,
    monolix_equivalent="oral1_1cpt_kaVClVmKm",
    code=r"""
pk_1cmt_oral_mixed_elim <- function() {
  ini({
    lka  <- log(1);    label("Absorption rate constant (1/h)")
    lcl  <- log(2);    label("Linear clearance (L/h)")
    lVm  <- log(10);   label("Maximum nonlinear elimination rate (mg/h)")
    lKm  <- log(5);    label("Michaelis-Menten constant (mg/L)")
    lv   <- log(50);   label("Volume of distribution (L)")
    eta.ka ~ 0.3
    eta.cl ~ 0.1
    eta.v  ~ 0.1
    prop.sd <- 0.2
  })
  model({
    ka <- exp(lka + eta.ka)
    cl <- exp(lcl + eta.cl)
    Vm <- exp(lVm)
    Km <- exp(lKm)
    v  <- exp(lv  + eta.v)
    d/dt(depot)   = -ka * depot
    d/dt(central) =  ka * depot - cl/v * central - (Vm * central/v) / (Km + central/v)
    Cc = central / v
    Cc ~ prop(prop.sd)
  })
}
""")

# ═══════════════════════════════════════════════════════════
# 1-CMT IV BOLUS
# ═══════════════════════════════════════════════════════════

register_model(
    name="pk_1cmt_iv_bolus",
    category="pk",
    description="1-compartment, IV bolus, linear elimination",
    route="iv_bolus", elimination="linear", compartments=1,
    monolix_equivalent="bolus_1cpt_VCl",
    code=r"""
pk_1cmt_iv_bolus <- function() {
  ini({
    lcl <- log(5);    label("Clearance (L/h)")
    lv  <- log(50);   label("Volume of distribution (L)")
    eta.cl ~ 0.1
    eta.v  ~ 0.1
    prop.sd <- 0.2
  })
  model({
    cl <- exp(lcl + eta.cl)
    v  <- exp(lv  + eta.v)
    Cc <- linCmt()
    Cc ~ prop(prop.sd)
  })
}
""")

register_model(
    name="pk_1cmt_iv_bolus_mm",
    category="pk",
    description="1-compartment, IV bolus, Michaelis-Menten elimination",
    route="iv_bolus", elimination="michaelis-menten", compartments=1,
    monolix_equivalent="bolus_1cpt_VVmKm",
    code=r"""
pk_1cmt_iv_bolus_mm <- function() {
  ini({
    lVm <- log(10);   label("Maximum elimination rate (mg/h)")
    lKm <- log(5);    label("Michaelis-Menten constant (mg/L)")
    lv  <- log(50);   label("Volume of distribution (L)")
    eta.Vm ~ 0.1
    eta.v  ~ 0.1
    prop.sd <- 0.2
  })
  model({
    Vm <- exp(lVm + eta.Vm)
    Km <- exp(lKm)
    v  <- exp(lv  + eta.v)
    d/dt(central) = -(Vm * central/v) / (Km + central/v)
    Cc = central / v
    Cc ~ prop(prop.sd)
  })
}
""")

# ═══════════════════════════════════════════════════════════
# 1-CMT IV INFUSION
# ═══════════════════════════════════════════════════════════

register_model(
    name="pk_1cmt_iv_infusion",
    category="pk",
    description="1-compartment, IV infusion, linear elimination",
    route="iv_infusion", elimination="linear", compartments=1,
    monolix_equivalent="infusion_1cpt_VCl",
    code=r"""
pk_1cmt_iv_infusion <- function() {
  ini({
    lcl <- log(5);    label("Clearance (L/h)")
    lv  <- log(50);   label("Volume of distribution (L)")
    eta.cl ~ 0.1
    eta.v  ~ 0.1
    prop.sd <- 0.2
  })
  model({
    cl <- exp(lcl + eta.cl)
    v  <- exp(lv  + eta.v)
    Cc <- linCmt()
    Cc ~ prop(prop.sd)
  })
}
""")

register_model(
    name="pk_1cmt_iv_infusion_mm",
    category="pk",
    description="1-compartment, IV infusion, Michaelis-Menten elimination",
    route="iv_infusion", elimination="michaelis-menten", compartments=1,
    monolix_equivalent="infusion_1cpt_VVmKm",
    code=r"""
pk_1cmt_iv_infusion_mm <- function() {
  ini({
    lVm <- log(10);   label("Maximum elimination rate (mg/h)")
    lKm <- log(5);    label("Michaelis-Menten constant (mg/L)")
    lv  <- log(50);   label("Volume of distribution (L)")
    eta.Vm ~ 0.1
    eta.v  ~ 0.1
    prop.sd <- 0.2
  })
  model({
    Vm <- exp(lVm + eta.Vm)
    Km <- exp(lKm)
    v  <- exp(lv  + eta.v)
    d/dt(central) = -(Vm * central/v) / (Km + central/v)
    Cc = central / v
    Cc ~ prop(prop.sd)
  })
}
""")
