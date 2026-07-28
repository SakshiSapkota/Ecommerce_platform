/**
 * auth.js — Session + navbar
 */
let currentUser = null;

async function initAuth() {
  try {
    const d = await API.get('/api/session');
    if (d.loggedIn) { currentUser = d.user; setLoggedIn(d.user); }
    else setLoggedOut();
  } catch { setLoggedOut(); }
}

function setLoggedIn(u) {
  document.querySelectorAll('.js-logged-out').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.js-logged-in').forEach(el => el.style.display = 'block');
  document.querySelectorAll('.js-user-name').forEach(el => el.textContent = u.name.split(' ')[0]);
  document.querySelectorAll('.js-greeting').forEach(el => el.textContent = `Hi, ${u.name.split(' ')[0]}`);
}
function setLoggedOut() {
  document.querySelectorAll('.js-logged-in').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.js-logged-out').forEach(el => el.style.display = 'block');
}

function toggleUserMenu() {
  document.getElementById('user-dropdown')?.classList.toggle('open');
}
document.addEventListener('click', e => {
  const m = document.getElementById('user-menu');
  if (m && !m.contains(e.target))
    document.getElementById('user-dropdown')?.classList.remove('open');
});

async function logout() {
  await API.post('/api/logout', {});
  currentUser = null;
  showToast('Signed out','info');
  setTimeout(() => location.href = 'index.html', 700);
}

window.addEventListener('scroll', () => {
  document.getElementById('navbar')?.classList.toggle('scrolled', scrollY > 16);
});

function toggleMobileMenu() {
  const links = document.querySelector('.nav-links');
  if (!links) return;
  const open = links.style.display === 'flex';
  Object.assign(links.style, {
    display: open ? '' : 'flex',
    flexDirection: 'column',
    position: 'absolute',
    top: '64px', left: '0', right: '0',
    background: '#fff',
    borderBottom: '1px solid #e2e8f0',
    padding: '12px 24px',
    zIndex: '99'
  });
}

function togglePasswordVisibility(inputId, btn) {
  const el = document.getElementById(inputId);
  if (!el) return;
  el.type = el.type === 'password' ? 'text' : 'password';
  btn.textContent = el.type === 'password' ? '👁' : '🙈';
}

document.addEventListener('DOMContentLoaded', initAuth);
