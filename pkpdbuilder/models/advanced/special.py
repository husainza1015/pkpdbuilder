"""Advanced/Special Models — TTE, Count, Parent-Metabolite, allometric."""
from pkpdbuilder.models import register_model

register_model(
    name="pk_1cmt_oral_allometric",
    category="pk",
    description="1-CMT oral with allometric scaling on WT — CL~WT^0.75, V~WT^1.0",
    route="oral", elimination="linear", compartments=1,
    monolix_equivalent="oral1_1cpt with allometric covariates",
    code=r"""
pk_1cmt_oral_allometric <- function() {
  ini({
    lka  <- log(1);   label("Absorption rate constant (1/h)")
    lcl  <- log(5);   label("Clearance at 70 kg (L/h)")
    lv   <- log(50);  label("Volume at 70 kg (L)")
    eta.ka ~ 0.3
    eta.cl ~ 0.1
    eta.v  ~ 0.1
    prop.sd <- 0.2
  })
  model({
    ka <- exp(lka + eta.ka)
    cl <- exp(lcl + eta.cl) * (WT/70)^0.75
    v  <- exp(lv  + eta.v)  * (WT/70)^1.0
    d/dt(depot)   = -ka * depot
    d/dt(central) =  ka * depot - cl/v * central
    Cc = central / v
    Cc ~ prop(prop.sd)
  })
}
""")

register_model(
    name="pk_parent_metabolite_1cmt",
    category="pk",
    description="Parent + metabolite model — both 1-CMT, sequential metabolism",
    route="oral", elimination="linear", compartments=1,
    monolix_equivalent="parent_metabolite_1cpt",
    code=r"""
pk_parent_metabolite_1cmt <- function() {
  ini({
    lka   <- log(1);     label("Parent absorption rate (1/h)")
    lcl_p <- log(5);     label("Parent clearance (L/h)")
    lv_p  <- log(50);    label("Parent volume (L)")
    lfm   <- logit(0.5); label("Fraction metabolized")
    lcl_m <- log(10);    label("Metabolite clearance (L/h)")
    lv_m  <- log(30);    label("Metabolite volume (L)")
    eta.cl_p ~ 0.1
    eta.cl_m ~ 0.1
    prop.sd.p <- 0.2
    prop.sd.m <- 0.25
  })
  model({
    ka   <- exp(lka)
    cl_p <- exp(lcl_p + eta.cl_p)
    v_p  <- exp(lv_p)
    fm   <- expit(lfm)
    cl_m <- exp(lcl_m + eta.cl_m)
    v_m  <- exp(lv_m)
    d/dt(depot)    = -ka * depot
    d/dt(parent)   =  ka * depot - cl_p/v_p * parent
    d/dt(metabol)  =  fm * cl_p/v_p * parent * v_p/v_m - cl_m/v_m * metabol
    Cp = parent  / v_p
    Cm = metabol / v_m
    Cp ~ prop(prop.sd.p)
    Cm ~ prop(prop.sd.m)
  })
}
""")

register_model(
    name="tte_weibull",
    category="advanced",
    description="Time-to-event model with Weibull hazard — h(t) = (beta/alpha)*(t/alpha)^(beta-1)",
    pd_type="time_to_event",
    monolix_equivalent="weibull_hazard",
    code=r"""
# NOTE: TTE models in nlmixr2 require special handling via rxode2
# This provides the hazard/survival functions for manual implementation
tte_weibull <- function() {
  ini({
    lalpha <- log(100);  label("Scale parameter (h)")
    lbeta  <- log(1.5);  label("Shape parameter")
    lHR    <- log(0.5);  label("Hazard ratio for drug effect")
    eta.alpha ~ 0.1
  })
  model({
    alpha <- exp(lalpha + eta.alpha)
    beta  <- exp(lbeta)
    HR    <- exp(lHR)
    # Hazard function
    h = (beta/alpha) * (TIME/alpha)^(beta-1) * HR^DRUG
    # Cumulative hazard
    H = (TIME/alpha)^beta * HR^DRUG
    # Survival
    S = exp(-H)
  })
}
""")

register_model(
    name="count_poisson",
    category="advanced",
    description="Count data model — Poisson distribution with drug effect on rate",
    pd_type="count",
    monolix_equivalent="poisson",
    code=r"""
# NOTE: Count models use family = poisson() in nlmixr2
count_poisson <- function() {
  ini({
    llambda0 <- log(5);   label("Baseline event rate")
    lEC50    <- log(10);   label("EC50 for rate reduction (mg/L)")
    lImax    <- logit(0.8); label("Maximum rate reduction")
    eta.lambda ~ 0.2
  })
  model({
    lambda0 <- exp(llambda0 + eta.lambda)
    EC50    <- exp(lEC50)
    Imax    <- expit(lImax)
    lambda  <- lambda0 * (1 - Imax * Cc / (IC50 + Cc))
    Y ~ dpois(lambda)
  })
}
""")

register_model(
    name="pk_2cmt_iv_mab",
    category="pk",
    description="2-CMT IV model parameterized for monoclonal antibodies — typical mAb PK",
    route="iv_infusion", elimination="linear", compartments=2,
    monolix_equivalent="infusion_2cpt_VClV2Q (mAb parameterization)",
    code=r"""
pk_2cmt_iv_mab <- function() {
  ini({
    lcl  <- log(0.2);    label("Clearance (L/day)")
    lv   <- log(3.5);    label("Central volume (L)")
    lv2  <- log(2.8);    label("Peripheral volume (L)")
    lq   <- log(0.5);    label("Intercompartmental clearance (L/day)")
    eta.cl ~ 0.15
    eta.v  ~ 0.10
    eta.v2 ~ 0.10
    prop.sd <- 0.15
  })
  model({
    cl <- exp(lcl + eta.cl) * (WT/70)^0.75
    v  <- exp(lv  + eta.v)  * (WT/70)^1.0
    v2 <- exp(lv2 + eta.v2) * (WT/70)^1.0
    q  <- exp(lq)
    Cc <- linCmt()
    Cc ~ prop(prop.sd)
  })
}
""")
