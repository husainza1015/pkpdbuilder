# PKPDBuilder CLI — Node.js Rebuild Spec

## Vision
"Claude Code for Pharmacometrics" — an intelligent CLI that auto-discovers your environment, connects to AI, and helps you do population PK/PD analysis through natural conversation.

## UX Goals
- `npm install -g pkpdbuilder` → `pkpdbuilder` → working in 60 seconds
- Zero-config: auto-detect R, find datasets, detect API keys from env
- Claude Code-like intelligence: reads your project, understands context
- Natural language: "fit a 2-compartment model to my data" just works

## Architecture

```
pkpdbuilder/
├── src/
│   ├── index.ts          # Entry point + commander CLI
│   ├── setup.ts          # First-run setup (minimal, intelligent)
│   ├── repl.ts           # Interactive REPL loop
│   ├── agent.ts          # AI agent with tool-calling loop
│   ├── providers/        # LLM provider adapters
│   │   ├── anthropic.ts
│   │   ├── openai.ts
│   │   ├── google.ts
│   │   └── ollama.ts
│   ├── tools/            # Tool definitions + implementations
│   │   ├── registry.ts   # Tool registry
│   │   ├── data.ts       # Dataset loading, QC, summary
│   │   ├── modeling.ts   # Model fitting (nlmixr2)
│   │   ├── diagnostics.ts # GOF, VPC, ETAs
│   │   ├── nca.ts        # Non-compartmental analysis
│   │   ├── simulation.ts # mrgsolve simulation
│   │   ├── literature.ts # PubMed search
│   │   ├── covariate.ts  # Covariate screening/SCM
│   │   ├── export.ts     # Export to NONMEM/Monolix
│   │   ├── report.ts     # HTML report generation
│   │   └── memory.ts     # Project memory
│   ├── r-bridge.ts       # R subprocess execution
│   ├── discovery.ts      # Auto-detect R, datasets, project structure
│   ├── config.ts         # Config management (~/.pkpdbuilder/)
│   ├── models/           # Model library (59 models as JSON/R templates)
│   │   ├── pk/
│   │   ├── pd/
│   │   ├── pkpd/
│   │   ├── tmdd/
│   │   └── advanced/
│   ├── r-scripts/        # R scripts (copied from Python version)
│   │   ├── fit_nlmixr2.R
│   │   ├── diagnostics.R
│   │   ├── vpc.R
│   │   ├── run_nca.R
│   │   ├── simulate_mrgsolve.R
│   │   └── ... (15 scripts total)
│   ├── banner.ts         # Gradient ASCII banner
│   └── audit.ts          # API call logging
├── package.json
├── tsconfig.json
└── README.md
```

## First-Run Experience

```
$ pkpdbuilder

  ██████╗ ██╗  ██╗██████╗ ██████╗
  ██╔══██╗██║ ██╔╝██╔══██╗██╔══██╗
  ...gradient banner...

  The Pharmacometrician's Co-Pilot
  ─────────────────────────────────

  Welcome! Let me check your environment...

  ✓ R 4.4.0 found at C:\Program Files\R\R-4.4.0\bin\Rscript.exe
  ✓ nlmixr2 installed
  ✓ mrgsolve installed
  ✗ PKNCA not found (optional — install with install.packages("PKNCA"))

  API Key: (looks for ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY in env)
  → Found GOOGLE_API_KEY ✓

  Ready! Type naturally or use /help for commands.

pkpdbuilder>
```

If NO env var key found:
```
  No API key found. Paste one to get started:
  → Anthropic: console.anthropic.com/keys
  → OpenAI:    platform.openai.com/api-keys
  → Google:    aistudio.google.com/apikey

  API key: sk-ant-...
  ✓ Anthropic Claude Sonnet verified. Saved to ~/.pkpdbuilder/keys.json

pkpdbuilder>
```

## Auto-Discovery (discovery.ts)

On every launch:
1. **Find R** — check PATH, common install dirs (Windows Program Files, macOS /usr/local, Framework)
2. **Check R packages** — run quick R script to test nlmixr2, mrgsolve, PKNCA
3. **Scan cwd for datasets** — look for .csv, .xpt (SAS), .nm (NONMEM) files
4. **Detect project structure** — look for MEMORY.md, existing model fits, output dirs
5. **Find API keys** — check env vars (ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY), then ~/.pkpdbuilder/keys.json

## Provider Auto-Detection

Priority order when multiple keys available:
1. ANTHROPIC_API_KEY → use Claude
2. OPENAI_API_KEY → use GPT-4
3. GOOGLE_API_KEY → use Gemini
4. Ollama running on localhost:11434 → use local model
5. No key → prompt for one

## Interactive REPL

Commands (slash prefix):
- `/help` — show commands
- `/tools` — list available tools
- `/model <name>` — switch AI model
- `/provider <name>` — switch provider
- `/profile` — show learning profile
- `/audit` — show recent API calls
- `/clear` — clear conversation
- `/exit` — quit

Everything else → sent to AI agent as natural language.

## Agent (agent.ts)

- System prompt includes: available tools, current project context, discovered datasets, R environment status
- Tool-calling loop: send message → get response → if tool calls, execute them → send results back → repeat
- Supports streaming responses
- Tracks conversation history
- Logs all API calls to audit log

## R Bridge (r-bridge.ts)

```typescript
import { execFile } from 'child_process';

async function runRScript(scriptName: string, args: Record<string, any>): Promise<any> {
  // Write args to temp JSON
  // Execute: Rscript <script_path>
  // Read result from temp JSON
  // Return parsed result
}

async function runRCode(code: string): Promise<{ stdout: string; stderr: string }> {
  // Write code to temp .R file
  // Execute: Rscript <temp_file>
  // Return output
}

function findRscript(): string | null {
  // Check PATH
  // Check Windows: C:\Program Files\R\R-*\bin\Rscript.exe
  // Check macOS: /usr/local/bin, /opt/homebrew/bin, /Library/Frameworks/R.framework/...
  // Check Linux: /usr/bin, /usr/local/bin
}
```

## Model Library

Port all 59 models from Python version. Each model is a JSON file with:
```json
{
  "name": "pk_2cmt_iv_bolus",
  "category": "pk",
  "description": "2-compartment, IV bolus, linear elimination",
  "monolix_equivalent": "bolus_2cpt_VClV2Q",
  "code": "pk_2cmt_iv_bolus <- function() {\n  ini({\n    ..."
}
```

## Tools (33 total)

Port all tools from Python version:
1. load_dataset, summarize_dataset, dataset_qc, handle_blq
2. plot_data, fit_model, fit_from_library, compare_models
3. goodness_of_fit, vpc, eta_plots, individual_fits, parameter_table
4. run_nca, simulate_regimen, population_simulation
5. search_pubmed, lookup_drug
6. generate_report, build_shiny_app, generate_beamer_slides
7. covariate_screening, stepwise_covariate_model, forest_plot
8. list_backends, export_model, import_model
9. memory_read, memory_write, memory_search
10. init_project, list_model_library, get_model_code

## Package.json

```json
{
  "name": "pkpdbuilder",
  "version": "0.2.0",
  "description": "The Pharmacometrician's Co-Pilot",
  "bin": { "pkpdbuilder": "./dist/index.js" },
  "scripts": {
    "build": "tsc",
    "dev": "tsx src/index.ts"
  },
  "dependencies": {
    "@anthropic-ai/sdk": "^0.40.0",
    "openai": "^4.0.0",
    "@google/genai": "^1.0.0",
    "commander": "^12.0.0",
    "chalk": "^5.0.0",
    "inquirer": "^9.0.0",
    "ora": "^8.0.0",
    "conf": "^12.0.0"
  },
  "devDependencies": {
    "typescript": "^5.4.0",
    "tsx": "^4.0.0",
    "@types/node": "^20.0.0"
  }
}
```

## Key Differences from Python Version

1. **Zero-config** — no setup wizard, auto-discovers everything
2. **Streaming** — responses stream token-by-token
3. **Auto-install check** — detects missing R packages and offers to install
4. **Project-aware** — reads cwd for datasets, previous fits, project memory
5. **Env var first** — API keys from environment, no manual paste needed
6. **Gradient banner** — port using chalk with RGB support
7. **npm global install** — `npm install -g pkpdbuilder`

## Developer
Husain Z Attarwala, PhD
