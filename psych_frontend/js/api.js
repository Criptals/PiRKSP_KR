/* ─────────────────────────────────────────
   api.js  —  обёртка над fetch + авторизация
   ───────────────────────────────────────── */

const API_BASE = 'http://localhost:8000/api/v1';

// ─── хранение токена ───
const Auth = {
  getToken:       ()    => localStorage.getItem('token'),
  setToken:       (t)   => localStorage.setItem('token', t),
  removeToken:    ()    => localStorage.removeItem('token'),
  getUser:        ()    => { const u = localStorage.getItem('user'); return u ? JSON.parse(u) : null; },
  setUser:        (u)   => localStorage.setItem('user', JSON.stringify(u)),
  removeUser:     ()    => localStorage.removeItem('user'),
  isLoggedIn:     ()    => !!localStorage.getItem('token'),
  isPsychologist: ()    => Auth.getUser()?.role === 'psychologist',

  logout() {
    this.removeToken();
    this.removeUser();
    window.location.href = '/pages/login.html';
  },
};

// ─── базовый fetch ───
async function apiFetch(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth) {
    const token = Auth.getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(API_BASE + path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401) { Auth.logout(); return; }
  if (res.status === 204) return null;

  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Ошибка ${res.status}`);
  return data;
}

const api = {
  // auth
  register:         (b)      => apiFetch('/auth/register',   { method: 'POST', body: b, auth: false }),
  login:            (b)      => apiFetch('/auth/login',       { method: 'POST', body: b, auth: false }),

  // users
  getMe:            ()       => apiFetch('/users/me'),
  updateMe:         (b)      => apiFetch('/users/me',         { method: 'PATCH', body: b }),
  deleteMe:         ()       => apiFetch('/users/me',         { method: 'DELETE' }),

  // psychologists
  getPsychologists: ()       => apiFetch('/psychologists/'),
  getPsychologist:  (id)     => apiFetch(`/psychologists/${id}`),
  updateMyProfile:  (b)      => apiFetch('/psychologists/me', { method: 'PATCH', body: b }),

  // schedule
  getMySlots:       ()       => apiFetch('/schedule/'),
  getSlotsFor:      (id)     => apiFetch(`/schedule/${id}`),
  createSlot:       (b)      => apiFetch('/schedule/',        { method: 'POST', body: b }),
  deleteSlot:       (id)     => apiFetch(`/schedule/${id}`,   { method: 'DELETE' }),

  // appointments
  getAppointments:  ()       => apiFetch('/appointments/'),
  bookAppointment:  (b)      => apiFetch('/appointments/',    { method: 'POST', body: b }),
  updateStatus:     (id, b)  => apiFetch(`/appointments/${id}/status`, { method: 'PATCH', body: b }),
  cancelAppointment:(id)     => apiFetch(`/appointments/${id}`, { method: 'DELETE' }),

  // sessions
  getSession:       (apId)   => apiFetch(`/sessions/${apId}`),
  startSession:     (apId)   => apiFetch(`/sessions/${apId}/start`, { method: 'POST' }),
  endSession:       (apId)   => apiFetch(`/sessions/${apId}/end`,   { method: 'POST' }),
};

// ─── toast-уведомления ───
const Toast = (() => {
  let container;
  function init() {
    container = document.querySelector('.toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
  }
  function show(message, type = 'info', duration = 3500) {
    if (!container) init();
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    el.textContent = message;
    container.appendChild(el);
    setTimeout(() => {
      el.style.cssText = 'opacity:0;transition:opacity .3s';
      setTimeout(() => el.remove(), 300);
    }, duration);
  }
  return {
    success: (m) => show(m, 'success'),
    error:   (m) => show(m, 'error'),
    info:    (m) => show(m, 'info'),
  };
})();

// ─── защита страниц ───
function requireAuth() {
  if (!Auth.isLoggedIn()) { window.location.href = '/pages/login.html'; }
}
function requirePsychologist() {
  requireAuth();
  if (!Auth.isPsychologist()) window.location.href = '/pages/dashboard.html';
}
function requireUser() {
  requireAuth();
  if (Auth.isPsychologist()) window.location.href = '/pages/psych-dashboard.html';
}

// ─── хелперы ───
function formatDate(d) {
  return new Date(d).toLocaleString('ru-RU', {
    day:'2-digit', month:'long', year:'numeric', hour:'2-digit', minute:'2-digit',
  });
}
function formatDateShort(d) {
  return new Date(d).toLocaleString('ru-RU', {
    day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit',
  });
}
const STATUS_LABEL = { pending:'Ожидает', confirmed:'Подтверждена', cancelled:'Отменена', completed:'Завершена' };
function badgeHtml(s) { return `<span class="badge badge-${s}">${STATUS_LABEL[s] ?? s}</span>`; }

// ─── навбар ───
function initNavbar() {
  const user  = Auth.getUser();
  const links = document.getElementById('nav-links');
  if (!links) return;

  if (!user) {
    links.innerHTML = `
      <a href="/pages/login.html">Войти</a>
      <a href="/pages/register.html" class="btn btn-sm btn-primary">Регистрация</a>`;
    return;
  }

  links.innerHTML = user.role === 'psychologist' ? `
    <a href="/pages/psych-dashboard.html">Обзор</a>
    <a href="/pages/schedule.html">Расписание</a>
    <a href="/pages/appointments-psych.html">Записи</a>
    <a href="/pages/profile.html">Профиль</a>
    <button onclick="Auth.logout()">Выйти</button>` : `
    <a href="/pages/dashboard.html">Обзор</a>
    <a href="/pages/psychologists.html">Психологи</a>
    <a href="/pages/appointments.html">Мои записи</a>
    <a href="/pages/profile.html">Профиль</a>
    <button onclick="Auth.logout()">Выйти</button>`;

  links.querySelectorAll('a').forEach(a => {
    if (a.href === window.location.href) a.classList.add('active');
  });
}
