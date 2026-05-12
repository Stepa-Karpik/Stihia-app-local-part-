from __future__ import annotations

from pathlib import Path
import re

from app.core.settings import AppSettings
from app.services.text_tools import draft_variants, rhyme_candidates


class TextAIService:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._llm: object | None = None

    def draft(self, text: str, mode: str) -> tuple[list[str], str]:
        prompt = self._draft_prompt(text=text, mode=mode)
        generated = self._try_generate(prompt, max_tokens=420)
        if generated:
            variants = self._line_locked_variants(generated, text)
            if variants:
                return variants[:3], "local_gguf"
        return draft_variants(text, mode), "fallback"

    def rhyme(self, word: str, context: str | None = None) -> tuple[list[str], str]:
        prompt = (
            "Подбери 12 русских рифм к слову. Учитывай смысл и ритм контекста. "
            "Верни только слова или короткие фразы через запятую.\n"
            f"Слово: {word}\nКонтекст: {context or ''}"
        )
        generated = self._try_generate(prompt, max_tokens=80)
        if generated:
            candidates = [part.strip(" .;:\n\t") for part in generated.replace("\n", ",").split(",")]
            clean = [candidate for candidate in candidates if candidate]
            if clean:
                return clean[:12], "local_gguf"
        return rhyme_candidates(word), "fallback"

    def complete_line(self, poem_text: str, current_line: str, scope: str) -> tuple[str, str]:
        prompt = (
            "Ты пишешь только продолжение текущей строки русского стихотворения.\n"
            "Правила ответа:\n"
            "- верни 2-7 слов;\n"
            "- без объяснений, кавычек, списков и переносов строки;\n"
            "- не повторяй уже написанные слова;\n"
            "- не говори о задании, вариантах, рифме или пользователе.\n"
            f"Режим: {'под стиль автора' if scope == 'personal' else 'точно по смыслу и ритму'}\n"
            f"Контекст стихотворения:\n{poem_text[-1200:]}\n"
            f"Текущая строка: {current_line}\n"
            "Продолжение:"
        )
        generated = self._try_generate(prompt, max_tokens=24)
        completion = self._clean_single_line(generated)
        if completion:
            return completion, "local_gguf"
        return self._fallback_completion(current_line, bool(generated)), "fallback"

    def _try_generate(self, prompt: str, max_tokens: int) -> str:
        model_path = Path(self._settings.text_fast_model_path).expanduser()
        if not model_path.exists():
            return ""
        try:
            from llama_cpp import Llama
        except ImportError:
            return ""
        if self._llm is None:
            self._llm = Llama(
                model_path=str(model_path),
                n_gpu_layers=-1,
                n_ctx=4096,
                n_threads=8,
                verbose=False,
            )
        response = self._llm(
            prompt,
            max_tokens=max_tokens,
            temperature=0.42,
            top_p=0.82,
            repeat_penalty=1.2,
            stop=["\n", "\n\n", "###", "Текущая строка:", "Контекст стихотворения:"],
        )
        return str(response["choices"][0]["text"]).strip()

    @staticmethod
    def _line_locked_variants(generated: str, source: str) -> list[str]:
        source_count = len(source.splitlines() or [""])
        chunks = [chunk.strip() for chunk in generated.split("\n\n") if chunk.strip()]
        variants: list[str] = []
        for chunk in chunks:
            lines = chunk.splitlines()
            if len(lines) == source_count:
                variants.append("\n".join(lines))
        return variants

    @staticmethod
    def _clean_single_line(value: str) -> str:
        if not value.strip():
            return ""
        line = value.strip().strip('"').splitlines()[0].strip()
        if "Продолжение:" in line:
            line = line.split("Продолжение:", 1)[1].strip()
        line = re.sub(r"^[\s,.;:!?-]+", "", line).strip()
        line = re.sub(r"\s+", " ", line)
        if TextAIService._has_repetitive_loop(line) or TextAIService._looks_like_bad_completion(line):
            return ""
        return line

    @staticmethod
    def _looks_like_bad_completion(value: str) -> bool:
        normalized = value.lower()
        words = re.findall(r"[а-яёa-z0-9-]+", normalized)
        forbidden = (
            "ты должен",
            "продолж",
            "строк",
            "вариант",
            "ответ",
            "задани",
            "пользовател",
            "человек",
            "разговарива",
            "подходящ",
            "рифм",
            "ритм",
            "стихотворен",
            "контекст",
        )
        return len(words) > 9 or any(fragment in normalized for fragment in forbidden)

    @staticmethod
    def _has_repetitive_loop(value: str) -> bool:
        normalized = re.sub(r"\s+", " ", value.lower()).strip()
        if not normalized:
            return False
        comma_chunks = [chunk.strip(" ,.;:!?-") for chunk in normalized.split(",") if chunk.strip(" ,.;:!?-")]
        if comma_chunks and max(comma_chunks.count(chunk) for chunk in set(comma_chunks)) >= 3:
            return True
        words = normalized.split()
        for size in (1, 2, 3):
            if len(words) < size * 3:
                continue
            groups = [" ".join(words[index : index + size]) for index in range(0, len(words), size)]
            if len(groups) >= 3 and len(set(groups[:3])) == 1:
                return True
        return False

    @staticmethod
    def _fallback_completion(current_line: str, rejected_model_output: bool = False) -> str:
        return ""

    @staticmethod
    def _draft_prompt(text: str, mode: str) -> str:
        return (
            "Перепиши выбранный фрагмент русского стихотворения. "
            "Сохрани ровно такое же количество строк, стиль, смысл, ритм и форму. "
            "Верни 3 варианта, раздели варианты пустой строкой.\n"
            f"Режим: {mode}\nФрагмент:\n{text}"
        )
