from ..interface import console, Panel

def calculator(expression, *, session, client, config, **kwargs):
    console.print(Panel(f"Tool: Calculator\nExpression: '{expression}'", title="[bold dark_orange]Tool Call[/]", border_style="dark_orange", expand=False))
    try:
        allowed_chars = "0123456789+-*/(). "
        if not all(char in allowed_chars for char in expression):
            raise ValueError("Expression contains disallowed characters.")
        if any(c.isalpha() for c in expression):
            raise ValueError("Expression contains alphabetic characters and cannot be evaluated for security reasons.")
        result = eval(expression)
        return {"status": "success", "expression": expression, "result": str(result)}
    except Exception as e:
        return {"status": "error", "expression": expression, "message": f"Calculator error for expression '{expression}': {str(e)}"}
