"""PKPDBuilder CLI — interactive terminal for pharmacometrics analysis."""
import sys
import os
import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from pathlib import Path

console = Console()

from pkpdbuilder import __version__ as VERSION

LOGO_PKPD = [
    "  ██████╗ ██╗  ██╗██████╗ ██████╗ ",
    "  ██╔══██╗██║ ██╔╝██╔══██╗██╔══██╗",
    "  ██████╔╝█████╔╝ ██████╔╝██║  ██║",
    "  ██╔═══╝ ██╔═██╗ ██╔═══╝ ██║  ██║",
    "  ██║     ██║  ██╗██║     ██████╔╝",
    "  ╚═╝     ╚═╝  ╚═╝╚═╝     ╚═════╝ ",
]

LOGO_BUILDER = [
    "  ██████╗ ██╗   ██╗██╗██╗     ██████╗ ███████╗██████╗ ",
    "  ██╔══██╗██║   ██║██║██║     ██╔══██╗██╔════╝██╔══██╗",
    "  ██████╔╝██║   ██║██║██║     ██║  ██║█████╗  ██████╔╝",
    "  ██╔══██╗██║   ██║██║██║     ██║  ██║██╔══╝  ██╔══██╗",
    "  ██████╔╝╚██████╔╝██║███████╗██████╔╝███████╗██║  ██║",
    "  ╚═════╝  ╚═════╝ ╚═╝╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝",
]

GRADIENT_START = (168, 85, 247)   # violet
GRADIENT_MID = (99, 102, 241)     # indigo
GRADIENT_END = (6, 182, 212)      # cyan


def _gradient_text(text, c1, c2):
    """Render text with per-character horizontal gradient."""
    from rich.text import Text as RichText
    t = RichText()
    n = max(len(text.rstrip()) - 1, 1)
    for j, ch in enumerate(text):
        frac = min(j / n, 1.0)
        r = int(c1[0] + (c2[0] - c1[0]) * frac)
        g = int(c1[1] + (c2[1] - c1[1]) * frac)
        b = int(c1[2] + (c2[2] - c1[2]) * frac)
        t.append(ch, style=f"bold rgb({r},{g},{b})")
    return t


def _render_banner():
    """Render the full banner with gradient logo, tagline, and stats."""
    from rich.text import Text as RichText

    parts = []

    # PKPD block — violet → mid gradient
    for line in LOGO_PKPD:
        parts.append(_gradient_text(line, GRADIENT_START, GRADIENT_MID))

    # Builder block — mid → cyan gradient
    for line in LOGO_BUILDER:
        parts.append(_gradient_text(line, GRADIENT_MID, GRADIENT_END))

    # Tagline + stats
    tagline = RichText()
    tagline.append("\n")
    tagline.append("  The Pharmacometrician's Co-Pilot\n", style="bold white")
    tagline.append(f"  {'─' * 55}\n", style="dim")
    tagline.append("  ⚗  33 tools", style="rgb(168,85,247)")
    tagline.append("  •  ", style="dim")
    tagline.append("59 models", style="rgb(99,102,241)")
    tagline.append("  •  ", style="dim")
    tagline.append("5 providers", style="rgb(6,182,212)")
    tagline.append("  •  ", style="dim")
    tagline.append(f"v{VERSION}\n", style="dim bold")

    return parts, tagline

HELP_TEXT = """
## Commands

| Command | Description |
|---------|-------------|
| `/help` | Show this help |
| `/tools` | List available tools |
| `/status` | Show loaded dataset and model status |
| `/reset` | Clear conversation history |
| `/output` | Open output directory |
| `/doctor` | Check R environment |
| `/provider` | Show/switch AI provider (anthropic, openai, google) |
| `/model` | Show/switch model |
| `/profile` | View learned preferences and usage stats |
| `/forget` | Reset learned preferences (start fresh) |
| `/quit` | Exit pkpdbuilder |

## Quick Start

1. `Load the theophylline dataset from ./data/theo_sd.csv`
2. `Fit a one-compartment oral model`
3. `Run diagnostics`
4. `Compare with a two-compartment model`
5. `Generate a report for theophylline`
6. `Build a Shiny simulator app`

## Tips

- Be specific about model structure: "1-compartment oral with IIV on CL and V"
- Ask for NCA first to get initial parameter estimates
- Use "lookup drug X" to find published PK parameters
- Ask to "search PubMed for X population pharmacokinetics" for references
"""


@click.group(invoke_without_command=True)
@click.version_option(VERSION, prog_name="pkpdbuilder")
@click.pass_context
def main(ctx):
    """PKPDBuilder — The Pharmacometrician's Co-Pilot"""
    if ctx.invoked_subcommand is None:
        interactive_mode()


@main.command()
@click.argument("query")
def ask(query):
    """Run a single query and exit."""
    from .agent import PKPDBuilderAgent
    try:
        agent = PKPDBuilderAgent()
        response = agent.chat(query)
        console.print(Markdown(response))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
def setup():
    """Interactive onboarding — configure provider, API key, model, and autonomy."""
    from .config import save_config, load_config, save_api_key, get_api_key, PROVIDERS, CONFIG_DIR
    
    config = load_config()
    
    # Check if already onboarded
    if config.get("onboarded"):
        console.print("[bold]PKPDBuilder Configuration[/bold]\n")
        console.print(f"  Provider: [cyan]{config.get('provider', 'anthropic')}[/cyan]")
        console.print(f"  Model:    [cyan]{config.get('model')}[/cyan]")
        console.print(f"  API Key:  [green]{'configured' if get_api_key() else 'missing'}[/green]")
        console.print(f"  Autonomy: [cyan]{config.get('autonomy', 'full')}[/cyan]")
        console.print(f"  Output:   [cyan]{config.get('output_dir')}[/cyan]")
        if not click.confirm("\n  Reconfigure?", default=False):
            return
    
    console.print()
    console.print(Panel.fit(
        "[bold white]Welcome to PKPDBuilder — The Pharmacometrician's Co-Pilot[/bold white]\n\n"
        "Let's get you set up in 60 seconds.",
        border_style="blue"
    ))
    
    # ── Step 1: Provider ──
    console.print("\n[bold]Step 1: Choose your AI provider[/bold]\n")
    provider_choices = list(PROVIDERS.keys())
    for i, p in enumerate(provider_choices, 1):
        info = PROVIDERS[p]
        console.print(f"  {i}. {info['name']}")
        console.print(f"     Models: {', '.join(info['models'][:3])}")
    
    choice = click.prompt(
        "\n  Provider",
        type=click.IntRange(1, len(provider_choices)),
        default=provider_choices.index(config.get("provider", "anthropic")) + 1
    )
    provider = provider_choices[choice - 1]
    config["provider"] = provider
    provider_info = PROVIDERS[provider]
    
    # ── Step 2: API Key ──
    console.print(f"\n[bold]Step 2: {provider_info['name']} API Key[/bold]\n")
    
    existing_key = get_api_key(provider)
    if existing_key:
        masked = existing_key[:8] + "..." + existing_key[-4:] if len(existing_key) > 12 else "***"
        console.print(f"  Current key: [green]{masked}[/green]")
        if not click.confirm("  Change key?", default=False):
            pass  # Keep existing
        else:
            existing_key = None
    
    if not existing_key:
        # Check for Claude Max / OAuth option
        if provider == "anthropic":
            console.print("  [dim]Options:[/dim]")
            console.print("    a) API key from [link=https://console.anthropic.com/settings/keys]console.anthropic.com[/link]")
            console.print("    b) Claude Max subscription (uses Claude Code OAuth)")
            console.print()
            auth_method = click.prompt("  Auth method", type=click.Choice(["a", "b"]), default="a")
            
            if auth_method == "b":
                # Claude Max OAuth — check for existing Claude Code credentials
                claude_config = Path.home() / ".claude" / "config.json"
                if claude_config.exists():
                    console.print("  [green]✓ Claude Code credentials found![/green]")
                    console.print("  PMX will use your Claude Max subscription via Claude Code.")
                    config["auth_method"] = "claude_oauth"
                    # Store a sentinel — actual auth handled by Claude Code
                    save_api_key(provider, "__CLAUDE_MAX_OAUTH__")
                else:
                    console.print("  [yellow]Claude Code not found.[/yellow]")
                    console.print("  Install: [cyan]npm install -g @anthropic-ai/claude-code[/cyan]")
                    console.print("  Then run: [cyan]claude login[/cyan]")
                    console.print("  Falling back to API key...\n")
                    auth_method = "a"
            
            if auth_method == "a":
                key = click.prompt("  API Key", hide_input=True)
                if key:
                    save_api_key(provider, key)
                    config["auth_method"] = "api_key"
        else:
            console.print(f"  Get your key: [link={provider_info['docs']}]{provider_info['docs']}[/link]\n")
            key = click.prompt("  API Key", hide_input=True)
            if key:
                save_api_key(provider, key)
    
    # ── Step 3: Model ──
    console.print(f"\n[bold]Step 3: Default model[/bold]\n")
    models = provider_info["models"]
    for i, m in enumerate(models, 1):
        default_marker = " [green](recommended)[/green]" if m == provider_info["default"] else ""
        console.print(f"  {i}. {m}{default_marker}")
    
    default_idx = models.index(provider_info["default"]) + 1 if provider_info["default"] in models else 1
    model_choice = click.prompt(
        "\n  Model",
        type=click.IntRange(1, len(models)),
        default=default_idx
    )
    config["model"] = models[model_choice - 1]
    
    # ── Step 4: Autonomy ──
    console.print(f"\n[bold]Step 4: Autonomy level[/bold]\n")
    console.print("  1. [green]Full[/green] — Run analyses end-to-end autonomously (recommended)")
    console.print("     PMX makes sensible defaults, asks only if genuinely ambiguous")
    console.print("  2. [yellow]Supervised[/yellow] — Ask before fitting models or generating reports")
    console.print("  3. [red]Ask[/red] — Confirm every major step")
    
    autonomy_choice = click.prompt("\n  Autonomy", type=click.IntRange(1, 3), default=1)
    config["autonomy"] = ["full", "supervised", "ask"][autonomy_choice - 1]
    
    # ── Step 5: Output ──
    out = click.prompt("\n  Output directory", default=config.get("output_dir", "./pmx_output"))
    config["output_dir"] = out
    
    # ── Save ──
    config["onboarded"] = True
    save_config(config)
    
    # ── R Environment Check ──
    console.print("\n[bold]Checking R environment...[/bold]")
    from .r_bridge import check_r_environment
    env = check_r_environment(config)
    if env.get("success"):
        console.print(f"  R: [green]{env.get('r_version', '?')}[/green]")
        pkgs = env.get("packages", {})
        missing = [p for p, v in pkgs.items() if not v]
        installed = [p for p, v in pkgs.items() if v]
        if installed:
            console.print(f"  Packages: [green]{len(installed)} installed[/green]", end="")
            if missing:
                console.print(f", [yellow]{len(missing)} missing ({', '.join(missing[:5])})[/yellow]")
            else:
                console.print()
    else:
        console.print(f"  [red]R not found — install R 4.x and required packages[/red]")
        console.print(f"  [dim]nlmixr2, mrgsolve, PKNCA, vpc, ggplot2, xpose, dplyr[/dim]")
    
    # ── Summary ──
    console.print()
    console.print(Panel.fit(
        f"[green]✓ Setup complete![/green]\n\n"
        f"  Provider: [bold]{PROVIDERS[provider]['name']}[/bold]\n"
        f"  Model:    [bold]{config['model']}[/bold]\n"
        f"  Autonomy: [bold]{config['autonomy']}[/bold]\n"
        f"  Output:   [bold]{config['output_dir']}[/bold]\n\n"
        f"  [dim]Run [bold]pkpdbuilder[/bold] to start, or [bold]pkpdbuilder init <drug>[/bold] for a new project[/dim]",
        border_style="green",
        title="Ready"
    ))


@main.command(name="init")
@click.argument("drug_name")
@click.option("--indication", "-i", default="", help="Therapeutic indication")
@click.option("--analysis", "-a", default="popPK", type=click.Choice(["popPK", "popPKPD", "PKPD", "exposureResponse"]))
@click.option("--dir", "-d", "project_dir", default=None, help="Project directory (default: ./<drug_name>)")
def init_cmd(drug_name, indication, analysis, project_dir):
    """Initialize a new drug program analysis project."""
    from .tools.memory import init_project
    
    if project_dir is None:
        project_dir = f"./{drug_name.lower().replace(' ', '_')}"
    
    result = init_project(drug_name=drug_name, indication=indication, 
                          analysis_type=analysis, project_dir=project_dir)
    
    if result["success"]:
        console.print(f"\n[green]✓ Project initialized: {result['drug_name']}[/green]")
        console.print(f"  Directory: [cyan]{result['project_dir']}[/cyan]")
        console.print(f"  Created: {result['directories_created']} dirs + {len(result['files_created'])} files")
        console.print(f"\n  [dim]cd {result['project_dir']} && pmx[/dim]")
    else:
        console.print(f"[red]Failed: {result.get('error')}[/red]")


@main.command()
def doctor():
    """Check R environment and dependencies."""
    from .r_bridge import check_r_environment
    from .config import load_config
    
    config = load_config()
    console.print("[bold]Checking environment...[/bold]\n")
    
    env = check_r_environment(config)
    if env.get("success"):
        console.print(f"  R: [green]{env.get('r_version', '?')}[/green]")
        pkgs = env.get("packages", {})
        all_ok = True
        for pkg, installed in pkgs.items():
            if installed:
                console.print(f"  {pkg}: [green]✓ installed[/green]")
            else:
                console.print(f"  {pkg}: [red]✗ missing[/red]")
                all_ok = False
        if all_ok:
            console.print("\n[green]All dependencies satisfied![/green]")
        else:
            console.print("\n[yellow]Install missing packages: install.packages(c('missing_pkg'))[/yellow]")
    else:
        console.print(f"[red]R not found or error: {env.get('error')}[/red]")


@main.command()
def tools():
    """List all available tools."""
    from .tools.registry import get_all_tools
    # Force import to register
    from .tools import data, nlmixr2, diagnostics, nca, simulation, literature, report, shiny, covariate, presentation, backends, memory, model_library, data_qc
    
    all_tools = get_all_tools()
    console.print(f"\n[bold]Available Tools ({len(all_tools)})[/bold]\n")
    for tool in all_tools:
        console.print(f"  [cyan]{tool['name']}[/cyan]")
        # First line of description
        desc = tool['description'].strip().split('\n')[0]
        console.print(f"    {desc}\n")


def interactive_mode():
    """Run the interactive REPL."""
    from .config import load_config, get_api_key
    
    config = load_config()
    
    # Auto-onboarding if not set up
    if not config.get("onboarded") and not get_api_key():
        console.print("\n[yellow]First time? Let's get you set up.[/yellow]\n")
        from click.testing import CliRunner
        ctx = click.Context(main)
        ctx.invoke(setup)
        config = load_config()  # Reload
    
    logo_lines, tagline = _render_banner()
    console.print()
    for line in logo_lines:
        console.print(line)
    console.print(tagline)
    
    # Show provider info
    provider = config.get("provider", "anthropic")
    model = config.get("model", "?")
    autonomy = config.get("autonomy", "full")
    console.print(f"  [dim]{provider} / {model} / autonomy: {autonomy}[/dim]\n")
    
    from .agent import PKPDBuilderAgent
    from .tools.data import get_current_dataset
    
    try:
        agent = PKPDBuilderAgent()
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        console.print("Run [bold]pkpdbuilder setup[/bold] to configure.")
        sys.exit(1)
    
    # History file
    history_dir = Path.home() / ".pkpdbuilder"
    history_dir.mkdir(exist_ok=True)
    history = FileHistory(str(history_dir / "history"))
    
    session = PromptSession(history=history, auto_suggest=AutoSuggestFromHistory())
    
    while True:
        try:
            user_input = session.prompt("\npkpdbuilder> ", multiline=False).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break
        
        if not user_input:
            continue
        
        # Handle commands
        if user_input.startswith("/"):
            cmd = user_input.lower().split()[0]
            if cmd in ("/quit", "/exit", "/q"):
                console.print("[dim]Goodbye![/dim]")
                break
            elif cmd == "/help":
                console.print(Markdown(HELP_TEXT))
                continue
            elif cmd == "/reset":
                agent.reset()
                console.print("[green]Conversation reset.[/green]")
                continue
            elif cmd == "/status":
                ds = get_current_dataset()
                if ds is not None:
                    console.print(f"[green]Dataset loaded: {len(ds)} rows, {ds['ID'].nunique()} subjects[/green]")
                else:
                    console.print("[yellow]No dataset loaded[/yellow]")
                continue
            elif cmd == "/tools":
                from .tools.registry import get_all_tools as gat
                for t in gat():
                    console.print(f"  [cyan]{t['name']}[/cyan] — {t['description'].split(chr(10))[0]}")
                continue
            elif cmd == "/output":
                from .config import load_config as lc
                out = lc()["output_dir"]
                console.print(f"Output directory: [cyan]{out}[/cyan]")
                os.makedirs(out, exist_ok=True)
                continue
            elif cmd == "/doctor":
                from .r_bridge import check_r_environment
                from .config import load_config as lc
                env = check_r_environment(lc())
                if env.get("success"):
                    console.print(f"R {env.get('r_version', '?')}: ", end="")
                    pkgs = env.get("packages", {})
                    missing = [p for p, v in pkgs.items() if not v]
                    if missing:
                        console.print(f"[yellow]Missing: {', '.join(missing)}[/yellow]")
                    else:
                        console.print("[green]All good![/green]")
                else:
                    console.print(f"[red]{env.get('error')}[/red]")
                continue
            elif cmd == "/provider":
                parts = user_input.split()
                if len(parts) >= 2:
                    new_provider = parts[1].lower()
                    from .config import PROVIDERS
                    if new_provider in PROVIDERS:
                        try:
                            agent = PKPDBuilderAgent(provider=new_provider)
                            console.print(f"[green]Switched to {PROVIDERS[new_provider]['name']} / {agent.model}[/green]")
                        except ValueError as e:
                            console.print(f"[red]{e}[/red]")
                    else:
                        console.print(f"[yellow]Unknown provider. Options: {', '.join(PROVIDERS.keys())}[/yellow]")
                else:
                    console.print(f"  Current: [cyan]{agent.provider} / {agent.model}[/cyan]")
                    console.print(f"  Switch: /provider [anthropic|openai|google]")
                continue
            elif cmd == "/model":
                parts = user_input.split()
                if len(parts) >= 2:
                    new_model = parts[1]
                    try:
                        agent.model = new_model
                        agent._init_client()
                        console.print(f"[green]Model set to {new_model}[/green]")
                    except Exception as e:
                        console.print(f"[red]{e}[/red]")
                else:
                    console.print(f"  Current model: [cyan]{agent.model}[/cyan]")
                continue
            elif cmd == "/profile":
                from .learner import load_profile, get_personalized_prompt_section
                profile = load_profile()
                stats = profile["stats"]
                console.print(f"\n[bold]Your PKPDBuilder Profile[/bold]\n")
                console.print(f"  Sessions: [cyan]{stats.get('total_sessions', 0)}[/cyan]")
                console.print(f"  Models fit: [cyan]{stats.get('total_models_fit', 0)}[/cyan]")
                console.print(f"  Analyses: [cyan]{stats.get('total_analyses', 0)}[/cyan]")
                drugs = profile["expertise"]["drugs_analyzed"]
                if drugs:
                    console.print(f"  Drugs: [cyan]{', '.join(drugs[-5:])}[/cyan]")
                prefs = get_personalized_prompt_section()
                if prefs:
                    console.print(f"\n[bold]Learned Preferences:[/bold]")
                    for line in prefs.strip().split("\n"):
                        if line.startswith("- "):
                            console.print(f"  [green]✓[/green] {line[2:]}")
                else:
                    console.print(f"\n  [dim]No preferences learned yet — keep using pkpdbuilder![/dim]")
                console.print()
                continue
            elif cmd == "/forget":
                from .learner import PROFILE_FILE, USAGE_LOG
                if PROFILE_FILE.exists():
                    PROFILE_FILE.unlink()
                if USAGE_LOG.exists():
                    USAGE_LOG.unlink()
                agent._personalized_prompt = ""
                console.print("[green]Profile reset. Starting fresh.[/green]")
                continue
            else:
                console.print(f"[yellow]Unknown command: {cmd}. Type /help[/yellow]")
                continue
        
        # Send to agent
        try:
            with console.status("[bold blue]Thinking..."):
                response = agent.chat(user_input)
            console.print()
            console.print(Markdown(response))
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")


if __name__ == "__main__":
    main()
