from types import SimpleNamespace

from app.core.continuation_text import (
    append_user_instruction_for_relevance,
    format_next_chapter_reference,
    format_recent_chapters_for_prompt,
    format_world_context_for_prompt,
)


def test_format_recent_chapters_for_prompt_preserves_existing_shape():
    chapters = [
        SimpleNamespace(chapter_number=1, title="第一章", content="云澈看向远方。"),
        SimpleNamespace(chapter_number=2, title="第二章", content="楚月仙静坐不语。"),
    ]

    result = format_recent_chapters_for_prompt(chapters)

    # Default locale is zh
    assert "【第1章：第一章】" in result
    assert "云澈看向远方。" in result
    assert "【第2章：第二章】" in result
    assert "楚月仙静坐不语。" in result


def test_format_recent_chapters_for_prompt_uses_internal_heading_when_title_is_blank():
    chapters = [
        SimpleNamespace(chapter_number=1, title="", source_chapter_label="序章", content="云澈看向远方。"),
    ]

    result = format_recent_chapters_for_prompt(chapters)

    assert "【第1章】" in result
    assert "云澈看向远方。" in result


def test_format_recent_chapters_for_prompt_uses_internal_heading_even_with_source_metadata():
    chapters = [
        SimpleNamespace(
            chapter_number=2,
            title="归来",
            source_chapter_label="第844章 归来",
            content="楚月仙静坐不语。",
        ),
    ]

    result = format_recent_chapters_for_prompt(chapters)

    assert "【第2章：归来】" in result
    assert "【第844章 归来】" not in result


def test_format_recent_chapters_en_locale():
    chapters = [
        SimpleNamespace(chapter_number=1, title="Dawn", content="The sun rose."),
    ]
    result = format_recent_chapters_for_prompt(chapters, locale="en")
    assert "【Chapter 1: Dawn】" in result
    assert "The sun rose." in result


def test_append_user_instruction_for_relevance_uses_dedicated_heading():
    result = append_user_instruction_for_relevance("recent text", "请继续写云澈的内心戏")

    assert result.endswith("【用户续写指令】\n请继续写云澈的内心戏")


def test_append_user_instruction_en_locale():
    result = append_user_instruction_for_relevance(
        "recent text", "Continue the inner monologue", locale="en",
    )
    assert "【User Instruction】" in result
    assert "Continue the inner monologue" in result


def test_format_next_chapter_reference_uses_internal_chapter_numbering():
    assert format_next_chapter_reference(
        3,
        latest_source_chapter_label="第844章 归来",
        latest_source_chapter_number=844,
        locale="zh",
    ) == "第3章"
    assert format_next_chapter_reference(
        3,
        latest_source_chapter_label="Chapter 17 Return",
        latest_source_chapter_number=17,
        locale="en",
    ) == "Chapter 3"
    assert format_next_chapter_reference(
        3,
        latest_source_chapter_label=None,
        latest_source_chapter_number=None,
        locale="zh",
    ) == "第3章"


def test_format_world_context_for_prompt_renders_sections_without_constraints_inline():
    writer_ctx = {
        "systems": [
            {
                "name": "修炼体系",
                "display_type": "list",
                "description": "玄气等级划分",
                "data": {"items": [{"label": "真玄境", "description": "基础境界"}]},
                "constraints": ["每章最多一次时间跳转"],
            }
        ],
        "entities": [
            {
                "id": 1,
                "name": "云澈",
                "entity_type": "Character",
                "description": "主角",
                "aliases": ["小澈"],
                "attributes": [{"key": "身份", "surface": "苍风弟子"}],
            },
            {
                "id": 2,
                "name": "楚月仙",
                "entity_type": "Character",
                "description": "师父",
                "aliases": [],
                "attributes": [],
            },
        ],
        "relationships": [
            {
                "source_id": 1,
                "target_id": 2,
                "label": "师徒",
                "description": "云澈拜楚月仙为师",
            }
        ],
    }

    result = format_world_context_for_prompt(writer_ctx)

    assert "〈世界体系〉" in result
    assert "〈角色与事物〉" in result
    assert "〈人物关系〉" in result
    assert "修炼体系" in result
    assert "真玄境：基础境界" in result
    assert "别名：小澈" in result
    assert "身份：苍风弟子" in result
    assert "云澈 —师徒→ 楚月仙：云澈拜楚月仙为师" in result
    assert "每章最多一次时间跳转" not in result


def test_format_world_context_en_locale():
    writer_ctx = {
        "systems": [],
        "entities": [
            {
                "id": 1,
                "name": "John",
                "entity_type": "Character",
                "description": "Hero",
                "aliases": ["Johnny"],
                "attributes": [],
            },
        ],
        "relationships": [],
    }
    result = format_world_context_for_prompt(writer_ctx, locale="en")
    assert "〈Characters & Entities〉" in result
    assert "Aliases: Johnny" in result


def test_format_world_context_for_prompt_renders_timeline_time_field():
    writer_ctx = {
        "systems": [
            {
                "name": "历史年表",
                "display_type": "timeline",
                "description": "关键节点",
                "data": {"events": [{"time": "千年前", "label": "灵气衰退", "description": "大灾变"}]},
                "constraints": [],
            }
        ],
        "entities": [],
        "relationships": [],
    }

    result = format_world_context_for_prompt(writer_ctx)

    assert "千年前，灵气衰退：大灾变" in result
