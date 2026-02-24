"""Multi-provider agent loop with pharmacometrics tools."""
import json
from rich.console import Console
from rich.markdown import Markdown

from .config import get_api_key, load_config, PROVIDERS
from .tools.registry import get_all_tools, execute_tool
from .learner import (
    log_tool_call, log_prompt, log_session_start, learn_from_history,
    get_personalized_prompt_section, load_profile
)
from .audit import APICallTimer, log_api_call

# Import tools to register them
from .tools import data, nlmixr2, diagnostics, nca, simulation, literature, report, shiny, covariate, presentation, backends, memory, model_library, data_qc

console = Console()

SYSTEM_PROMPT = """You are PMX, a pharmacometrics co-pilot. You help scientists with population PK/PD analysis.

You have access to specialized tools for:
- Loading and exploring PK/PD datasets (NONMEM format)
- Fitting population PK models with nlmixr2 (1/2/3-compartment, oral/IV, with IIV)
- Running diagnostics (GOF plots, VPC, ETA distributions)
- Non-compartmental analysis (NCA) using PKNCA
- Covariate screening and stepwise covariate modeling (SCM)
- Forest plots for covariate effects
- Dose simulation with mrgsolve
- Population simulation with inter-individual variability
- Searching PubMed for published PopPK models
- Looking up drug PK parameters from PKPDBuilder
- Generating analysis reports (FDA-style HTML)
- Generating Beamer slide presentations (PDF)
- Building interactive Shiny simulator apps
- Multi-backend support: nlmixr2 (open source), NONMEM, Monolix, Phoenix NLME (PML), Pumas (Julia)
- Model export/import between platforms (via babelmixr2, nonmem2rx, monolix2rx)
- Project memory management (memory_read/write/search, init_project)

## Operating Mode: Autonomous

You run AUTONOMOUSLY by default. When given a task:
1. Do the full analysis without stopping to ask permission at each step
2. Make sensible default choices (start simple, compare models, pick the best)
3. Only pause to ask if there's genuine ambiguity that affects the outcome

## When to Ask (BEFORE starting, not midway)

If the user's prompt is ambiguous on any of these, ask 1-3 focused questions UPFRONT:
- **Route of administration** — if not obvious from the data (look for CMT, EVID columns)
- **Which models to try** — if they say "analyze" without specifying (default: 1-CMT and 2-CMT)
- **Covariates of interest** — if not mentioned (default: auto-screen all available)
- **Dosing regimen for simulation** — if they want sims but didn't specify doses
- **Target audience for report** — internal team meeting vs regulatory submission

For everything else, just do it. Pick reasonable defaults:
- Estimation: FOCE-I (fallback to SAEM if convergence fails)
- Error model: proportional (add combined if prop fails)
- IIV: on CL, V, Ka (remove if shrinkage > 40%)
- VPC: 500 simulations, prediction-corrected if multiple doses
- Model selection: ΔOFV > 3.84 (1 df, p<0.05) for nested models
- Report: FDA PopPK Guidance (2022) format

## Standard Workflow

When asked to "analyze" or "run PopPK analysis":
1. load_dataset → summarize_dataset → plot_data
2. run_nca (initial parameter estimates)
3. fit_model (1-CMT) → fit_model (2-CMT)
4. compare_models → select best
5. goodness_of_fit → vpc → eta_plots
6. covariate_screening → stepwise_covariate_model (if significant)
7. parameter_table → generate_report
8. memory_write (log decisions and model history)

## Memory

At session start, call memory_read to restore project context.
After key decisions, call memory_write to log them.
This project may span months — your memory files are the continuity.

## Communication Style

Be concise but thorough. Use pharmacometrics terminology correctly.
Present parameter tables in readable format.
Always state model recommendation with reasoning.
Flag concerns: high RSE (>50%), large shrinkage (>30%), convergence issues.
Cross-reference unusual parameters against published values (lookup_drug).
"""


class PKPDBuilderAgent:
    """Multi-provider agent that uses Claude, GPT, or Gemini with PMX tools."""
    
    def __init__(self, provider: str = None, model: str = None, autonomy: str = None):
        self.config = load_config()
        self.provider = provider or self.config.get("provider", "anthropic")
        self.model = model or self.config.get("model")
        self.autonomy = autonomy or self.config.get("autonomy", "full")
        
        # Default model for provider if not set
        if not self.model or self.model not in str(PROVIDERS.get(self.provider, {}).get("models", [])):
            self.model = PROVIDERS.get(self.provider, {}).get("default", self.config["model"])
        
        self.api_key = get_api_key(self.provider)
        if not self.api_key:
            raise ValueError(
                f"No API key for {self.provider}. "
                f"Run 'pkpdbuilder setup' or set {PROVIDERS.get(self.provider, {}).get('env_key', 'API_KEY')}"
            )
        
        self.messages = []
        self.tools = get_all_tools()
        self._tool_call_count = 0
        self._dataset_in_context = False
        self._tools_this_turn = []
        
        # Learn from past usage at startup
        log_session_start()
        learn_from_history()
        self._personalized_prompt = get_personalized_prompt_section()
        
        self._init_client()
    
    def _init_client(self):
        """Initialize the appropriate SDK client."""
        if self.provider == "anthropic":
            from anthropic import Anthropic
            if self.api_key == "__CLAUDE_MAX_OAUTH__":
                # Use Claude Max subscription via OAuth token
                oauth_token = self._get_claude_oauth_token()
                if not oauth_token:
                    raise ValueError(
                        "Claude Max OAuth token not found. Run 'claude login' first.\n"
                        "See: https://docs.anthropic.com/en/docs/claude-code/cli-usage"
                    )
                self.client = Anthropic(api_key=oauth_token)
            else:
                self.client = Anthropic(api_key=self.api_key)
        elif self.provider == "openai":
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        elif self.provider == "google":
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def _get_claude_oauth_token(self) -> str:
        """Extract OAuth token from Claude Code credentials for Claude Max subscribers.
        
        To get your OAuth token:
        1. Install Claude Code: npm install -g @anthropic-ai/claude-code
        2. Run: claude login
        3. Complete the browser OAuth flow
        4. Token is stored in ~/.claude/config.json
        
        This lets you use your Claude Max subscription ($100/mo or $200/mo)
        instead of paying per-API-call.
        """
        import json
        from pathlib import Path
        
        # Check Claude Code config
        config_path = Path.home() / ".claude" / "config.json"
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text())
                # Claude Code stores OAuth token in config
                token = config.get("oauthToken") or config.get("oauth_token")
                if token:
                    return token
            except (json.JSONDecodeError, KeyError):
                pass
        
        # Check Claude credentials file
        creds_path = Path.home() / ".claude" / "credentials.json"
        if creds_path.exists():
            try:
                creds = json.loads(creds_path.read_text())
                token = creds.get("token") or creds.get("oauth_token")
                if token:
                    return token
            except (json.JSONDecodeError, KeyError):
                pass
        
        return ""
    
    def chat(self, user_message: str) -> str:
        """Send a message and get a response, handling tool calls."""
        log_prompt(user_message)
        self.messages.append({"role": "user", "content": user_message})
        
        if self.provider == "anthropic":
            return self._chat_anthropic()
        elif self.provider == "openai":
            return self._chat_openai()
        elif self.provider == "google":
            return self._chat_google()
    
    # ── Anthropic (Claude) ──────────────────────────────────
    
    def _chat_anthropic(self) -> str:
        response = self._call_anthropic()
        
        while response.stop_reason == "tool_use":
            assistant_content = response.content
            self.messages.append({"role": "assistant", "content": assistant_content})
            
            tool_results = []
            for block in assistant_content:
                if block.type == "tool_use":
                    result = self._run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            
            self.messages.append({"role": "user", "content": tool_results})
            response = self._call_anthropic()
        
        text = "\n".join(b.text for b in response.content if hasattr(b, 'text'))
        self.messages.append({"role": "assistant", "content": text})
        return text
    
    def _get_system_prompt(self):
        """System prompt with learned user preferences injected."""
        prompt = SYSTEM_PROMPT
        if self._personalized_prompt:
            prompt += "\n" + self._personalized_prompt
        return prompt

    def _call_anthropic(self):
        timer = APICallTimer(self.provider, self.model, self._dataset_in_context)
        timer.__enter__()
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.config.get("max_tokens", 8192),
                system=self._get_system_prompt(),
                tools=self.tools,
                messages=self.messages,
            )
            usage = getattr(response, "usage", None)
            timer.log(
                prompt_tokens=getattr(usage, "input_tokens", 0) if usage else 0,
                completion_tokens=getattr(usage, "output_tokens", 0) if usage else 0,
                tools_called=self._tools_this_turn,
            )
            self._tools_this_turn = []
            return response
        except Exception as e:
            timer.log(error=str(e))
            raise
    
    # ── OpenAI (GPT / o-series) ─────────────────────────────
    
    def _call_openai(self, openai_messages, openai_tools):
        """Single OpenAI API call with audit logging."""
        timer = APICallTimer(self.provider, self.model, self._dataset_in_context)
        timer.__enter__()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                tools=openai_tools if openai_tools else None,
                max_tokens=self.config.get("max_tokens", 8192),
            )
            usage = getattr(response, "usage", None)
            timer.log(
                prompt_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
                completion_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
                tools_called=self._tools_this_turn,
            )
            self._tools_this_turn = []
            return response
        except Exception as e:
            timer.log(error=str(e))
            raise

    def _chat_openai(self) -> str:
        openai_tools = self._tools_to_openai_format()
        openai_messages = self._messages_to_openai_format()
        
        response = self._call_openai(openai_messages, openai_tools)
        msg = response.choices[0].message
        
        # Tool call loop
        while msg.tool_calls:
            self.messages.append({"role": "assistant", "content": msg.content or "", "_tool_calls": [
                {"id": tc.id, "name": tc.function.name, "arguments": tc.function.arguments}
                for tc in msg.tool_calls
            ]})
            
            tool_results = []
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                result = self._run_tool(tc.function.name, args)
                tool_results.append({"tool_call_id": tc.id, "content": result})
            
            self.messages.append({"role": "tool_results", "content": tool_results})
            
            openai_messages = self._messages_to_openai_format()
            response = self._call_openai(openai_messages, openai_tools)
            msg = response.choices[0].message
        
        text = msg.content or ""
        self.messages.append({"role": "assistant", "content": text})
        return text
    
    def _tools_to_openai_format(self) -> list:
        """Convert Anthropic-style tools to OpenAI function calling format."""
        openai_tools = []
        for tool in self.tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("input_schema", {"type": "object", "properties": {}}),
                }
            })
        return openai_tools
    
    def _messages_to_openai_format(self) -> list:
        """Convert internal messages to OpenAI format."""
        msgs = [{"role": "system", "content": self._get_system_prompt()}]
        
        for m in self.messages:
            role = m["role"]
            content = m.get("content", "")
            
            if role == "user":
                if isinstance(content, list):
                    # Tool results
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "tool_result":
                            msgs.append({
                                "role": "tool",
                                "tool_call_id": item["tool_use_id"],
                                "content": item["content"],
                            })
                else:
                    msgs.append({"role": "user", "content": content})
            
            elif role == "assistant":
                if isinstance(content, str):
                    msgs.append({"role": "assistant", "content": content})
                elif isinstance(content, list):
                    # Anthropic content blocks with tool_use
                    text_parts = []
                    tool_calls = []
                    for block in content:
                        if hasattr(block, 'text'):
                            text_parts.append(block.text)
                        elif hasattr(block, 'type') and block.type == 'tool_use':
                            tool_calls.append({
                                "id": block.id,
                                "type": "function",
                                "function": {
                                    "name": block.name,
                                    "arguments": json.dumps(block.input),
                                }
                            })
                    
                    msg_dict = {"role": "assistant", "content": "\n".join(text_parts) or None}
                    if tool_calls:
                        msg_dict["tool_calls"] = tool_calls
                    msgs.append(msg_dict)
                elif "_tool_calls" in m:
                    tool_calls = [{
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]}
                    } for tc in m["_tool_calls"]]
                    msgs.append({"role": "assistant", "content": content or None, "tool_calls": tool_calls})
            
            elif role == "tool_results":
                for tr in content:
                    msgs.append({
                        "role": "tool",
                        "tool_call_id": tr["tool_call_id"],
                        "content": tr["content"],
                    })
        
        return msgs
    
    # ── Google (Gemini) — using new google-genai SDK ───────
    
    def _chat_google(self) -> str:
        from google.genai import types
        
        # Build tool declarations for Gemini
        gemini_tools = self._tools_to_gemini_format()
        
        # Build contents from message history
        contents = self._messages_to_gemini_format()
        
        # Send request with tools
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=self._get_system_prompt(),
                tools=gemini_tools,
                max_output_tokens=self.config.get("max_tokens", 8192),
            ),
        )
        
        # Handle function calls in a loop
        while response.candidates and response.candidates[0].content.parts:
            has_function_call = False
            function_responses = []
            
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    has_function_call = True
                    fc = part.function_call
                    args = dict(fc.args) if fc.args else {}
                    result = self._run_tool(fc.name, args)
                    
                    function_responses.append(
                        types.Part.from_function_response(
                            name=fc.name,
                            response={"result": result},
                        )
                    )
            
            if not has_function_call:
                break
            
            # Append the model's response and tool results to contents
            contents.append(response.candidates[0].content)
            contents.append(types.Content(role="user", parts=function_responses))
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=self._get_system_prompt(),
                    tools=gemini_tools,
                    max_output_tokens=self.config.get("max_tokens", 8192),
                ),
            )
        
        text = response.text if hasattr(response, 'text') and response.text else ""
        if not text and response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text') and part.text:
                    text += part.text
        
        self.messages.append({"role": "assistant", "content": text})
        return text
    
    def _tools_to_gemini_format(self):
        """Convert tools to Gemini function declarations using new google-genai SDK."""
        from google.genai import types
        
        declarations = []
        for tool in self.tools:
            schema = tool.get("input_schema", {})
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            
            # Build property schemas
            prop_schemas = {}
            for name, prop in properties.items():
                prop_type = prop.get("type", "STRING").upper()
                # Map JSON Schema types to Gemini types
                type_map = {
                    "STRING": "STRING",
                    "NUMBER": "NUMBER",
                    "INTEGER": "INTEGER",
                    "BOOLEAN": "BOOLEAN",
                    "ARRAY": "ARRAY",
                    "OBJECT": "OBJECT",
                }
                schema_kwargs = {"type": type_map.get(prop_type, "STRING")}
                if "description" in prop:
                    schema_kwargs["description"] = prop["description"]
                if "enum" in prop:
                    schema_kwargs["enum"] = prop["enum"]
                # Gemini requires 'items' for array types
                if prop_type == "ARRAY":
                    items_schema = prop.get("items", {"type": "string"})
                    items_type = items_schema.get("type", "string").upper()
                    schema_kwargs["items"] = types.Schema(type=type_map.get(items_type, "STRING"))
                prop_schemas[name] = types.Schema(**schema_kwargs)
            
            func_decl = types.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"][:512],
                parameters=types.Schema(
                    type="OBJECT",
                    properties=prop_schemas,
                    required=required,
                ) if prop_schemas else None,
            )
            declarations.append(func_decl)
        
        return [types.Tool(function_declarations=declarations)]
    
    def _messages_to_gemini_format(self) -> list:
        """Convert messages to Gemini contents format."""
        from google.genai import types
        
        contents = []
        for m in self.messages:
            role = m["role"]
            content = m.get("content", "")
            if role == "user" and isinstance(content, str):
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=content)]))
            elif role == "assistant" and isinstance(content, str):
                contents.append(types.Content(role="model", parts=[types.Part.from_text(text=content)]))
        return contents
    
    # ── Shared ──────────────────────────────────────────────
    
    def _run_tool(self, name: str, args: dict) -> str:
        """Execute a tool, display progress, and log for learning."""
        console.print(f"  [dim]→ {name}({_format_args(args)})[/dim]")
        result = execute_tool(name, args)
        result_preview = result[:200] + "..." if len(result) > 200 else result
        console.print(f"  [dim green]✓ {result_preview}[/dim green]")

        # Track dataset presence for audit
        if name == "load_dataset":
            self._dataset_in_context = True
        self._tools_this_turn.append(name)

        # Log for adaptive learning
        log_tool_call(name, args, result_preview)
        self._tool_call_count += 1

        # Re-learn every 20 tool calls to update preferences mid-session
        if self._tool_call_count % 20 == 0:
            learn_from_history()
            self._personalized_prompt = get_personalized_prompt_section()

        return result
    
    def reset(self):
        """Clear conversation history."""
        self.messages = []


def _format_args(args: dict) -> str:
    """Format tool args for display."""
    parts = []
    for k, v in list(args.items())[:3]:
        if isinstance(v, str) and len(v) > 50:
            v = v[:50] + "..."
        parts.append(f"{k}={v}")
    return ", ".join(parts)
