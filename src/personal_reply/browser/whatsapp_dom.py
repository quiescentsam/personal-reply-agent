"""Extract WhatsApp Web thread data from the browser DOM."""

WHATSAPP_EXTRACT_SCRIPT = """
() => {
  const isStatusText = (text) => {
    if (!text) return true;
    const lower = text.toLowerCase();
    return (
      lower.includes('last seen') ||
      lower.includes('online') ||
      lower.includes('typing') ||
      lower.includes('recording') ||
      /^today at \\d/i.test(text) ||
      /^yesterday at \\d/i.test(text)
    );
  };

  const compose =
    document.querySelector('footer div[contenteditable="true"][data-tab="10"]') ||
    document.querySelector('footer div[contenteditable="true"][role="textbox"]') ||
    document.querySelector('div[contenteditable="true"][data-tab="10"]');

  const contactCandidates = [];
  const pushCandidate = (value) => {
    const text = (value || '').trim();
    if (text && !isStatusText(text)) {
      contactCandidates.push(text);
    }
  };

  for (const node of document.querySelectorAll(
    '#main header span[title], header [data-testid="conversation-info-header"] span[title]'
  )) {
    pushCandidate(node.getAttribute('title'));
  }

  const infoHeader = document.querySelector('header [data-testid="conversation-info-header"]');
  if (infoHeader) {
    for (const node of infoHeader.querySelectorAll('span[dir="auto"]')) {
      pushCandidate(node.textContent);
    }
  }

  for (const node of document.querySelectorAll('#main header span[dir="auto"]')) {
    pushCandidate(node.textContent);
  }

  const contact = contactCandidates[0] || '';

  const messageNodes = Array.from(
    document.querySelectorAll('#main [data-testid="msg-container"]')
  );

  const messages = [];
  for (const node of messageNodes) {
    const prePlain = node.querySelector('[data-pre-plain-text]');
    let sender = '';
    let text = '';
    let time = '';

    if (prePlain) {
      const raw = prePlain.getAttribute('data-pre-plain-text') || '';
      const timeMatch = raw.match(/^\\[([^\\]]+)\\]/);
      time = timeMatch ? timeMatch[1].trim() : '';
      const match = raw.match(/^\\[[^\\]]+\\]\\s([^:]+):\\s([\\s\\S]*)$/);
      if (match) {
        sender = match[1].trim();
        text = match[2].trim();
      } else {
        text = prePlain.textContent?.trim() || '';
      }
    }

    if (!text) {
      const textNode =
        node.querySelector('[data-testid="msg-text"] span.selectable-text') ||
        node.querySelector('span.selectable-text.copyable-text') ||
        node.querySelector('span.selectable-text');
      text = textNode?.textContent?.trim() || '';
    }

    if (!sender) {
      const outgoing =
        node.closest('.message-out') ||
        node.querySelector('.message-out') ||
        node.querySelector('[data-testid="outgoing-msg"]');
      sender = outgoing ? 'me' : contact;
    }

    if (text) {
      messages.push({ sender, text, time });
    }
  }

  return {
    contact,
    messages,
    composeSelector: compose
      ? 'footer div[contenteditable="true"][data-tab="10"], footer div[contenteditable="true"][role="textbox"], div[contenteditable="true"][data-tab="10"]'
      : null,
    url: location.href,
  };
}
"""
