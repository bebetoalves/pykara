"""Text rendering for template bodies."""

from __future__ import annotations

import re
from types import CodeType

from pykara.engine.variable_context import Environment
from pykara.errors import (
    BoundMethodInExpressionError,
    TemplateCodeError,
    TemplateRuntimeError,
    UnknownVariableError,
)

_VARIABLE_PATTERN = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")
_EXPRESSION_PATTERN = re.compile(r"!(.+?)!", re.DOTALL)


class TextRenderer:
    """Render template text by expanding variables and expressions."""

    def __init__(self) -> None:
        self._compiled_expression_cache: dict[str, CodeType] = {}

    def render(self, text: str, env: Environment) -> str:
        """Expand `$var` and `!expr!` in one template string."""

        if "$" not in text and "!" not in text:
            return text

        rendered = text
        if "$" in rendered:
            rendered = _VARIABLE_PATTERN.sub(
                lambda match: self._replace_variable(match.group(1), text, env),
                rendered,
            )
        if "!" not in rendered:
            return rendered
        return _EXPRESSION_PATTERN.sub(
            lambda match: self._replace_expression(match.group(1), env),
            rendered,
        )

    def evaluate_expression(
        self,
        expression: str,
        env: Environment,
    ) -> object:
        """Evaluate one inline expression in the closed environment."""

        try:
            compiled = self._compiled_expression_cache.get(expression)
            if compiled is None:
                compiled = compile(expression, "<pykara-expression>", "eval")
                self._compiled_expression_cache[expression] = compiled
        except SyntaxError as error:
            raise TemplateCodeError(expression, error) from error

        try:
            result = eval(  # noqa: S307
                compiled,
                {"__builtins__": {}},
                env.as_dict(),
            )
        except Exception as error:  # pragma: no cover - exercised in tests
            raise TemplateRuntimeError(expression, error) from error

        if callable(result):
            raise BoundMethodInExpressionError(
                expression=expression,
                result_type=type(result).__name__,
            )
        return result

    def _replace_variable(
        self,
        variable_name: str,
        template_text: str,
        env: Environment,
    ) -> str:
        variables = env.variable_dict()
        if variable_name not in variables:
            raise UnknownVariableError(variable_name, template_text)
        return str(variables[variable_name])

    def _replace_expression(self, expression: str, env: Environment) -> str:
        return str(self.evaluate_expression(expression, env))
