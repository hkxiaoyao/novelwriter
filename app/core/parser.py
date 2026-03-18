# SPDX-FileCopyrightText: 2026 Isaac.X.Ω.Yuan
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path

from app.language_policy import get_language_policy


_CHINESE_NUMERAL_RE = "0-9０-９零〇一二三四五六七八九十百千万兩两壱弐参肆伍陆陸柒捌玖拾佰仟萬貳叁"
_CHAPTER_PATTERNS_BY_LANGUAGE = {
    "zh": (
        rf"^\s*(?:第[{_CHINESE_NUMERAL_RE}]+[章回节卷篇幕]|序[章言]|楔子|尾声|尾聲|后记|後記|番外(?:篇)?|终章|終章).*$",
    ),
    "ja": (
        rf"^\s*(?:第[{_CHINESE_NUMERAL_RE}]+[章話回節幕巻卷編篇]|プロローグ|エピローグ|外伝|番外編?|後書き|あとがき|序章|終章).*$",
    ),
    "ko": (
        r"^\s*(?:제\s*[0-9０-９]+(?:장|화|편|막)|프롤로그|에필로그|외전|후기|서장|종장).*$",
    ),
    "en": (
        r"^\s*(?:(?:chapter\s+(?:\d+|[ivxlcdm]+)\b.*)|prologue\b.*|epilogue\b.*|afterword\b.*|appendix\b.*|interlude\b.*|preface\b.*)$",
    ),
}
_SUPPORTED_TEXT_ENCODINGS = ("utf-8", "gb18030", "gbk", "gb2312", "utf-16")
_FULLWIDTH_DIGIT_TRANSLATION = str.maketrans("０１２３４５６７８９", "0123456789")
_HEADING_REST_SEPARATOR_RE = re.compile(r"^[\s·•\-—–:：、.．]+")
_NUMBERED_CJK_HEADING_RE = re.compile(
    rf"^\s*(?P<prefix>第\s*(?P<number>[{_CHINESE_NUMERAL_RE}]+)\s*(?P<unit>[章回节卷篇幕話话節編编巻卷]))(?P<rest>.*)$",
    re.IGNORECASE,
)
_KOREAN_NUMBERED_HEADING_RE = re.compile(
    r"^\s*(?P<prefix>제\s*(?P<number>[0-9０-９]+)\s*(?P<unit>장|화|편|막))(?P<rest>.*)$",
    re.IGNORECASE,
)
_EN_NUMBERED_HEADING_RE = re.compile(
    r"^\s*(?P<prefix>chapter\s+(?P<number>\d+|[ivxlcdm]+))(?P<rest>.*)$",
    re.IGNORECASE,
)
_SPECIAL_HEADING_RE = re.compile(
    (
        r"^\s*(?P<prefix>"
        r"(?:序[章言]|楔子|尾声|尾聲|后记|後記|番外(?:篇)?|终章|終章|"
        r"プロローグ|エピローグ|外伝|番外編?|後書き|あとがき|序章|終章|"
        r"프롤로그|에필로그|외전|후기|서장|종장|"
        r"prologue|epilogue|afterword|appendix|interlude|preface)"
        r")(?P<rest>.*)$"
    ),
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedChapterHeading:
    source_label: str
    title: str
    source_number: int | None = None


@dataclass(frozen=True)
class ParsedChapter:
    title: str
    content: str
    source_chapter_label: str | None = None
    source_chapter_number: int | None = None


def _ordered_chapter_patterns(language: str | None, *, sample_text: str) -> list[str]:
    policy = get_language_policy(language, sample_text=sample_text)
    ordered_languages = [policy.base_language, "zh", "ja", "ko", "en"]
    seen: set[str] = set()
    patterns: list[str] = []
    for code in ordered_languages:
        if code in seen:
            continue
        seen.add(code)
        patterns.extend(_CHAPTER_PATTERNS_BY_LANGUAGE.get(code, ()))
    return patterns


def _normalize_heading_rest(rest: str) -> str:
    return _HEADING_REST_SEPARATOR_RE.sub("", rest.strip()).strip()


def _roman_to_arabic(token: str) -> int | None:
    roman_digits = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
    normalized = token.strip().lower()
    if not normalized or not re.fullmatch(r"[ivxlcdm]+", normalized):
        return None

    total = 0
    previous = 0
    for char in reversed(normalized):
        value = roman_digits[char]
        if value < previous:
            total -= value
        else:
            total += value
            previous = value
    return total if total > 0 else None


def _parse_source_number(token: str) -> int | None:
    normalized = token.strip().translate(_FULLWIDTH_DIGIT_TRANSLATION)
    if not normalized:
        return None
    if normalized.isdigit():
        return int(normalized)

    roman_value = _roman_to_arabic(normalized)
    if roman_value is not None:
        return roman_value

    return chinese_to_arabic(normalized)


def parse_chapter_heading(label: str) -> ParsedChapterHeading | None:
    trimmed = label.strip()
    if not trimmed:
        return None

    numbered_match = _NUMBERED_CJK_HEADING_RE.match(trimmed)
    if numbered_match:
        return ParsedChapterHeading(
            source_label=trimmed,
            title=_normalize_heading_rest(numbered_match.group("rest") or ""),
            source_number=_parse_source_number(numbered_match.group("number") or ""),
        )

    korean_match = _KOREAN_NUMBERED_HEADING_RE.match(trimmed)
    if korean_match:
        return ParsedChapterHeading(
            source_label=trimmed,
            title=_normalize_heading_rest(korean_match.group("rest") or ""),
            source_number=_parse_source_number(korean_match.group("number") or ""),
        )

    english_match = _EN_NUMBERED_HEADING_RE.match(trimmed)
    if english_match:
        return ParsedChapterHeading(
            source_label=trimmed,
            title=_normalize_heading_rest(english_match.group("rest") or ""),
            source_number=_parse_source_number(english_match.group("number") or ""),
        )

    special_match = _SPECIAL_HEADING_RE.match(trimmed)
    if special_match:
        return ParsedChapterHeading(
            source_label=trimmed,
            title=_normalize_heading_rest(special_match.group("rest") or ""),
            source_number=None,
        )

    return None


def strip_leading_chapter_heading(label: str) -> str:
    parsed = parse_chapter_heading(label)
    if parsed is None:
        return label.strip()
    return parsed.title


def read_novel_file_text(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Novel file not found: {file_path}")

    for encoding in _SUPPORTED_TEXT_ENCODINGS:
        try:
            return path.read_text(encoding=encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue

    raise ValueError(f"Unable to decode file with supported encodings: {file_path}")


def parse_novel_text(content: str, *, language: str | None = None) -> list[ParsedChapter]:
    """Parse novel text into structured chapter records."""
    chapter_title_patterns = _ordered_chapter_patterns(language, sample_text=content)

    chapter_positions: list[tuple[int, str]] = []
    for pattern in chapter_title_patterns:
        for match in re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE):
            chapter_positions.append((match.start(), match.group()))
        if chapter_positions:
            break

    if not chapter_positions:
        return [ParsedChapter(title="", content=content.strip())]

    chapter_positions.sort(key=lambda item: item[0])

    parsed_chapters: list[ParsedChapter] = []
    for index, (position, raw_label) in enumerate(chapter_positions):
        content_start = position + len(raw_label)
        if index + 1 < len(chapter_positions):
            content_end = chapter_positions[index + 1][0]
        else:
            content_end = len(content)

        chapter_content = content[content_start:content_end].strip()
        parsed_heading = parse_chapter_heading(raw_label.strip())
        if parsed_heading is None:
            parsed_chapters.append(
                ParsedChapter(
                    title=raw_label.strip(),
                    content=chapter_content,
                )
            )
            continue

        parsed_chapters.append(
            ParsedChapter(
                title=parsed_heading.title,
                content=chapter_content,
                source_chapter_label=parsed_heading.source_label,
                source_chapter_number=parsed_heading.source_number,
            )
        )

    return parsed_chapters


def parse_novel_file(file_path: str, *, language: str | None = None) -> list[ParsedChapter]:
    return parse_novel_text(read_novel_file_text(file_path), language=language)


def chinese_to_arabic(chinese_num: str) -> int | None:
    """Convert Chinese numerals or full-width digits to Arabic numerals."""
    normalized = chinese_num.strip().translate(_FULLWIDTH_DIGIT_TRANSLATION)
    if not normalized:
        return None
    if normalized.isdigit():
        return int(normalized)

    chinese_digits = {
        "零": 0,
        "〇": 0,
        "一": 1,
        "二": 2,
        "两": 2,
        "兩": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "壱": 1,
        "弐": 2,
        "参": 3,
        "肆": 4,
        "伍": 5,
        "陆": 6,
        "陸": 6,
        "柒": 7,
        "捌": 8,
        "玖": 9,
        "貳": 2,
        "叁": 3,
    }
    chinese_units = {
        "十": 10,
        "拾": 10,
        "百": 100,
        "佰": 100,
        "千": 1000,
        "仟": 1000,
        "万": 10000,
        "萬": 10000,
    }

    total = 0
    section = 0
    number = 0

    for char in normalized:
        if char in chinese_digits:
            number = chinese_digits[char]
            continue
        unit = chinese_units.get(char)
        if unit is None:
            return None
        if unit >= 10000:
            section = (section + (number or 1)) * unit
            total += section
            section = 0
        else:
            section += (number or 1) * unit
        number = 0

    total += section + number
    return total if total > 0 else None
