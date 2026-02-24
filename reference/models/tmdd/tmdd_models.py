"""TMDD Models — Monolix equivalents translated to nlmixr2."""
from pkpdbuilder.models import register_model

register_model(
    name="tmdd_full_1cmt",
    category="tmdd",
    description="Full TMDD model — 1-compartment with ligand-receptor binding kinetics",
    route="iv_bolus", compartments=1,
    monolix_equivalent="TMDD_full",
    code=r"""
tmdd_full_1cmt <- function() {
  ini({
    lv    <- log(50);   label("Volume of distribution (L)")
    lkel  <- log(0.1);  label("Ligand elimination rate (1/h)")
    lkon  <- log(0.1);  label("Association rate (1/nM/h)")
    lkoff <- log(0.01); label("Dissociation rate (1/h)")
    lksyn <- log(1);    label("Receptor synthesis rate (nM/h)")
    lkdeg <- log(0.1);  label("Receptor degradation rate (1/h)")
    lkint <- log(0.05); label("Complex internalization rate (1/h)")
    eta.v    ~ 0.1
    eta.ksyn ~ 0.1
    prop.sd <- 0.2
  })
  model({
    v    <- exp(lv   + eta.v)
    kel  <- exp(lkel)
    kon  <- exp(lkon)
    koff <- exp(lkoff)
    ksyn <- exp(lksyn + eta.ksyn)
    kdeg <- exp(lkdeg)
    kint <- exp(lkint)
    R0   <- ksyn / kdeg
    R(0) <- R0
    d/dt(L)  = -kon*L*R + koff*RL - kel*L
    d/dt(R)  =  ksyn - kdeg*R - kon*L*R + koff*RL
    d/dt(RL) =  kon*L*R - koff*RL - kint*RL
    Cc = L
    Cc ~ prop(prop.sd)
  })
}
""")

register_model(
    name="tmdd_qss_1cmt",
    category="tmdd",
    description="TMDD QSS approximation — 1-compartment, quasi-steady-state",
    route="iv_bolus", compartments=1,
    monolix_equivalent="TMDD_QSS",
    code=r"""
tmdd_qss_1cmt <- function() {
  ini({
    lv    <- log(50);   label("Volume of distribution (L)")
    lkel  <- log(0.1);  label("Ligand elimination rate (1/h)")
    lksyn <- log(1);    label("Receptor synthesis rate (nM/h)")
    lkdeg <- log(0.1);  label("Receptor degradation rate (1/h)")
    lkint <- log(0.05); label("Complex internalization rate (1/h)")
    lKSS  <- log(10);   label("Quasi-steady-state constant (nM)")
    eta.v    ~ 0.1
    eta.ksyn ~ 0.1
    prop.sd <- 0.2
  })
  model({
    v    <- exp(lv   + eta.v)
    kel  <- exp(lkel)
    ksyn <- exp(lksyn + eta.ksyn)
    kdeg <- exp(lkdeg)
    kint <- exp(lkint)
    KSS  <- exp(lKSS)
    d/dt(Ltot) = -kel * Lfree - kint * (Ltot - Lfree)
    d/dt(Rtot) =  ksyn - kdeg * Rfree - kint * (Rtot - Rfree)
    Lfree = 0.5 * ((Ltot - Rtot - KSS) + sqrt((Ltot - Rtot - KSS)^2 + 4*KSS*Ltot))
    Rfree = Rtot * KSS / (KSS + Lfree)
    Cc = Lfree
    Cc ~ prop(prop.sd)
  })
}
""")

register_model(
    name="tmdd_qe_1cmt",
    category="tmdd",
    description="TMDD QE approximation — 1-compartment, quasi-equilibrium (KD = koff/kon)",
    route="iv_bolus", compartments=1,
    monolix_equivalent="TMDD_QE",
    code=r"""
tmdd_qe_1cmt <- function() {
  ini({
    lv    <- log(50);   label("Volume of distribution (L)")
    lkel  <- log(0.1);  label("Ligand elimination rate (1/h)")
    lksyn <- log(1);    label("Receptor synthesis rate (nM/h)")
    lkdeg <- log(0.1);  label("Receptor degradation rate (1/h)")
    lkint <- log(0.05); label("Complex internalization rate (1/h)")
    lKD   <- log(5);    label("Equilibrium dissociation constant (nM)")
    eta.v    ~ 0.1
    eta.ksyn ~ 0.1
    prop.sd <- 0.2
  })
  model({
    v    <- exp(lv   + eta.v)
    kel  <- exp(lkel)
    ksyn <- exp(lksyn + eta.ksyn)
    kdeg <- exp(lkdeg)
    kint <- exp(lkint)
    KD   <- exp(lKD)
    d/dt(Ltot) = -kel * Lfree - kint * (Ltot - Lfree)
    d/dt(Rtot) =  ksyn - kdeg * Rfree - kint * (Rtot - Rfree)
    Lfree = 0.5 * ((Ltot - Rtot - KD) + sqrt((Ltot - Rtot - KD)^2 + 4*KD*Ltot))
    Rfree = Rtot * KD / (KD + Lfree)
    Cc = Lfree
    Cc ~ prop(prop.sd)
  })
}
""")

register_model(
    name="tmdd_full_2cmt",
    category="tmdd",
    description="Full TMDD model — 2-compartment with peripheral distribution",
    route="iv_bolus", compartments=2,
    monolix_equivalent="TMDD_full_2cpt",
    code=r"""
tmdd_full_2cmt <- function() {
  ini({
    lv    <- log(50);   label("Central volume (L)")
    lv2   <- log(30);   label("Peripheral volume (L)")
    lQ    <- log(5);    label("Intercompartmental clearance (L/h)")
    lkel  <- log(0.1);  label("Ligand elimination rate (1/h)")
    lkon  <- log(0.1);  label("Association rate (1/nM/h)")
    lkoff <- log(0.01); label("Dissociation rate (1/h)")
    lksyn <- log(1);    label("Receptor synthesis rate (nM/h)")
    lkdeg <- log(0.1);  label("Receptor degradation rate (1/h)")
    lkint <- log(0.05); label("Complex internalization rate (1/h)")
    eta.v    ~ 0.1
    eta.ksyn ~ 0.1
    prop.sd <- 0.2
  })
  model({
    v    <- exp(lv   + eta.v)
    v2   <- exp(lv2)
    Q    <- exp(lQ)
    kel  <- exp(lkel)
    kon  <- exp(lkon)
    koff <- exp(lkoff)
    ksyn <- exp(lksyn + eta.ksyn)
    kdeg <- exp(lkdeg)
    kint <- exp(lkint)
    R0   <- ksyn / kdeg
    R(0) <- R0
    d/dt(L)   = -kon*L*R + koff*RL - kel*L - Q/v*L + Q/v2*L2
    d/dt(L2)  =  Q/v*L - Q/v2*L2
    d/dt(R)   =  ksyn - kdeg*R - kon*L*R + koff*RL
    d/dt(RL)  =  kon*L*R - koff*RL - kint*RL
    Cc = L
    Cc ~ prop(prop.sd)
  })
}
""")

register_model(
    name="tmdd_qss_2cmt",
    category="tmdd",
    description="TMDD QSS approximation — 2-compartment with peripheral distribution",
    route="iv_bolus", compartments=2,
    monolix_equivalent="TMDD_QSS_2cpt",
    code=r"""
tmdd_qss_2cmt <- function() {
  ini({
    lv    <- log(50);   label("Central volume (L)")
    lv2   <- log(30);   label("Peripheral volume (L)")
    lQ    <- log(5);    label("Intercompartmental clearance (L/h)")
    lkel  <- log(0.1);  label("Ligand elimination rate (1/h)")
    lksyn <- log(1);    label("Receptor synthesis rate (nM/h)")
    lkdeg <- log(0.1);  label("Receptor degradation rate (1/h)")
    lkint <- log(0.05); label("Complex internalization rate (1/h)")
    lKSS  <- log(10);   label("Quasi-steady-state constant (nM)")
    eta.v    ~ 0.1
    eta.ksyn ~ 0.1
    prop.sd <- 0.2
  })
  model({
    v    <- exp(lv   + eta.v)
    v2   <- exp(lv2)
    Q    <- exp(lQ)
    kel  <- exp(lkel)
    ksyn <- exp(lksyn + eta.ksyn)
    kdeg <- exp(lkdeg)
    kint <- exp(lkint)
    KSS  <- exp(lKSS)
    d/dt(Ltot) = -kel * Lfree - kint * (Ltot - Lfree) - Q/v * Lfree + Q/v2 * L2
    d/dt(L2)   =  Q/v * Lfree - Q/v2 * L2
    d/dt(Rtot) =  ksyn - kdeg * Rfree - kint * (Rtot - Rfree)
    Lfree = 0.5 * ((Ltot - Rtot - KSS) + sqrt((Ltot - Rtot - KSS)^2 + 4*KSS*Ltot))
    Rfree = Rtot * KSS / (KSS + Lfree)
    Cc = Lfree
    Cc ~ prop(prop.sd)
  })
}
""")

register_model(
    name="tmdd_irreversible_1cmt",
    category="tmdd",
    description="TMDD irreversible binding — 1-compartment, koff ≈ 0",
    route="iv_bolus", compartments=1,
    monolix_equivalent="TMDD_IB",
    code=r"""
tmdd_irreversible_1cmt <- function() {
  ini({
    lv    <- log(50);   label("Volume of distribution (L)")
    lkel  <- log(0.1);  label("Ligand elimination rate (1/h)")
    lkon  <- log(0.1);  label("Association rate (1/nM/h)")
    lksyn <- log(1);    label("Receptor synthesis rate (nM/h)")
    lkdeg <- log(0.1);  label("Receptor degradation rate (1/h)")
    lkint <- log(0.05); label("Complex internalization rate (1/h)")
    eta.v    ~ 0.1
    eta.ksyn ~ 0.1
    prop.sd <- 0.2
  })
  model({
    v    <- exp(lv   + eta.v)
    kel  <- exp(lkel)
    kon  <- exp(lkon)
    ksyn <- exp(lksyn + eta.ksyn)
    kdeg <- exp(lkdeg)
    kint <- exp(lkint)
    R0   <- ksyn / kdeg
    R(0) <- R0
    d/dt(L)  = -kon*L*R - kel*L
    d/dt(R)  =  ksyn - kdeg*R - kon*L*R
    d/dt(RL) =  kon*L*R - kint*RL
    Cc = L
    Cc ~ prop(prop.sd)
  })
}
""")
