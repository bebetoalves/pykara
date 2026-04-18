"""Core engine implementation."""

from __future__ import annotations

import random
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from types import CodeType

from pykara.data import Event, Metadata, Style
from pykara.data.events.karaoke import Karaoke, Syllable, Word
from pykara.engine.variable_context import (
    Environment,
    GeneratedLine,
    LoopState,
)
from pykara.errors import (
    BoundMethodInExpressionError,
    TemplateCodeError,
    TemplateRuntimeError,
)
from pykara.parsing import (
    CodeDeclaration,
    ParsedDeclarations,
    TemplateDeclaration,
)
from pykara.parsing.karaoke_parser import KaraokeParser
from pykara.processing.line_preprocessor import (
    LinePreprocessor,
    PositionedLine,
)
from pykara.processing.text_renderer import TextRenderer


class _CodeRunner:
    """Compile and execute code declarations inside the environment."""

    def __init__(self) -> None:
        self._compiled_code_cache: dict[str, CodeType] = {}

    def run(self, source: str, env: Environment) -> None:
        try:
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
                if name not in reserved_names and name != "__builtins__"
            }
        )


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
            self._execute_code(declaration, env)

        output_events: list[Event] = []
        karaoke_index = 0
        for event in events:
            if not self._is_karaoke_event(event):
                continue
            style = styles[event.style]
            karaoke = self._karaoke_parser.parse(event)
            positioned = self._preprocessor.preprocess(
                event,
                karaoke,
                meta,
                style,
            )
            line_output = self._apply_line(
                event=event,
                line_index=karaoke_index,
                positioned=positioned,
                declarations=declarations,
                karaoke=karaoke,
                env=env,
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
    ) -> list[Event]:
        env.source_line = event
        env.karaoke = karaoke
        env.line = None
        env.word = None
        env.syl = None
        env.char = None
        words = self._iter_words(positioned.syllables)
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
            if isinstance(declaration, CodeDeclaration):
                self._execute_code(declaration, env)
                continue

            descendants: Callable[[], list[Event]] | None = None
            if declaration.modifiers.loops:
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
                    env,
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
        env: Environment,
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
            lambda: self._build_line_event(declaration, source_event, env),
            descendants,
        )

    def _render_syllable_template(
        self,
        declaration: TemplateDeclaration,
        source_event: Event,
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
                syllable,
                env,
            ),
            descendants,
        )

    def _render_word_template(
        self,
        declaration: TemplateDeclaration,
        source_event: Event,
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
                word,
                env,
            ),
            descendants,
        )

    def _render_char_template(
        self,
        declaration: TemplateDeclaration,
        source_event: Event,
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
                    if isinstance(declaration, CodeDeclaration):
                        self._execute_code(declaration, env)
                        continue
                    if not self._passes_conditions(declaration, env):
                        continue

                    descendants: Callable[[], list[Event]] | None = None
                    if declaration.modifiers.loops:
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
                    if declaration.modifiers.loops:
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
        env: Environment,
    ) -> Event:
        return self._build_scoped_event(
            declaration=declaration,
            source_event=source_event,
            styleref=env.styles[source_event.style],
            suffix_text=self._strip_karaoke_text(source_event.text),
            env=env,
        )

    def _build_syllable_event(
        self,
        declaration: TemplateDeclaration,
        source_event: Event,
        syllable: Syllable,
        env: Environment,
    ) -> Event:
        return self._build_scoped_event(
            declaration=declaration,
            source_event=source_event,
            styleref=syllable.style or env.styles[source_event.style],
            suffix_text=syllable.text,
            env=env,
        )

    def _build_word_event(
        self,
        declaration: TemplateDeclaration,
        source_event: Event,
        word: Word,
        env: Environment,
    ) -> Event:
        return self._build_scoped_event(
            declaration=declaration,
            source_event=source_event,
            styleref=word.style or env.styles[source_event.style],
            suffix_text=word.text,
            env=env,
        )

    def _build_char_event(
        self,
        declaration: TemplateDeclaration,
        source_event: Event,
        char_syllable: Syllable,
        env: Environment,
    ) -> Event:
        return self._build_scoped_event(
            declaration=declaration,
            source_event=source_event,
            styleref=char_syllable.style or env.styles[source_event.style],
            suffix_text=char_syllable.text,
            env=env,
        )

    def _build_scoped_event(
        self,
        *,
        declaration: TemplateDeclaration,
        source_event: Event,
        styleref: Style,
        suffix_text: str,
        env: Environment,
    ) -> Event:
        output = GeneratedLine.from_event(
            source_event,
            styleref,
        )
        output.style = output.styleref.name
        env.line = output
        env.declaration = "template"
        env.begin_template_evaluation(declaration.scope)
        output.text = self._renderer.render(declaration.body.text, env)
        if not declaration.modifiers.no_text:
            output.text += suffix_text
        return output.to_event()

    def _passes_conditions(
        self,
        declaration: TemplateDeclaration,
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
        declaration: TemplateDeclaration | CodeDeclaration,
        event: Event,
    ) -> bool:
        return not declaration.style or declaration.style == event.style

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

    def _iter_words(self, syllables: tuple[Syllable, ...]) -> list[Word]:
        words: list[Word] = []
        current_syllables: list[Syllable] = []

        def append_current() -> None:
            if not current_syllables:
                return
            words.append(self._build_word(len(words), tuple(current_syllables)))
            current_syllables.clear()

        for syllable in syllables:
            if current_syllables and syllable.prespace:
                append_current()
            current_syllables.append(syllable)
            if syllable.postspace:
                append_current()

        append_current()
        return words

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
