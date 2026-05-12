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
        generated = self._try_chat_generate(
            system=(
                "Ты редактор русской поэзии. Переписываешь только слабые места. "
                "Смысл, стиль и количество строк сохраняются строго."
            ),
            user=self._draft_prompt(text=text, mode=mode),
            max_tokens=360,
            temperature=0.52,
        )
        if generated:
            variants = self._line_locked_variants(generated, text)
            if variants:
                return variants[:3], "local_gguf"
        return draft_variants(text, mode), "fallback"

    def rhyme(self, word: str, context: str | None = None) -> tuple[list[str], str]:
        generated = self._try_chat_generate(
            system="Ты подбираешь русские рифмы. Отвечаешь только списком через запятую.",
            user=(
                "Подбери 12 русских рифм к слову. Учитывай смысл и ритм контекста.\n"
                f"Слово: {word}\nКонтекст: {context or ''}"
            ),
            max_tokens=80,
            temperature=0.45,
        )
        if generated:
            candidates = [part.strip(" .;:\n\t") for part in generated.replace("\n", ",").split(",")]
            clean = [candidate for candidate in candidates if candidate and not self._looks_like_bad_completion(candidate)]
            if clean:
                return clean[:12], "local_gguf"
        return rhyme_candidates(word), "fallback"

    def complete_line(self, poem_text: str, current_line: str, scope: str) -> tuple[str, str]:
        generated = self._try_chat_generate(
            system=(
                "Ты поэтический автокомплит. Отвечаешь только хвостом текущей строки: "
                "2-7 слов, без объяснений, кавычек, списков и переноса строки."
            ),
            user=(
                f"Режим: {'под стиль автора' if scope == 'personal' else 'точно по смыслу и ритму'}\n"
                f"Контекст:\n{poem_text[-1200:]}\n"
                f"Текущая строка: {current_line}\n"
                "Продолжи только эту строку:"
            ),
            max_tokens=24,
            temperature=0.36,
        )
        completion = self._clean_single_line(generated)
        if completion:
            return completion, "local_gguf"
        return self._fallback_completion(current_line, bool(generated)), "fallback"

    def _try_chat_generate(self, system: str, user: str, max_tokens: int, temperature: float) -> str:
        llm = self._get_llm()
        if llm is None:
            return ""
        try:
            if hasattr(llm, "create_chat_completion"):
                response = llm.create_chat_completion(
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=0.82,
                    repeat_penalty=1.22,
                    stop=["\n\n\n", "###"],
                )
                return self._strip_reasoning(str(response["choices"][0]["message"]["content"]))
        except Exception:
            pass
        prompt = f"Система: {system}\nПользователь: {user}\nОтвет:"
        return self._strip_reasoning(
            self._generate_with_llm(
                llm,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=["\n\n\n", "###", "Система:", "Пользователь:"],
            )
        )

    def _try_generate(self, prompt: str, max_tokens: int) -> str:
        llm = self._get_llm()
        if llm is None:
            return ""
        return self._generate_with_llm(llm, prompt=prompt, max_tokens=max_tokens, temperature=0.42)

    def _get_llm(self) -> object | None:
        model_path = Path(self._settings.text_fast_model_path).expanduser()
        if not model_path.exists():
            return None
        try:
            from llama_cpp import Llama
        except ImportError:
            return None
        if self._llm is None:
            self._llm = Llama(
                model_path=str(model_path),
                n_gpu_layers=-1,
                n_ctx=4096,
                n_threads=8,
                verbose=False,
            )
        return self._llm

    @staticmethod
    def _generate_with_llm(
        llm: object,
        prompt: str,
        max_tokens: int,
        temperature: float,
        stop: list[str] | None = None,
    ) -> str:
        response = llm(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=0.82,
            repeat_penalty=1.2,
            stop=stop or ["\n", "\n\n", "###", "Текущая строка:", "Контекст стихотворения:"],
        )
        return str(response["choices"][0]["text"]).strip()

    @staticmethod
    def _line_locked_variants(generated: str, source: str) -> list[str]:
        generated = TextAIService._strip_reasoning(generated)
        if not generated:
            return []
        source_count = len(source.splitlines() or [""])
        source_normalized = TextAIService._normalize_multiline(source)
        chunks = [chunk.strip() for chunk in generated.split("\n\n") if chunk.strip()]
        variants: list[str] = []
        for chunk in chunks:
            lines = [TextAIService._clean_variant_line(line) for line in chunk.splitlines()]
            lines = [line for line in lines if line]
            variant = "\n".join(lines)
            if len(lines) == source_count and TextAIService._normalize_multiline(variant) != source_normalized:
                variants.append(variant)
        return variants

    @staticmethod
    def _clean_variant_line(value: str) -> str:
        return re.sub(r"^\s*(?:вариант\s*)?\d+[\).\:-]\s*", "", value.strip(), flags=re.IGNORECASE)

    @staticmethod
    def _normalize_multiline(value: str) -> str:
        return "\n".join(re.sub(r"\s+", " ", line.strip().lower()) for line in value.splitlines())

    @staticmethod
    def _clean_single_line(value: str) -> str:
        value = TextAIService._strip_reasoning(value)
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
            "think",
            "assistant",
            "system",
            "user",
        )
        return "<" in normalized or ">" in normalized or len(words) > 9 or any(fragment in normalized for fragment in forbidden)

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
    def _strip_reasoning(value: str) -> str:
        if not value.strip():
            return ""
        normalized = value.lower()
        if "<think" in normalized and "</think>" not in normalized:
            return ""
        cleaned = re.sub(r"<think\b[^>]*>.*?</think>", "", value, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"</?think\b[^>]*>", "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip()

    @staticmethod
    def _draft_prompt(text: str, mode: str) -> str:
        return (
            "Перепиши выбранный фрагмент русского стихотворения.\n"
            "Жесткие правила:\n"
            "- верни 3 варианта;\n"
            "- каждый вариант содержит ровно такое же количество строк;\n"
            "- не добавляй комментарии и пояснения;\n"
            "- не возвращай исходный текст без изменений;\n"
            "- разделяй варианты одной пустой строкой.\n"
            f"Режим: {mode}\nФрагмент:\n{text}"
        )
