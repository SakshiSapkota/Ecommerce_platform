function clearErrs(){document.querySelectorAll('.form-error-msg').forEach(e=>e.textContent='');document.getElementById('global-err').style.display='none';}
function fErr(inputId,errId,msg){const i=document.getElementById(inputId);const e=document.getElementById(errId);if(i)i.classList.add('is-error');if(e)e.textContent=msg;}
document.getElementById('login-form').addEventListener('submit',async e=>{
  e.preventDefault(); clearErrs();
  const email=document.getElementById('email').value.trim();
  const pw=document.getElementById('password').value;
  let ok=true;
  if(!email||!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)){fErr('email','e-email','Valid email required');ok=false;}
  if(!pw){fErr('password','e-pw','Password required');ok=false;}
  if(!ok)return;
  const btn=document.getElementById('submit-btn'); btn.disabled=true; btn.textContent='Signing in…';
  try {
    const r=await API.post('/api/login',{email,password:pw});
    if(r.success){showToast(`Welcome back, ${r.user.name.split(' ')[0]}!`,'success');setTimeout(()=>location.href=new URLSearchParams(location.search).get('redirect')||'index.html',800);}
    else{const ge=document.getElementById('global-err');ge.textContent=r.errors?.general||r.error||'Login failed';ge.style.display='flex';btn.disabled=false;btn.textContent='Sign In';}
  } catch{document.getElementById('global-err').textContent='Server error — make sure backend is running.';document.getElementById('global-err').style.display='flex';btn.disabled=false;btn.textContent='Sign In';}
});
document.addEventListener('DOMContentLoaded',async()=>{const d=await API.get('/api/session');if(d.loggedIn)location.href='index.html';});
