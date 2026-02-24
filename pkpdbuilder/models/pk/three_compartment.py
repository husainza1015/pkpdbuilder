"""3-Compartment PK Models — Monolix equivalents translated to nlmixr2."""
from pkpdbuilder.models import register_model

register_model(
    name="pk_3cmt_oral",
    category="pk",
    description="3-compartment, first-order oral absorption, linear elimination",
    route="oral", elimination="linear", compartments=3,
    monolix_equivalent="oral1_3cpt_kaVClV2QV3Q2",
    code=r"""
pk_3cmt_oral <- function() {
  ini({
    lka  <- log(1);    label("Absorption rate constant (1/h)")
    lcl  <- log(5);    label("Clearance (L/h)")
    lv   <- log(50);   label("Central volume (L)")
    lv2  <- log(30);   label("Shallow peripheral volume (L)")
    lq   <- log(3);    label("Intercompartmental clearance Q (L/h)")
    lv3  <- log(20);   label("Deep peripheral volume (L)")
    lq2  <- log(1);    label("Intercompartmental clearance Q2 (L/h)")
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
    v3 <- exp(lv3)
    q2 <- exp(lq2)
    Cc <- linCmt()
    Cc ~ prop(prop.sd)
  })
}
""")

register_model(
    name="pk_3cmt_oral_tlag",
    category="pk",
    description="3-compartment, first-order oral absorption with lag time, linear elimination",
    route="oral", elimination="linear", compartments=3,
    monolix_equivalent="oral1_3cpt_TlagkaVClV2QV3Q2",
    code=r"""
pk_3cmt_oral_tlag <- function() {
  ini({
    ltlag <- log(0.5); label("Absorption lag time (h)")
    lka   <- log(1);   label("Absorption rate constant (1/h)")
    lcl   <- log(5);   label("Clearance (L/h)")
    lv    <- log(50);  label("Central volume (L)")
    lv2   <- log(30);  label("Shallow peripheral volume (L)")
    lq    <- log(3);   label("Intercompartmental clearance Q (L/h)")
    lv3   <- log(20);  label("Deep peripheral volume (L)")
    lq2   <- log(1);   label("Intercompartmental clearance Q2 (L/h)")
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
    v3   <- exp(lv3)
    q2   <- exp(lq2)
    alag(depot) <- tlag
    d/dt(depot)       = -ka * depot
    d/dt(central)     =  ka * depot - (cl/v + q/v + q2/v) * central + q/v2 * periph1 + q2/v3 * periph2
    d/dt(periph1)     =  q/v * central - q/v2 * periph1
    d/dt(periph2)     =  q2/v * central - q2/v3 * periph2
    Cc = central / v
    Cc ~ prop(prop.sd)
  })
}
""")

register_model(
    name="pk_3cmt_iv_bolus",
    category="pk",
    description="3-compartment, IV bolus, linear elimination",
    route="iv_bolus", elimination="linear", compartments=3,
    monolix_equivalent="bolus_3cpt_VClV2QV3Q2",
    code=r"""
pk_3cmt_iv_bolus <- function() {
  ini({
    lcl  <- log(5);    label("Clearance (L/h)")
    lv   <- log(50);   label("Central volume (L)")
    lv2  <- log(30);   label("Shallow peripheral volume (L)")
    lq   <- log(3);    label("Intercompartmental clearance Q (L/h)")
    lv3  <- log(20);   label("Deep peripheral volume (L)")
    lq2  <- log(1);    label("Intercompartmental clearance Q2 (L/h)")
    eta.cl ~ 0.1
    eta.v  ~ 0.1
    prop.sd <- 0.2
  })
  model({
    cl <- exp(lcl + eta.cl)
    v  <- exp(lv  + eta.v)
    v2 <- exp(lv2)
    q  <- exp(lq)
    v3 <- exp(lv3)
    q2 <- exp(lq2)
    Cc <- linCmt()
    Cc ~ prop(prop.sd)
  })
}
""")

register_model(
    name="pk_3cmt_iv_infusion",
    category="pk",
    description="3-compartment, IV infusion, linear elimination",
    route="iv_infusion", elimination="linear", compartments=3,
    monolix_equivalent="infusion_3cpt_VClV2QV3Q2",
    code=r"""
pk_3cmt_iv_infusion <- function() {
  ini({
    lcl  <- log(5);    label("Clearance (L/h)")
    lv   <- log(50);   label("Central volume (L)")
    lv2  <- log(30);   label("Shallow peripheral volume (L)")
    lq   <- log(3);    label("Intercompartmental clearance Q (L/h)")
    lv3  <- log(20);   label("Deep peripheral volume (L)")
    lq2  <- log(1);    label("Intercompartmental clearance Q2 (L/h)")
    eta.cl ~ 0.1
    eta.v  ~ 0.1
    prop.sd <- 0.2
  })
  model({
    cl <- exp(lcl + eta.cl)
    v  <- exp(lv  + eta.v)
    v2 <- exp(lv2)
    q  <- exp(lq)
    v3 <- exp(lv3)
    q2 <- exp(lq2)
    Cc <- linCmt()
    Cc ~ prop(prop.sd)
  })
}
""")
