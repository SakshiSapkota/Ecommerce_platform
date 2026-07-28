document.getElementById('password').addEventListener('input',function(){
  const v=this.value,bar=document.getElementById('pw-bar');
  if(!bar)return;
  let s=0;if(v.length>=6)s++;if(v.length>=10)s++;if(/[A-Z]/.test(v))s++;if(/[0-9]/.test(v))s++;if(/[^A-Za-z0-9]/.test(v))s++;
  const colors=['','#f43f5e','#f59e0b','#f59e0b','#10b981','#10b981'];
  bar.style.width=(s/5*100)+'%'; bar.style.background=colors[s]||'var(--slate-200)';
});
function clearErrs(){document.querySelectorAll('.form-error-msg').forEach(e=>e.textContent='');document.getElementById('global-err').style.display='none';}
function fErr(inputId,errId,msg){const i=document.getElementById(inputId);const e=document.getElementById(errId);if(i)i.classList.add('is-error');if(e)e.textContent=msg;}
document.getElementById('register-form').addEventListener('submit',async e=>{
  e.preventDefault(); clearErrs();
  const name=document.getElementById('name').value.trim();
  const email=document.getElementById('email').value.trim();
  const pw=document.getElementById('password').value;
  const cpw=document.getElementById('confirm-pw').value;
  let ok=true;
  if(name.length<2){fErr('name','e-name','Min 2 characters');ok=false;}
  if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)){fErr('email','e-email','Valid email required');ok=false;}
  if(pw.length<6){fErr('password','e-pw','Min 6 characters');ok=false;}
  if(pw!==cpw){fErr('confirm-pw','e-cpw','Passwords do not match');ok=false;}
  if(!ok)return;
  const btn=document.getElementById('submit-btn'); btn.disabled=true; btn.textContent='Creating…';
  try {
    const r=await API.post('/api/register',{name,email,password:pw});
    if(r.success){showToast(`Welcome, ${r.user.name.split(' ')[0]}!`,'success');setTimeout(()=>location.href=new URLSearchParams(location.search).get('redirect')||'index.html',800);}
    else{if(r.errors){if(r.errors.name)fErr('name','e-name',r.errors.name);if(r.errors.email)fErr('email','e-email',r.errors.email);if(r.errors.password)fErr('password','e-pw',r.errors.password);}else{const ge=document.getElementById('global-err');ge.textContent=r.error||'Registration failed';ge.style.display='flex';}btn.disabled=false;btn.textContent='Create Account';}
  } catch{document.getElementById('global-err').textContent='Server error';document.getElementById('global-err').style.display='flex';btn.disabled=false;btn.textContent='Create Account';}
});
document.addEventListener('DOMContentLoaded',async()=>{const d=await API.get('/api/session');if(d.loggedIn)location.href='index.html';});
