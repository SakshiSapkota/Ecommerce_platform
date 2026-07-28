/**
 * products.js — Product listing, search, filter, sort
 */
let allProducts = [], wishIds = [], selectedCat = 'All', currentView = 'grid';
const urlP = new URLSearchParams(location.search);

async function loadProducts() {
  const grid = document.getElementById('products-grid');
  grid.innerHTML = '<div class="skeleton"></div>'.repeat(8);
  try {
    const session = await API.get('/api/session');
    if (session.loggedIn) {
      const wl = await API.get('/api/wishlist');
      wishIds = (wl.items||[]).map(i => i.id);
    }
    const d = await API.get('/api/products');
    allProducts = d.products || [];
    const urlCat = urlP.get('category'), urlQ = urlP.get('search');
    if (urlCat) { selectedCat = urlCat; document.querySelectorAll('.cat-pill').forEach(b => { b.classList.toggle('active', b.dataset.cat === urlCat); }); }
    if (urlQ) { const si = document.getElementById('search-in'); if (si) si.value = urlQ; }
    applyFilters();
    const totalEl = document.getElementById('total-count');
    if (totalEl) totalEl.textContent = allProducts.length;
  } catch(e) {
    grid.innerHTML = '<p style="color:var(--text-muted);padding:2rem;grid-column:1/-1">Server not running. Start with: python backend/server.py</p>';
  }
}

function applyFilters() {
  const q    = (document.getElementById('search-in')?.value||'').toLowerCase().trim();
  const minP = parseFloat(document.getElementById('min-price')?.value)||0;
  const maxP = parseFloat(document.getElementById('max-price')?.value)||Infinity;
  const sort = document.getElementById('sort-sel')?.value||'';
  let list = allProducts.filter(p => {
    const mCat = selectedCat==='All' || p.category===selectedCat;
    const mQ   = !q || p.name.toLowerCase().includes(q) || (p.description||'').toLowerCase().includes(q) || p.category.toLowerCase().includes(q);
    const price = p.final_price ?? p.price;
    const mP   = price>=minP && price<=maxP;
    return mCat && mQ && mP;
  });
  if (sort==='price_asc')  list.sort((a,b)=>(a.final_price ?? a.price)-(b.final_price ?? b.price));
  else if (sort==='price_desc') list.sort((a,b)=>(b.final_price ?? b.price)-(a.final_price ?? a.price));
  else if (sort==='rating')     list.sort((a,b)=>b.rating-a.rating);
  else if (sort==='name')       list.sort((a,b)=>a.name.localeCompare(b.name));
  renderProducts(list);
}

function renderProducts(list) {
  const grid    = document.getElementById('products-grid');
  const noRes   = document.getElementById('no-results');
  const resTxt  = document.getElementById('results-txt');
  if (resTxt) resTxt.textContent = `${list.length} product${list.length!==1?'s':''}`;
  if (!list.length) { grid.innerHTML=''; if(noRes) noRes.style.display='flex'; return; }
  if (noRes) noRes.style.display='none';
  grid.className = `products-grid${currentView==='list'?' list-view':''}`;
  grid.innerHTML = list.map(p => renderProductCard(p, wishIds)).join('');
}

function selectCat(btn, cat) {
  selectedCat = cat;
  document.querySelectorAll('.cat-pill').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  applyFilters();
}
function setView(v) {
  currentView = v;
  document.getElementById('btn-grid')?.classList.toggle('active', v==='grid');
  document.getElementById('btn-list')?.classList.toggle('active', v==='list');
  applyFilters();
}
function clearFilters() {
  selectedCat = 'All';
  document.querySelectorAll('.cat-pill').forEach(b => b.classList.toggle('active', b.dataset.cat==='All'));
  ['search-in','min-price','max-price'].forEach(id => { const el=document.getElementById(id); if(el) el.value=''; });
  const ss = document.getElementById('sort-sel'); if (ss) ss.value='';
  applyFilters();
}
let _ft;
function debounceFilter() { clearTimeout(_ft); _ft=setTimeout(applyFilters,220); }
document.addEventListener('DOMContentLoaded', loadProducts);
