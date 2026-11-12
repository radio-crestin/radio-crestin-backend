"""Announcement markdown rendered to sanitized HTML (python-markdown, then nh3 with an allowlist)."""
import re

import markdown as markdown_lib
import nh3

LINK_SCHEMES = {'http', 'https', 'mailto', 'tel'}

BODY_TAGS = {'strong', 'em', 'a', 'br'}
PAGE_TAGS = BODY_TAGS | {
    'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote',
    'img', 'figure', 'figcaption', 'hr',
}
# nh3 adds rel="noopener noreferrer" to every link itself (link_rel), so rel isn't listed.
ATTRIBUTES = {
    'a': {'href', 'target'},
    'img': {'src', 'alt', 'width', 'height'},
}
_PARAGRAPH_BREAK = re.compile(r'</p>\s*<p>')


def _attribute_filter(tag, attribute, value):
    # Images only from http(s) (nh3 checks links against url_schemes, but mailto:/tel: images make no sense).
    if tag == 'img' and attribute == 'src' and not value.lower().startswith(('https://', 'http://')):
        return None
    return value


def _sanitize(html: str, tags) -> str:
    return nh3.clean(
        html,
        tags=tags,
        attributes={tag: allowed for tag, allowed in ATTRIBUTES.items() if tag in tags},
        attribute_filter=_attribute_filter,
        url_schemes=LINK_SCHEMES,
        link_rel='noopener noreferrer',
        set_tag_attribute_values={'a': {'target': '_blank'}},
    ).strip()


def body_html(markdown_text: str) -> str:
    """The card description: bold, italic, links and line breaks only."""
    if not (markdown_text or '').strip():
        return ''
    html = markdown_lib.markdown(markdown_text)
    return _sanitize(_PARAGRAPH_BREAK.sub('<br>', html), BODY_TAGS)


def page_html(markdown_text: str) -> str:
    """The announcement page: also headings, lists, quotes, images and rules."""
    if not (markdown_text or '').strip():
        return ''
    return _sanitize(markdown_lib.markdown(markdown_text), PAGE_TAGS)
