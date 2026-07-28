let step = 'shipping';
function initCheckout() {
  const cart = getCart();
  if (!cart.length) { document.getElementById('empty-warn').style.display='block'; document.getElementById('checkout-layout').style.display='none'; return; }
  API.get('/api/session').then(d => {
    if (!d.loggedIn) {
      document.getElementById('checkout-layout').style.display='none';
      document.getElementById('guest-warn').style.display='block';
      return;
    }
    renderSummary(cart);
    const ne=document.getElementById('ship-name'), ee=document.getElementById('ship-email');
    if(ne&&!ne.value) ne.value=d.user.name;
    if(ee&&!ee.value) ee.value=d.user.email;
  });
}
function renderSummary(cart) {
  const sub = cart.reduce((s,i)=>s+i.price*i.quantity,0);
  const ship = sub>=50?0:5.99, total=sub+ship;
  document.getElementById('sum-items').innerHTML = cart.map(i=>{
    const th=(i.image&&i.image.startsWith('/uploads/'))?`<img src="${i.image}" alt="" style="width:100%;height:100%;object-fit:cover;border-radius:4px;">`:(EMOJI_MAP[i.image]||CAT_EMOJI[i.category]||'📦');
    return `<div class="order-line"><div class="order-line-img">${th}</div><div><div class="order-line-name">${i.name}</div><div class="order-line-qty">×${i.quantity}</div></div><div class="order-line-price">$${(i.price*i.quantity).toFixed(2)}</div></div>`;
  }).join('');
  document.getElementById('sum-sub').textContent   = '$'+sub.toFixed(2);
  document.getElementById('sum-ship').textContent  = ship===0?'Free':'$'+ship.toFixed(2);
  document.getElementById('sum-total').textContent = '$'+total.toFixed(2);
}
function clearFErrs() { document.querySelectorAll('.form-error-msg').forEach(e=>e.textContent=''); document.querySelectorAll('.form-input.is-error').forEach(e=>e.classList.remove('is-error')); }
function fErr(inputId,errId,msg){const i=document.getElementById(inputId);const e=document.getElementById(errId);if(i)i.classList.add('is-error');if(e)e.textContent=msg;}
function validEmail(e){return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e)}
function goToPayment() {
  clearFErrs(); let ok=true;
  const name=document.getElementById('ship-name')?.value.trim();
  const email=document.getElementById('ship-email')?.value.trim();
  const addr=document.getElementById('ship-address')?.value.trim();
  const city=document.getElementById('ship-city')?.value.trim();
  const zip=document.getElementById('ship-zip')?.value.trim();
  if(!name||name.length<2){fErr('ship-name','e-name','Full name required');ok=false;}
  if(!validEmail(email)){fErr('ship-email','e-email','Valid email required');ok=false;}
  if(!addr){fErr('ship-address','e-addr','Address required');ok=false;}
  if(!city){fErr('ship-city','e-city','City required');ok=false;}
  if(!zip||zip.length<3){fErr('ship-zip','e-zip','ZIP required');ok=false;}
  if(!ok)return;
  document.getElementById('step-shipping').style.display='none';
  document.getElementById('step-payment').style.display='block';
  document.getElementById('step-lbl-payment').classList.add('active');
  step='payment'; window.scrollTo({top:0,behavior:'smooth'});
}
function goBack() {
  document.getElementById('step-payment').style.display='none';
  document.getElementById('step-shipping').style.display='block';
  document.getElementById('step-lbl-payment').classList.remove('active');
  step='shipping';
}
function selectPayment(radio) {
  document.querySelectorAll('.pay-opt').forEach(o=>o.classList.remove('selected'));
  radio.closest('.pay-opt').classList.add('selected');
  document.getElementById('card-fields').style.display = radio.value==='card'?'block':'none';
}
function fmtCard(el){let v=el.value.replace(/\D/g,'').substring(0,16);el.value=v.replace(/(.{4})/g,'$1 ').trim();}
function fmtExpiry(el){let v=el.value.replace(/\D/g,'').substring(0,4);if(v.length>=3)v=v.substring(0,2)+'/'+v.substring(2);el.value=v;}
async function placeOrder() {
  clearFErrs(); let ok=true;
  const method=document.querySelector('input[name=payment]:checked')?.value||'card';
  if(method==='card'){
    const card=document.getElementById('card-num')?.value.replace(/\s/g,'');
    const exp=document.getElementById('card-exp')?.value;
    const cvv=document.getElementById('card-cvv')?.value;
    if(!card||card.length<13){fErr('card-num','e-card','Enter valid card number');ok=false;}
    if(!exp||!/^\d{2}\/\d{2}$/.test(exp)){fErr('card-exp','e-exp','Format MM/YY');ok=false;}
    if(!cvv||cvv.length<3){fErr('card-cvv','e-cvv','3-digit CVV');ok=false;}
    if(!ok)return;
  }
  const btn=document.getElementById('place-btn'); btn.disabled=true; btn.textContent='Placing…';
  const cart=getCart();
  const shipping={
    name:document.getElementById('ship-name').value.trim(),
    email:document.getElementById('ship-email').value.trim(),
    address:document.getElementById('ship-address').value.trim(),
    city:document.getElementById('ship-city').value.trim(),
    zip:document.getElementById('ship-zip').value.trim()
  };
  try {
    const r=await API.post('/api/orders',{items:cart.map(i=>({id:i.id,quantity:i.quantity})),shipping,payment_method:method});
    if(r.success){
      clearCart();
      document.getElementById('order-id-show').textContent='#'+r.order_id;
      document.getElementById('success-modal').classList.add('open');
    } else {
      if(r.errors)Object.entries(r.errors).forEach(([k,v])=>showToast(`${k}: ${v}`,'error'));
      else showToast(r.error||'Order failed','error');
      btn.disabled=false; btn.textContent='Place Order';
    }
  } catch(e){ showToast('Network error','error'); btn.disabled=false; btn.textContent='Place Order'; }
}
document.addEventListener('DOMContentLoaded',initCheckout);
