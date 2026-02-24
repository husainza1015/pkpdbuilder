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
            self.client = Anthropic(api_key=self.api_key)
        elif self.provider in ("openai", "deepseek", "xai", "ollama"):
            from openai import OpenAI
            provider_info = PROVIDERS.get(self.provider, {})
            base_url = provider_info.get("base_url")
            api_key = self.api_key if self.provider != "ollama" else "ollama"
            self.client = OpenAI(api_key=api_key, **({"base_url": base_url} if base_url else {}))
        elif self.provider == "google":
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def chat(self, user_message: str) -> str:
        """Send a message and get a response, handling tool calls."""
        log_prompt(user_message)
        self.messages.append({"role": "user", "content": user_message})
        
        if self.provider == "anthropic":
            return self._chat_anthropic()
        elif self.provider in ("openai", "deepseek", "xai", "ollama"):
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
    
    # ── Google (Gemini) ─────────────────────────────────────
    
    def _chat_google(self) -> str:
        from google.generativeai.types import content_types
        import google.generativeai as genai
        
        # Build tool declarations for Gemini
        gemini_tools = self._tools_to_gemini_format()
        
        model = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=self._get_system_prompt(),
            tools=gemini_tools,
        )
        
        chat = model.start_chat(history=self._messages_to_gemini_format())
        
        # Send last user message
        last_msg = self.messages[-1]["content"]
        response = chat.send_message(last_msg)
        
        # Handle function calls
        while response.candidates[0].content.parts:
            has_function_call = False
            tool_responses = []
            
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    has_function_call = True
                    fc = part.function_call
                    args = dict(fc.args) if fc.args else {}
                    console.print(f"  [dim]→ {fc.name}({_format_args(args)})[/dim]")
                    result = execute_tool(fc.name, args)
                    result_preview = result[:200] + "..." if len(result) > 200 else result
                    console.print(f"  [dim green]✓ {result_preview}[/dim green]")
                    
                    tool_responses.append(
                        genai.protos.Part(function_response=genai.protos.FunctionResponse(
                            name=fc.name,
                            response={"result": result}
                        ))
                    )
            
            if not has_function_call:
                break
            
            response = chat.send_message(tool_responses)
        
        text = response.text if hasattr(response, 'text') else str(response.candidates[0].content.parts[0].text)
        self.messages.append({"role": "assistant", "content": text})
        return text
    
    def _tools_to_gemini_format(self):
        """Convert tools to Gemini function declarations."""
        import google.generativeai as genai
        
        declarations = []
        for tool in self.tools:
            schema = tool.get("input_schema", {})
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            
            # Clean properties for Gemini (no unsupported fields)
            clean_props = {}
            for name, prop in properties.items():
                clean = {"type": prop.get("type", "string").upper()}
                if "description" in prop:
                    clean["description"] = prop["description"]
                if "enum" in prop:
                    clean["enum"] = prop["enum"]
                clean_props[name] = clean
            
            declarations.append(genai.protos.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"][:512],  # Gemini limit
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={k: genai.protos.Schema(**v) for k, v in clean_props.items()},
                    required=required,
                ) if clean_props else None,
            ))
        
        return [genai.protos.Tool(function_declarations=declarations)]
    
    def _messages_to_gemini_format(self) -> list:
        """Convert messages to Gemini history format (excluding last user msg)."""
        history = []
        for m in self.messages[:-1]:  # Exclude last (sent separately)
            role = m["role"]
            content = m.get("content", "")
            if role == "user" and isinstance(content, str):
                history.append({"role": "user", "parts": [content]})
            elif role == "assistant" and isinstance(content, str):
                history.append({"role": "model", "parts": [content]})
        return history
    
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
