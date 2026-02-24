"""Tool registry — maps tool names to definitions and handlers."""


TOOL_DEFINITIONS = []
TOOL_HANDLERS = {}


def register_tool(name: str, description: str, parameters: dict):
    """Decorator to register a tool for Claude."""
    def decorator(func):
        TOOL_DEFINITIONS.append({
            "name": name,
            "description": description,
            "input_schema": {
                "type": "object",
                "properties": parameters.get("properties", {}),
                "required": parameters.get("required", []),
            }
        })
        TOOL_HANDLERS[name] = func
        return func
    return decorator


def get_all_tools() -> list:
    """Return all tool definitions for Claude API."""
    return TOOL_DEFINITIONS


def execute_tool(name: str, args: dict) -> str:
    """Execute a tool by name with given args."""
    if name not in TOOL_HANDLERS:
        return f"Unknown tool: {name}"
    try:
        result = TOOL_HANDLERS[name](**args)
        if isinstance(result, dict):
            import json
            return json.dumps(result, indent=2, default=str)
        return str(result)
    except Exception as e:
        return f"Tool error: {e}"
