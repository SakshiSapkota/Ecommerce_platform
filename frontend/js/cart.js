/**
 * cart.js — Cart state (localStorage) + sidebar
 */
const CART_KEY = 'sajhamart_cart_v2';

function getCart() {
  try { return JSON.parse(localStorage.getItem(CART_KEY)) || []; } catch { return []; }
}
function saveCart(cart) {
  localStorage.setItem(CART_KEY, JSON.stringify(cart));
  renderCart(); updateCartCount();
}
function addToCart(pid) {
  API.get(`/api/products/${pid}`).then(d => {
    if (!d.success) return showToast('Product not found','error');
    const p = d.product;
    const cart = getCart();
    const ex = cart.find(i => i.id === p.id);
    if (ex) ex.quantity = Math.min(ex.quantity + 1, 10);
    else cart.push({ id:p.id, name:p.name, price:(p.final_price ?? p.price), image:p.image, category:p.category, quantity:1 });
    saveCart(cart);
    showToast(`${p.name} added to cart`, 'success');
    openCart();
  });
}
function removeFromCart(pid) { saveCart(getCart().filter(i => i.id !== pid)); }
function updateQty(pid, delta) {
  const cart = getCart();
  const item = cart.find(i => i.id === pid);
  if (item) item.quantity = Math.max(1, Math.min(item.quantity + delta, 10));
  saveCart(cart);
}
function clearCart() { saveCart([]); showToast('Cart cleared','info'); }
function getTotal() { return getCart().reduce((s,i) => s + i.price * i.quantity, 0); }
function getCount() { return getCart().reduce((s,i) => s + i.quantity, 0); }

function updateCartCount() {
  const n = getCount();
  document.querySelectorAll('.cart-badge').forEach(el => el.textContent = n);
}

function renderCart() {
  const cart  = getCart();
  const body  = document.getElementById('cart-body');
  const foot  = document.getElementById('cart-foot');
  const empty = document.getElementById('cart-empty');
  const total = document.getElementById('cart-total');
  if (!body) return;

  if (!cart.length) {
    body.innerHTML = '';
    if (foot)  foot.style.display  = 'none';
    if (empty) empty.style.display = 'flex';
    return;
  }
  if (empty) empty.style.display = 'none';
  if (foot)  foot.style.display  = 'flex';

  body.innerHTML = cart.map(item => {
    const thumb = (item.image && item.image.startsWith('/uploads/'))
      ? `<img src="${item.image}" alt="" style="width:100%;height:100%;object-fit:cover;border-radius:6px;">`
      : (EMOJI_MAP[item.image] || CAT_EMOJI[item.category] || '📦');
    return `
    <div class="cart-item">
      <div class="cart-item-img">${thumb}</div>
      <div>
        <div class="cart-item-name">${item.name}</div>
        <div class="cart-item-price">$${(item.price * item.quantity).toFixed(2)}</div>
      </div>
      <div class="cart-item-right">
        <div class="qty-row">
          <button class="qty-btn" onclick="updateQty(${item.id},-1)">−</button>
          <span class="qty-val">${item.quantity}</span>
          <button class="qty-btn" onclick="updateQty(${item.id},1)">+</button>
        </div>
        <button class="remove-btn" onclick="removeFromCart(${item.id})" title="Remove">🗑</button>
      </div>
    </div>`;
  }).join('');

  if (total) total.textContent = `$${getTotal().toFixed(2)}`;
}

function toggleCart() {
  const sb = document.getElementById('cart-sidebar');
  const ov = document.getElementById('cart-overlay');
  if (!sb) return;
  const open = sb.classList.contains('open');
  sb.classList.toggle('open', !open);
  if (ov) ov.classList.toggle('open', !open);
  document.body.style.overflow = open ? '' : 'hidden';
  if (!open) renderCart();
}
function openCart() {
  const sb = document.getElementById('cart-sidebar');
  const ov = document.getElementById('cart-overlay');
  if (!sb) return;
  sb.classList.add('open');
  if (ov) ov.classList.add('open');
  document.body.style.overflow = 'hidden';
  renderCart();
}

document.addEventListener('DOMContentLoaded', () => { updateCartCount(); renderCart(); });
