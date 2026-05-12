import re

from app.schemas import LineAnalysisResponse

VOWELS = set("аеёиоуыэюяАЕЁИОУЫЭЮЯ")

RHYME_BANK = {
    "иг": ["стих", "миг", "крик", "лик", "тупик"],
    "ете": ["свете", "ответе", "пистолете", "куплете"],
    "ак": ["знак", "так", "мрак", "пустяк"],
    "им": ["чужим", "немым", "живым", "твоим"],
}


def analyze_lines(text: str) -> list[LineAnalysisResponse]:
    lines = text.splitlines() or [""]
    syllables = [count_syllables(line) for line in lines]
    non_empty_counts = [count for count in syllables if count > 0]
    target = round(sum(non_empty_counts) / len(non_empty_counts)) if non_empty_counts else 0
    return [
        LineAnalysisResponse(
            number=index + 1,
            text=line,
            syllables=syllables[index],
            last_word=last_word(line),
            rhyme_tail=rhyme_tail(last_word(line)),
            rhythm_delta=syllables[index] - target,
            flags=line_flags(line, syllables[index], target),
        )
        for index, line in enumerate(lines)
    ]


def count_syllables(line: str) -> int:
    return sum(1 for char in line if char in VOWELS)


def last_word(line: str) -> str | None:
    words = re.findall(r"[A-Za-zА-Яа-яЁё-]+", line)
    return words[-1].lower() if words else None


def rhyme_candidates(word: str) -> list[str]:
    normalized = word.lower().strip(" .,!?;:—-")
    for size in (3, 2):
        tail = normalized[-size:]
        if tail in RHYME_BANK:
            return RHYME_BANK[tail]
    return [f"{normalized}ом", f"{normalized}а", f"{normalized}е"]


def rhyme_tail(word: str | None) -> str | None:
    if not word:
        return None
    normalized = word.lower().replace("ё", "е").strip(" .,!?;:—-")
    if len(normalized) <= 3:
        return normalized
    return normalized[-3:]


def line_flags(line: str, syllables: int, target: int) -> list[str]:
    flags: list[str] = []
    if not line.strip():
        flags.append("empty")
    if target and syllables and abs(syllables - target) >= 3:
        flags.append("rhythm")
    return flags


def draft_variants(text: str, mode: str) -> list[str]:
    lines = text.splitlines() or [""]
    variants: list[str] = []
    for prefix in ("мягче", "точнее", "жестче"):
        rewritten = [f"{line}  [{prefix}]" if line.strip() else line for line in lines]
        variants.append("\n".join(rewritten))
    return variants
