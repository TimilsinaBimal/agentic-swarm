import inspect
from datetime import datetime


def debug_print(debug: bool, *args: str) -> None:
    if not debug:
        return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = " ".join(map(str, args))
    print(f"\033[97m[\033[90m{timestamp}\033[97m]\033[90m {message}\033[0m")


def merge_fields(target, source):
    for key, value in source.items():
        if isinstance(value, str):
            target[key] += value
        elif value is not None and isinstance(value, dict):
            merge_fields(target[key], value)


def merge_chunk(final_response: dict, delta: dict) -> None:
    delta.pop("role", None)
    merge_fields(final_response, delta)

    tool_calls = delta.get("tool_calls")
    if tool_calls and len(tool_calls) > 0:
        index = tool_calls[0].pop("index")
        merge_fields(final_response["tool_calls"][index], tool_calls[0])

def function_to_json(func) -> dict:
    """
    Converts a Python function into a JSON-serializable dictionary
    that describes the function's signature, including its name,
    description, and parameters.

    Args:
        func: The function to be converted.

    Returns:
        A dictionary representing the function's signature in JSON format.
    """
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
        type(None): "null",
    }

    try:
        signature = inspect.signature(func)
    except ValueError as e:
        raise ValueError(
            f"Failed to get signature for function {func.__name__}: {str(e)}"
        )

    # Extract parameter descriptions from docstring
    param_descriptions = {}
    func_description = ""
    if func.__doc__:
        docstring_lines = func.__doc__.split('\n')
        in_args_section = False
        for line in docstring_lines:
            line = line.strip()
            if line.lower().startswith('args:'):
                in_args_section = True
                continue

            elif in_args_section:
                if not line:  # Empty line
                    in_args_section = False
                    continue
                if line.startswith(('Returns:', 'Raises:')):
                    break
                if ':' in line:
                    param_name, description = line.split(':', 1)
                    param_name = param_name.strip()
                    # if param_name also contains types, remove them
                    if '(' in param_name:
                        param_name = param_name.split('(')[0].strip()
                    description = description.strip()
                    param_descriptions[param_name] = description
            else:
                func_description += line + ' '

    parameters = {}
    for param in signature.parameters.values():
        try:
            param_type = type_map.get(param.annotation, "string")
        except KeyError as e:
            raise KeyError(
                f"Unknown type annotation {param.annotation} for parameter {param.name}: {str(e)}"
            )
        parameters[param.name] = {
            "type": param_type,
            "description": param_descriptions.get(param.name, "")
        }

    required = [
        param.name
        for param in signature.parameters.values()
        if param.default == inspect._empty
    ]

    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": func_description.strip() or "",
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required,
            },
        },
    }
