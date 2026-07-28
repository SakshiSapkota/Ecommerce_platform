/**
 * api.js — API client + shared UI helpers
 */

const API = {
  async get(path) {
    const r = await fetch(path, { credentials: 'include' });
    return r.json();
  },
  async post(path, body) {
    const r = await fetch(path, {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    return r.json();
  },
  async del(path) {
    const r = await fetch(path, { method: 'DELETE', credentials: 'include' });
    return r.json();
  },
  async upload(path, formData) {
    const r = await fetch(path, { method: 'POST', credentials: 'include', body: formData });
    return r.json();
  }
};

/* ── Toast ─────────────────────────────────────────────────── */
function ensureToasts() {
  let w = document.getElementById('toasts-wrap');
  if (!w) {
    w = document.createElement('div');
    w.id = 'toasts-wrap';
    w.className = 'toasts-wrap';
    document.body.appendChild(w);
  }
  return w;
}
function showToast(msg, type = 'info', ms = 3500) {
  const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
  const w = ensureToasts();
  const t = document.createElement('div');
  t.className = `toast toast-${type}`;
  t.innerHTML = `<span>${icons[type]||'ℹ️'}</span><span>${msg}</span>`;
  w.appendChild(t);
  setTimeout(() => {
    t.style.opacity = '0';
    t.style.transform = 'translateY(8px)';
    t.style.transition = 'all .3s';
    setTimeout(() => t.remove(), 350);
  }, ms);
}

/* ── Product emoji map ──────────────────────────────────────── */
const EMOJI_MAP = {
  'headphones.svg':'🎧','keyboard.svg':'⌨️','webcam.svg':'📷',
  'ssd.svg':'💾','hoodie.svg':'👘','chinos.svg':'👖',
  'sneakers.svg':'👟','wallet.svg':'👛','book1.svg':'📗',
  'book2.svg':'📘','book3.svg':'📙','book4.svg':'📕',
  'lamp.svg':'💡','cushion.svg':'🛋️','organizer.svg':'🗂️','coffee.svg':'☕'
};
const CAT_EMOJI = { Electronics:'⚡', Books:'📚', Clothing:'👕', Home:'🏠' };

function productVisual(product) {
  if (product.image && product.image.startsWith('/uploads/')) {
    return `<img class="product-card-img" src="${product.image}" alt="${product.name}">`;
  }
  const emoji = EMOJI_MAP[product.image] || CAT_EMOJI[product.category] || '📦';
  return `<span style="font-size:4rem">${emoji}</span>`;
}
function productThumb(product) {
  if (product.image && product.image.startsWith('/uploads/')) {
    return `<img class="product-thumb-img" src="${product.image}" alt="${product.name}">`;
  }
  return EMOJI_MAP[product.image] || CAT_EMOJI[product.category] || '📦';
}

function renderStars(r) {
  const f = Math.floor(r), h = r % 1 >= 0.5;
  return '★'.repeat(f) + (h ? '½' : '');
}

/* ── Product card renderer ──────────────────────────────────── */
function renderProductCard(p, wishIds = []) {
  const inWish = wishIds.includes(p.id);
  const badges = [
    p.badge ? `<div class="product-badge-pill">${p.badge}</div>` : '',
    p.offer_label ? `<div class="product-offer-pill ${p.badge ? 'stacked' : ''}">${p.offer_label}</div>` : '',
    p.discount_percent ? `<div class="product-discount-pill">-${p.discount_percent}%</div>` : ''
  ].join('');
  const price = Number(p.final_price ?? p.price);
  const priceHtml = p.discount_percent
    ? `<div><div class="product-price">$${price.toFixed(2)}</div><div class="product-old-price">$${Number(p.price).toFixed(2)}</div></div>`
    : `<div class="product-price">$${Number(p.price).toFixed(2)}</div>`;
  const visual = productVisual(p);
  return `
  <div class="product-card" data-id="${p.id}">
    <div class="product-img">
      ${visual}${badges}
      <button class="product-wish ${inWish?'active':''}" onclick="toggleWishlist(${p.id},this)">
        ${inWish?'♥':'♡'}
      </button>
    </div>
    <div class="product-body">
      <div class="product-cat">${p.category}</div>
      <div class="product-name">${p.name}</div>
      <div class="product-desc">${p.description||''}</div>
      <div class="product-stars">
        <span class="stars">${renderStars(p.rating)}</span>
        <span class="rating-n">${p.rating}</span>
        <span class="rating-c">(${p.reviews})</span>
      </div>
      <div class="product-foot">
        ${priceHtml}
        <button class="btn-add" onclick="addToCartAnim(${p.id},this)">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/>
            <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>
          </svg>Add
        </button>
      </div>
    </div>
  </div>`;
}

function addToCartAnim(id, btn) {
  addToCart(id);
  const orig = btn.innerHTML;
  btn.classList.add('added');
  btn.innerHTML = '✓ Added';
  setTimeout(() => { btn.classList.remove('added'); btn.innerHTML = orig; }, 1500);
}

/* ── Guest wishlist (localStorage) ─────────────────────────── */
function getGuestWishlist() {
  try { return JSON.parse(localStorage.getItem('guest_wishlist') || '[]'); } catch { return []; }
}
function saveGuestWishlist(ids) {
  localStorage.setItem('guest_wishlist', JSON.stringify(ids));
}

/* ── Wishlist toggle ────────────────────────────────────────── */
async function toggleWishlist(productId, btn) {
  const s = await API.get('/api/session');
  if (!s.loggedIn) {
    // Guest: use localStorage
    let ids = getGuestWishlist();
    if (ids.includes(productId)) {
      ids = ids.filter(i => i !== productId);
      saveGuestWishlist(ids);
      btn.classList.remove('active'); btn.innerHTML = '♡';
      showToast('Removed from wishlist', 'info');
    } else {
      ids.push(productId);
      saveGuestWishlist(ids);
      btn.classList.add('active'); btn.innerHTML = '♥';
      showToast('Saved to wishlist — sign in to keep it across devices', 'success');
    }
    return;
  }
  // Logged in: use server
  if (btn.classList.contains('active')) {
    const r = await API.del(`/api/wishlist/${productId}`);
    if (r.success) { btn.classList.remove('active'); btn.innerHTML = '♡'; showToast('Removed from wishlist','info'); }
  } else {
    const r = await API.post('/api/wishlist', { product_id: productId });
    if (r.success) { btn.classList.add('active'); btn.innerHTML = '♥'; showToast('Saved to wishlist','success'); }
    else showToast(r.error||'Failed','error');
  }
}
