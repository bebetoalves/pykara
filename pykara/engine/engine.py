"""Core engine implementation."""

from __future__ import annotations

import ast
import random
import re
from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import replace
from types import CodeType
from typing import cast

from pykara.data import Event, Metadata, Style
from pykara.data.events.karaoke import Karaoke, Syllable, Word
from pykara.declaration import Scope
from pykara.declaration.template import LoopDescriptor
from pykara.engine.variable_context import (
    Environment,
    GeneratedLine,
    LoopState,
)
from pykara.errors import (
    BoundMethodInExpressionError,
    ReservedNameError,
    TemplateCodeError,
    TemplateRuntimeError,
    UnknownStyleReferenceError,
)
from pykara.parsing import (
    CodeDeclaration,
    ParsedDeclarations,
    PatchDeclaration,
    TemplateDeclaration,
)
from pykara.parsing.karaoke_parser import KaraokeParser
from pykara.processing.line_preprocessor import (
    LinePreprocessor,
    PositionedLine,
)
from pykara.processing.text_renderer import TextRenderer

_PLAIN_WORD_PATTERN = re.compile(r"[ \t]*[^ \t]+")
_TEMPLATE_VARIABLE_PATTERN = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")


class _AssignedNameCollector(ast.NodeVisitor):
    """Collect module-scope names bound by a code declaration."""

    def __init__(self) -> None:
        self.names: set[str] = set()

    def _visit_function_definition(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        self.names.add(node.name)
        for decorator in node.decorator_list:
            self.visit(decorator)
        if node.returns is not None:
            self.visit(node.returns)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function_definition(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function_definition(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.names.add(node.name)
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            self.names.add(node.id)

    def visit_alias(self, node: ast.alias) -> None:
        self.names.add(node.asname or node.name.split(".", 1)[0])

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name is not None:
            self.names.add(node.name)
        if node.type is not None:
            self.visit(node.type)
        for statement in node.body:
            self.visit(statement)

    def _visit_comprehension(
        self,
        node: ast.ListComp | ast.SetComp | ast.GeneratorExp,
    ) -> None:
        self.visit(node.elt)
        for generator in node.generators:
            self.visit(generator.iter)
            for condition in generator.ifs:
                self.visit(condition)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comprehension(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_comprehension(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self.visit(node.key)
        self.visit(node.value)
        for generator in node.generators:
            self.visit(generator.iter)
            for condition in generator.ifs:
                self.visit(condition)


class _CodeRunner:
    """Compile and execute code declarations inside the environment."""

    def __init__(self) -> None:
        self._compiled_code_cache: dict[str, CodeType] = {}
        self._assigned_name_cache: dict[str, frozenset[str]] = {}

    def run(self, source: str, env: Environment) -> None:
        try:
            self._validate_reserved_assignments(source, env.reserved_names())
            compiled = self._compiled_code_cache.get(source)
            if compiled is None:
                compiled = compile(source, "<pykara-code>", "exec")
                self._compiled_code_cache[source] = compiled
        except SyntaxError as error:
            raise TemplateCodeError(source, error) from error

        namespace = env.as_dict()
        reserved_names = set(namespace) - set(env.user_namespace)
        namespace["__builtins__"] = {}
        try:
            exec(compiled, namespace, namespace)  # noqa: S102
        except BoundMethodInExpressionError:
            raise
        except Exception as error:  # pragma: no cover - exercised in tests
            raise TemplateRuntimeError(source, error) from error

        env.user_namespace.update(
            {
                name: value
                for name, value in namespace.items()
                if (
                    name not in reserved_names
                    and name not in env.reserved_names()
                    and name != "__builtins__"
                )
            }
        )

    def _validate_reserved_assignments(
        self,
        source: str,
        reserved_names: frozenset[str],
    ) -> None:
        assigned_names = self._assigned_name_cache.get(source)
        if assigned_names is None:
            try:
                tree = ast.parse(source, filename="<pykara-code>", mode="exec")
            except SyntaxError as error:
                raise TemplateCodeError(source, error) from error
            collector = _AssignedNameCollector()
            collector.visit(tree)
            assigned_names = frozenset(collector.names)
            self._assigned_name_cache[source] = assigned_names

        for name in sorted(assigned_names & reserved_names):
            raise ReservedNameError(name, source)


class Engine:
    """Apply karaoke effect templates to a parsed subtitle document."""

    def __init__(
        self,
        preprocessor: LinePreprocessor,
        rng_seed: int | None = None,
    ) -> None:
        self._preprocessor = preprocessor
        self._rng_seed = rng_seed
        self._karaoke_parser = KaraokeParser()
        self._renderer = TextRenderer()
        self._code_runner = _CodeRunner()

    def apply(
        self,
        events: list[Event],
        declarations: ParsedDeclarations,
        meta: Metadata,
        styles: dict[str, Style],
    ) -> list[Event]:
        """Execute template declarations without mutating the input.

        Args:
            events: Source document events.
            declarations: Parsed declarations grouped by scope.
            meta: Script-level metadata.
            styles: Style table indexed by style name.

        Returns:
            Generated ``fx`` events.
        """

        env = Environment(
            styles=styles,
            declaration="code",
            metadata=meta,
            rng=random.Random(self._rng_seed),  # noqa: S311
        )
        for declaration in declarations.setup:
            self._execute_setup_code(declaration, env)
        env.reference_style = None

        output_events: list[Event] = []
        karaoke_index = 0
        for event in events:
            if not self._is_karaoke_event(event):
                continue
            karaoke = self._karaoke_parser.parse(event)
            for reference_style_name in self._reference_style_names_for_event(
                declarations,
                event,
                env,
            ):
                reference_style = styles[reference_style_name]
                positioned = self._preprocessor.preprocess(
                    event,
                    karaoke,
                    meta,
                    reference_style,
                )
                line_output = self._apply_line(
                    event=event,
                    line_index=karaoke_index,
                    positioned=positioned,
                    declarations=declarations,
                    karaoke=karaoke,
                    env=env,
                    reference_style=reference_style,
                )
                output_events.extend(line_output)
            karaoke_index += 1

        return output_events

    def _apply_line(
        self,
        *,
        event: Event,
        line_index: int,
        positioned: PositionedLine,
        declarations: ParsedDeclarations,
        karaoke: Karaoke,
        env: Environment,
        reference_style: Style,
    ) -> list[Event]:
        env.source_line = event
        env.karaoke = karaoke
        env.line = None
        env.reference_style = reference_style
        env.word = None
        env.syl = None
        env.char = None
        words = self._iter_words(
            positioned.syllables,
            split_untimed=bool(declarations.word),
        )
        line_char_count = self._count_text_characters(positioned.syllables)
        env.retime_line_words = tuple(words)
        env.retime_line_syls = tuple(positioned.syllables)
        env.retime_line_chars = tuple(
            char
            for syllable in positioned.syllables
            for char in self._iter_char_syllables(env, syllable)
        )
        env.vars.set_line(
            index=line_index,
            start_time=event.start_time,
            end_time=event.end_time,
            width=positioned.width,
            height=positioned.height,
            left=positioned.left,
            center=positioned.center,
            right=positioned.right,
            top=positioned.top,
            middle=positioned.middle,
            bottom=positioned.bottom,
            x=positioned.x,
            y=positioned.y,
            syllable_count=len(karaoke.syllables),
            word_count=len(words),
        )

        output_events: list[Event] = []
        had_looping_line_template = False
        for declaration in declarations.line:
            if not self._declaration_applies_to_style(declaration, event):
                continue
            if not self._declaration_applies_to_reference_style(
                declaration,
                event,
                reference_style.name,
                env,
            ):
                continue
            if isinstance(declaration, CodeDeclaration):
                self._execute_code(declaration, env)
                continue

            descendants: Callable[[], list[Event]] | None = None
            if (
                declaration.modifiers.loops
                and self._line_descendants_reference_loops(
                    declaration,
                    declarations,
                )
            ):
                had_looping_line_template = True

                def render_line_descendants() -> list[Event]:
                    return self._apply_words(
                        event=event,
                        words=words,
                        line_char_count=line_char_count,
                        declarations=declarations,
                        env=env,
                    )

                descendants = render_line_descendants
            output_events.extend(
                self._render_line_template(
                    declaration,
                    event,
                    declarations,
                    env,
                    reference_style,
                    descendants,
                )
            )

        if not had_looping_line_template:
            output_events.extend(
                self._apply_words(
                    event=event,
                    words=words,
                    line_char_count=line_char_count,
                    declarations=declarations,
                    env=env,
                )
            )

        env.word = None
        env.syl = None
        return output_events

    def _execute_setup_code(
        self,
        declaration: CodeDeclaration,
        env: Environment,
    ) -> None:
        styles_token = declaration.modifiers.styles
        if styles_token is None:
            self._execute_code(declaration, env)
            return

        for style_name in self._resolve_reference_style_names(
            styles_token,
            env,
        ):
            env.reference_style = env.styles[style_name]
            self._execute_code(declaration, env)

    def _execute_code(
        self,
        declaration: CodeDeclaration,
        env: Environment,
    ) -> None:
        env.declaration = "code"
        env.active_code_scope = declaration.scope
        self._code_runner.run(declaration.body.source, env)

    def _render_line_template(
        self,
        declaration: TemplateDeclaration,
        source_event: Event,
        declarations: ParsedDeclarations,
        env: Environment,
        styleref: Style,
        descendants: Callable[[], list[Event]] | None,
    ) -> list[Event]:
        if (
            declaration.modifiers.no_blank
            and self._strip_karaoke_text(source_event.text).strip() == ""
        ):
            return []
        return self._loop_render(
            declaration,
            env,
            lambda: self._build_line_event(
                declaration,
                source_event,
                declarations,
                env,
                styleref,
            ),
            descendants,
        )

    def _render_syllable_template(
        self,
        declaration: TemplateDeclaration,
        source_event: Event,
        declarations: ParsedDeclarations,
        syllable: Syllable,
        env: Environment,
        descendants: Callable[[], list[Event]] | None,
    ) -> list[Event]:
        if declaration.modifiers.no_blank and self._is_blank_syllable(syllable):
            return []
        return self._loop_render(
            declaration,
            env,
            lambda: self._build_syllable_event(
                declaration,
                source_event,
                declarations,
                syllable,
                env,
            ),
            descendants,
        )

    def _render_word_template(
        self,
        declaration: TemplateDeclaration,
        source_event: Event,
        declarations: ParsedDeclarations,
        word: Word,
        env: Environment,
        descendants: Callable[[], list[Event]] | None,
    ) -> list[Event]:
        if declaration.modifiers.no_blank and word.trimmed_text == "":
            return []
        return self._loop_render(
            declaration,
            env,
            lambda: self._build_word_event(
                declaration,
                source_event,
                declarations,
                word,
                env,
            ),
            descendants,
        )

    def _render_char_template(
        self,
        declaration: TemplateDeclaration,
        source_event: Event,
        declarations: ParsedDeclarations,
        char_syllable: Syllable,
        env: Environment,
    ) -> list[Event]:
        if declaration.modifiers.no_blank and not char_syllable.text.strip():
            return []
        return self._loop_render(
            declaration,
            env,
            lambda: self._build_char_event(
                declaration,
                source_event,
                declarations,
                char_syllable,
                env,
            ),
            None,
        )

    def _loop_render(
        self,
        declaration: TemplateDeclaration,
        env: Environment,
        builder: Callable[[], Event],
        descendants: Callable[[], list[Event]] | None,
    ) -> list[Event]:
        events: list[Event] = []

        for loop_state_set in self._iter_loop_state_products(
            declaration,
            env,
        ):
            env.push_loop_states(loop_state_set)
            try:
                if not self._passes_conditions(declaration, env):
                    continue
                events.append(builder())
                if descendants is not None:
                    events.extend(descendants())
            finally:
                env.pop_loop_states(len(loop_state_set))

        return events

    def _apply_words(
        self,
        *,
        event: Event,
        words: list[Word],
        line_char_count: int,
        declarations: ParsedDeclarations,
        env: Environment,
    ) -> list[Event]:
        output_events: list[Event] = []
        with self._preserved_word_scope(env):
            env.line_char_count = line_char_count
            next_char_index = 0
            for word in words:
                env.word = word
                env.vars.set_word(word)

                had_looping_word_template = False
                for declaration in declarations.word:
                    if not self._declaration_applies_to_style(
                        declaration,
                        event,
                    ):
                        continue
                    if not self._declaration_applies_to_current_reference_style(
                        declaration,
                        event,
                        env,
                    ):
                        continue
                    if isinstance(declaration, CodeDeclaration):
                        self._execute_code(declaration, env)
                        continue
                    if not self._passes_conditions(declaration, env):
                        continue

                    descendants: Callable[[], list[Event]] | None = None
                    if (
                        declaration.modifiers.loops
                        and self._word_descendants_reference_loops(
                            declaration,
                            declarations,
                        )
                    ):
                        had_looping_word_template = True
                        descendants = self._make_syllable_descendants(
                            event=event,
                            declarations=declarations,
                            syllables=word.syllables,
                            line_char_start_index=next_char_index,
                            env=env,
                        )
                    output_events.extend(
                        self._render_word_template(
                            declaration,
                            event,
                            declarations,
                            word,
                            env,
                            descendants,
                        )
                    )

                if not had_looping_word_template:
                    output_events.extend(
                        self._apply_syllables(
                            event=event,
                            declarations=declarations,
                            syllables=word.syllables,
                            line_char_start_index=next_char_index,
                            env=env,
                        )
                    )
                next_char_index += self._count_text_characters(word.syllables)
        return output_events

    def _make_syllable_descendants(
        self,
        *,
        event: Event,
        declarations: ParsedDeclarations,
        syllables: tuple[Syllable, ...],
        line_char_start_index: int,
        env: Environment,
    ) -> Callable[[], list[Event]]:
        def render_syllable_descendants() -> list[Event]:
            return self._apply_syllables(
                event=event,
                declarations=declarations,
                syllables=syllables,
                line_char_start_index=line_char_start_index,
                env=env,
            )

        return render_syllable_descendants

    def _apply_syllables(
        self,
        *,
        event: Event,
        declarations: ParsedDeclarations,
        syllables: tuple[Syllable, ...],
        line_char_start_index: int,
        env: Environment,
    ) -> list[Event]:
        output_events: list[Event] = []
        with self._preserved_syllable_scope(env):
            next_char_index = line_char_start_index
            for syllable in syllables:
                env.syl = syllable
                env.vars.set_syl(syllable)
                char_syllables = self._iter_char_syllables(env, syllable)
                env.retime_syl_chars = char_syllables

                had_looping_syl_template = False
                for declaration in declarations.syl:
                    if not self._declaration_applies_to_style(
                        declaration,
                        event,
                    ):
                        continue
                    if not self._declaration_applies_to_current_reference_style(
                        declaration,
                        event,
                        env,
                    ):
                        continue
                    if isinstance(declaration, CodeDeclaration):
                        self._execute_code(declaration, env)
                        continue
                    if not self._should_apply_template(
                        declaration,
                        env,
                        syllable,
                    ):
                        continue

                    descendants: Callable[[], list[Event]] | None = None
                    if (
                        declaration.modifiers.loops
                        and self._syl_descendants_reference_loops(
                            declaration,
                            declarations,
                        )
                    ):
                        had_looping_syl_template = True
                        descendants = self._make_char_descendants(
                            event=event,
                            declarations=declarations,
                            source_syllable=syllable,
                            char_syllables=char_syllables,
                            line_char_start_index=next_char_index,
                            env=env,
                        )
                    output_events.extend(
                        self._render_syllable_template(
                            declaration,
                            event,
                            declarations,
                            syllable,
                            env,
                            descendants,
                        )
                    )

                if not had_looping_syl_template:
                    output_events.extend(
                        self._apply_chars(
                            event=event,
                            declarations=declarations,
                            source_syllable=syllable,
                            char_syllables=char_syllables,
                            line_char_start_index=next_char_index,
                            env=env,
                        )
                    )
                next_char_index += len(char_syllables)
        return output_events

    def _make_char_descendants(
        self,
        *,
        event: Event,
        declarations: ParsedDeclarations,
        source_syllable: Syllable,
        char_syllables: tuple[Syllable, ...],
        line_char_start_index: int,
        env: Environment,
    ) -> Callable[[], list[Event]]:
        def render_char_descendants() -> list[Event]:
            return self._apply_chars(
                event=event,
                declarations=declarations,
                source_syllable=source_syllable,
                char_syllables=char_syllables,
                line_char_start_index=line_char_start_index,
                env=env,
            )

        return render_char_descendants

    def _apply_chars(
        self,
        *,
        event: Event,
        declarations: ParsedDeclarations,
        source_syllable: Syllable,
        char_syllables: tuple[Syllable, ...],
        line_char_start_index: int,
        env: Environment,
    ) -> list[Event]:
        output_events: list[Event] = []
        with self._preserved_char_scope(env):
            char_count = len(char_syllables)
            env.retime_syl_chars = char_syllables
            for char_index, char_syllable in enumerate(char_syllables):
                env.syl = source_syllable
                env.char = char_syllable
                env.char_index = line_char_start_index + char_index
                env.vars.set_syl(source_syllable)
                env.vars.set_char(
                    char_syllable,
                    char_count=char_count,
                    char_index=line_char_start_index + char_index,
                )

                for declaration in declarations.char:
                    if not self._declaration_applies_to_style(
                        declaration,
                        event,
                    ):
                        continue
                    if not self._declaration_applies_to_current_reference_style(
                        declaration,
                        event,
                        env,
                    ):
                        continue
                    if not self._should_apply_template(
                        declaration,
                        env,
                        source_syllable,
                    ):
                        continue
                    output_events.extend(
                        self._render_char_template(
                            declaration,
                            event,
                            declarations,
                            char_syllable,
                            env,
                        )
                    )
        return output_events

    @contextmanager
    def _preserved_word_scope(self, env: Environment) -> Iterator[None]:
        saved_vars = env.vars.snapshot_word_scope()
        saved_word = env.word
        saved_syl = env.syl
        saved_char = env.char
        saved_char_index = env.char_index
        saved_line_char_count = env.line_char_count
        saved_syl_chars = env.retime_syl_chars
        try:
            yield
        finally:
            env.vars.restore_word_scope(saved_vars)
            env.word = saved_word
            env.syl = saved_syl
            env.char = saved_char
            env.char_index = saved_char_index
            env.line_char_count = saved_line_char_count
            env.retime_syl_chars = saved_syl_chars

    @contextmanager
    def _preserved_syllable_scope(self, env: Environment) -> Iterator[None]:
        saved_vars = env.vars.snapshot_syllable_scope()
        saved_syl = env.syl
        saved_char = env.char
        saved_char_index = env.char_index
        saved_syl_chars = env.retime_syl_chars
        try:
            yield
        finally:
            env.vars.restore_syllable_scope(saved_vars)
            env.syl = saved_syl
            env.char = saved_char
            env.char_index = saved_char_index
            env.retime_syl_chars = saved_syl_chars

    @contextmanager
    def _preserved_char_scope(self, env: Environment) -> Iterator[None]:
        saved_vars = env.vars.snapshot_char_scope()
        saved_syl = env.syl
        saved_char = env.char
        saved_char_index = env.char_index
        saved_syl_chars = env.retime_syl_chars
        try:
            yield
        finally:
            env.vars.restore_char_scope(saved_vars)
            env.syl = saved_syl
            env.char = saved_char
            env.char_index = saved_char_index
            env.retime_syl_chars = saved_syl_chars

    def _iter_loop_state_products(
        self,
        declaration: TemplateDeclaration,
        env: Environment,
    ) -> Iterator[list[LoopState]]:
        declared_loops = declaration.modifiers.loops
        if not declared_loops:
            yield []
            return

        yield from self._expand_loop_states(
            declaration,
            env,
            index=0,
            current_states=[],
        )

    def _expand_loop_states(
        self,
        declaration: TemplateDeclaration,
        env: Environment,
        *,
        index: int,
        current_states: list[LoopState],
    ) -> Iterator[list[LoopState]]:
        if index >= len(declaration.modifiers.loops):
            yield list(current_states)
            return

        descriptor = declaration.modifiers.loops[index]
        iterations = self._resolve_loop_iterations(descriptor.iterations, env)
        for loop_index in range(iterations):
            current_states.append(
                LoopState(
                    name=descriptor.name,
                    index=loop_index,
                    total=iterations,
                    scope=declaration.scope,
                )
            )
            yield from self._expand_loop_states(
                declaration,
                env,
                index=index + 1,
                current_states=current_states,
            )
            current_states.pop()

    def _resolve_loop_iterations(
        self,
        iterations: int | str,
        env: Environment,
    ) -> int:
        if isinstance(iterations, int):
            return iterations

        try:
            rendered = self._renderer.render(f"!{iterations}!", env)
            resolved = int(float(rendered))
        except TemplateRuntimeError:
            raise
        except Exception as error:
            raise TemplateRuntimeError(iterations, error) from error

        if resolved <= 0:
            error = ValueError(
                "loop expression must resolve to a positive integer"
            )
            raise TemplateRuntimeError(iterations, error) from error

        return resolved

    def _build_line_event(
        self,
        declaration: TemplateDeclaration,
        source_event: Event,
        declarations: ParsedDeclarations,
        env: Environment,
        styleref: Style,
    ) -> Event:
        return self._build_scoped_event(
            declaration=declaration,
            source_event=source_event,
            patches=declarations.patch_line,
            styleref=styleref,
            suffix_text=self._strip_karaoke_text(source_event.text),
            env=env,
        )

    def _build_syllable_event(
        self,
        declaration: TemplateDeclaration,
        source_event: Event,
        declarations: ParsedDeclarations,
        syllable: Syllable,
        env: Environment,
    ) -> Event:
        return self._build_scoped_event(
            declaration=declaration,
            source_event=source_event,
            patches=declarations.patch_syl,
            styleref=syllable.style or env.styles[source_event.style],
            suffix_text=syllable.text,
            env=env,
        )

    def _build_word_event(
        self,
        declaration: TemplateDeclaration,
        source_event: Event,
        declarations: ParsedDeclarations,
        word: Word,
        env: Environment,
    ) -> Event:
        return self._build_scoped_event(
            declaration=declaration,
            source_event=source_event,
            patches=declarations.patch_word,
            styleref=word.style or env.styles[source_event.style],
            suffix_text=word.text,
            env=env,
        )

    def _build_char_event(
        self,
        declaration: TemplateDeclaration,
        source_event: Event,
        declarations: ParsedDeclarations,
        char_syllable: Syllable,
        env: Environment,
    ) -> Event:
        return self._build_scoped_event(
            declaration=declaration,
            source_event=source_event,
            patches=declarations.patch_char,
            styleref=char_syllable.style or env.styles[source_event.style],
            suffix_text=char_syllable.text,
            env=env,
        )

    def _build_scoped_event(
        self,
        *,
        declaration: TemplateDeclaration,
        source_event: Event,
        patches: list[PatchDeclaration],
        styleref: Style,
        suffix_text: str,
        env: Environment,
    ) -> Event:
        output = GeneratedLine.from_event(
            source_event,
            styleref,
        )
        output.style = output.styleref.name
        output.layer = declaration.layer
        env.line = output
        env.declaration = "template"
        env.begin_template_evaluation(
            declaration.scope,
            declaration.modifiers,
        )
        with self._apply_template_modifier_context(declaration, env):
            template_text = self._renderer.render(declaration.body.text, env)
            prepend_text = self._render_patch_text(
                template=declaration,
                source_event=source_event,
                patches=patches,
                env=env,
                prepend=True,
            )
            injected_text = self._render_patch_text(
                template=declaration,
                source_event=source_event,
                patches=patches,
                env=env,
                prepend=False,
            )
        if declaration.scope is Scope.LINE:
            output.text = prepend_text + injected_text + template_text
        else:
            output.text = prepend_text + template_text + injected_text
        if not declaration.modifiers.no_text:
            output.text += suffix_text
        return output.to_event()

    @contextmanager
    def _apply_template_modifier_context(
        self,
        declaration: TemplateDeclaration,
        env: Environment,
    ) -> Iterator[None]:
        saved_syl_i = env.vars.syl_i
        saved_syl_n = env.vars.syl_n
        saved_line_syls = env.active_line_syls
        try:
            if (
                declaration.scope is Scope.SYL
                and declaration.modifiers.no_blank
                and env.karaoke is not None
                and env.syl is not None
            ):
                visible_syllables = tuple(
                    syllable
                    for syllable in env.karaoke.syllables
                    if not self._is_blank_syllable(syllable)
                )
                if env.syl in visible_syllables:
                    env.active_line_syls = visible_syllables
                    visible_index = visible_syllables.index(env.syl)
                    env.vars.syl_i = visible_index
                    env.vars.syl_n = len(visible_syllables)
            yield
        finally:
            env.vars.syl_i = saved_syl_i
            env.vars.syl_n = saved_syl_n
            env.active_line_syls = saved_line_syls

    def _line_descendants_reference_loops(
        self,
        declaration: TemplateDeclaration,
        declarations: ParsedDeclarations,
    ) -> bool:
        descendants = [
            *declarations.word,
            *declarations.syl,
            *declarations.char,
            *declarations.patch_word,
            *declarations.patch_syl,
            *declarations.patch_char,
        ]
        return self._declarations_reference_loops(
            descendants,
            declaration.modifiers.loops,
        )

    def _word_descendants_reference_loops(
        self,
        declaration: TemplateDeclaration,
        declarations: ParsedDeclarations,
    ) -> bool:
        descendants = [
            *declarations.syl,
            *declarations.char,
            *declarations.patch_syl,
            *declarations.patch_char,
        ]
        return self._declarations_reference_loops(
            descendants,
            declaration.modifiers.loops,
        )

    def _syl_descendants_reference_loops(
        self,
        declaration: TemplateDeclaration,
        declarations: ParsedDeclarations,
    ) -> bool:
        descendants = [
            *declarations.char,
            *declarations.patch_char,
        ]
        return self._declarations_reference_loops(
            descendants,
            declaration.modifiers.loops,
        )

    def _declarations_reference_loops(
        self,
        declarations: Sequence[
            TemplateDeclaration | CodeDeclaration | PatchDeclaration
        ],
        loops: tuple[LoopDescriptor, ...],
    ) -> bool:
        loop_variable_names = self._loop_variable_names(loops)
        return any(
            isinstance(declaration, (TemplateDeclaration, PatchDeclaration))
            and bool(
                self._template_variable_names(declaration) & loop_variable_names
            )
            for declaration in declarations
        )

    def _loop_variable_names(
        self,
        loops: tuple[LoopDescriptor, ...],
    ) -> frozenset[str]:
        variable_names: set[str] = set()
        for loop in loops:
            variable_names.add(f"loop_{loop.name}_i")
            variable_names.add(f"loop_{loop.name}_n")
        if len(loops) == 1:
            variable_names.update({"loop_i", "loop_n"})
        return frozenset(variable_names)

    def _template_variable_names(
        self,
        declaration: TemplateDeclaration | PatchDeclaration,
    ) -> frozenset[str]:
        variable_names = set(
            _TEMPLATE_VARIABLE_PATTERN.findall(declaration.body.text)
        )
        if declaration.modifiers.when is not None:
            variable_names.update(
                _TEMPLATE_VARIABLE_PATTERN.findall(
                    declaration.modifiers.when,
                )
            )
        if declaration.modifiers.unless is not None:
            variable_names.update(
                _TEMPLATE_VARIABLE_PATTERN.findall(
                    declaration.modifiers.unless,
                )
            )
        return frozenset(variable_names)

    def _render_patch_text(
        self,
        *,
        template: TemplateDeclaration,
        source_event: Event,
        patches: list[PatchDeclaration],
        env: Environment,
        prepend: bool,
    ) -> str:
        rendered: list[str] = []
        for patch in patches:
            if patch.modifiers.prepend is not prepend:
                continue
            if not self._patch_applies_to_template(
                patch=patch,
                template=template,
                source_event=source_event,
                env=env,
            ):
                continue
            rendered.append(self._renderer.render(patch.body.text, env))
        return "".join(rendered)

    def _patch_applies_to_template(
        self,
        *,
        patch: PatchDeclaration,
        template: TemplateDeclaration,
        source_event: Event,
        env: Environment,
    ) -> bool:
        if patch.scope is not template.scope:
            return False
        if not self._patch_applies_to_style(
            patch=patch,
            template=template,
            source_event=source_event,
        ):
            return False
        if (
            patch.modifiers.for_actor is not None
            and patch.modifiers.for_actor != template.actor
        ):
            return False
        if patch.modifiers.layer is not None:
            if env.line is None or env.line.layer != patch.modifiers.layer:
                return False
        if patch.modifiers.fx is not None:
            if env.syl is None or env.syl.inline_fx != patch.modifiers.fx:
                return False
        if not self._passes_patch_conditions(patch, env):
            return False
        return True

    def _patch_applies_to_style(
        self,
        *,
        patch: PatchDeclaration,
        template: TemplateDeclaration,
        source_event: Event,
    ) -> bool:
        if self._declaration_reference_styles_token(template) is None:
            return self._declaration_applies_to_style(patch, source_event)
        if template.style:
            return not patch.style or patch.style == template.style
        return not patch.style or patch.style == source_event.style

    def _passes_conditions(
        self,
        declaration: TemplateDeclaration,
        env: Environment,
    ) -> bool:
        with self._apply_template_modifier_context(declaration, env):
            if declaration.modifiers.when is not None and not bool(
                self._renderer.evaluate_expression(
                    declaration.modifiers.when,
                    env,
                )
            ):
                return False
            if declaration.modifiers.unless is not None and bool(
                self._renderer.evaluate_expression(
                    declaration.modifiers.unless,
                    env,
                )
            ):
                return False
        return True

    def _passes_patch_conditions(
        self,
        declaration: PatchDeclaration,
        env: Environment,
    ) -> bool:
        if declaration.modifiers.when is not None and not bool(
            self._renderer.evaluate_expression(
                declaration.modifiers.when,
                env,
            )
        ):
            return False
        if declaration.modifiers.unless is not None and bool(
            self._renderer.evaluate_expression(
                declaration.modifiers.unless,
                env,
            )
        ):
            return False
        return True

    def _should_apply_template(
        self,
        declaration: TemplateDeclaration,
        env: Environment,
        syllable: Syllable,
    ) -> bool:
        if not self._passes_conditions(declaration, env):
            return False
        if declaration.modifiers.fx is not None:
            return declaration.modifiers.fx == syllable.inline_fx
        return True

    def _declaration_applies_to_style(
        self,
        declaration: TemplateDeclaration | CodeDeclaration | PatchDeclaration,
        event: Event,
    ) -> bool:
        if (
            not isinstance(declaration, PatchDeclaration)
            and self._declaration_reference_styles_token(declaration)
            is not None
        ):
            return True
        return not declaration.style or declaration.style == event.style

    def _declaration_applies_to_current_reference_style(
        self,
        declaration: TemplateDeclaration | CodeDeclaration,
        event: Event,
        env: Environment,
    ) -> bool:
        return self._declaration_applies_to_reference_style(
            declaration,
            event,
            self._current_reference_style_name(event, env),
            env,
        )

    def _current_reference_style_name(
        self,
        event: Event,
        env: Environment,
    ) -> str:
        if env.reference_style is not None:
            return env.reference_style.name
        return event.style

    def _declaration_applies_to_reference_style(
        self,
        declaration: TemplateDeclaration | CodeDeclaration,
        event: Event,
        reference_style_name: str,
        env: Environment,
    ) -> bool:
        reference_style_names = self._reference_style_names_for_declaration(
            declaration,
            event,
            env,
        )
        return reference_style_name in reference_style_names

    def _declaration_reference_styles_token(
        self,
        declaration: TemplateDeclaration | CodeDeclaration,
    ) -> str | None:
        if isinstance(declaration, TemplateDeclaration):
            return declaration.modifiers.styles
        return declaration.modifiers.styles

    def _reference_style_names_for_event(
        self,
        declarations: ParsedDeclarations,
        event: Event,
        env: Environment,
    ) -> tuple[str, ...]:
        names: list[str] = []
        for declaration in self._scoped_declarations(declarations):
            if not self._declaration_applies_to_style(declaration, event):
                continue
            for style_name in self._reference_style_names_for_declaration(
                declaration,
                event,
                env,
            ):
                if style_name not in names:
                    names.append(style_name)
        return tuple(names)

    def _reference_style_names_for_declaration(
        self,
        declaration: TemplateDeclaration | CodeDeclaration,
        event: Event,
        env: Environment,
    ) -> tuple[str, ...]:
        styles_token = self._declaration_reference_styles_token(declaration)
        if styles_token is None:
            return (event.style,)
        style_names = self._resolve_reference_style_names(styles_token, env)
        if event.style not in style_names:
            return ()
        return (event.style,)

    def _scoped_declarations(
        self,
        declarations: ParsedDeclarations,
    ) -> tuple[TemplateDeclaration | CodeDeclaration, ...]:
        return (
            *declarations.line,
            *declarations.word,
            *declarations.syl,
            *declarations.char,
        )

    def _resolve_reference_style_names(
        self,
        styles_token: str,
        env: Environment,
    ) -> tuple[str, ...]:
        value = env.user_namespace.get(styles_token)
        if isinstance(value, tuple):
            raw_style_names = cast(tuple[object, ...], value)
        else:
            error = TypeError(
                "styles modifier must resolve to a tuple of style names"
            )
            raise TemplateRuntimeError(styles_token, error) from error

        style_names: list[str] = []
        for style_name in raw_style_names:
            if not isinstance(style_name, str):
                error = TypeError(
                    "styles modifier tuple must contain only style names"
                )
                raise TemplateRuntimeError(styles_token, error) from error
            if style_name not in env.styles:
                raise UnknownStyleReferenceError(style_name, styles_token)
            style_names.append(style_name)
        return tuple(style_names)

    def _iter_char_syllables(
        self,
        env: Environment,
        syllable: Syllable,
    ) -> tuple[Syllable, ...]:
        cache_key = id(syllable)
        cached = env.char_syllable_cache.get(cache_key)
        if cached is not None:
            return cached

        characters: list[Syllable] = []
        if syllable.style is None:
            return ()

        current_left = syllable.left
        for index, char in enumerate(syllable.text):
            measurement = self._preprocessor.extents.measure(
                syllable.style,
                char,
            )
            width = measurement.width
            char_left = current_left
            char_right = char_left + width
            characters.append(
                Syllable(
                    index=index,
                    raw_text=char,
                    text=char,
                    trimmed_text=char.strip(),
                    prespace="",
                    postspace="",
                    start_time=syllable.start_time,
                    end_time=syllable.end_time,
                    duration=syllable.duration,
                    kdur=syllable.kdur,
                    tag=syllable.tag,
                    inline_fx=syllable.inline_fx,
                    highlights=[],
                    style=syllable.style,
                    width=width,
                    height=syllable.height,
                    prespacewidth=0.0,
                    postspacewidth=0.0,
                    left=char_left,
                    center=char_left + width / 2,
                    right=char_right,
                    top=syllable.top,
                    middle=syllable.middle,
                    bottom=syllable.bottom,
                    x=char_left + width / 2,
                    y=syllable.y,
                )
            )
            current_left = char_right
        resolved = tuple(characters)
        env.char_syllable_cache[cache_key] = resolved
        return resolved

    def _count_text_characters(self, syllables: tuple[Syllable, ...]) -> int:
        return sum(len(syllable.text) for syllable in syllables)

    def _iter_words(
        self,
        syllables: tuple[Syllable, ...],
        *,
        split_untimed: bool = False,
    ) -> list[Word]:
        words: list[Word] = []
        current_syllables: list[Syllable] = []

        def append_current() -> None:
            if not current_syllables:
                return
            words.append(self._build_word(len(words), tuple(current_syllables)))
            current_syllables.clear()

        iterable_syllables: Iterable[Syllable]
        if split_untimed:
            iterable_syllables = self._iter_word_syllables(syllables)
        else:
            iterable_syllables = syllables

        for syllable in iterable_syllables:
            if current_syllables and syllable.prespace:
                append_current()
            current_syllables.append(syllable)
            if syllable.postspace:
                append_current()

        append_current()
        return words

    def _iter_word_syllables(
        self,
        syllables: tuple[Syllable, ...],
    ) -> Iterator[Syllable]:
        for syllable in syllables:
            if not self._should_split_untimed_words(syllable):
                yield syllable
                continue
            yield from self._split_untimed_word_syllable(syllable)

    def _should_split_untimed_words(self, syllable: Syllable) -> bool:
        return (
            syllable.tag == ""
            and syllable.style is not None
            and any(char in syllable.trimmed_text for char in (" ", "\t"))
        )

    def _split_untimed_word_syllable(
        self,
        syllable: Syllable,
    ) -> Iterator[Syllable]:
        segments = self._plain_word_segments(syllable.text)
        if len(segments) <= 1:
            yield syllable
            return

        cursor = syllable.left - syllable.prespacewidth
        scale = self._resolve_syllable_x_scale(syllable)
        for index, segment_text in enumerate(segments):
            prespace, trimmed_text, postspace = self._split_horizontal_spaces(
                segment_text,
            )
            prespacewidth = self._measure_scaled_text_width(
                syllable,
                prespace,
                scale,
            )
            width = self._measure_scaled_text_width(
                syllable,
                trimmed_text,
                scale,
            )
            postspacewidth = self._measure_scaled_text_width(
                syllable,
                postspace,
                scale,
            )
            left = cursor + prespacewidth
            right = left + width
            center = left + width / 2

            yield replace(
                syllable,
                index=index,
                raw_text=segment_text,
                text=segment_text,
                trimmed_text=trimmed_text,
                prespace=prespace,
                postspace=postspace,
                start_time=syllable.start_time,
                end_time=syllable.end_time,
                duration=syllable.duration,
                kdur=syllable.kdur,
                tag=syllable.tag,
                inline_fx=syllable.inline_fx,
                highlights=list(syllable.highlights),
                width=width,
                prespacewidth=prespacewidth,
                postspacewidth=postspacewidth,
                left=left,
                center=center,
                right=right,
                x=self._resolve_segment_anchor_x(syllable, left, center, right),
            )
            cursor = right + postspacewidth

    def _plain_word_segments(self, text: str) -> list[str]:
        matches = list(_PLAIN_WORD_PATTERN.finditer(text))
        return [
            text[
                match.start() : self._plain_word_segment_end(
                    text,
                    matches,
                    index,
                )
            ]
            for index, match in enumerate(matches)
        ]

    def _plain_word_segment_end(
        self,
        text: str,
        matches: list[re.Match[str]],
        index: int,
    ) -> int:
        if index + 1 < len(matches):
            return matches[index].end()
        return len(text)

    def _resolve_syllable_x_scale(self, syllable: Syllable) -> float:
        if syllable.style is None or syllable.trimmed_text == "":
            return 1.0
        measured_width = self._preprocessor.extents.measure(
            syllable.style,
            syllable.trimmed_text,
        ).width
        if measured_width == 0:
            return 1.0
        return syllable.width / measured_width

    def _measure_scaled_text_width(
        self,
        syllable: Syllable,
        text: str,
        scale: float,
    ) -> float:
        if syllable.style is None or text == "":
            return 0.0
        return (
            self._preprocessor.extents.measure(
                syllable.style,
                text,
            ).width
            * scale
        )

    def _split_horizontal_spaces(self, text: str) -> tuple[str, str, str]:
        prespace_length = len(text) - len(text.lstrip(" \t"))
        postspace_length = len(text) - len(text.rstrip(" \t"))
        trimmed_end = len(text) - postspace_length
        return (
            text[:prespace_length],
            text[prespace_length:trimmed_end],
            text[trimmed_end:],
        )

    def _resolve_segment_anchor_x(
        self,
        source: Syllable,
        left: float,
        center: float,
        right: float,
    ) -> float:
        if source.x == source.left:
            return left
        if source.x == source.right:
            return right
        return center

    def _build_word(self, index: int, syllables: tuple[Syllable, ...]) -> Word:
        first = syllables[0]
        last = syllables[-1]
        text = "".join(syllable.text for syllable in syllables)
        trimmed_text = "".join(syllable.trimmed_text for syllable in syllables)
        raw_text = "".join(syllable.raw_text for syllable in syllables)
        duration = last.end_time - first.start_time
        width = last.right - first.left
        return Word(
            index=index,
            syllables=syllables,
            raw_text=raw_text,
            text=text,
            trimmed_text=trimmed_text,
            prespace=first.prespace,
            postspace=last.postspace,
            start_time=first.start_time,
            end_time=last.end_time,
            duration=duration,
            kdur=duration / 10,
            style=first.style,
            width=width,
            height=first.height,
            prespacewidth=first.prespacewidth,
            postspacewidth=last.postspacewidth,
            left=first.left,
            center=first.left + width / 2,
            right=last.right,
            top=first.top,
            middle=first.middle,
            bottom=first.bottom,
            x=first.x,
            y=first.y,
        )

    def _is_blank_syllable(self, syllable: Syllable) -> bool:
        return syllable.duration <= 0 or syllable.trimmed_text == ""

    def _is_karaoke_event(self, event: Event) -> bool:
        return event.effect.lower() == "karaoke"

    def _strip_karaoke_text(self, text: str) -> str:
        return self._karaoke_parser.parse_text(text).text
