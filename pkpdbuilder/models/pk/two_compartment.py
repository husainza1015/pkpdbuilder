"""2-Compartment PK Models — all Monolix equivalents translated to nlmixr2."""
from pkpdbuilder.models import register_model

# ═══════════════════════════════════════════════════════════
# 2-CMT ORAL
# ═══════════════════════════════════════════════════════════

register_model(
    name="pk_2cmt_oral",
    category="pk",
    description="2-compartment, first-order oral absorption, linear elimination",
    route="oral", elimination="linear", compartments=2,
    monolix_equivalent="oral1_2cpt_kaVClV2Q",
    code=r"""
pk_2cmt_oral <- function() {
  ini({
    lka  <- log(1);    label("Absorption rate constant (1/h)")
    lcl  <- log(5);    label("Clearance (L/h)")
    lv   <- log(50);   label("Central volume (L)")
    lv2  <- log(30);   label("Peripheral volume (L)")
    lq   <- log(3);    label("Intercompartmental clearance (L/h)")
    eta.ka ~ 0.3
    eta.cl ~ 0.1
    eta.v  ~ 0.1
    prop.sd <- 0.2
  })
  model({
    ka <- exp(lka + eta.ka)
    cl <- exp(lcl + eta.cl)
    v  <- exp(lv  + eta.v)
    v2 <- exp(lv2)
    q  <- exp(lq)
    Cc <- linCmt()
    Cc ~ prop(prop.sd)
  })
}
""")

register_model(
    name="pk_2cmt_oral_tlag",
    category="pk",
    description="2-compartment, first-order oral absorption with lag time, linear elimination",
    route="oral", elimination="linear", compartments=2,
    monolix_equivalent="oral1_2cpt_TlagkaVClV2Q",
    code=r"""
pk_2cmt_oral_tlag <- function() {
  ini({
    ltlag <- log(0.5); label("Absorption lag time (h)")
    lka   <- log(1);   label("Absorption rate constant (1/h)")
    lcl   <- log(5);   label("Clearance (L/h)")
    lv    <- log(50);  label("Central volume (L)")
    lv2   <- log(30);  label("Peripheral volume (L)")
    lq    <- log(3);   label("Intercompartmental clearance (L/h)")
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
    v2   <- exp(lv2)
    q    <- exp(lq)
    alag(depot) <- tlag
    d/dt(depot)      = -ka * depot
    d/dt(central)    =  ka * depot - (cl/v + q/v) * central + q/v2 * peripheral
    d/dt(peripheral) =  q/v * central - q/v2 * peripheral
    Cc = central / v
    Cc ~ prop(prop.sd)
  })
}
""")

register_model(
    name="pk_2cmt_oral_mm",
    category="pk",
    description="2-compartment, first-order oral absorption, Michaelis-Menten elimination",
    route="oral", elimination="michaelis-menten", compartments=2,
    monolix_equivalent="oral1_2cpt_kaVClV2QVmKm",
    code=r"""
pk_2cmt_oral_mm <- function() {
  ini({
    lka  <- log(1);    label("Absorption rate constant (1/h)")
    lVm  <- log(10);   label("Maximum elimination rate (mg/h)")
    lKm  <- log(5);    label("Michaelis-Menten constant (mg/L)")
    lv   <- log(50);   label("Central volume (L)")
    lv2  <- log(30);   label("Peripheral volume (L)")
    lq   <- log(3);    label("Intercompartmental clearance (L/h)")
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
    v2 <- exp(lv2)
    q  <- exp(lq)
    d/dt(depot)      = -ka * depot
    d/dt(central)    =  ka * depot - (Vm * central/v)/(Km + central/v) - q/v * central + q/v2 * peripheral
    d/dt(peripheral) =  q/v * central - q/v2 * peripheral
    Cc = central / v
    Cc ~ prop(prop.sd)
  })
}
""")

# ═══════════════════════════════════════════════════════════
# 2-CMT IV BOLUS
# ═══════════════════════════════════════════════════════════

register_model(
    name="pk_2cmt_iv_bolus",
    category="pk",
    description="2-compartment, IV bolus, linear elimination",
    route="iv_bolus", elimination="linear", compartments=2,
    monolix_equivalent="bolus_2cpt_VClV2Q",
    code=r"""
pk_2cmt_iv_bolus <- function() {
  ini({
    lcl  <- log(5);    label("Clearance (L/h)")
    lv   <- log(50);   label("Central volume (L)")
    lv2  <- log(30);   label("Peripheral volume (L)")
    lq   <- log(3);    label("Intercompartmental clearance (L/h)")
    eta.cl ~ 0.1
    eta.v  ~ 0.1
    prop.sd <- 0.2
  })
  model({
    cl <- exp(lcl + eta.cl)
    v  <- exp(lv  + eta.v)
    v2 <- exp(lv2)
    q  <- exp(lq)
    Cc <- linCmt()
    Cc ~ prop(prop.sd)
  })
}
""")

register_model(
    name="pk_2cmt_iv_bolus_mm",
    category="pk",
    description="2-compartment, IV bolus, mixed linear + Michaelis-Menten elimination",
    route="iv_bolus", elimination="mixed", compartments=2,
    monolix_equivalent="bolus_2cpt_VClV2QVmKm",
    code=r"""
pk_2cmt_iv_bolus_mm <- function() {
  ini({
    lcl  <- log(2);    label("Linear clearance (L/h)")
    lVm  <- log(10);   label("Maximum nonlinear elimination rate (mg/h)")
    lKm  <- log(5);    label("Michaelis-Menten constant (mg/L)")
    lv   <- log(50);   label("Central volume (L)")
    lv2  <- log(30);   label("Peripheral volume (L)")
    lq   <- log(3);    label("Intercompartmental clearance (L/h)")
    eta.cl ~ 0.1
    eta.v  ~ 0.1
    prop.sd <- 0.2
  })
  model({
    cl <- exp(lcl + eta.cl)
    Vm <- exp(lVm)
    Km <- exp(lKm)
    v  <- exp(lv  + eta.v)
    v2 <- exp(lv2)
    q  <- exp(lq)
    d/dt(central)    = -cl/v * central - (Vm * central/v)/(Km + central/v) - q/v * central + q/v2 * peripheral
    d/dt(peripheral) =  q/v * central - q/v2 * peripheral
    Cc = central / v
    Cc ~ prop(prop.sd)
  })
}
""")

# ═══════════════════════════════════════════════════════════
# 2-CMT IV INFUSION
# ═══════════════════════════════════════════════════════════

register_model(
    name="pk_2cmt_iv_infusion",
    category="pk",
    description="2-compartment, IV infusion, linear elimination",
    route="iv_infusion", elimination="linear", compartments=2,
    monolix_equivalent="infusion_2cpt_VClV2Q",
    code=r"""
pk_2cmt_iv_infusion <- function() {
  ini({
    lcl  <- log(5);    label("Clearance (L/h)")
    lv   <- log(50);   label("Central volume (L)")
    lv2  <- log(30);   label("Peripheral volume (L)")
    lq   <- log(3);    label("Intercompartmental clearance (L/h)")
    eta.cl ~ 0.1
    eta.v  ~ 0.1
    prop.sd <- 0.2
  })
  model({
    cl <- exp(lcl + eta.cl)
    v  <- exp(lv  + eta.v)
    v2 <- exp(lv2)
    q  <- exp(lq)
    Cc <- linCmt()
    Cc ~ prop(prop.sd)
  })
}
""")
