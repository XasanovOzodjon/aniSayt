const API = {
  BASE_URL: '/uz/api',

  endpoints: {
    animeList:    () => `${API.BASE_URL}/anime/`,
    animeDetail:  (id) => `${API.BASE_URL}/anime/${id}/`,
    seasons:      (animeId) => `${API.BASE_URL}/seasons/`,
    episodes:     (seasonId) => `${API.BASE_URL}/episodes/?season=${seasonId}`,
    videoDetail:  (episodeId) => `${API.BASE_URL}/episodes/${episodeId}/`,
    genres:       () => `${API.BASE_URL}/genres/`,
    search:       (q, kind) => {
      const params = new URLSearchParams({ search: q });
      if (kind) params.set('kind', kind);
      return `${API.BASE_URL}/anime/?${params}`;
    },
    searchUsers:  (q) => `${API.BASE_URL}/search/users/?q=${encodeURIComponent(q)}`,
    trending:     () => `${API.BASE_URL}/anime/?ordering=-id`,
    newReleases:  () => `${API.BASE_URL}/anime/?ordering=-id`,
    byGenre:      (genreId) => `${API.BASE_URL}/anime/?genres=${genreId}`,
    me:           () => `${API.BASE_URL}/auth/me/`,
    mePhoto:      () => `${API.BASE_URL}/auth/me/photo/`,
    meBanner:     () => `${API.BASE_URL}/auth/me/banner/`,
    telegramLogin:(purpose) => `${API.BASE_URL}/auth/telegram-login/${purpose ? `?purpose=${encodeURIComponent(purpose)}` : ''}`,
    telegramUnlink:() => `${API.BASE_URL}/auth/telegram-unlink/`,
    notices:      (unread) => `${API.BASE_URL}/auth/notices/${unread ? '?unread=1' : ''}`,
    noticeRead:   (id) => `${API.BASE_URL}/auth/notices/${id}/read/`,
    noticesReadAll:() => `${API.BASE_URL}/auth/notices/read-all/`,
    lists:        (status) => `${API.BASE_URL}/auth/lists/${status ? `?status=${encodeURIComponent(status)}` : ''}`,
    partyCreate:  () => `${API.BASE_URL}/party/`,
    partyDetail:  (code) => `${API.BASE_URL}/party/${encodeURIComponent(code)}/`,
    partyPreview: (code) => `${API.BASE_URL}/party/${encodeURIComponent(code)}/preview/`,
    dashStats:    () => `${API.BASE_URL}/dashboard/stats/`,
    dashCatalog:  (q, kind) => {
      const params = new URLSearchParams();
      if (q) params.set('q', q);
      if (kind) params.set('kind', kind);
      const qs = params.toString();
      return `${API.BASE_URL}/dashboard/catalog/${qs ? `?${qs}` : ''}`;
    },
    dashTitle:    (id) => `${API.BASE_URL}/dashboard/catalog/${id}/`,
    dashPoster:   (id) => `${API.BASE_URL}/dashboard/catalog/${id}/poster/`,
    dashSeasons:  (id) => `${API.BASE_URL}/dashboard/catalog/${id}/seasons/`,
    dashSeason:   (id) => `${API.BASE_URL}/dashboard/seasons/${id}/`,
    dashEpisodes: (id) => `${API.BASE_URL}/dashboard/seasons/${id}/episodes/`,
    dashEpisode:  (id) => `${API.BASE_URL}/dashboard/episodes/${id}/`,
    dashVideos:   (id) => `${API.BASE_URL}/dashboard/episodes/${id}/videos/`,
    dashVideo:    (id) => `${API.BASE_URL}/dashboard/videos/${id}/`,
    dashGenres:   () => `${API.BASE_URL}/dashboard/genres/`,
    dashGenre:    (id) => `${API.BASE_URL}/dashboard/genres/${id}/`,
    dashPeople:   () => `${API.BASE_URL}/dashboard/people/`,
    dashPerson:   (id) => `${API.BASE_URL}/dashboard/people/${id}/`,
    dashUsers:    (q) => `${API.BASE_URL}/dashboard/users/${q ? `?q=${encodeURIComponent(q)}` : ''}`,
    dashUser:     (id) => `${API.BASE_URL}/dashboard/users/${id}/`,
    dashNotices:  () => `${API.BASE_URL}/dashboard/notices/`,
    dashParties:  () => `${API.BASE_URL}/dashboard/parties/`,
    dashParty:    (code) => `${API.BASE_URL}/dashboard/parties/${encodeURIComponent(code)}/`,
    dashPlayerPoster: () => `${API.BASE_URL}/dashboard/player-poster/`,
    comments:     (id) => `${API.BASE_URL}/auth/episodes/${id}/comments/`,
    comment:      (id) => `${API.BASE_URL}/auth/comments/${id}/`,
    commentLike:  (id) => `${API.BASE_URL}/auth/comments/${id}/like/`,
    episodeLike:  (id) => `${API.BASE_URL}/auth/episodes/${id}/like/`,
    listStatus:   (id) => `${API.BASE_URL}/auth/lists/${id}/`,
    progress:     (id) => `${API.BASE_URL}/auth/progress/${id}/`,
    publicProfile:(username) => `${API.BASE_URL}/auth/u/${encodeURIComponent(username)}/`,
    publicLists:  (username, status) => `${API.BASE_URL}/auth/u/${encodeURIComponent(username)}/lists/${status ? `?status=${encodeURIComponent(status)}` : ''}`,
    reportProfile:(username) => `${API.BASE_URL}/auth/u/${encodeURIComponent(username)}/report/`,
    banAppeal:    () => `${API.BASE_URL}/auth/ban/appeal/`,
    dashReports:  () => `${API.BASE_URL}/dashboard/reports/`,
    dashReport:   (id) => `${API.BASE_URL}/dashboard/reports/${id}/`,
    dashAppeals:  () => `${API.BASE_URL}/dashboard/appeals/`,
    dashAppeal:   (id) => `${API.BASE_URL}/dashboard/appeals/${id}/`,
  },

  async _headers(json = true) {
    const headers = json ? { 'Content-Type': 'application/json' } : {};
    let token = localStorage.getItem('animee_access');
    if (typeof Auth !== 'undefined' && Auth.ensureAccess) {
      token = (await Auth.ensureAccess()) || token;
    }
    if (token) headers.Authorization = `Bearer ${token}`;
    return headers;
  },

  _fail(res, data) {
    if (res.status === 403 && data && data.code === 'banned') {
      const cur = (typeof Auth !== 'undefined' && Auth.user()) || {};
      if (typeof Auth !== 'undefined' && Auth.setSession) {
        Auth.setSession(null, { ...cur, banned: data });
      }
      const here = (location.pathname || '').replace(/\/+$/, '');
      if (here !== '/banned') {
        location.href = (window.ANIMEE_URLS || {}).banned || '/banned/';
      }
    }
    const msg = data.detail || data.message || (data.non_field_errors && data.non_field_errors[0]) || `HTTP ${res.status}`;
    const err = new Error(typeof msg === 'string' ? msg : JSON.stringify(data));
    err.payload = data;
    err.status = res.status;
    throw err;
  },

  async get(url) {
    const headers = await this._headers();
    const res = await fetch(url, { headers });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) this._fail(res, data);
    return data;
  },

  async post(url, body) {
    const headers = await this._headers();
    const res = await fetch(url, { method: 'POST', headers, body: JSON.stringify(body) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) this._fail(res, data);
    return data;
  },

  async patch(url, body) {
    return this._send('PATCH', url, body);
  },

  async put(url, body) {
    return this._send('PUT', url, body);
  },

  async delete(url) {
    const headers = await this._headers();
    const res = await fetch(url, { method: 'DELETE', headers });
    if (res.status === 204) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) this._fail(res, data);
    return data;
  },

  async _send(method, url, body) {
    const headers = await this._headers();
    const res = await fetch(url, { method, headers, body: JSON.stringify(body) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) this._fail(res, data);
    return data;
  },

  async upload(url, formData) {
    const send = async (force) => {
      if (force && typeof Auth !== 'undefined') await Auth.ensureAccess(true);
      const headers = await this._headers(false);
      return fetch(url, { method: 'POST', headers, body: formData });
    };
    let res = await send(false);
    if (res.status === 401) res = await send(true);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = data.detail || data.message || `HTTP ${res.status}`;
      const err = new Error(typeof msg === 'string' ? msg : JSON.stringify(data));
      err.payload = data;
      err.status = res.status;
      throw err;
    }
    return data;
  },

  async uploadWithProgress(url, formData, onProgress) {
    const send = async (force) => {
      if (force && typeof Auth !== 'undefined') await Auth.ensureAccess(true);
      const headers = await this._headers(false);
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', url);
        Object.keys(headers).forEach((key) => xhr.setRequestHeader(key, headers[key]));
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable && onProgress) {
            onProgress(Math.round((event.loaded / event.total) * 100));
          }
        };
        xhr.onload = () => {
          let payload = {};
          try { payload = JSON.parse(xhr.responseText || '{}'); } catch { payload = {}; }
          resolve({ ok: xhr.status >= 200 && xhr.status < 300, status: xhr.status, data: payload });
        };
        xhr.onerror = () => reject(new Error('Tarmoq xatosi'));
        xhr.send(formData);
      });
    };
    let res = await send(false);
    if (res.status === 401) res = await send(true);
    if (!res.ok) this._fail({ status: res.status }, res.data || {});
    return res.data;
  },

  // Paginated list
  async getAnimeList(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.get(`${this.BASE_URL}/anime/${query ? '?' + query : ''}`);
  },
};

// ============================================
//  ROUTER — simple hash-based SPA router
// ============================================
const Router = {
  routes: {},

  on(path, handler) {
    this.routes[path] = handler;
  },

  navigate(path) {
    window.location.hash = path;
  },

  init() {
    window.addEventListener('hashchange', () => this._resolve());
    this._resolve();
  },

  _resolve() {
    const hash = window.location.hash.slice(1) || '/';
    // Match dynamic routes like /anime/123
    for (const [pattern, handler] of Object.entries(this.routes)) {
      const regex = new RegExp('^' + pattern.replace(/:\w+/g, '([^/]+)') + '$');
      const match = hash.match(regex);
      if (match) {
        const paramNames = [...pattern.matchAll(/:(\w+)/g)].map(m => m[1]);
        const params = {};
        paramNames.forEach((name, i) => params[name] = match[i + 1]);
        handler(params);
        return;
      }
    }
    // 404
    document.getElementById('app').innerHTML = `
      <div class="not-found">
        <h1>404</h1><p>Sahifa topilmadi</p>
        <a href="#/" class="btn-primary">Bosh sahifaga qaytish</a>
      </div>`;
  }
};

// ============================================
//  UTILS
// ============================================
const Utils = {
  // Format episode duration  
  formatDuration(seconds) {
    if (!seconds) return '—';
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  },

  formatMinutes(minutes) {
    if (!minutes) return '—';
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return h ? `${h}s ${m}d` : `${m} daq`;
  },

  sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  },

  noticeTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleString('uz-UZ', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  },

  // Star rating display
  stars(rating) {
    const full = Math.round(rating / 2);
    return '★'.repeat(full) + '☆'.repeat(5 - full);
  },

  // Skeleton loader HTML
  skeleton(count = 6) {
    return Array(count).fill(`
      <div class="skeleton-card">
        <div class="skeleton-img skeleton-anim"></div>
        <div class="skeleton-title skeleton-anim"></div>
        <div class="skeleton-sub skeleton-anim"></div>
      </div>`).join('');
  },

  // Toast notification
  toast(msg, type = 'info') {
    const t = document.createElement('div');
    t.className = `toast toast-${type}`;
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.classList.add('show'), 10);
    setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 300); }, 3000);
  },

  // Debounce
  debounce(fn, delay = 400) {
    let timer;
    return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay); };
  },

  // Image fallback
  imgFallback(img) {
    img.onerror = null;
    img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjQwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMWEwYTNjIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJzYW5zLXNlcmlmIiBmb250LXNpemU9IjE0IiBmaWxsPSIjN2M1Y2ZmIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+ANIMEEPC90ZXh0Pjwvc3ZnPg==';
  },

  year(anime) {
    const years = (anime.seasons || []).map(s => s.release_date).filter(Boolean);
    return years.length ? Math.max(...years) : (anime.year || '—');
  },

  episodes(anime) {
    if (anime.episode_count) return anime.episode_count;
    return (anime.seasons || []).reduce((n, s) => n + (s.episodes || []).length, 0) || '?';
  },

  jp(title) {
    return ({
      'Neon Qish': 'ネオンの冬',
      'Oy Ostidagi Qilich': '月下の剣',
      'Sakura Server': '桜サーバー',
      'Qora Poyezd': '黒い列車',
      'Yulduz Ovchisi': '星の狩人',
      'Ikki Qalb': '二つの心',
      'Oxirgi Stansiya': '終着駅',
    })[title] || 'アニメ';
  },

  escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (ch) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[ch]));
  },

  safeUrl(value) {
    const raw = String(value || '').trim();
    if (!raw) return '';
    try {
      const url = new URL(raw, window.location.origin);
      if (url.protocol !== 'https:' && url.protocol !== 'http:') return '';
      return url.href;
    } catch {
      return '';
    }
  },

  kindLabel(kind) {
    return ({ anime: 'Anime', drama: 'Drama', film: 'Kino', serial: 'Serial' })[kind] || 'Anime';
  },

  kindPrefix(kind) {
    return ({ anime: 'anime', drama: 'drama', film: 'kino', serial: 'serial' })[kind] || 'anime';
  },

  titleHref(item) {
    if (item?.path) return item.path;
    if (item?.slug) return `/${this.kindPrefix(item.kind)}/${item.slug}/`;
    if (item?.id) return `/detail/?id=${item.id}`;
    return (window.ANIMEE_URLS || {}).catalog || '/catalog/';
  },

  watchHref(ep, party) {
    let path = ep?.watch_path || '';
    if (!path && ep?.anime_slug) {
      const prefix = this.kindPrefix(ep.anime_kind);
      const season = ep.season_number || (ep.season && ep.season.number);
      path = (season && Number(season) !== 1)
        ? `/${prefix}/${ep.anime_slug}/s${season}/episode${ep.number}/`
        : `/${prefix}/${ep.anime_slug}/episode${ep.number}/`;
    }
    if (!path && (ep?.id || ep?.episode_id)) {
      path = `${(window.ANIMEE_URLS || {}).player || '/player/'}?episode=${ep.id || ep.episode_id}`;
    }
    if (party && path) {
      path += path.includes('?') ? '&' : '?';
      path += `party=${encodeURIComponent(party)}`;
    }
    return path || ((window.ANIMEE_URLS || {}).player || '/player/');
  },

  kindBadge(item) {
    const kind = item?.kind || 'anime';
    return `<span class="kind-badge kind-${kind}">${this.kindLabel(kind)}</span>`;
  },

  epLabel(item) {
    if ((item?.kind || 'anime') === 'film') return 'Kino';
    const n = this.episodes(item);
    return n === '?' ? '—' : `${n} qism`;
  }
};

const Auth = {
  user() {
    try { return JSON.parse(localStorage.getItem('animee_user') || 'null'); }
    catch { return null; }
  },
  rememberNext(url) {
    const path = String(url || '');
    if (path.startsWith('/') && !path.startsWith('//')) {
      sessionStorage.setItem('animee_next', path);
    }
  },
  consumeNext() {
    const next = sessionStorage.getItem('animee_next') || '';
    sessionStorage.removeItem('animee_next');
    if (next.startsWith('/') && !next.startsWith('//')) return next;
    return '';
  },
  goAfterLogin(fallback) {
    location.href = this.consumeNext() || fallback || (window.ANIMEE_URLS?.profile || '/profile/');
  },
  setSession(tokens, user) {
    if (tokens?.access) localStorage.setItem('animee_access', tokens.access);
    if (tokens?.refresh) localStorage.setItem('animee_refresh', tokens.refresh);
    if (user) localStorage.setItem('animee_user', JSON.stringify(user));
  },
  clear() {
    localStorage.removeItem('animee_access');
    localStorage.removeItem('animee_refresh');
    localStorage.removeItem('animee_user');
  },
  captureOAuth() {
    const q = new URLSearchParams(window.location.search);
    if (q.get('google_auth') !== 'success' || !q.get('access')) return;
    const email = q.get('email') || '';
    const username = q.get('username') || (email.split('@')[0] || 'user');
    this.setSession(
      { access: q.get('access'), refresh: q.get('refresh') },
      { username, photo: q.get('photo') || '', email, via: 'google' }
    );
    ['access', 'refresh', 'google_auth', 'username', 'photo', 'email'].forEach((key) => q.delete(key));
    const next = q.toString();
    history.replaceState(null, '', window.location.pathname + (next ? '?' + next : ''));
    Utils.toast('Google orqali kirdingiz', 'success');
    this.syncFromMe();
    const after = this.consumeNext();
    if (after) location.href = after;
  },
  async syncFromMe() {
    const token = localStorage.getItem('animee_access');
    if (!token) return this.user();
    try {
      const data = await API.get(API.endpoints.me());
      const cur = this.user() || {};
      this.setSession(null, { ...cur, ...data });
      this.bootNav();
      return this.user();
    } catch {
      return this.user();
    }
  },
  jwtExpired(token, skewSec = 90) {
    if (!token) return true;
    try {
      const part = token.split('.')[1] || '';
      const padded = part.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(part.length / 4) * 4, '=');
      const payload = JSON.parse(atob(padded));
      return !payload.exp || payload.exp * 1000 < Date.now() + skewSec * 1000;
    } catch {
      return true;
    }
  },
  async ensureAccess(force = false) {
    const access = localStorage.getItem('animee_access');
    const refresh = localStorage.getItem('animee_refresh');
    if (!refresh) return access;
    if (!force && access && !this.jwtExpired(access)) return access;
    if (this._refreshing) return this._refreshing;
    this._refreshing = (async () => {
      try {
        const res = await fetch('/uz/api/auth/token/refresh/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.access) throw new Error('refresh');
        this.setSession({ access: data.access, refresh: data.refresh || refresh });
        return data.access;
      } catch {
        return localStorage.getItem('animee_access');
      } finally {
        this._refreshing = null;
      }
    })();
    return this._refreshing;
  },
  bootNav() {
    const user = this.user();
    const cta = document.getElementById('navAuthCta');
    const bot = document.getElementById('botAuth');
    const urls = window.ANIMEE_URLS || {};
    const here = (location.pathname || '').replace(/\/+$/, '');
    if (user?.banned && here !== '/banned') {
      location.href = urls.banned || '/banned/';
      return;
    }
    this.mountAccount(user, urls, cta);
    if (bot) {
      if (user) {
        bot.href = urls.profile || '/profile/';
        bot.innerHTML = '<span class="nav-ico" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="8" r="3.5"/><path d="M5.5 19a6.5 6.5 0 0113 0"/></svg></span>Profil';
      } else {
        bot.href = urls.auth || '/auth/';
        bot.innerHTML = '<span class="nav-ico" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 018 0v4"/></svg></span>Kirish';
      }
    }
    Notices.syncBell(user);
    const dash = document.getElementById('navDash');
    if (dash) dash.hidden = !(user?.is_admin || user?.is_moderator || user?.can_dashboard);
  },
  displayName(user) {
    const full = [user?.first_name, user?.last_name].filter(Boolean).join(' ').trim();
    return full || user?.username || 'Profil';
  },
  mountAccount(user, urls, cta) {
    const wrap = document.getElementById('navAccount');
    const btn = document.getElementById('navAvatarBtn');
    const menu = document.getElementById('navMenu');
    const img = document.getElementById('navAvatarImg');
    const letter = document.getElementById('navAvatarLetter');
    if (cta) cta.hidden = Boolean(user);
    if (!wrap || !btn || !menu) return;
    if (!user) {
      wrap.hidden = true;
      menu.hidden = true;
      btn.setAttribute('aria-expanded', 'false');
      return;
    }
    wrap.hidden = false;
    const photo = Utils.safeUrl(user.photo);
    const uname = user.username || '';
    const name = this.displayName(user);
    const initial = (uname || name || '?').slice(0, 1).toUpperCase();
    if (img) {
      if (photo) {
        img.src = photo;
        img.hidden = false;
        if (letter) letter.hidden = true;
      } else {
        img.removeAttribute('src');
        img.hidden = true;
        if (letter) {
          letter.hidden = false;
          letter.textContent = initial;
        }
      }
    }
    const ico = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
    const face = photo
      ? `<img src="${photo}" alt="">`
      : Utils.escapeHtml(initial);
    const dash = (user.is_admin || user.is_moderator || user.can_dashboard)
      ? `<a href="${urls.dashboard || '/dashboard/'}" role="menuitem">${ico('<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>')}Boshqaruv</a>`
      : '';
    const here = location.pathname.replace(/\/+$/, '') || '/';
    const on = (path) => {
      const p = path.replace(/\/+$/, '') || '/';
      return here === p ? 'active' : '';
    };
    menu.innerHTML = `
      <div class="nav-menu-head">
        <div class="nav-menu-face">${face}</div>
        <div>
          <strong>${Utils.escapeHtml(name)}</strong>
          <em>${Utils.escapeHtml(uname)}</em>
        </div>
      </div>
      <a href="${urls.profile || '/profile/'}" class="${on('/profile/')}" role="menuitem">${ico('<circle cx="12" cy="8" r="3.5"/><path d="M5.5 19a6.5 6.5 0 0113 0"/>')}Profilim</a>
      <a href="${urls.lists || '/lists/'}" class="${on('/lists/')}" role="menuitem">${ico('<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>')}Ro‘yxatlar</a>
      <a href="${urls.settings || '/settings/'}" class="${on('/settings/')}" role="menuitem">${ico('<circle cx="12" cy="12" r="3"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>')}Sozlamalar</a>
      <a href="${urls.notices || '/notices/'}" class="${on('/notices/')}" role="menuitem">${ico('<path d="M6 9a6 6 0 0112 0c0 7 2 7 2 9H4c0-2 2-2 2-9"/><path d="M10 21a2 2 0 004 0"/>')}Bildirishnomalar</a>
      ${dash}
      <button type="button" class="nav-menu-out" id="navLogoutBtn" role="menuitem">${ico('<path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/>')}Chiqish</button>`;
    document.getElementById('navLogoutBtn')?.addEventListener('click', () => {
      this.clear();
      location.href = urls.index || '/';
    });
    if (!btn.dataset.bound) {
      btn.dataset.bound = '1';
      const close = () => {
        menu.hidden = true;
        btn.setAttribute('aria-expanded', 'false');
      };
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const open = menu.hidden;
        menu.hidden = !open;
        btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
      document.addEventListener('click', (e) => {
        if (!wrap.contains(e.target)) close();
      });
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') close();
      });
    }
  }
};

const Notices = {
  kindLabel(kind) {
    return ({ new_season: 'Yangi sezon', new_episode: 'Yangi qism', news: 'Yangilik' })[kind] || 'Yangilik';
  },
  paintBadge(count) {
    const el = document.getElementById('navBellCount');
    const bell = document.getElementById('navBell');
    if (!el || !bell) return;
    const n = Number(count) || 0;
    bell.classList.toggle('has-unread', n > 0);
    if (n <= 0) {
      el.hidden = true;
      el.textContent = '';
      return;
    }
    el.hidden = false;
    el.textContent = n > 9 ? '9+' : String(n);
  },
  syncBell(user) {
    const bell = document.getElementById('navBell');
    if (!bell) return;
    if (!user) {
      bell.hidden = true;
      this.paintBadge(0);
      return;
    }
    bell.hidden = false;
    this.refreshBadge();
  },
  async refreshBadge() {
    if (!Auth.user()) {
      this.paintBadge(0);
      return;
    }
    try {
      const data = await API.get(`${API.endpoints.notices()}?limit=1`);
      this.paintBadge(data.unread_count);
    } catch {
      this.paintBadge(0);
    }
  },
  async markRead(id) {
    const data = await API.post(API.endpoints.noticeRead(id), {});
    this.paintBadge(data.unread_count);
    return data;
  },
  async markAll() {
    const data = await API.post(API.endpoints.noticesReadAll(), {});
    this.paintBadge(0);
    return data;
  }
};

const Lists = {
  labels: {
    watching: 'Ko‘ryapman',
    completed: 'Ko‘rib bo‘ldim',
    planned: 'Ko‘rmoqchiman',
    dropped: 'Qiziq emas',
    favorite: 'Sevimli',
  },
  async mine(status) {
    return API.get(API.endpoints.lists(status));
  },
  async of(username, status) {
    return API.get(API.endpoints.publicLists(username, status));
  },
  async status(animeId) {
    if (!Auth.user()) return { status: null, score: null };
    try { return await API.get(API.endpoints.listStatus(animeId)); }
    catch { return { status: null, score: null }; }
  },
  async set(anime, status, score) {
    if (!Auth.user()) {
      Utils.toast('Ro‘yxat uchun kiring', 'info');
      const urls = window.ANIMEE_URLS || {};
      setTimeout(() => { window.location.href = urls.auth || '/auth/'; }, 400);
      return null;
    }
    const row = await API.put(API.endpoints.lists(), {
      anime: anime.id,
      status,
      score: score || null,
    });
    Utils.toast(`${this.labels[status] || 'Ro‘yxat'} · saqlandi`, 'success');
    return row;
  },
  async remove(animeId) {
    if (!Auth.user()) return false;
    await API.delete(`${API.BASE_URL}/auth/lists/?anime=${encodeURIComponent(animeId)}`);
    Utils.toast('Ro‘yxatdan olindi', 'info');
    return true;
  }
};

const Library = {
  _key: 'animee_library',
  all() {
    try { return JSON.parse(localStorage.getItem(this._key) || '[]'); }
    catch { return []; }
  },
  has(id) { return this.all().some(x => String(x.id) === String(id)); },
  toggle(anime) {
    if (!Auth.user()) {
      Utils.toast('Saqlash uchun kiring', 'info');
      const urls = window.ANIMEE_URLS || {};
      setTimeout(() => { window.location.href = urls.auth || '/auth/'; }, 500);
      return false;
    }
    const list = this.all();
    const i = list.findIndex(x => String(x.id) === String(anime.id));
    if (i >= 0) {
      list.splice(i, 1);
      localStorage.setItem(this._key, JSON.stringify(list));
      Utils.toast('Ro‘yxatdan olib tashlandi', 'info');
      return false;
    }
    list.unshift({
      id: anime.id,
      title: anime.title,
      poster: anime.poster,
      year: Utils.year(anime),
    });
    localStorage.setItem(this._key, JSON.stringify(list.slice(0, 40)));
    Utils.toast('Ro‘yxatga qo‘shildi', 'success');
    return true;
  }
};

const ContinueWatch = {
  _key: 'animee_continue',
  remember(item) {
    const list = this.all().filter(x => String(x.anime_id) !== String(item.anime_id));
    list.unshift({ ...item, at: Date.now() });
    localStorage.setItem(this._key, JSON.stringify(list.slice(0, 12)));
  },
  all() {
    try { return JSON.parse(localStorage.getItem(this._key) || '[]'); }
    catch { return []; }
  }
};

const ProgressStore = {
  _key: 'animee_progress',
  all() {
    try { return JSON.parse(localStorage.getItem(this._key) || '{}'); }
    catch { return {}; }
  },
  get(episodeId) {
    const row = this.all()[String(episodeId)];
    const pos = Number(row?.position);
    return Number.isFinite(pos) && pos > 0 ? { position: pos, duration: Number(row.duration) || 0 } : null;
  },
  set(episodeId, position, duration) {
    const all = this.all();
    all[String(episodeId)] = { position: Number(position) || 0, duration: Number(duration) || 0, at: Date.now() };
    const keys = Object.keys(all);
    if (keys.length > 40) {
      keys.sort((a, b) => (all[a].at || 0) - (all[b].at || 0))
        .slice(0, keys.length - 40)
        .forEach((k) => delete all[k]);
    }
    localStorage.setItem(this._key, JSON.stringify(all));
  },
  clear(episodeId) {
    const all = this.all();
    delete all[String(episodeId)];
    localStorage.setItem(this._key, JSON.stringify(all));
  },
};

const SearchHistory = {
  _key: 'animee_search_history',
  all() {
    try { return JSON.parse(localStorage.getItem(this._key) || '[]'); }
    catch { return []; }
  },
  save(list) {
    localStorage.setItem(this._key, JSON.stringify(list.slice(0, 12)));
  },
  remember(row) {
    if (!row?.key) return;
    const list = this.all().filter((item) => item.key !== row.key);
    list.unshift({ ...row, at: Date.now() });
    this.save(list);
  },
  forget(key) {
    this.save(this.all().filter((item) => item.key !== key));
  },
  get(key) {
    return this.all().find((item) => item.key === key) || null;
  },
};

const SearchGate = {
  init() {
    const portal = document.getElementById('searchPortal');
    if (!portal) return;
    const input = document.getElementById('searchPortalInput');
    const results = document.getElementById('searchPortalResults');
    const clock = '<svg class="search-history-clock" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="8"/><path d="M12 8v4l2.5 1.5"/></svg>';
    let scope = 'all';
    let seq = 0;

    const setScope = (next) => {
      scope = next || 'all';
      document.querySelectorAll('#searchScopes [data-search-scope]').forEach((btn) => {
        btn.setAttribute('aria-pressed', btn.dataset.searchScope === scope ? 'true' : 'false');
      });
    };

    const rememberQuery = (q) => {
      const text = (q || '').trim();
      if (text.length < 2) return;
      SearchHistory.remember({
        key: `q:${scope}:${text.toLowerCase()}`,
        type: 'query',
        q: text,
        scope,
        title: text,
      });
    };

    const hitFromEl = (el) => ({
      key: el.dataset.searchKey,
      type: el.dataset.searchType,
      title: el.dataset.searchTitle,
      href: el.getAttribute('href'),
      poster: el.dataset.searchPoster || '',
      q: el.dataset.searchQ || '',
      scope: el.dataset.searchScope || scope,
    });

    const paintHistory = () => {
      const rows = SearchHistory.all();
      if (!rows.length) {
        results.innerHTML = '';
        return;
      }
      results.innerHTML = rows.map((row) => {
        const title = Utils.escapeHtml(row.title || row.q || '');
        const href = row.href && row.type !== 'query' ? Utils.escapeHtml(row.href) : '#';
        const thumb = row.poster
          ? `<img class="${row.type === 'user' ? 'search-hit-avatar' : ''}" src="${Utils.escapeHtml(row.poster)}" alt="" onerror="Utils.imgFallback(this)"/>`
          : clock;
        return `<a class="search-history-row${row.type === 'user' ? ' is-user' : ''}" href="${href}" data-history-key="${Utils.escapeHtml(row.key)}">
          ${thumb}
          <span class="search-history-text">${title}</span>
          <button type="button" class="search-history-forget" data-history-forget="${Utils.escapeHtml(row.key)}" aria-label="O‘chirish">✕</button>
        </a>`;
      }).join('');
    };

    const paintTitles = (list, q) => list.map((a) => {
      const href = Utils.titleHref(a);
      const title = a.title || '—';
      const poster = a.poster || '';
      return `<a class="search-hit" href="${Utils.escapeHtml(href)}" data-search-key="t:${Utils.escapeHtml(href)}" data-search-type="title" data-search-title="${Utils.escapeHtml(title)}" data-search-poster="${Utils.escapeHtml(poster)}" data-search-q="${Utils.escapeHtml(q)}" data-search-scope="${scope}">
        <img src="${Utils.escapeHtml(poster)}" alt="" onerror="Utils.imgFallback(this)"/>
        <div>
          <strong>${Utils.escapeHtml(title)}</strong>
          <span>${Utils.escapeHtml(Utils.kindLabel(a.kind))} · ${Utils.year(a)}</span>
        </div>
      </a>`;
    }).join('');

    const paintUsers = (list, q) => list.map((u) => {
      const href = `/u/${encodeURIComponent(u.username)}/`;
      const name = u.first_name || u.username;
      const photo = u.photo || '';
      return `<a class="search-hit is-user" href="${Utils.escapeHtml(href)}" data-search-key="u:${Utils.escapeHtml(u.username)}" data-search-type="user" data-search-title="${Utils.escapeHtml(name)}" data-search-poster="${Utils.escapeHtml(photo)}" data-search-q="${Utils.escapeHtml(q)}" data-search-scope="users">
        <img class="search-hit-avatar" src="${Utils.escapeHtml(photo)}" alt="" onerror="Utils.imgFallback(this)"/>
        <div>
          <strong>${Utils.escapeHtml(name)}</strong>
          <span>@${Utils.escapeHtml(u.username)}</span>
        </div>
      </a>`;
    }).join('');

    const run = Utils.debounce(async () => {
      const q = input.value.trim();
      const stamp = ++seq;
      if (q.length < 2) {
        paintHistory();
        return;
      }
      try {
        let html = '';
        if (scope === 'users') {
          const data = await API.get(API.endpoints.searchUsers(q));
          if (stamp !== seq) return;
          const list = (data.results || []).slice(0, 8);
          html = list.length ? paintUsers(list, q) : '';
        } else {
          const kind = scope === 'all' ? '' : scope;
          const data = await API.get(API.endpoints.search(q, kind));
          if (stamp !== seq) return;
          const list = (data.results || data || []).slice(0, 8);
          html = list.length ? paintTitles(list, q) : '';
        }
        results.innerHTML = html || '<p class="search-portal-empty">Hech narsa topilmadi</p>';
      } catch {
        if (stamp !== seq) return;
        results.innerHTML = '<p class="search-portal-empty">Qidiruv ishlamadi</p>';
      }
    }, 280);

    const open = () => {
      portal.hidden = false;
      document.body.classList.add('portal-open');
      if (input.value.trim().length < 2) paintHistory();
      setTimeout(() => input.focus(), 40);
    };
    const close = () => {
      portal.hidden = true;
      document.body.classList.remove('portal-open');
    };

    document.querySelectorAll('[data-open-search]').forEach((el) => {
      el.addEventListener('click', (e) => { e.preventDefault(); open(); });
    });
    document.querySelectorAll('#searchScopes [data-search-scope]').forEach((chip) => {
      chip.addEventListener('click', () => {
        setScope(chip.dataset.searchScope);
        run();
        input.focus();
      });
    });
    document.querySelectorAll('[data-close-search]').forEach((el) => el.addEventListener('click', close));
    portal.addEventListener('click', (e) => { if (e.target === portal) close(); });
    results.addEventListener('click', (e) => {
      const forget = e.target.closest('[data-history-forget]');
      if (forget) {
        e.preventDefault();
        e.stopPropagation();
        SearchHistory.forget(forget.dataset.historyForget);
        if (input.value.trim().length < 2) paintHistory();
        return;
      }
      const replay = e.target.closest('[data-history-key]');
      if (replay) {
        const row = SearchHistory.get(replay.dataset.historyKey);
        if (!row) return;
        if (row.href && row.type !== 'query') return;
        e.preventDefault();
        setScope(row.scope || 'all');
        input.value = row.q || row.title || '';
        run();
        return;
      }
      const hit = e.target.closest('.search-hit');
      if (hit) SearchHistory.remember(hitFromEl(hit));
    });
    input.addEventListener('input', run);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') close();
      if (e.key === 'Enter') {
        const first = results.querySelector('.search-hit');
        rememberQuery(input.value);
        if (first) {
          SearchHistory.remember(hitFromEl(first));
          window.location.href = first.href;
        }
      }
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !portal.hidden) close();
      if (e.key === '/' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
        e.preventDefault();
        open();
      }
    });
  }
};

Auth.captureOAuth();
Auth.bootNav();
SearchGate.init();
window.Auth = Auth;
