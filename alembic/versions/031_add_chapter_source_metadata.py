"""Add chapter source metadata and normalize imported titles.

Deletion notes:
- Removes the legacy contract where imported chapter headings were stored only in
  `chapters.title`, forcing UI/search code to guess whether a title contained a
  raw source label or a user-edited title.

Rollback:
- `alembic downgrade 030`
"""

from __future__ import annotations

from typing import Sequence, Union
import re

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "031"
down_revision: Union[str, None] = "030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CHINESE_NUMERAL_RE = "0-9０-９零〇一二三四五六七八九十百千万兩两壱弐参肆伍陆陸柒捌玖拾佰仟萬貳叁"
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


def _chinese_to_arabic(token: str) -> int | None:
    normalized = token.strip().translate(_FULLWIDTH_DIGIT_TRANSLATION)
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


def _parse_source_number(token: str) -> int | None:
    normalized = token.strip().translate(_FULLWIDTH_DIGIT_TRANSLATION)
    if not normalized:
        return None
    if normalized.isdigit():
        return int(normalized)

    roman_value = _roman_to_arabic(normalized)
    if roman_value is not None:
        return roman_value

    return _chinese_to_arabic(normalized)


def _parse_heading(title: str) -> tuple[str, int | None, str] | None:
    trimmed = (title or "").strip()
    if not trimmed:
        return None

    for pattern in (_NUMBERED_CJK_HEADING_RE, _KOREAN_NUMBERED_HEADING_RE, _EN_NUMBERED_HEADING_RE):
        match = pattern.match(trimmed)
        if not match:
            continue
        return (
            trimmed,
            _parse_source_number(match.group("number") or ""),
            _normalize_heading_rest(match.group("rest") or ""),
        )

    special_match = _SPECIAL_HEADING_RE.match(trimmed)
    if special_match:
        return (
            trimmed,
            None,
            _normalize_heading_rest(special_match.group("rest") or ""),
        )

    return None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("chapters")}

    with op.batch_alter_table("chapters") as batch_op:
        if "source_chapter_label" not in columns:
            batch_op.add_column(sa.Column("source_chapter_label", sa.String(length=255), nullable=True))
        if "source_chapter_number" not in columns:
            batch_op.add_column(sa.Column("source_chapter_number", sa.Integer(), nullable=True))

    rows = bind.execute(sa.text("SELECT id, title FROM chapters")).mappings().all()
    for row in rows:
        parsed = _parse_heading(str(row.get("title") or ""))
        if parsed is None:
            continue
        source_label, source_number, stripped_title = parsed
        bind.execute(
            sa.text(
                "UPDATE chapters "
                "SET source_chapter_label = :source_label, "
                "    source_chapter_number = :source_chapter_number, "
                "    title = :title "
                "WHERE id = :chapter_id"
            ),
            {
                "chapter_id": row["id"],
                "source_label": source_label,
                "source_chapter_number": source_number,
                "title": stripped_title,
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("chapters")}

    if "source_chapter_label" in columns:
        bind.execute(
            sa.text(
                "UPDATE chapters "
                "SET title = CASE "
                "    WHEN source_chapter_label IS NOT NULL AND TRIM(source_chapter_label) <> '' "
                "    THEN source_chapter_label "
                "    ELSE title "
                "END"
            )
        )

    with op.batch_alter_table("chapters") as batch_op:
        if "source_chapter_number" in columns:
            batch_op.drop_column("source_chapter_number")
        if "source_chapter_label" in columns:
            batch_op.drop_column("source_chapter_label")
