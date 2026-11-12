// Live preview next to the announcement's markdown fields.
// "inline" mode (card description): **bold**, *italic*, [link](url).
// "full" mode (page): also headings, lists, quotes and images.
(function () {
  'use strict';

  function escapeHtml(text) {
    return text.replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }

  function safeUrl(url) {
    return /^(https?:|mailto:|\/)/i.test(url) ? url : '#';
  }

  function inline(text) {
    return escapeHtml(text)
      .replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, function (_, alt, url) {
        return '<img alt="' + alt + '" src="' + safeUrl(url) + '">';
      })
      .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, function (_, label, url) {
        return '<a href="' + safeUrl(url) + '" target="_blank" rel="noopener">' + label + '</a>';
      })
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, '$1<em>$2</em>');
  }

  // A paragraph that is only a YouTube link: the facade the clients show (the server checks the same rule).
  function youtube(text) {
    var url;
    try { url = new URL(text.trim()); } catch (e) { return ''; }
    if (!/^(www\.|m\.|music\.)?(youtube\.com|youtube-nocookie\.com|youtu\.be)$/.test(url.hostname)) return '';
    var parts = url.pathname.split('/').filter(Boolean);
    var video = url.hostname.indexOf('youtu.be') > -1 ? parts[0]
      : parts[0] === 'watch' ? url.searchParams.get('v')
      : /^(shorts|live|embed)$/.test(parts[0]) ? parts[1] : null;
    var list = url.searchParams.get('list');
    if (video && /^[A-Za-z0-9_-]{11}$/.test(video)) {
      return '<figure class="rc-embed' + (parts[0] === 'shorts' ? ' rc-embed--short' : '') + '">' +
        '<img src="https://i.ytimg.com/vi/' + video + '/hqdefault.jpg" alt=""><span>▶</span></figure>';
    }
    if (parts[0] === 'playlist' && list && /^[A-Za-z0-9_-]{10,64}$/.test(list)) {
      return '<figure class="rc-embed rc-embed--list"><span>▶</span> YouTube playlist</figure>';
    }
    return '';
  }

  function block(markdown) {
    var html = [];
    var list = null;
    var paragraph = [];

    function flushParagraph() {
      var embed = paragraph.length === 1 && youtube(paragraph[0].replace(/^<(.*)>$/, '$1'));
      if (embed) html.push(embed);
      else if (paragraph.length) html.push('<p>' + inline(paragraph.join(' ')) + '</p>');
      paragraph = [];
    }
    function closeList() {
      if (list) html.push('</' + list + '>');
      list = null;
    }
    function openList(tag) {
      if (list !== tag) { closeList(); html.push('<' + tag + '>'); list = tag; }
    }

    markdown.split(/\r?\n/).forEach(function (line) {
      var heading = line.match(/^(#{1,3})\s+(.*)$/);
      var bullet = line.match(/^\s*[-*]\s+(.*)$/);
      var numbered = line.match(/^\s*\d+[.)]\s+(.*)$/);
      var quote = line.match(/^>\s?(.*)$/);

      if (!line.trim()) { flushParagraph(); closeList(); return; }
      if (heading) {
        flushParagraph(); closeList();
        var level = heading[1].length + 1;
        html.push('<h' + level + '>' + inline(heading[2]) + '</h' + level + '>');
      } else if (bullet || numbered) {
        flushParagraph(); openList(bullet ? 'ul' : 'ol');
        html.push('<li>' + inline((bullet || numbered)[1]) + '</li>');
      } else if (quote) {
        flushParagraph(); closeList();
        html.push('<blockquote>' + inline(quote[1]) + '</blockquote>');
      } else {
        closeList(); paragraph.push(line.trim());
      }
    });
    flushParagraph();
    closeList();
    return html.join('');
  }

  function render(textarea, preview) {
    var value = textarea.value || '';
    var mode = textarea.getAttribute('data-markdown-preview');
    preview.innerHTML = value.trim()
      ? (mode === 'full' ? block(value) : '<p>' + inline(value.replace(/\s*\n\s*/g, ' ')) + '</p>')
      : '<p class="announcement-md__empty">Preview</p>';
  }

  function setup() {
    document.querySelectorAll('textarea[data-markdown-preview]').forEach(function (textarea) {
      var preview = document.querySelector('[data-preview-for="' + textarea.id + '"]');
      if (!preview || textarea.dataset.previewReady) return;
      textarea.dataset.previewReady = '1';
      textarea.addEventListener('input', function () { render(textarea, preview); });
      render(textarea, preview);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setup);
  else setup();
})();
