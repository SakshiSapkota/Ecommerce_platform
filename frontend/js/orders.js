async function cancelOrder(oid) {
  if (!confirm(`Cancel order #${oid}? This cannot be undone.`)) return;
  const r = await API.del(`/api/orders/${oid}/cancel`);
  if (r.success) { showToast(r.message, 'success'); setTimeout(loadOrders, 600); }
  else showToast(r.error || 'Could not cancel order', 'error');
}

async function loadOrders(){
  const s=await API.get('/api/session');
  if(!s.loggedIn){document.getElementById('auth-req').style.display='block';document.getElementById('orders-content').style.display='none';return;}
  document.getElementById('auth-req').style.display='none';document.getElementById('orders-content').style.display='block';
  const d=await API.get('/api/orders');
  const list=document.getElementById('orders-list'),none=document.getElementById('no-orders');
  if(!d.orders?.length){none.style.display='flex';list.innerHTML='';return;}
  none.style.display='none';
  const statusClass={Pending:'sp-pending',Shipped:'sp-shipped',Delivered:'sp-delivered',Cancelled:'sp-cancelled',Processing:'sp-processing'};
  const now=Date.now();
  list.innerHTML=d.orders.map(o=>{
    const dt=new Date(o.created_at).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',hour:'2-digit',minute:'2-digit'});
    const items=o.items.map(i=>{
      const th=(i.image&&i.image.startsWith('/uploads/'))?`<img src="${i.image}" alt="" style="width:100%;height:100%;object-fit:cover;border-radius:4px;">`:(EMOJI_MAP[i.image]||CAT_EMOJI[i.category]||'📦');
      return `<div class="oi-row"><div class="oi-img">${th}</div><div class="oi-name">${i.name}</div><div class="oi-qty">×${i.quantity}</div><div class="oi-price">$${(i.price*i.quantity).toFixed(2)}</div></div>`;
    }).join('');
    const canCancel = o.status === 'Pending' && (now - new Date(o.created_at).getTime()) < 24*60*60*1000;
    const cancelBtn = canCancel ? `<button onclick="cancelOrder(${o.id})" style="background:none;border:1px solid var(--danger,#f43f5e);color:var(--danger,#f43f5e);padding:.35rem .85rem;border-radius:6px;cursor:pointer;font-size:.82rem;">Cancel Order</button>` : '';
    return `<div class="order-card">
      <div class="order-card-head"><div><div class="order-id">Order #${o.id}</div><div class="order-meta"><span>📅 ${dt}</span><span>📦 ${o.items.length} item(s)</span></div></div><span class="sp ${statusClass[o.status]||'sp-pending'}">${o.status}</span></div>
      <div class="order-items-list">${items}</div>
      <div class="order-card-foot"><span class="order-total-lbl">Order Total</span><span class="order-total-val">$${Number(o.total).toFixed(2)}</span>${cancelBtn}</div>
    </div>`;
  }).join('');
}
document.addEventListener('DOMContentLoaded',loadOrders);
