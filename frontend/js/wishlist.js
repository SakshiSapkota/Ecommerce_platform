async function loadWishlist(){
  const s=await API.get('/api/session');
  const grid=document.getElementById('wish-grid'),none=document.getElementById('no-wish');
  document.getElementById('auth-req').style.display='none';
  document.getElementById('wish-content').style.display='block';

  if(!s.loggedIn){
    // Guest: load from localStorage
    const ids=getGuestWishlist();
    if(!ids.length){none.style.display='flex';grid.innerHTML='';return;}
    // Fetch product details for each saved id
    const prods=await API.get('/api/products');
    const items=(prods.products||[]).filter(p=>ids.includes(p.id));
    if(!items.length){none.style.display='flex';grid.innerHTML='';return;}
    none.style.display='none';
    grid.innerHTML=items.map(p=>renderProductCard(p,ids)).join('');
    // Show a gentle prompt to sign in
    const note=document.createElement('p');
    note.style.cssText='text-align:center;color:var(--text-light);margin-top:1.5rem;font-size:.9rem';
    note.innerHTML='<a href="login.html" style="color:var(--accent)">Sign in</a> to save your wishlist across devices.';
    grid.parentNode.appendChild(note);
    return;
  }

  const d=await API.get('/api/wishlist');
  const items=d.items||[];
  if(!items.length){none.style.display='flex';grid.innerHTML='';return;}
  none.style.display='none';
  const ids=items.map(i=>i.id);
  grid.innerHTML=items.map(p=>renderProductCard(p,ids)).join('');
}
const _origToggle=window.toggleWishlist;
window.toggleWishlist=async(pid,btn)=>{await toggleWishlist(pid,btn);setTimeout(loadWishlist,500);};
document.addEventListener('DOMContentLoaded',loadWishlist);
