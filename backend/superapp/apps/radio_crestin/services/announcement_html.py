"""Announcement markdown rendered to sanitized HTML (python-markdown, then nh3 with an allowlist)."""
import html as html_lib
import re

import markdown as markdown_lib
import nh3

from . import youtube_embeds

LINK_SCHEMES = {'http', 'https', 'mailto', 'tel'}

BODY_TAGS = {'strong', 'em', 'a', 'br'}
PAGE_TAGS = BODY_TAGS | {
    'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote',
    'img', 'figure', 'figcaption', 'hr',
}
# nh3 adds rel="noopener noreferrer" to every link itself (link_rel), so rel isn't listed.
BODY_ATTRIBUTES = {'a': {'href', 'target'}}
PAGE_ATTRIBUTES = {
    **BODY_ATTRIBUTES,
    'img': {'src', 'alt', 'width', 'height', 'loading'},
    # YouTube embeds (figure.rc-embed); each value is checked in _attribute_filter.
    'figure': {'data-provider', 'data-kind', 'data-video-id', 'data-list-id', 'data-start'},
}
PAGE_CLASSES = {'figure': {'rc-embed'}}

_PARAGRAPH_BREAK = re.compile(r'</p>\s*<p>')
_PARAGRAPH = re.compile(r'<p>(.*?)</p>', re.DOTALL)
_LINK_ONLY = re.compile(r'^\s*<a href="([^"]*)">([^<]*)</a>\s*$')
_EMBED_FIGURE = re.compile(r'<figure class="rc-embed"([^>]*)>')


def _attribute_filter(tag, attribute, value):
    # Images only from http(s) (nh3 checks links against url_schemes, but mailto:/tel: images make no sense).
    if tag == 'img' and attribute == 'src' and not value.lower().startswith(('https://', 'http://')):
        return None
    if tag == 'img' and attribute == 'loading' and value not in ('lazy', 'eager'):
        return None
    # Clients build player URLs from these: only exact, valid values pass.
    if tag == 'figure' and attribute.startswith('data-') and not youtube_embeds.is_valid_attribute(attribute, value):
        return None
    return value


def _sanitize(html: str, tags, attributes, classes=None) -> str:
    return nh3.clean(
        html,
        tags=tags,
        attributes=attributes,
        allowed_classes=classes,
        attribute_filter=_attribute_filter,
        url_schemes=LINK_SCHEMES,
        link_rel='noopener noreferrer',
        set_tag_attribute_values={'a': {'target': '_blank'}},
    ).strip()


def _paragraph_url(inner_html: str):
    """The URL a paragraph consists of (bare, or a link whose text is the URL), or None."""
    link = _LINK_ONLY.match(inner_html)
    if link:
        href, text = html_lib.unescape(link.group(1)), html_lib.unescape(link.group(2)).strip()
        return href if text == href else None
    if '<' in inner_html:
        return None
    text = html_lib.unescape(inner_html).strip()
    return text if text and not any(char.isspace() for char in text) else None


def _embed_paragraphs(html: str) -> str:
    """A paragraph that is only a YouTube URL becomes its placeholder figure."""
    def replace(match):
        embed = youtube_embeds.parse(_paragraph_url(match.group(1)) or '')
        return youtube_embeds.figure(embed) if embed else match.group(0)
    return _PARAGRAPH.sub(replace, html)


def body_html(markdown_text: str) -> str:
    """The card description: bold, italic, links and line breaks only."""
    if not (markdown_text or '').strip():
        return ''
    html = markdown_lib.markdown(markdown_text)
    return _sanitize(_PARAGRAPH_BREAK.sub('<br>', html), BODY_TAGS, BODY_ATTRIBUTES)


def page_html(markdown_text: str) -> str:
    """The announcement page: also headings, lists, quotes, images, rules and YouTube embeds."""
    if not (markdown_text or '').strip():
        return ''
    html = _embed_paragraphs(markdown_lib.markdown(markdown_text))
    return _drop_incomplete_embeds(_sanitize(html, PAGE_TAGS, PAGE_ATTRIBUTES, PAGE_CLASSES))


def _drop_incomplete_embeds(html: str) -> str:
    """A figure.rc-embed (say, hand-written) without a provider and a valid id is just a figure."""
    def check(match):
        attributes = match.group(1)
        complete = 'data-provider="youtube"' in attributes and (
            'data-video-id=' in attributes or 'data-list-id=' in attributes)
        return match.group(0) if complete else '<figure>'
    return _EMBED_FIGURE.sub(check, html)
