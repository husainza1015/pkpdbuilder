"""Transit Absorption PK Models — Monolix equivalents translated to nlmixr2."""
from pkpdbuilder.models import register_model

register_model(
    name="pk_transit1_1cmt",
    category="pk",
    description="1 transit compartment + 1-CMT, first-order absorption, linear elimination",
    route="oral", elimination="linear", compartments=1,
    monolix_equivalent="transit1_1cpt",
    code=r"""
pk_transit1_1cmt <- function() {
  ini({
    lMTT <- log(1);   label("Mean transit time (h)")
    lka  <- log(1);   label("Absorption rate constant (1/h)")
    lcl  <- log(5);   label("Clearance (L/h)")
    lv   <- log(50);  label("Volume of distribution (L)")
    eta.MTT ~ 0.3
    eta.cl  ~ 0.1
    eta.v   ~ 0.1
    prop.sd <- 0.2
  })
  model({
    MTT <- exp(lMTT + eta.MTT)
    ka  <- exp(lka)
    cl  <- exp(lcl + eta.cl)
    v   <- exp(lv  + eta.v)
    ktr <- 2 / MTT
    d/dt(transit1) = -ktr * transit1
    d/dt(depot)    =  ktr * transit1 - ka * depot
    d/dt(central)  =  ka * depot - cl/v * central
    Cc = central / v
    Cc ~ prop(prop.sd)
  })
}
""")

register_model(
    name="pk_transit3_1cmt",
    category="pk",
    description="3 transit compartments + 1-CMT, first-order absorption, linear elimination",
    route="oral", elimination="linear", compartments=1,
    monolix_equivalent="transit3_1cpt",
    code=r"""
pk_transit3_1cmt <- function() {
  ini({
    lMTT <- log(1);   label("Mean transit time (h)")
    lka  <- log(1);   label("Absorption rate constant (1/h)")
    lcl  <- log(5);   label("Clearance (L/h)")
    lv   <- log(50);  label("Volume of distribution (L)")
    eta.MTT ~ 0.3
    eta.cl  ~ 0.1
    eta.v   ~ 0.1
    prop.sd <- 0.2
  })
  model({
    MTT <- exp(lMTT + eta.MTT)
    ka  <- exp(lka)
    cl  <- exp(lcl + eta.cl)
    v   <- exp(lv  + eta.v)
    ktr <- 4 / MTT  # (n+1)/MTT where n=3
    d/dt(transit1) = -ktr * transit1
    d/dt(transit2) =  ktr * transit1 - ktr * transit2
    d/dt(transit3) =  ktr * transit2 - ktr * transit3
    d/dt(depot)    =  ktr * transit3 - ka * depot
    d/dt(central)  =  ka * depot - cl/v * central
    Cc = central / v
    Cc ~ prop(prop.sd)
  })
}
""")

register_model(
    name="pk_transit5_1cmt",
    category="pk",
    description="5 transit compartments + 1-CMT, first-order absorption, linear elimination",
    route="oral", elimination="linear", compartments=1,
    monolix_equivalent="transitN_1cpt (N=5)",
    code=r"""
pk_transit5_1cmt <- function() {
  ini({
    lMTT <- log(1);   label("Mean transit time (h)")
    lka  <- log(1);   label("Absorption rate constant (1/h)")
    lcl  <- log(5);   label("Clearance (L/h)")
    lv   <- log(50);  label("Volume of distribution (L)")
    eta.MTT ~ 0.3
    eta.cl  ~ 0.1
    eta.v   ~ 0.1
    prop.sd <- 0.2
  })
  model({
    MTT <- exp(lMTT + eta.MTT)
    ka  <- exp(lka)
    cl  <- exp(lcl + eta.cl)
    v   <- exp(lv  + eta.v)
    ktr <- 6 / MTT
    d/dt(transit1) = -ktr * transit1
    d/dt(transit2) =  ktr * transit1 - ktr * transit2
    d/dt(transit3) =  ktr * transit2 - ktr * transit3
    d/dt(transit4) =  ktr * transit3 - ktr * transit4
    d/dt(transit5) =  ktr * transit4 - ktr * transit5
    d/dt(depot)    =  ktr * transit5 - ka * depot
    d/dt(central)  =  ka * depot - cl/v * central
    Cc = central / v
    Cc ~ prop(prop.sd)
  })
}
""")

register_model(
    name="pk_transit3_2cmt",
    category="pk",
    description="3 transit compartments + 2-CMT, first-order absorption, linear elimination",
    route="oral", elimination="linear", compartments=2,
    monolix_equivalent="transit3_2cpt",
    code=r"""
pk_transit3_2cmt <- function() {
  ini({
    lMTT <- log(1);   label("Mean transit time (h)")
    lka  <- log(1);   label("Absorption rate constant (1/h)")
    lcl  <- log(5);   label("Clearance (L/h)")
    lv   <- log(50);  label("Central volume (L)")
    lv2  <- log(30);  label("Peripheral volume (L)")
    lq   <- log(3);   label("Intercompartmental clearance (L/h)")
    eta.MTT ~ 0.3
    eta.cl  ~ 0.1
    eta.v   ~ 0.1
    prop.sd <- 0.2
  })
  model({
    MTT <- exp(lMTT + eta.MTT)
    ka  <- exp(lka)
    cl  <- exp(lcl + eta.cl)
    v   <- exp(lv  + eta.v)
    v2  <- exp(lv2)
    q   <- exp(lq)
    ktr <- 4 / MTT
    d/dt(transit1)   = -ktr * transit1
    d/dt(transit2)   =  ktr * transit1 - ktr * transit2
    d/dt(transit3)   =  ktr * transit2 - ktr * transit3
    d/dt(depot)      =  ktr * transit3 - ka * depot
    d/dt(central)    =  ka * depot - (cl/v + q/v) * central + q/v2 * peripheral
    d/dt(peripheral) =  q/v * central - q/v2 * peripheral
    Cc = central / v
    Cc ~ prop(prop.sd)
  })
}
""")

register_model(
    name="pk_double_abs_1cmt",
    category="pk",
    description="Double absorption (first-order + zero-order parallel) + 1-CMT, linear elimination",
    route="oral", elimination="linear", compartments=1,
    monolix_equivalent="oral1_oral0_1cpt",
    code=r"""
pk_double_abs_1cmt <- function() {
  ini({
    lka   <- log(1);   label("First-order absorption rate (1/h)")
    lTk   <- log(2);   label("Zero-order absorption duration (h)")
    lFr   <- logit(0.6); label("Fraction via first-order route")
    lcl   <- log(5);   label("Clearance (L/h)")
    lv    <- log(50);  label("Volume of distribution (L)")
    eta.ka ~ 0.3
    eta.cl ~ 0.1
    eta.v  ~ 0.1
    prop.sd <- 0.2
  })
  model({
    ka  <- exp(lka + eta.ka)
    Tk  <- exp(lTk)
    Fr  <- expit(lFr)
    cl  <- exp(lcl + eta.cl)
    v   <- exp(lv  + eta.v)
    f(depot1)  <- Fr
    f(depot2)  <- 1 - Fr
    dur(depot2) <- Tk
    d/dt(depot1)  = -ka * depot1
    d/dt(depot2)  = -depot2 / Tk
    d/dt(central) =  ka * depot1 + depot2/Tk - cl/v * central
    Cc = central / v
    Cc ~ prop(prop.sd)
  })
}
""")
