(() => {
  'use strict';

  const menu = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.nav');
  const mobile = window.matchMedia('(max-width: 760px)');

  const setMenu = (open, returnFocus = false) => {
    if (!menu || !nav) return;
    const expanded = mobile.matches && open;
    menu.setAttribute('aria-expanded', String(expanded));
    nav.classList.toggle('is-open', expanded);
    nav.inert = mobile.matches && !expanded;
    if (mobile.matches && !expanded) nav.setAttribute('aria-hidden', 'true');
    else nav.removeAttribute('aria-hidden');
    if (returnFocus) menu.focus({ preventScroll: true });
  };

  if (menu && nav) {
    menu.addEventListener('click', () => {
      setMenu(menu.getAttribute('aria-expanded') !== 'true');
    });
    nav.addEventListener('click', event => {
      if (event.target.closest('a')) setMenu(false);
    });
    document.addEventListener('click', event => {
      if (!nav.contains(event.target) && !menu.contains(event.target)) {
        setMenu(false, nav.contains(document.activeElement));
      }
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && menu.getAttribute('aria-expanded') === 'true') {
        setMenu(false, true);
      }
    });
    const resetMenu = () => setMenu(false, mobile.matches && nav.contains(document.activeElement));
    if (mobile.addEventListener) mobile.addEventListener('change', resetMenu);
    else mobile.addListener(resetMenu);
    setMenu(false);
    document.documentElement.classList.add('nav-ready');
  }

  document.querySelectorAll('[data-filter-group]').forEach(group => {
    const target = document.getElementById(group.dataset.filterGroup);
    if (!target) return;
    const buttons = [...group.querySelectorAll('button[data-filter]')];
    const entries = [...target.querySelectorAll('[data-category]')];
    const status = document.getElementById(`${group.dataset.filterGroup}-status`);
    const apply = (button, announce = true) => {
      let count = 0;
      buttons.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
      entries.forEach(item => {
        const show = button.dataset.filter === 'all' || item.dataset.category === button.dataset.filter;
        item.hidden = !show;
        if (show) count++;
      });
      if (status && announce) status.textContent = `${count} ${count === 1 ? 'entry' : 'entries'} shown`;
    };
    buttons.forEach(button => button.addEventListener('click', () => apply(button)));
    const selected = buttons.find(button => button.getAttribute('aria-pressed') === 'true') || buttons[0];
    if (selected) {
      apply(selected, false);
      group.classList.add('is-ready');
    }
  });

  const dialog = document.getElementById('photo-dialog');
  if (!dialog || typeof dialog.showModal !== 'function') return;
  const image = dialog.querySelector('#lightbox-image');
  const caption = dialog.querySelector('#lightbox-caption');
  const counter = dialog.querySelector('#lightbox-counter');
  const previous = dialog.querySelector('.lightbox-prev');
  const next = dialog.querySelector('.lightbox-next');
  const close = dialog.querySelector('.lightbox-close');
  if (!image || !caption || !counter || !previous || !next || !close) return;

  let message = dialog.querySelector('.lightbox-message');
  if (!message) {
    message = document.createElement('p');
    message.className = 'lightbox-message';
    message.setAttribute('role', 'status');
    image.insertAdjacentElement('afterend', message);
  }
  let group = [];
  let index = 0;
  let opener = null;
  let request = 0;
  let pending = null;
  let previousOverflow = '';

  const cancelLoad = () => {
    request++;
    if (pending) {
      pending.onload = null;
      pending.onerror = null;
      pending.removeAttribute('src');
      pending = null;
    }
  };

  const showPhoto = nextIndex => {
    if (!group.length) return;
    index = (nextIndex + group.length) % group.length;
    cancelLoad();
    const token = request;
    const anchor = group[index];
    const thumbnail = anchor.querySelector('img');
    const description = anchor.dataset.caption || thumbnail?.alt || '';
    const source = anchor.dataset.full ? new URL(anchor.dataset.full, document.baseURI).href : anchor.href;
    image.style.transform = anchor.dataset.rotation === '180' ? 'rotate(180deg)' : '';
    image.hidden = true;
    image.removeAttribute('src');
    image.alt = thumbnail?.alt || description;
    caption.textContent = description;
    counter.textContent = `${index + 1} / ${group.length}`;
    dialog.classList.toggle('single-image', group.length < 2);
    previous.hidden = group.length < 2;
    next.hidden = group.length < 2;
    previous.disabled = group.length < 2;
    next.disabled = group.length < 2;
    message.hidden = false;
    message.textContent = 'Loading photo…';
    dialog.setAttribute('aria-busy', 'true');

    const candidate = new Image();
    pending = candidate;
    candidate.onload = () => {
      if (token !== request || !dialog.open) return;
      image.src = source;
      image.width = candidate.naturalWidth;
      image.height = candidate.naturalHeight;
      image.hidden = false;
      message.hidden = true;
      dialog.removeAttribute('aria-busy');
      pending = null;
    };
    candidate.onerror = () => {
      if (token !== request || !dialog.open) return;
      const fallback = document.createElement('a');
      fallback.href = source;
      fallback.textContent = 'Open the photo directly';
      message.replaceChildren(document.createTextNode('This photo could not be loaded. '), fallback);
      dialog.removeAttribute('aria-busy');
      pending = null;
    };
    candidate.src = source;
  };

  document.addEventListener('click', event => {
    const anchor = event.target.closest('a[data-lightbox]');
    if (!anchor || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const gallery = anchor.closest('[data-gallery]');
    group = gallery
      ? [...gallery.querySelectorAll('a[data-lightbox]')].filter(item => !item.closest('[hidden]'))
      : [anchor];
    index = group.indexOf(anchor);
    if (index < 0) return;
    opener = anchor;
    setMenu(false);
    try {
      if (!dialog.open) dialog.showModal();
    } catch {
      return; // Leave the normal image link usable if the dialog cannot open.
    }
    event.preventDefault();
    previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    showPhoto(index);
    close.focus({ preventScroll: true });
  });

  close.addEventListener('click', () => dialog.close());
  previous.addEventListener('click', () => showPhoto(index - 1));
  next.addEventListener('click', () => showPhoto(index + 1));
  dialog.addEventListener('keydown', event => {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault();
      showPhoto(index + (event.key === 'ArrowRight' ? 1 : -1));
    }
  });
  // A native dialog traps focus, makes the rest of the page inert, and handles Escape.
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const bounds = dialog.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
  });
  dialog.addEventListener('close', () => {
    cancelLoad();
    image.removeAttribute('src');
    image.hidden = true;
    dialog.removeAttribute('aria-busy');
    document.body.style.overflow = previousOverflow;
    if (opener?.isConnected) opener.focus({ preventScroll: true });
    group = [];
    opener = null;
  });
})();
