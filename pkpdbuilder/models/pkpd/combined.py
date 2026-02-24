"""Combined PK/PD Models — Monolix equivalents translated to nlmixr2."""
from pkpdbuilder.models import register_model

register_model(
    name="pkpd_1cmt_oral_direct_emax",
    category="pkpd",
    description="1-CMT oral PK + direct Emax PD — simultaneous PK/PD fitting",
    route="oral", compartments=1, pd_type="direct_emax",
    monolix_equivalent="oral1_1cpt_kaVCl_direct_Emax",
    code=r"""
pkpd_1cmt_oral_direct_emax <- function() {
  ini({
    lka   <- log(1);   label("Absorption rate constant (1/h)")
    lcl   <- log(5);   label("Clearance (L/h)")
    lv    <- log(50);  label("Volume (L)")
    lE0   <- log(10);  label("Baseline effect")
    lEmax <- log(50);  label("Maximum drug effect")
    lEC50 <- log(5);   label("EC50 (mg/L)")
    eta.ka   ~ 0.3
    eta.cl   ~ 0.1
    eta.v    ~ 0.1
    eta.E0   ~ 0.1
    eta.Emax ~ 0.1
    prop.sd.pk <- 0.2
    add.sd.pd  <- 5
  })
  model({
    ka   <- exp(lka  + eta.ka)
    cl   <- exp(lcl  + eta.cl)
    v    <- exp(lv   + eta.v)
    E0   <- exp(lE0  + eta.E0)
    Emax <- exp(lEmax + eta.Emax)
    EC50 <- exp(lEC50)
    d/dt(depot)   = -ka * depot
    d/dt(central) =  ka * depot - cl/v * central
    Cc = central / v
    E  = E0 + Emax * Cc / (EC50 + Cc)
    Cc ~ prop(prop.sd.pk)
    E  ~ add(add.sd.pd)
  })
}
""")

register_model(
    name="pkpd_1cmt_oral_effect_cmt_emax",
    category="pkpd",
    description="1-CMT oral PK + effect compartment Emax PD — hysteresis model",
    route="oral", compartments=1, pd_type="effect_compartment",
    monolix_equivalent="oral1_1cpt_kaVCl_effectCpt_Emax",
    code=r"""
pkpd_1cmt_oral_effect_cmt_emax <- function() {
  ini({
    lka   <- log(1);   label("Absorption rate constant (1/h)")
    lcl   <- log(5);   label("Clearance (L/h)")
    lv    <- log(50);  label("Volume (L)")
    lke0  <- log(0.5); label("Effect compartment rate (1/h)")
    lE0   <- log(10);  label("Baseline effect")
    lEmax <- log(50);  label("Maximum drug effect")
    lEC50 <- log(5);   label("EC50 (mg/L)")
    eta.ka   ~ 0.3
    eta.cl   ~ 0.1
    eta.v    ~ 0.1
    eta.E0   ~ 0.1
    prop.sd.pk <- 0.2
    add.sd.pd  <- 5
  })
  model({
    ka   <- exp(lka  + eta.ka)
    cl   <- exp(lcl  + eta.cl)
    v    <- exp(lv   + eta.v)
    ke0  <- exp(lke0)
    E0   <- exp(lE0  + eta.E0)
    Emax <- exp(lEmax)
    EC50 <- exp(lEC50)
    d/dt(depot)   = -ka * depot
    d/dt(central) =  ka * depot - cl/v * central
    d/dt(Ce)      =  ke0 * (central/v - Ce)
    Cc = central / v
    E  = E0 + Emax * Ce / (EC50 + Ce)
    Cc ~ prop(prop.sd.pk)
    E  ~ add(add.sd.pd)
  })
}
""")

register_model(
    name="pkpd_1cmt_oral_idr1",
    category="pkpd",
    description="1-CMT oral PK + IDR Type I (inhibition of kin) — turnover model",
    route="oral", compartments=1, pd_type="idr_type1",
    monolix_equivalent="oral1_1cpt_kaVCl_turnover_kin_Imax",
    code=r"""
pkpd_1cmt_oral_idr1 <- function() {
  ini({
    lka   <- log(1);      label("Absorption rate constant (1/h)")
    lcl   <- log(5);      label("Clearance (L/h)")
    lv    <- log(50);     label("Volume (L)")
    lR0   <- log(100);    label("Baseline response")
    lkout <- log(0.1);    label("Response elimination rate (1/h)")
    lIC50 <- log(10);     label("IC50 (mg/L)")
    lImax <- logit(0.9);  label("Maximum inhibition fraction")
    eta.ka   ~ 0.3
    eta.cl   ~ 0.1
    eta.R0   ~ 0.1
    eta.IC50 ~ 0.1
    prop.sd.pk <- 0.2
    add.sd.pd  <- 5
  })
  model({
    ka   <- exp(lka  + eta.ka)
    cl   <- exp(lcl  + eta.cl)
    v    <- exp(lv)
    R0   <- exp(lR0  + eta.R0)
    kout <- exp(lkout)
    kin  <- R0 * kout
    IC50 <- exp(lIC50 + eta.IC50)
    Imax <- expit(lImax)
    d/dt(depot)    = -ka * depot
    d/dt(central)  =  ka * depot - cl/v * central
    d/dt(response) =  kin * (1 - Imax * Cc / (IC50 + Cc)) - kout * response
    response(0) <- R0
    Cc = central / v
    R  = response
    Cc ~ prop(prop.sd.pk)
    R  ~ add(add.sd.pd)
  })
}
""")

register_model(
    name="pkpd_2cmt_iv_idr3",
    category="pkpd",
    description="2-CMT IV PK + IDR Type III (stimulation of kin) — mAb/biologic PK/PD",
    route="iv_infusion", compartments=2, pd_type="idr_type3",
    monolix_equivalent="infusion_2cpt_VClV2Q_turnover_kin_Emax",
    code=r"""
pkpd_2cmt_iv_idr3 <- function() {
  ini({
    lcl   <- log(0.2);   label("Clearance (L/day)")
    lv    <- log(3);      label("Central volume (L)")
    lv2   <- log(2);      label("Peripheral volume (L)")
    lq    <- log(0.5);    label("Intercompartmental clearance (L/day)")
    lR0   <- log(100);    label("Baseline response")
    lkout <- log(0.05);   label("Response elimination rate (1/day)")
    lEmax <- log(3);      label("Maximum stimulation fold")
    lEC50 <- log(10);     label("EC50 (mg/L)")
    eta.cl   ~ 0.1
    eta.v    ~ 0.1
    eta.R0   ~ 0.1
    prop.sd.pk <- 0.15
    add.sd.pd  <- 10
  })
  model({
    cl   <- exp(lcl  + eta.cl)
    v    <- exp(lv   + eta.v)
    v2   <- exp(lv2)
    q    <- exp(lq)
    R0   <- exp(lR0  + eta.R0)
    kout <- exp(lkout)
    kin  <- R0 * kout
    Emax <- exp(lEmax)
    EC50 <- exp(lEC50)
    d/dt(central)    = -(cl/v + q/v) * central + q/v2 * peripheral
    d/dt(peripheral) =  q/v * central - q/v2 * peripheral
    d/dt(response)   =  kin * (1 + Emax * Cc / (EC50 + Cc)) - kout * response
    response(0) <- R0
    Cc = central / v
    R  = response
    Cc ~ prop(prop.sd.pk)
    R  ~ add(add.sd.pd)
  })
}
""")

register_model(
    name="pkpd_1cmt_oral_idr4",
    category="pkpd",
    description="1-CMT oral PK + IDR Type IV (stimulation of kout) — e.g., warfarin PD",
    route="oral", compartments=1, pd_type="idr_type4",
    monolix_equivalent="oral1_1cpt_kaVCl_turnover_kout_Emax",
    code=r"""
pkpd_1cmt_oral_idr4 <- function() {
  ini({
    lka   <- log(1);     label("Absorption rate constant (1/h)")
    lcl   <- log(5);     label("Clearance (L/h)")
    lv    <- log(50);    label("Volume (L)")
    lR0   <- log(100);   label("Baseline response")
    lkout <- log(0.1);   label("Response elimination rate (1/h)")
    lEmax <- log(2);     label("Maximum stimulation of degradation")
    lEC50 <- log(10);    label("EC50 (mg/L)")
    eta.ka   ~ 0.3
    eta.cl   ~ 0.1
    eta.R0   ~ 0.1
    prop.sd.pk <- 0.2
    add.sd.pd  <- 5
  })
  model({
    ka   <- exp(lka  + eta.ka)
    cl   <- exp(lcl  + eta.cl)
    v    <- exp(lv)
    R0   <- exp(lR0  + eta.R0)
    kout <- exp(lkout)
    kin  <- R0 * kout
    Emax <- exp(lEmax)
    EC50 <- exp(lEC50)
    d/dt(depot)    = -ka * depot
    d/dt(central)  =  ka * depot - cl/v * central
    d/dt(response) =  kin - kout * (1 + Emax * Cc / (EC50 + Cc)) * response
    response(0) <- R0
    Cc = central / v
    R  = response
    Cc ~ prop(prop.sd.pk)
    R  ~ add(add.sd.pd)
  })
}
""")
