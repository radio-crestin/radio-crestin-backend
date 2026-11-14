"""Turns an uploaded announcement icon into a safe file, or says why it can't.

An icon is an SVG, or a JPEG, PNG or WebP picture. Pictures are re-encoded
(services/contact_images.py). An SVG is rebuilt from an allow-list of drawing
elements and attributes: no scripts, event handlers, foreign content,
animations or links outside the file survive, so the stored file is safe even
when opened on its own in a browser.
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from django.core.files.base import ContentFile

from ..models.announcement_validators import ICON_RASTER_EXTENSIONS
from .contact_images import ImageRejected, clean_image

MAX_SVG_BYTES = 512 * 1024

SVG_NS = 'http://www.w3.org/2000/svg'
XLINK_NS = 'http://www.w3.org/1999/xlink'
ET.register_namespace('', SVG_NS)
ET.register_namespace('xlink', XLINK_NS)

ALLOWED_ELEMENTS = {
    'svg', 'g', 'defs', 'symbol', 'use', 'title', 'desc', 'style',
    'path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon', 'text', 'tspan',
    'linearGradient', 'radialGradient', 'stop', 'clipPath', 'mask', 'pattern',
    'filter', 'feGaussianBlur', 'feOffset', 'feBlend', 'feColorMatrix', 'feFlood',
    'feComposite', 'feMerge', 'feMergeNode', 'feDropShadow',
}
# Presentation and geometry attributes; anything else (on*, unknown) is dropped.
ALLOWED_ATTRIBUTES = {
    'id', 'class', 'style', 'transform', 'viewBox', 'preserveAspectRatio', 'width', 'height', 'version',
    'x', 'y', 'x1', 'y1', 'x2', 'y2', 'cx', 'cy', 'r', 'rx', 'ry', 'fx', 'fy', 'd', 'points', 'pathLength',
    'fill', 'fill-opacity', 'fill-rule', 'stroke', 'stroke-width', 'stroke-opacity', 'stroke-linecap',
    'stroke-linejoin', 'stroke-miterlimit', 'stroke-dasharray', 'stroke-dashoffset', 'opacity', 'color',
    'clip-path', 'clip-rule', 'mask', 'filter', 'display', 'visibility', 'overflow',
    'offset', 'stop-color', 'stop-opacity', 'gradientUnits', 'gradientTransform', 'spreadMethod',
    'patternUnits', 'patternContentUnits', 'patternTransform', 'clipPathUnits', 'maskUnits', 'maskContentUnits',
    'filterUnits', 'primitiveUnits', 'in', 'in2', 'result', 'stdDeviation', 'dx', 'dy', 'mode', 'type',
    'values', 'operator', 'k1', 'k2', 'k3', 'k4', 'flood-color', 'flood-opacity',
    'font-family', 'font-size', 'font-weight', 'font-style', 'text-anchor', 'dominant-baseline',
    'letter-spacing', 'href',
}
# A url() pointing anywhere but an id in the same file, an @import, or a script scheme.
UNSAFE_CSS = re.compile(r'url\(\s*["\']?\s*[^)#\s"\']|@import|expression\(|javascript:', re.IGNORECASE)


def clean_icon(upload) -> ContentFile:
    """The file to store for [upload]; raises ImageRejected with a code saying why not."""
    stem = Path(upload.name or 'icon').stem[:60] or 'icon'
    extension = Path(upload.name or '').suffix.lower().lstrip('.')
    if extension == 'svg':
        return ContentFile(clean_svg(_read(upload, MAX_SVG_BYTES)), name=f'{stem}.svg')
    if extension in ICON_RASTER_EXTENSIONS:
        picture = clean_image(upload).content
        return ContentFile(picture.read(), name=f'{stem}{Path(picture.name).suffix}')
    raise ImageRejected('unsupported_icon')


def clean_svg(data: bytes) -> bytes:
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise ImageRejected('invalid_svg')
    # Entity declarations can expand without bound or point at local files.
    if '<!ENTITY' in text:
        raise ImageRejected('unsafe_svg')
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        raise ImageRejected('invalid_svg')
    if _local_name(root.tag) != 'svg' or _namespace(root.tag) not in ('', SVG_NS):
        raise ImageRejected('invalid_svg')
    _clean_element(root)
    return ET.tostring(root, encoding='utf-8', xml_declaration=False)


def _read(upload, limit: int) -> bytes:
    if upload.size > limit:
        raise ImageRejected('file_too_large')
    upload.seek(0)
    return upload.read()


def _clean_element(element):
    for child in list(element):
        if not isinstance(child.tag, str) or not _is_allowed_element(child.tag):
            element.remove(child)  # comments, processing instructions and foreign elements
            continue
        _clean_element(child)
    for name in list(element.attrib):
        if not _is_safe_attribute(name, element.attrib[name]):
            del element.attrib[name]
    if _local_name(element.tag) == 'style' and element.text and UNSAFE_CSS.search(element.text):
        element.text = ''


def _is_allowed_element(tag: str) -> bool:
    return _namespace(tag) in ('', SVG_NS) and _local_name(tag) in ALLOWED_ELEMENTS


def _is_safe_attribute(name: str, value: str) -> bool:
    namespace, local = _namespace(name), _local_name(name)
    if local == 'href':
        # Only references to an id in the same file (gradients, <use>).
        return namespace in ('', XLINK_NS) and value.strip().startswith('#')
    if namespace or local not in ALLOWED_ATTRIBUTES:
        return False
    return not UNSAFE_CSS.search(value)


def _namespace(tag: str) -> str:
    return tag[1:].split('}', 1)[0] if tag.startswith('{') else ''


def _local_name(tag: str) -> str:
    return tag.split('}', 1)[-1]
