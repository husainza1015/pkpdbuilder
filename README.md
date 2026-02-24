# PKPDBuilder CLI

**The Pharmacometrician's Co-Pilot** — an AI-powered terminal tool for population PK/PD analysis.

33 tools • 59 models • 5 providers • Local-first

## Quick Start

```bash
# Clone
git clone https://github.com/husainza1015/pkpdbuilder.git
cd pkpdbuilder

# Install
pip install -e .

# First-time setup (choose provider, enter API key)
pkpdbuilder setup

# Launch
pkpdbuilder
```

## Prerequisites

- **Python 3.10+**
- **R 4.2+** with `nlmixr2` and `mrgsolve` installed
- An API key for at least one provider (or Ollama for fully local use)

## Supported Providers

| Provider | Model | API Key |
|----------|-------|---------|
| Anthropic | Claude Sonnet/Opus | [console.anthropic.com](https://console.anthropic.com) |
| OpenAI | GPT-4o/o1 | [platform.openai.com](https://platform.openai.com) |
| Google | Gemini 2.5 Pro/Flash | [aistudio.google.com](https://aistudio.google.com/apikey) |
| Ollama | Llama 3.3, DeepSeek-R1, etc. | None (local) |

## Local / Air-Gapped Mode (Ollama)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3.3

# Setup PKPDBuilder with Ollama — no API key needed
pkpdbuilder setup  # choose "ollama"
```

All data stays on your machine. No external API calls.

## Usage

```
pkpdbuilder                  # Interactive session
pkpdbuilder tools            # List all 33 tools
pkpdbuilder --version        # Version check
```

### Interactive Commands

```
/help       Full command list
/tools      Available tools
/profile    Your adaptive learning profile
/forget     Reset learning profile
/audit      Recent API call log
/local      Switch to Ollama
```

### Example Prompts

```
> Load the dataset from data/pk_study.csv and summarize it
> Fit a 2-compartment oral model with allometric scaling on weight
> Generate goodness-of-fit plots for the last model
> Run a VPC with 500 simulations
> Compare all fitted models and recommend the best one
> Export the final model to NONMEM format
> Generate a PopPK analysis report
```

## Model Library

59 pre-built models across 6 categories:

- **PK Models (28):** 1/2/3-CMT, oral/IV/infusion, linear/MM elimination, lag time, parallel absorption
- **PD Models (18):** Direct Emax/Imax, effect compartment, indirect response (IDR Types I-IV)
- **PK/PD Models (5):** Linked PK-PD with various response models
- **TMDD Models (6):** Full, QSS, QE, irreversible binding
- **Advanced (2):** Time-to-event (Weibull), count data (Poisson)

## Project Structure

```
pkpdbuilder/
├── cli.py          # CLI entry point, interactive loop
├── agent.py        # AI agent with tool-calling
├── config.py       # Providers, models, API key management
├── r_bridge.py     # R/nlmixr2/mrgsolve interface
├── learner.py      # Adaptive learning engine
├── audit.py        # API call logging & cost tracking
└── tools/          # 33 pharmacometric tools
```

## Developer

**Husain Z Attarwala, PhD**

---

*For research and educational purposes. Not for clinical decision-making.*
