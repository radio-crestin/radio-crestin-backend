from django.test import SimpleTestCase

from ..services.announcement_html import body_html, page_html

LINK_ATTRS = 'target="_blank" rel="noopener noreferrer"'


class BodyHtmlTests(SimpleTestCase):
    def test_inline_markdown(self):
        self.assertEqual(
            body_html('**Live** at *19:00* on [Radio Elim](https://radioelim.ro)'),
            f'<strong>Live</strong> at <em>19:00</em> on <a href="https://radioelim.ro" {LINK_ATTRS}>Radio Elim</a>',
        )

    def test_paragraphs_become_line_breaks(self):
        self.assertEqual(body_html('One\n\nTwo'), 'One<br>Two')

    def test_only_the_inline_allowlist(self):
        html = body_html('# Big\n\n- item\n\n<script>alert(1)</script><img src="https://x/i.png" onerror="x">')
        for tag in ('<h1', '<li', '<script', '<img', 'alert', 'onerror'):
            self.assertNotIn(tag, html)
        self.assertIn('Big', html)

    def test_contact_links_kept_unsafe_ones_dropped(self):
        self.assertIn('href="mailto:radio@x.ro"', body_html('[mail](mailto:radio@x.ro)'))
        self.assertIn('href="tel:+40700000000"', body_html('[call](tel:+40700000000)'))
        for url in ('javascript:alert(1)', 'data:text/html,x', 'vbscript:x', 'file:///etc/passwd'):
            self.assertNotIn('href', body_html(f'[x]({url})'), url)
        self.assertNotIn('javascript', body_html('<a href="javascript:alert(1)">x</a>'))

    def test_empty(self):
        self.assertEqual(body_html(''), '')
        self.assertEqual(body_html('   '), '')


class PageHtmlTests(SimpleTestCase):
    def test_full_markdown(self):
        html = page_html('## Program\n\n1. Opening\n2. Carols\n\n> Luke 2:11\n\n---\n\n![Choir](https://cdn.x/c.png)')
        for fragment in ('<h2>Program</h2>', '<ol>', '<li>Opening</li>', '<blockquote>', '<hr>',
                         '<img alt="Choir" src="https://cdn.x/c.png">'):
            self.assertIn(fragment, html)

    def test_figures_and_image_sizes(self):
        html = page_html('<figure><img src="https://cdn.x/c.png" alt="Choir" width="640" height="360" '
                         'style="x" onload="x"><figcaption>Choir</figcaption></figure>')
        self.assertIn('<figure><img src="https://cdn.x/c.png" alt="Choir" width="640" height="360">', html)
        self.assertIn('<figcaption>Choir</figcaption>', html)
        self.assertNotIn('onload', html)
        self.assertNotIn('style', html)

    def test_images_only_from_http(self):
        self.assertNotIn('src', page_html('![x](data:image/png;base64,AAAA)'))
        self.assertNotIn('src', page_html('<img src="javascript:alert(1)">'))
        self.assertNotIn('<iframe', page_html('<iframe src="https://x"></iframe>'))
