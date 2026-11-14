"""Uploaded announcement icons: SVGs are stored without anything that could run, pictures re-encoded."""
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from ..forms.announcement_admin import AnnouncementAdminForm
from ..services.announcement_icons import ImageRejected, clean_svg
from .test_announcement_admin import form_data

CLEAN_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 24 24">'
    b'<defs><linearGradient id="g"><stop offset="0" stop-color="#f00"/></linearGradient></defs>'
    b'<path d="M0 0h24v24H0z" fill="url(#g)"/><use xlink:href="#g"/></svg>'
)
HOSTILE_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" onload="alert(1)">'
    b'<script>alert(1)</script>'
    b'<foreignObject><div xmlns="http://www.w3.org/1999/xhtml">x</div></foreignObject>'
    b'<a href="javascript:alert(1)"><circle r="4"/></a>'
    b'<image href="https://evil.example/x.png"/>'
    b'<animate attributeName="href" to="javascript:alert(1)"/>'
    b'<rect width="4" height="4" style="fill:url(https://evil.example/x)" onclick="alert(1)"/>'
    b'<style>@import url(https://evil.example/x.css);</style>'
    b'<rect width="1" style="fill:u\\72l(https://evil.example/escaped)"/>'
    b'<rect width="2" fill="image-set(\'https://evil.example/set\' 1x)"/>'
    b'<rect width="3" fill="url( //evil.example/spaced)"/>'
    b'<circle r="2" fill="red"/></svg>'
)


def png_bytes(mode='RGBA'):
    buffer = io.BytesIO()
    Image.new(mode, (64, 64), (200, 0, 0, 128) if mode == 'RGBA' else (200, 0, 0)).save(buffer, format='PNG')
    return buffer.getvalue()


class CleanSvgTests(TestCase):
    def test_a_drawing_keeps_its_shapes_and_same_file_references(self):
        cleaned = clean_svg(CLEAN_SVG).decode()
        for kept in ('viewBox="0 0 24 24"', 'fill="url(#g)"', 'href="#g"', '<linearGradient', 'stop-color="#f00"'):
            self.assertIn(kept, cleaned)

    def test_scripts_handlers_foreign_content_and_outside_links_are_removed(self):
        cleaned = clean_svg(HOSTILE_SVG).decode()
        for removed in ('script', 'onload', 'onclick', 'foreignObject', 'javascript', 'evil.example',
                        '<animate', '<image', '<style', '@import', 'image-set'):
            self.assertNotIn(removed, cleaned)
        self.assertIn('fill="red"', cleaned)
        self.assertIn('width="1"', cleaned)  # the shape stays, without its unsafe style

    def test_colours_and_transforms_keep_their_functions(self):
        cleaned = clean_svg(
            b'<svg xmlns="http://www.w3.org/2000/svg"><g transform="translate(2, 3) rotate(45)">'
            b'<rect fill="rgba(0, 0, 0, 0.5)" style="stroke:#fff;stroke-width:2"/></g></svg>'
        ).decode()
        for kept in ('translate(2, 3) rotate(45)', 'rgba(0, 0, 0, 0.5)', 'stroke:#fff;stroke-width:2'):
            self.assertIn(kept, cleaned)

    def test_entities_and_non_svg_files_are_refused(self):
        bomb = b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY a "aaaa">]><svg xmlns="http://www.w3.org/2000/svg">&a;</svg>'
        for data, code in (
            (bomb, 'unsafe_svg'),
            (bomb.decode().encode('utf-16'), 'invalid_svg'),
            (b'<html><body/></html>', 'invalid_svg'),
            (b'not xml', 'invalid_svg'),
        ):
            with self.assertRaises(ImageRejected) as raised:
                clean_svg(data)
            self.assertEqual(raised.exception.code, code)


class IconUploadFormTests(TestCase):
    def form(self, name, content, **overrides):
        upload = SimpleUploadedFile(name, content)
        return AnnouncementAdminForm(data=form_data(icon_name='', **overrides), files={'icon_image': upload})

    def test_an_svg_replaces_the_named_icon_and_is_stored_cleaned(self):
        form = self.form('choir.svg', HOSTILE_SVG)
        self.assertTrue(form.is_valid(), form.errors)
        stored = form.cleaned_data['icon_image']
        self.assertEqual(stored.name, 'choir.svg')
        self.assertNotIn(b'script', stored.read())

    def test_a_picture_is_re_encoded_and_keeps_its_transparency(self):
        form = self.form('choir.webp', png_bytes())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['icon_image'].name, 'choir.png')

    def test_other_files_are_refused(self):
        for name, content in (('icon.exe', b'MZ'), ('icon.png', b'not a picture'), ('icon.svg', b'<html/>')):
            self.assertIn('icon_image', self.form(name, content).errors, name)
