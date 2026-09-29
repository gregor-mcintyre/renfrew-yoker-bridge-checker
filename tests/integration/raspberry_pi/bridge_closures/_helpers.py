"""Webpage bodies and responses shared by the bridge closure integration tests."""

from html import escape
from itertools import groupby
from pathlib import Path
from string import Template
from typing import Literal, NamedTuple

from curl_cffi import requests

from tests import closures_webpage_text

_WEBPAGE_TEMPLATE = Template(
    (Path(__file__).parent / "closures_webpage.html").read_text(encoding="utf-8"),
)

# The banner at the top of the real webpage and the article below it mark up the same
# section differently: items are indented paragraphs in the banner, and bullets in the
# article.
_BANNER_ITEM_MARKUP = '<p style="margin-left: 40px">{text}</p>'
_HEADING_MARKUP = "<p><strong>{text}</strong></p>"
_ARTICLE_ITEM_MARKUP = "<li>{text}</li>"

_BANNER_MARKUP_BY_KIND = {
    "heading": _HEADING_MARKUP,
    "notice": _HEADING_MARKUP,
    "item": _BANNER_ITEM_MARKUP,
}


class _SectionLine(NamedTuple):
    """A single line of a section of the webpage listing closures.

    Attributes:
        kind: How the line is marked up. A heading and a notice are both bold, and an
            item is indented in the banner and bulleted in the article.
        text: The text displayed on the line.
    """

    kind: Literal["heading", "notice", "item"]
    text: str


def _heading(text: str) -> _SectionLine:
    """Builds a date heading line.

    Args:
        text: The date displayed in the heading.

    Returns:
        A `_SectionLine` for the heading.
    """
    return _SectionLine(kind="heading", text=text)


def _notice(text: str) -> _SectionLine:
    """Builds a line announcing that the bridge will be closed.

    Args:
        text: The announcement displayed on the webpage.

    Returns:
        A `_SectionLine` for the announcement.
    """
    return _SectionLine(kind="notice", text=text)


def _item(text: str) -> _SectionLine:
    """Builds an item line, such as a time range or a note that nothing is planned.

    Args:
        text: The text displayed on the item.

    Returns:
        A `_SectionLine` for the item.
    """
    return _SectionLine(kind="item", text=text)


def _render_banner(lines: tuple[_SectionLine, ...]) -> str:
    """Renders the lines of a section as they appear in the banner of the webpage.

    Args:
        lines: The lines of the section.

    Returns:
        The HTML of the section within the banner.
    """
    return "".join(
        _BANNER_MARKUP_BY_KIND[line.kind].format(text=escape(line.text))
        for line in lines
    )


def _render_article(lines: tuple[_SectionLine, ...]) -> str:
    """Renders the lines of a section as they appear in the article of the webpage.

    Args:
        lines: The lines of the section.

    Returns:
        The HTML of the section within the article, with each run of consecutive items
        in a single bulleted list.
    """
    rendered = []

    for kind, run in groupby(lines, key=lambda line: line.kind):
        if kind == "item":
            bullets = "".join(
                _ARTICLE_ITEM_MARKUP.format(text=escape(line.text)) for line in run
            )
            rendered.append(f"<ul>{bullets}</ul>")
        else:
            rendered.extend(
                _HEADING_MARKUP.format(text=escape(line.text)) for line in run
            )

    return "".join(rendered)


def _build_page(*lines: _SectionLine) -> str:
    """Builds a full webpage listing a section of closures twice, like the real one.

    Args:
        lines: The lines of the section, listed in both the banner and the article.

    Returns:
        The HTML of the full webpage.
    """
    return _WEBPAGE_TEMPLATE.substitute(
        banner_section=_render_banner(lines),
        article_section=_render_article(lines),
    )


PAGE_WITHOUT_CLOSURE = _build_page(
    _heading(closures_webpage_text.DATE_HEADING),
    _item(closures_webpage_text.NO_CLOSURES_LINE_CAPITALISED),
)

PAGE_WITH_CLOSURE = _build_page(
    _heading(closures_webpage_text.DATE_HEADING),
    _notice(closures_webpage_text.CLOSURE_NOTICE),
    _item(closures_webpage_text.TIME_RANGE),
)


def build_response(body: str = "", *, status_code: int = 200) -> requests.Response:
    """Builds a `Response` for the patched `requests.get` to return.

    `ok` is set from `status_code` as a real request sets it, since `Response`
    otherwise leaves it `True`.

    Args:
        body: The HTML response body.
        status_code: The HTTP status code of the response.

    Returns:
        The response, with `body` as the content and `status_code` as the status.
    """
    response = requests.Response()
    response.status_code = status_code
    response.ok = 200 <= status_code < 400
    response.content = body.encode()

    return response
