/* navbar.js — вставляет навбар в страницу */

function renderNavbar() {
  const nav = document.createElement('nav');
  nav.className = 'navbar';
  nav.innerHTML = `
    <a class="navbar-brand" href="/">
      <span>психо</span>лог онлайн
    </a>
    <div class="navbar-links" id="nav-links"></div>
  `;
  document.body.insertBefore(nav, document.body.firstChild);
  initNavbar();
}

document.addEventListener('DOMContentLoaded', renderNavbar);
