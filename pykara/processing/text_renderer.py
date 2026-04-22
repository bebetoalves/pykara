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
from pykara.specification.expressions import EXPRESSION_PROPERTY_SPECIFICATIONS

_VARIABLE_PATTERN = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")
_EXPRESSION_PATTERN = re.compile(r"!(.+?)!", re.DOTALL)
_ALIAS_EXPRESSION_BY_VARIABLE = {
    spec.source_variable: f"{object_name}.{property_name}"
    for (object_name, property_name), spec in (
        EXPRESSION_PROPERTY_SPECIFICATIONS.items()
    )
    if spec.source_variable is not None
}


class TextRenderer:
    """Render template text by expanding variables and expressions."""

    def __init__(self) -> None:
        self._compiled_expression_cache: dict[str, CodeType] = {}

    def render(self, text: str, env: Environment) -> str:
        """Expand `$var` and `!expr!` in one template string."""

        if "$" not in text and "!" not in text:
            return text

        rendered: list[str] = []
        position = 0
        while position < len(text):
            variable_match = _VARIABLE_PATTERN.match(text, position)
            if variable_match is not None:
                rendered.append(
                    self._replace_variable(
                        variable_match.group(1),
                        text,
                        env.variable_dict(),
                    )
                )
                position = variable_match.end()
                continue

            expression_match = _EXPRESSION_PATTERN.match(text, position)
            if expression_match is not None:
                expression = self._render_expression_variables(
                    expression_match.group(1),
                    text,
                    env,
                )
                rendered.append(
                    self._replace_expression(
                        expression,
                        env.as_dict(),
                    )
                )
                position = expression_match.end()
                continue

            rendered.append(text[position])
            position += 1

        return "".join(rendered)

    def evaluate_expression(
        self,
        expression: str,
        env: Environment,
    ) -> object:
        """Evaluate one inline expression in the closed environment."""

        compiled = self._compile_expression(expression)
        return self._evaluate_compiled(expression, compiled, env.as_dict())

    def _replace_variable(
        self,
        variable_name: str,
        template_text: str,
        variables: dict[str, object],
    ) -> str:
        if variable_name not in variables:
            raise UnknownVariableError(variable_name, template_text)
        return str(variables[variable_name])

    def _render_expression_variables(
        self,
        expression: str,
        template_text: str,
        env: Environment,
    ) -> str:
        if "$" not in expression:
            return expression
        variables = env.variable_dict()
        return _VARIABLE_PATTERN.sub(
            lambda match: self._replace_expression_variable(
                match.group(1),
                template_text,
                variables,
            ),
            expression,
        )

    def _replace_expression_variable(
        self,
        variable_name: str,
        template_text: str,
        variables: dict[str, object],
    ) -> str:
        if variable_name in _ALIAS_EXPRESSION_BY_VARIABLE:
            return _ALIAS_EXPRESSION_BY_VARIABLE[variable_name]
        return self._replace_variable(variable_name, template_text, variables)

    def _replace_expression(
        self,
        expression: str,
        namespace: dict[str, object],
    ) -> str:
        compiled = self._compile_expression(expression)
        result = self._evaluate_compiled(expression, compiled, namespace)
        if result is None:
            return ""
        try:
            return str(result)
        except Exception as error:  # pragma: no cover - exercised in tests
            raise TemplateRuntimeError(expression, error) from error

    def _compile_expression(self, expression: str) -> CodeType:
        try:
            compiled = self._compiled_expression_cache.get(expression)
            if compiled is None:
                compiled = compile(expression, "<pykara-expression>", "eval")
                self._compiled_expression_cache[expression] = compiled
        except SyntaxError as error:
            raise TemplateCodeError(expression, error) from error
        return compiled

    def _evaluate_compiled(
        self,
        expression: str,
        compiled: CodeType,
        namespace: dict[str, object],
    ) -> object:
        try:
            result = eval(  # noqa: S307
                compiled,
                {"__builtins__": {}},
                namespace,
            )
        except Exception as error:  # pragma: no cover - exercised in tests
            raise TemplateRuntimeError(expression, error) from error

        if callable(result):
            raise BoundMethodInExpressionError(
                expression=expression,
                result_type=type(result).__name__,
            )
        return result
