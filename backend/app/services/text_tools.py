import re
from collections import defaultdict
from dataclasses import dataclass

from app.schemas import LineAnalysisResponse

VOWELS = set("аеёиоуыэюяАЕЁИОУЫЭЮЯ")

RHYME_BANK = {
    "иг": ["стих", "миг", "крик", "лик", "тупик"],
    "ете": ["свете", "ответе", "пистолете", "куплете"],
    "вет": ["ответ", "след", "свет", "рассвет"],
    "рай": ["край", "рай", "невзначай", "прощай"],
    "ак": ["знак", "так", "мрак", "пустяк"],
    "им": ["чужим", "немым", "живым", "твоим"],
}


@dataclass(frozen=True)
class StanzaLine:
    absolute_index: int
    stanza_index: int
    line_in_stanza: int
    text: str
    syllables: int
    last_word: str | None
    rhyme_tail: str | None


def analyze_lines(text: str) -> list[LineAnalysisResponse]:
    raw_lines = text.splitlines() or [""]
    stanza_lines = _stanza_lines(raw_lines)
    expected_by_index = _expected_rhythm(stanza_lines)
    rhyme_by_index, scheme_by_stanza = _rhyme_groups(stanza_lines)
    responses: list[LineAnalysisResponse] = []

    for index, line in enumerate(raw_lines):
        stanza_line = stanza_lines.get(index)
        syllables = stanza_line.syllables if stanza_line else count_syllables(line)
        expected = expected_by_index.get(index, 0)
        delta = syllables - expected if expected else 0
        responses.append(
            LineAnalysisResponse(
                number=index + 1,
                text=line,
                syllables=syllables,
                last_word=last_word(line),
                rhyme_tail=rhyme_tail(last_word(line)),
                rhyme_group=rhyme_by_index.get(index),
                rhyme_scheme=scheme_by_stanza.get(stanza_line.stanza_index, "") if stanza_line else "",
                rhythm_expected=expected,
                rhythm_delta=delta,
                stanza_index=stanza_line.stanza_index if stanza_line else 0,
                line_in_stanza=stanza_line.line_in_stanza if stanza_line else 0,
                flags=line_flags(line, syllables, expected),
            )
        )
    return responses


def count_syllables(line: str) -> int:
    return sum(1 for char in line if char in VOWELS)


def last_word(line: str) -> str | None:
    words = re.findall(r"[A-Za-zА-Яа-яЁё-]+", line)
    return words[-1].lower() if words else None


def rhyme_candidates(word: str) -> list[str]:
    normalized = normalize_word(word)
    for size in (4, 3, 2):
        tail = normalized[-size:]
        if tail in RHYME_BANK:
            return RHYME_BANK[tail]
    tail = rhyme_tail(normalized) or normalized[-2:]
    return [candidate for candidate in (f"{tail}ом", f"{tail}а", f"{tail}е") if candidate.strip()]


def rhyme_tail(word: str | None) -> str | None:
    if not word:
        return None
    normalized = normalize_word(word)
    vowel_positions = [index for index, char in enumerate(normalized) if char in "аеёиоуыэюя"]
    if not vowel_positions:
        return normalized[-3:]
    tail = normalized[vowel_positions[-1] :]
    if len(tail) < 3 and len(vowel_positions) >= 2:
        tail = normalized[vowel_positions[-2] :]
    return tail[-4:] if len(tail) > 4 else tail


def normalize_word(word: str) -> str:
    return (
        word.lower()
        .replace("ё", "е")
        .strip(" .,!?;:—-")
        .replace("ь", "")
        .replace("ъ", "")
    )


def line_flags(line: str, syllables: int, expected: int) -> list[str]:
    flags: list[str] = []
    if not line.strip():
        flags.append("empty")
    if expected and syllables:
        delta = abs(syllables - expected)
        if delta >= 3:
            flags.append("rhythm")
        elif delta == 2:
            flags.append("near_rhythm")
    return flags


def draft_variants(text: str, mode: str) -> list[str]:
    return []


def _stanza_lines(raw_lines: list[str]) -> dict[int, StanzaLine]:
    result: dict[int, StanzaLine] = {}
    stanza_index = 1
    line_in_stanza = 0
    for absolute_index, text in enumerate(raw_lines):
        if not text.strip():
            if line_in_stanza:
                stanza_index += 1
                line_in_stanza = 0
            continue
        line_in_stanza += 1
        word = last_word(text)
        result[absolute_index] = StanzaLine(
            absolute_index=absolute_index,
            stanza_index=stanza_index,
            line_in_stanza=line_in_stanza,
            text=text,
            syllables=count_syllables(text),
            last_word=word,
            rhyme_tail=rhyme_tail(word),
        )
    return result


def _expected_rhythm(lines: dict[int, StanzaLine]) -> dict[int, int]:
    by_stanza: dict[int, list[StanzaLine]] = defaultdict(list)
    for line in lines.values():
        by_stanza[line.stanza_index].append(line)

    expected: dict[int, int] = {}
    for stanza in by_stanza.values():
        pattern_by_rhyme = _rhyme_rhythm_pattern(stanza)
        if pattern_by_rhyme:
            for line in stanza:
                expected[line.absolute_index] = pattern_by_rhyme.get(line.rhyme_tail or "", line.syllables)
            continue
        counts = [line.syllables for line in stanza]
        pattern = _rhythm_pattern(counts)
        for index, line in enumerate(stanza):
            expected[line.absolute_index] = pattern[index % len(pattern)] if pattern else 0
    return expected


def _rhyme_rhythm_pattern(stanza: list[StanzaLine]) -> dict[str, int]:
    tails = [line.rhyme_tail or "" for line in stanza]
    repeated = {tail for tail in tails if tail and tails.count(tail) > 1}
    if not repeated:
        return {}
    pattern: dict[str, int] = {}
    for line in stanza:
        tail = line.rhyme_tail or ""
        if tail in repeated and tail not in pattern:
            pattern[tail] = line.syllables
    return pattern


def _rhythm_pattern(counts: list[int]) -> list[int]:
    non_zero = [count for count in counts if count > 0]
    if not non_zero:
        return []
    if len(non_zero) >= 4 and all(abs(non_zero[index] - non_zero[index + 2]) <= 1 for index in range(len(non_zero) - 2)):
        return [_rounded_average(non_zero[0::2]), _rounded_average(non_zero[1::2])]
    return [_rounded_average(non_zero)]


def _rounded_average(values: list[int]) -> int:
    return round(sum(values) / len(values)) if values else 0


def _rhyme_groups(lines: dict[int, StanzaLine]) -> tuple[dict[int, str], dict[int, str]]:
    by_stanza: dict[int, list[StanzaLine]] = defaultdict(list)
    for line in lines.values():
        by_stanza[line.stanza_index].append(line)

    groups_by_index: dict[int, str] = {}
    scheme_by_stanza: dict[int, str] = {}
    for stanza_index, stanza in by_stanza.items():
        known_tails: dict[str, str] = {}
        next_letter = ord("A")
        scheme = []
        for line in stanza:
            tail = line.rhyme_tail or ""
            group = _known_rhyme_group(known_tails, tail)
            if group is None:
                group = chr(next_letter)
                next_letter += 1
                known_tails[tail] = group
            groups_by_index[line.absolute_index] = group
            scheme.append(group)
        scheme_by_stanza[stanza_index] = "".join(scheme)
    return groups_by_index, scheme_by_stanza


def _known_rhyme_group(known_tails: dict[str, str], tail: str) -> str | None:
    for known_tail, group in known_tails.items():
        if _rhyme_compatible(known_tail, tail):
            return group
    return None


def _rhyme_compatible(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return left == right or left.endswith(right) or right.endswith(left) or left[-2:] == right[-2:]
