# PKPDBuilder

**The Pharmacometrician's Co-Pilot** — Claude Code + 33 pharmacometric MCP tools + 59 pre-built models.

## How It Works

PKPDBuilder is a wrapper around [Claude Code](https://docs.anthropic.com/en/docs/claude-code) that adds pharmacometric superpowers via [MCP](https://modelcontextprotocol.io) (Model Context Protocol). You get all of Claude Code's capabilities (filesystem, terminal, git, streaming) plus specialized PK/PD tools.

## Quick Start

```bash
# Prerequisites: Node.js 18+, R 4.2+, Claude Code
npm install -g @anthropic-ai/claude-code
claude login

# Install PKPDBuilder
npm install -g pkpdbuilder

# Initialize a project
cd my-pk-analysis
pkpdbuilder init

# Launch (opens Claude Code with pharmacometric tools)
pkpdbuilder
```

## What You Get

### 33 Pharmacometric Tools
- **Data:** load, summarize, QC, BLQ handling
- **Modeling:** fit PopPK via nlmixr2 (SAEM/FOCEI), model library, model comparison
- **Diagnostics:** GOF plots, VPC, ETA diagnostics, individual fits, parameter tables
- **NCA:** Non-compartmental analysis via PKNCA
- **Simulation:** Dosing regimens, virtual populations via mrgsolve
- **Covariates:** Screening, stepwise model building, forest plots
- **Literature:** PubMed search, drug PK parameter lookup
- **Export:** NONMEM, Monolix, Pumas format conversion
- **Reports:** HTML analysis reports, Shiny apps

### 59 Pre-Built Models
- 28 PK models (1/2/3-CMT, oral/IV, linear/MM, transit, parallel absorption)
- 18 PD models (Emax, Imax, effect compartment, IDR Types I-IV)
- 5 PK/PD linked models
- 6 TMDD models (full, QSS, QE, irreversible)
- 2 Advanced (time-to-event, count data)

## Commands

```bash
pkpdbuilder          # Launch Claude Code with MCP tools
pkpdbuilder init     # Scaffold CLAUDE.md + project structure
pkpdbuilder doctor   # Check environment (Claude Code, R, packages)
```

## Prerequisites

- **Node.js 18+**
- **Claude Code** with Anthropic API key or Max subscription
- **R 4.2+** with: `nlmixr2`, `mrgsolve`, `PKNCA`, `ggplot2`

## Developer

**Husain Z Attarwala, PhD**

---

*For research and educational purposes. Not for clinical decision-making.*
