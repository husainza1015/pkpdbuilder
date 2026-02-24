# PKPDBuilder CLI

**The Pharmacometrician's Co-Pilot** — an AI-powered terminal tool for population PK/PD analysis.

33 tools • 59 models • 4 providers • Zero config

## Quick Start

```bash
# Install globally
npm install -g pkpdbuilder

# Or install from this repo
git clone https://github.com/husainza1015/pkpdbuilder.git
cd pkpdbuilder
git checkout node
npm install
npm run build
npm link

# Launch
pkpdbuilder
```

## Prerequisites

- **Node.js 18+**
- **R 4.2+** with `nlmixr2` and `mrgsolve` installed
- An API key for at least one provider (or Ollama for fully local use)

## Zero-Config Setup

PKPDBuilder auto-discovers your environment on first launch:

- **R** — scans PATH and common install locations (Windows, macOS, Linux)
- **API keys** — checks environment variables (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`)
- **Datasets** — finds `.csv` and `.xpt` files in your current directory
- **Project context** — detects previous model fits and project memory

If no API key is found in your environment, it asks once and saves it.

## Supported Providers

| Provider | Env Variable | Models |
|----------|-------------|--------|
| Anthropic | `ANTHROPIC_API_KEY` | Claude Sonnet / Opus |
| OpenAI | `OPENAI_API_KEY` | GPT-4o / o1 |
| Google | `GOOGLE_API_KEY` | Gemini 2.5 Pro / Flash |
| Ollama | (none needed) | Llama 3.3, DeepSeek-R1, etc. |

## Commands

```bash
pkpdbuilder              # Interactive session
pkpdbuilder doctor       # Check environment
pkpdbuilder tools        # List all 33 tools
pkpdbuilder setup        # Re-run setup
pkpdbuilder ask "query"  # One-shot question
```

### Interactive Commands

```
/help       Show commands
/tools      Available tools
/model      Switch AI model
/provider   Switch provider
/audit      Recent API call log
/clear      Clear conversation
/exit       Quit
```

### Example Prompts

```
> Load my dataset and summarize it
> Fit a 2-compartment oral model with allometric scaling
> Generate goodness-of-fit plots
> Run a VPC with 500 simulations
> Compare all fitted models
> Export to NONMEM format
> Generate a PopPK analysis report
```

## Developer

**Husain Z Attarwala, PhD**

---

*For research and educational purposes. Not for clinical decision-making.*
