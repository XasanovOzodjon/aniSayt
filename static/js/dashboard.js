const root = document.getElementById('dashRoot');
const urls = ANIMEE_URLS;
let genresCache = [];
let meFlags = { is_admin: false, is_moderator: false };
let videoPollTimer = 0;

const KINDS = [
  { id: 'anime', hash: 'anime', label: 'Anime', plural: 'Animelar' },
  { id: 'film', hash: 'kino', label: 'Kino', plural: 'Kinolar' },
  { id: 'drama', hash: 'drama', label: 'Drama', plural: 'Dramalar' },
  { id: 'serial', hash: 'serial', label: 'Serial', plural: 'Seriallar' },
];

function path() {
  const raw = (location.hash.replace(/^#\/?/, '') || 'home').split('?')[0];
  return raw.split('/').filter(Boolean);
}
function hashQuery() {
  return new URLSearchParams((location.hash.split('?')[1] || ''));
}
function go(hash) {
  location.hash = hash;
}
function esc(v) { return Utils.escapeHtml(v); }
function kindMeta(id) {
  return KINDS.find((k) => k.id === id || k.hash === id) || KINDS[0];
}
function kindLabel(k) {
  return kindMeta(k).label;
}
function canDash(user) {
  return Boolean(user?.is_admin || user?.is_moderator || user?.can_dashboard);
}
function isAdmin() {
  return Boolean(meFlags.is_admin);
}

function gate(kind) {
  const copy = kind === 'auth'
    ? ['Boshqaruv', 'Katalogni boshqarish uchun kiring.']
    : ['Ruxsat yo‘q', 'Bu panel faqat Admin va Moderator uchun.'];
  root.innerHTML = `
    <div class="profile-gate">
      <p class="dash-kicker">DASHBOARD</p>
      <h1 class="detail-title" style="font-size:2rem;margin:.2rem 0 .6rem">${copy[0]}</h1>
      <p>${copy[1]}</p>
      <div class="profile-gate-actions">
        <a class="btn-primary" href="${urls.auth}?next=${encodeURIComponent('/dashboard/')}">${kind === 'auth' ? 'Kirish' : 'Bosh sahifa'}</a>
      </div>
    </div>`;
}

function shell(active, body) {
  const kindLinks = KINDS.map((k) => {
    const on = active === k.hash || active === k.id;
    return `<a href="#/${k.hash}" class="${on ? 'active' : ''}">${k.plural}</a>`;
  }).join('');
  const adminLinks = isAdmin() ? `
      <div class="dash-nav-label">Tizim</div>
      <a href="#/poster" class="${active === 'poster' ? 'active' : ''}">Sayt posteri</a>
      <a href="#/users" class="${active === 'users' || active === 'user' ? 'active' : ''}">Userlar</a>
      <a href="#/reports" class="${active === 'reports' ? 'active' : ''}">Shikoyatlar</a>
      <a href="#/appeals" class="${active === 'appeals' ? 'active' : ''}">So‘rovlar</a>
      <a href="#/news" class="${active === 'news' ? 'active' : ''}">Yangilik</a>
      <a href="#/rooms" class="${active === 'rooms' ? 'active' : ''}">Birgalikda</a>
    ` : '';
  return `
    <div class="dash">
      <nav class="dash-side">
        <div class="dash-side-brand">
          <div class="dash-side-mark">A</div>
          <div><strong>Boshqaruv</strong><span>${isAdmin() ? 'Admin' : 'Moderator'}</span></div>
        </div>
        <a href="#/home" class="${active === 'home' ? 'active' : ''}">Umumiy</a>
        <div class="dash-nav-label">Katalog</div>
        ${kindLinks}
        <a href="#/genres" class="${active === 'genres' ? 'active' : ''}">Kategoriyalar</a>
        ${adminLinks}
      </nav>
      <div class="dash-main">${body}</div>
    </div>`;
}

function pageHead(kicker, title, lead, actions) {
  return `
    <div class="dash-head">
      <div>
        <p class="dash-kicker">${kicker}</p>
        <h1>${title}</h1>
        ${lead ? `<p>${lead}</p>` : ''}
      </div>
      ${actions ? `<div class="dash-head-actions">${actions}</div>` : ''}
    </div>`;
}

function err(ex) {
  Utils.toast(ex.payload?.message || ex.message || 'Xato', 'error');
}

function isTransient(ex) {
  const s = Number(ex && ex.status);
  const msg = String((ex && ex.message) || '');
  return s === 0 || s === 502 || s === 503 || s === 504
    || /Failed to fetch|NetworkError|HTTP 502|HTTP 503|HTTP 504/i.test(msg);
}

async function render() {
  const user = Auth.user();
  if (!user) { gate('auth'); return; }
  if (!canDash(user)) {
    try {
      const me = await Auth.syncFromMe();
      if (!canDash(me)) { gate('staff'); return; }
    } catch {
      gate('staff');
      return;
    }
  }
  meFlags = {
    is_admin: Boolean(Auth.user()?.is_admin),
    is_moderator: Boolean(Auth.user()?.is_moderator),
  };
  const parts = path();
  const page = parts[0] || 'home';
  try {
    const kindPage = KINDS.find((k) => k.hash === page);
    if (kindPage && parts[1] === 'new') await renderNew(kindPage.id);
    else if (kindPage) await renderTitles(kindPage.id);
    else if (page === 'title' && parts[2] === 'season' && parts[3] === 'new') await renderNewSeason(parts[1]);
    else if (page === 'title') await renderTitle(parts[1]);
    else if (page === 'season') await renderSeason(parts[1]);
    else if (page === 'episode') await renderEpisode(parts[1]);
    else if (page === 'genres') await renderGenres();
    else if (page === 'users') {
      if (!isAdmin()) { go('#/home'); return; }
      if (parts[1]) await renderUser(parts[1]);
      else await renderUsers();
    } else if (page === 'reports') {
      if (!isAdmin()) { go('#/home'); return; }
      await renderReports();
    } else if (page === 'appeals') {
      if (!isAdmin()) { go('#/home'); return; }
      await renderAppeals();
    } else if (page === 'news') {
      if (!isAdmin()) { go('#/home'); return; }
      await renderNews();
    } else if (page === 'rooms') {
      if (!isAdmin()) { go('#/home'); return; }
      await renderRooms();
    } else if (page === 'poster') {
      if (!isAdmin()) { go('#/home'); return; }
      await renderPlayerPoster();
    }     else await renderHome();
  } catch (ex) {
    if (isTransient(ex)) {
      if (!root.querySelector('.dash-head') && !root.querySelector('.dash-panel')) {
        root.innerHTML = shell(page, '<p class="settings-hint">Server javob bermoqda. Bir zumda qayta uriniladi…</p>');
      }
      clearTimeout(videoPollTimer);
      videoPollTimer = setTimeout(() => render(), 2000);
      return;
    }
    err(ex);
    root.innerHTML = shell(page, `<p class="error-state">${esc(ex.message)}</p>`);
  }
}

async function renderHome() {
  const s = await API.get(API.endpoints.dashStats());
  meFlags.is_admin = Boolean(s.is_admin);
  const cards = [
    [s.anime, 'Anime'],
    [s.film, 'Kino'],
    [s.drama, 'Drama'],
    [s.serial, 'Serial'],
    [s.episodes, 'Qism'],
    [s.videos, 'Master'],
    [s.genres, 'Janr'],
  ];
  if (s.is_admin) {
    cards.push([s.users, 'User'], [s.moderators, 'Moderator'], [s.parties_open, 'Ochiq xona']);
  }
  const cardHtml = cards.map(([n, l]) => `<div class="dash-stat"><b>${n ?? 0}</b><span>${l}</span></div>`).join('');
  const recent = (s.recent_anime || []).map((a) => `
    <a class="dash-cat-card" href="#/title/${a.id}">
      <img src="${esc(a.poster)}" alt="" onerror="Utils.imgFallback(this)"/>
      <div><strong>${esc(a.title)}</strong><em>${kindLabel(a.kind)} · ${a.episodes_count || 0} qism</em></div>
    </a>`).join('') || '<div class="dash-empty">Katalog hali bo‘sh</div>';
  const quick = KINDS.map((k) => `<a href="#/${k.hash}/new">${k.label} qo‘shish<span>Yangi ${k.label.toLowerCase()} yaratish</span></a>`).join('');
  root.innerHTML = shell('home', `
    ${pageHead('DASHBOARD', s.is_admin ? 'Butun tizim shu yerda' : 'Katalog shu yerda',
      s.is_admin ? 'Anime, kino, drama, serial, User va Moderatorlar.' : 'Anime, kino, drama va seriallarni qo‘shish va videoni yuklash.')}
    <div class="dash-stats">${cardHtml}</div>
    <div class="dash-quick">${quick}<a href="#/genres">Kategoriya<span>Janr qo‘shish</span></a></div>
    <h3 class="settings-h" style="margin:0 0 .8rem">So‘nggi nomlar</h3>
    <div class="dash-catalog">${recent}</div>
  `);
}

async function renderTitles(kind) {
  const meta = kindMeta(kind);
  const q = new URLSearchParams(location.hash.split('?')[1] || '').get('q') || '';
  const data = await API.get(API.endpoints.dashCatalog(q, meta.id));
  const isFilm = meta.id === 'film';
  const cards = (data.results || []).map((a) => `
    <a class="dash-cat-card" href="#/title/${a.id}">
      <img src="${esc(a.poster)}" alt="" onerror="Utils.imgFallback(this)"/>
      <div>
        <strong>${esc(a.title)}</strong>
        <em>${isFilm
          ? (a.next_title ? `Keyingi: ${esc(a.next_title.title)}` : 'Sequel yo‘q')
          : `${a.seasons_count || 0} sezon · ${a.episodes_count || 0} qism`}</em>
      </div>
    </a>`).join('');
  root.innerHTML = shell(meta.hash, `
    ${pageHead(meta.label.toUpperCase(), meta.plural, `${(data.results || []).length} ta nom katalogda.`,
      `<a class="btn-primary" href="#/${meta.hash}/new">Yangi ${meta.label.toLowerCase()}</a>`)}
    <div class="dash-toolbar">
      <input id="catQ" placeholder="Qidirish…" value="${esc(q)}"/>
    </div>
    ${cards ? `<div class="dash-catalog">${cards}</div>` : `<div class="dash-empty">Hali ${meta.label.toLowerCase()} yo‘q</div>`}
  `);
  document.getElementById('catQ')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') location.hash = `#/${meta.hash}?q=${encodeURIComponent(e.target.value.trim())}`;
  });
}

async function loadGenres() {
  const data = await API.get(API.endpoints.dashGenres());
  genresCache = data.results || [];
  return genresCache;
}

function genreChips(selected) {
  const set = new Set((selected || []).map((g) => String(g.id || g)));
  if (!genresCache.length) {
    return `<p class="settings-hint">Avval <a href="#/genres">kategoriya</a> qo‘shing.</p>`;
  }
  return `<div class="dash-chips">${genresCache.map((g) => `
    <label class="${set.has(String(g.id)) ? 'dash-chip-on' : ''}">
      <input type="checkbox" name="genre" value="${g.id}" ${set.has(String(g.id)) ? 'checked' : ''}/> ${esc(g.name)}
    </label>
  `).join('')}</div>`;
}

function selectedGenreIds() {
  return [...document.querySelectorAll('input[name="genre"]:checked')].map((el) => el.value).join(',');
}

function ageSelect(current) {
  const cur = current || '16+';
  return `<label>Yosh
    <select name="age_rating">${['0+','6+','12+','16+','18+'].map((a) =>
      `<option value="${a}" ${a === cur ? 'selected' : ''}>${a}</option>`
    ).join('')}</select>
  </label>`;
}

async function renderNew(kind) {
  const meta = kindMeta(kind);
  await loadGenres();
  root.innerHTML = shell(meta.hash, `
    ${pageHead(meta.label.toUpperCase(), `Yangi ${meta.label.toLowerCase()}`, meta.id === 'film'
      ? 'Kino sezonsiz. Saqlagach video va keyingi kino shu nomning sahifasida.'
      : 'Avval nom saqlanadi. Sezon va qism keyin alohida sahifalarda.')}
    <form class="dash-form dash-panel" id="newForm">
      <div class="dash-form-grid">
        <label class="dash-drop" id="posterDrop">Poster
          <input type="file" name="poster" accept="image/*" required id="newPoster" hidden/>
          <span id="posterHint">Rasmni tanlang yoki tashlang</span>
        </label>
        <div style="display:grid;gap:.8rem">
          <label>Nom <input name="title" required placeholder="Masalan: Neon Qish"/></label>
          <label>Tavsif <textarea name="description" required placeholder="Qisqa syujet…"></textarea></label>
          ${ageSelect('16+')}
          <div><p class="settings-hint" style="margin-bottom:.4rem">Kategoriyalar</p>${genreChips([])}</div>
        </div>
      </div>
      <button class="btn-primary" type="submit">Saqlash</button>
    </form>
  `);
  document.getElementById('newPoster')?.addEventListener('change', (e) => {
    const file = e.target.files[0];
    const drop = document.getElementById('posterDrop');
    if (!file || !drop) return;
    const url = URL.createObjectURL(file);
    drop.innerHTML = `<img src="${url}" alt="Poster"/>`;
    drop.appendChild(e.target);
  });
  document.getElementById('newForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    fd.set('genres', selectedGenreIds());
    fd.set('kind', meta.id);
    try {
      const data = await API.upload(API.endpoints.dashCatalog(), fd);
      Utils.toast('Saqlandi', 'success');
      go(`#/title/${data.id}`);
    } catch (ex) { err(ex); }
  });
}

function videoReady(v) {
  if (v.ingest_error || v.status === 'error') {
    return `Xato: ${v.ingest_error || 'yuklanmadi'}`;
  }
  if (v.hls_path) return v.hls_path.includes('.m3u8') ? 'Tayyor · HLS' : 'Tayyor';
  const pct = Number(v.progress) || 0;
  if (v.status === 'processing' || v.has_file) return `${pct}% · HLS qilinmoqda`;
  if (v.status === 'queued' || v.source_url) return `${pct}% · S3 ga yozilmoqda`;
  return 'Video yo‘q';
}

function videosBusy(videos) {
  return (videos || []).some((v) => v.status === 'queued' || v.status === 'processing');
}

function watchVideos(videos) {
  clearTimeout(videoPollTimer);
  if (videosBusy(videos)) {
    videoPollTimer = setTimeout(() => render(), 1500);
  }
}

function meterHTML(pct, label) {
  const n = Math.max(0, Math.min(100, Number(pct) || 0));
  return `<div class="dash-meter" role="progressbar" aria-valuenow="${n}" aria-valuemin="0" aria-valuemax="100">
    <div class="dash-meter-fill" style="width:${n}%"></div>
    <span>${n}%${label ? ` · ${esc(label)}` : ''}</span>
  </div>`;
}

function setFormMeter(form, pct, label) {
  const wrap = form.querySelector('[data-meter]');
  if (!wrap) return;
  wrap.hidden = false;
  wrap.innerHTML = meterHTML(pct, label);
}

function videoFormHTML(episodeId) {
  return `
    <form class="dash-form" data-video="${episodeId}" style="max-width:100%;margin-top:.4rem">
      <div class="dash-inline">
        <input name="language" value="uz" placeholder="til"/>
        <input name="translated_by" placeholder="tarjima (ixtiyoriy)" style="min-width:10rem"/>
      </div>
      <label>Video fayl <input type="file" name="video" accept="video/*"/></label>
      <label>Yoki internetdagi video havolasi <input name="source_url" placeholder="https://…/video.mp4"/></label>
      <div data-meter hidden></div>
      <p class="settings-hint">Fayl yoki havola to‘g‘ridan-to‘g‘ri S3 ga yoziladi. Pastdagi chiziq to‘lguncha foiz ko‘rinadi, keyin HLS fonda tayyorlanadi.</p>
      <button class="btn-primary" type="submit">Videoni yuklash</button>
    </form>`;
}

function bindVideoForms() {
  root.querySelectorAll('form[data-video]').forEach((form) => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(form);
      const file = fd.get('video');
      const url = String(fd.get('source_url') || '').trim();
      if ((!file || !file.size) && !url) {
        Utils.toast('Video fayl yoki havola kerak', 'error');
        return;
      }
      const body = new FormData();
      body.set('language', fd.get('language') || 'uz');
      body.set('translated_by', fd.get('translated_by') || '');
      if (file && file.size) body.set('video', file);
      if (url) body.set('source_url', url);
      const btn = form.querySelector('button[type="submit"]');
      try {
        if (btn) {
          btn.disabled = true;
          btn.textContent = 'Yuklanmoqda…';
        }
        setFormMeter(form, 1, file && file.size ? 'S3 ga yozilmoqda' : 'Qabul qilindi');
        if (file && file.size) {
          await API.uploadWithProgress(
            API.endpoints.dashVideos(form.dataset.video),
            body,
            (pct) => {
              setFormMeter(form, pct, 'S3 ga yozilmoqda');
              if (btn) btn.textContent = `${pct}%`;
            },
          );
        } else {
          await API.upload(API.endpoints.dashVideos(form.dataset.video), body);
        }
        setFormMeter(form, 100, 'Qabul qilindi');
        Utils.toast('Video S3 ga ketdi — holat pastda yangilanadi', 'success');
        render();
      } catch (ex) {
        if (btn) {
          btn.disabled = false;
          btn.textContent = 'Videoni yuklash';
        }
        err(ex);
      }
    });
  });
  root.querySelectorAll('[data-del-video]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      try { await API.delete(API.endpoints.dashVideo(btn.dataset.delVideo)); render(); }
      catch (ex) { err(ex); }
    });
  });
}

function videosHTML(videos) {
  watchVideos(videos);
  return (videos || []).map((v) => {
    const busy = v.status === 'queued' || v.status === 'processing';
    return `
    <div class="dash-video-row">
      <div class="settings-hint" style="margin:.2rem 0">
        <strong>${esc(v.language || 'uz')}</strong> · ${esc(videoReady(v))}
        <button type="button" class="btn-secondary" data-del-video="${v.id}">O‘chirish</button>
      </div>
      ${busy || v.hls_path ? meterHTML(v.hls_path ? 100 : v.progress, v.hls_path ? 'Tayyor' : '') : ''}
    </div>`;
  }).join('') || '<p class="settings-hint">Hali video yo‘q. Havola yoki fayl qo‘ying.</p>';
}

async function renderTitle(id) {
  const [title] = await Promise.all([API.get(API.endpoints.dashTitle(id)), loadGenres()]);
  const meta = kindMeta(title.kind);
  const isFilm = title.kind === 'film';
  const filmOpts = isFilm ? await API.get(API.endpoints.dashCatalog('', 'film')) : { results: [] };
  const sequel = (filmOpts.results || []).filter((a) => String(a.id) !== String(title.id));
  const seasons = (title.seasons || []).map((s) => `
    <a class="dash-cat-card" href="#/season/${s.id}">
      <div style="padding:1.1rem 1rem 1.15rem">
        <strong>${s.number}-sezon</strong>
        <em>${s.release_date} · ${s.episodes_count || 0} qism</em>
      </div>
    </a>`).join('');
  const filmBlock = isFilm ? `
    <h2 class="settings-h" style="margin-top:1.5rem">Video va tarjimalar</h2>
    <div class="dash-panel">
      ${videosHTML(title.film_episode?.videos)}
      ${title.film_episode ? videoFormHTML(title.film_episode.id) : '<p class="settings-hint">Video joyi yo‘q</p>'}
    </div>
    <h2 class="settings-h" style="margin-top:1.5rem">Keyingi kino</h2>
    <form class="dash-form dash-panel dash-form-narrow" id="sequelForm">
      <label>Shu film tugagach ochiladi
        <select name="next_title_id">
          <option value="">— yo‘q —</option>
          ${sequel.map((a) => `<option value="${a.id}" ${title.next_title && String(title.next_title.id)===String(a.id)?'selected':''}>${esc(a.title)}</option>`).join('')}
        </select>
      </label>
      <p class="settings-hint">Har bir kino alohida. 1 tugagach User 2 ni ko‘radi.</p>
      <button class="btn-primary" type="submit">Bog‘lash</button>
    </form>` : `
    <h2 class="settings-h" style="margin-top:1.5rem">Sezonlar</h2>
    ${(title.seasons || []).length ? `<div class="dash-catalog" style="grid-template-columns:repeat(auto-fill,minmax(14rem,1fr))">${seasons}</div>` : '<div class="dash-empty">Hali sezon yo‘q — pastdan yarating</div>'}
    <div class="dash-toolbar" style="margin-top:1rem">
      <a class="btn-primary" href="#/title/${id}/season/new">Sezon yaratish</a>
    </div>`;
  root.innerHTML = shell(meta.hash, `
    <p class="dash-crumb"><a href="#/${meta.hash}">${esc(meta.plural)}</a> / sozlamalar</p>
    ${pageHead(meta.label.toUpperCase(), esc(title.title), (title.genres||[]).map((g)=>g.name).join(' · ') || 'Kategoriya tanlanmagan',
      `<a class="btn-secondary" href="${title.path || Utils.titleHref(title)}">Saytda ochish</a>`)}
    <form class="dash-form dash-panel" id="editForm">
      <div class="dash-form-grid">
        <label class="dash-drop">Poster
          <img src="${esc(title.poster || '')}" alt="" onerror="Utils.imgFallback(this)"/>
          <input id="posterFile" type="file" accept="image/*" hidden/>
        </label>
        <div style="display:grid;gap:.8rem">
          <label>Nom <input name="title" value="${esc(title.title)}" required/></label>
          <label>Tavsif <textarea name="description">${esc(title.description)}</textarea></label>
          ${ageSelect(title.age_rating)}
          <div><p class="settings-hint" style="margin-bottom:.4rem">Kategoriyalar</p>${genreChips(title.genres)}</div>
          <div class="dash-inline">
            <button class="btn-primary" type="submit">Yangilash</button>
            <button type="button" class="btn-secondary dash-danger" id="delTitle">O‘chirish</button>
          </div>
        </div>
      </div>
    </form>
    ${filmBlock}
  `);
  document.getElementById('editForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await API.patch(API.endpoints.dashTitle(id), {
        title: fd.get('title'),
        description: fd.get('description'),
        age_rating: fd.get('age_rating'),
        genres: selectedGenreIds().split(',').filter(Boolean).map(Number),
      });
      Utils.toast('Yangilandi', 'success');
      render();
    } catch (ex) { err(ex); }
  });
  document.getElementById('posterFile')?.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('poster', file);
    try {
      await API.upload(API.endpoints.dashPoster(id), fd);
      Utils.toast('Poster yangilandi', 'success');
      render();
    } catch (ex) { err(ex); }
  });
  document.getElementById('delTitle').addEventListener('click', async () => {
    if (!confirm('Shu nom katalogdan o‘chsinmi?')) return;
    try {
      await API.delete(API.endpoints.dashTitle(id));
      Utils.toast('O‘chirildi', 'info');
      go(`#/${meta.hash}`);
    } catch (ex) { err(ex); }
  });
  document.getElementById('sequelForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await API.patch(API.endpoints.dashTitle(id), {
        next_title_id: new FormData(e.target).get('next_title_id') || '',
      });
      Utils.toast('Bog‘landi', 'success');
      render();
    } catch (ex) { err(ex); }
  });
  bindVideoForms();
}

async function renderNewSeason(titleId) {
  const title = await API.get(API.endpoints.dashTitle(titleId));
  const meta = kindMeta(title.kind);
  if (title.kind === 'film') { go(`#/title/${titleId}`); return; }
  root.innerHTML = shell(meta.hash, `
    <p class="dash-crumb"><a href="#/title/${titleId}">${esc(title.title)}</a> / yangi sezon</p>
    ${pageHead('SEZON', 'Sezon yaratish', 'Yaratilgach shu sezon sahifasida qism qo‘shasiz.')}
    <form class="dash-form dash-panel dash-form-narrow" id="seasonForm">
      <label>Raqam <input name="number" type="number" min="1" value="${(title.seasons_count || 0) + 1}" required/></label>
      <label>Yil <input name="release_date" type="number" value="${new Date().getFullYear()}"/></label>
      <button class="btn-primary" type="submit">Yaratish</button>
    </form>
  `);
  document.getElementById('seasonForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      const season = await API.post(API.endpoints.dashSeasons(titleId), {
        number: fd.get('number'),
        release_date: fd.get('release_date'),
      });
      Utils.toast('Sezon ochildi', 'success');
      go(`#/season/${season.id}`);
    } catch (ex) { err(ex); }
  });
}

async function renderSeason(id) {
  const season = await API.get(API.endpoints.dashSeason(id));
  const meta = kindMeta(season.kind);
  const rows = (season.episodes || []).map((ep) => `
    <a class="dash-cat-card" href="#/episode/${ep.id}">
      <div style="padding:1.05rem 1rem">
        <strong>${ep.number}. ${esc(ep.title)}</strong>
        <em>${(ep.videos || []).length} tarjima</em>
      </div>
    </a>`).join('');
  root.innerHTML = shell(meta.hash, `
    <p class="dash-crumb"><a href="#/title/${season.anime_id}">${esc(season.anime_title)}</a> / ${season.number}-sezon</p>
    ${pageHead(`SEZON ${season.number}`, `${esc(season.anime_title)}`, 'Qism yarating, keyin ochib video yuklang.')}
    <form class="dash-addbar" id="epForm">
      <input name="number" type="number" min="1" placeholder="№" required/>
      <input name="title" placeholder="Qism nomi" style="flex:1.4"/>
      <button class="btn-primary" type="submit">Qism yaratish</button>
    </form>
    ${rows ? `<div class="dash-catalog" style="grid-template-columns:repeat(auto-fill,minmax(14rem,1fr))">${rows}</div>` : '<div class="dash-empty">Hali qism yo‘q</div>'}
    <div class="dash-toolbar" style="margin-top:1.1rem">
      <button type="button" class="btn-secondary dash-danger" id="delSeason">Sezonni o‘chirish</button>
    </div>
  `);
  document.getElementById('epForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await API.post(API.endpoints.dashEpisodes(id), { number: fd.get('number'), title: fd.get('title') });
      Utils.toast('Qism qo‘shildi', 'success');
      render();
    } catch (ex) { err(ex); }
  });
  document.getElementById('delSeason').addEventListener('click', async () => {
    if (!confirm('Sezon o‘chsinmi?')) return;
    try {
      await API.delete(API.endpoints.dashSeason(id));
      Utils.toast('O‘chirildi', 'info');
      go(`#/title/${season.anime_id}`);
    } catch (ex) { err(ex); }
  });
}

async function renderEpisode(id) {
  const ep = await API.get(API.endpoints.dashEpisode(id));
  const meta = kindMeta(ep.kind);
  root.innerHTML = shell(meta.hash, `
    <p class="dash-crumb"><a href="#/title/${ep.anime_id}">${esc(ep.anime_title)}</a> / <a href="#/season/${ep.season_id}">${ep.season_number}-sezon</a> / qism</p>
    ${pageHead('QISM', `${ep.number}. ${esc(ep.title)}`, 'Har bir til alohida Master.')}
    <form class="dash-form dash-panel dash-form-narrow" id="epEdit">
      <label>Raqam <input name="number" type="number" min="1" value="${ep.number}" required/></label>
      <label>Nom <input name="title" value="${esc(ep.title)}" required/></label>
      <div class="dash-inline">
        <button class="btn-primary" type="submit">Yangilash</button>
        <button type="button" class="btn-secondary dash-danger" id="delEp">Qismni o‘chirish</button>
      </div>
    </form>
    <h2 class="settings-h" style="margin-top:1.4rem">Master / tarjimalar</h2>
    <div class="dash-panel">
      ${videosHTML(ep.videos)}
      ${videoFormHTML(ep.id)}
    </div>
  `);
  document.getElementById('epEdit').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await API.patch(API.endpoints.dashEpisode(id), { number: fd.get('number'), title: fd.get('title') });
      Utils.toast('Yangilandi', 'success');
      render();
    } catch (ex) { err(ex); }
  });
  document.getElementById('delEp').addEventListener('click', async () => {
    if (!confirm('Qism o‘chsinmi?')) return;
    try {
      await API.delete(API.endpoints.dashEpisode(id));
      Utils.toast('O‘chirildi', 'info');
      go(`#/season/${ep.season_id}`);
    } catch (ex) { err(ex); }
  });
  bindVideoForms();
}

async function renderGenres() {
  const data = await API.get(API.endpoints.dashGenres());
  const list = data.results || [];
  const cards = list.map((g) => `
    <div class="dash-genre">
      <div><strong>${esc(g.name)}</strong><code>${esc(g.slug)}</code></div>
      <button type="button" class="dash-genre-del" data-del="${g.id}">O‘chirish</button>
    </div>`).join('');
  root.innerHTML = shell('genres', `
    ${pageHead('KATEGORIYALAR', 'Janrlar', 'Katalogdagi nomlarni janr bo‘yicha ajratish. Yangi kategoriya shu yerda.')}
    <form class="dash-addbar" id="genreForm">
      <input name="name" placeholder="Masalan: Fantastika" required/>
      <button class="btn-primary" type="submit">Qo‘shish</button>
    </form>
    ${cards ? `<div class="dash-genres">${cards}</div>` : '<div class="dash-empty">Hali kategoriya yo‘q — yuqoridan qo‘shing</div>'}
  `);
  document.getElementById('genreForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await API.post(API.endpoints.dashGenres(), { name: new FormData(e.target).get('name') });
      e.target.reset();
      render();
    } catch (ex) { err(ex); }
  });
  root.querySelectorAll('[data-del]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      try { await API.delete(API.endpoints.dashGenre(btn.dataset.del)); render(); }
      catch (ex) { err(ex); }
    });
  });
}

function roleLabel(u) {
  return u.role || (u.is_admin ? 'Admin' : (u.is_moderator ? 'Moderator' : 'User'));
}

const REPORT_KINDS = { photo: 'Profil rasmi', banner: 'Banner', nick: 'Nick', bio: 'Tavsif' };

function userName(u) {
  return (u.first_name || '').trim() || u.username || 'User';
}

function avatarFallback(u) {
  const letter = (userName(u) || '?').charAt(0).toUpperCase();
  return `<span class="dash-user-letter">${esc(letter)}</span>`;
}

function avatarHtml(u, cls) {
  if (u.photo) {
    return `<img class="${cls}" src="${esc(u.photo)}" alt="" onerror="this.remove()"/>`;
  }
  return avatarFallback(u);
}

function isSnapUrl(s) {
  return /^(https?:\/\/|\/media\/|\/static\/)/.test(s || '');
}

function statusPills(u) {
  const bits = [`<span class="dash-pill">${esc(roleLabel(u))}</span>`];
  if (u.banned) bits.push('<span class="dash-pill is-ban">Ban</span>');
  if (!u.is_active) bits.push('<span class="dash-pill">O‘chiq</span>');
  if (u.open_reports) bits.push(`<span class="dash-pill is-warn">${u.open_reports} shikoyat</span>`);
  return bits.join('');
}

async function patchUser(id, body) {
  return API.patch(API.endpoints.dashUser(id), body);
}

async function renderUsers() {
  const q = hashQuery().get('q') || '';
  const data = await API.get(API.endpoints.dashUsers(q));
  const cards = (data.results || []).map((u) => `
    <a class="dash-user-card" href="#/users/${u.id}">
      <span class="dash-user-card-ava">${avatarHtml(u, 'dash-user-ava')}</span>
      <span class="dash-user-card-copy">
        <strong>${esc(userName(u))}</strong>
        <em>@${esc(u.username)}</em>
      </span>
      <span class="dash-user-card-meta">${statusPills(u)}</span>
    </a>`).join('');
  root.innerHTML = shell('users', `
    ${pageHead('USERLAR', 'Hisoblar', 'Userni ochib profilini ko‘ring, keyin chora qo‘llang.')}
    <form class="dash-addbar" id="userSearch">
      <input name="q" value="${esc(q)}" placeholder="Username, email…" autocomplete="off"/>
      <button class="btn-secondary" type="submit">Qidirish</button>
    </form>
    <div class="dash-user-list">${cards || '<p class="dash-empty">User yo‘q</p>'}</div>
  `);
  document.getElementById('userSearch')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const next = (new FormData(e.target).get('q') || '').trim();
    location.hash = next ? `#/users?q=${encodeURIComponent(next)}` : '#/users';
  });
}

function reportCard(r, { highlight, targetPage } = {}) {
  const snap = r.snapshot || '';
  const media = isSnapUrl(snap)
    ? `<img class="dash-report-snap" src="${esc(snap)}" alt="" onerror="this.remove()"/>`
    : (snap ? `<p class="dash-report-quote">${esc(snap)}</p>` : '');
  const href = targetPage
    ? `#/users/${r.target_id}?r=${r.id}`
    : `#/users/${r.reporter_id}`;
  return `
    <article class="dash-report-card${highlight ? ' is-on' : ''}${r.resolved ? ' is-done' : ''}" data-report="${r.id}">
      <div class="dash-report-top">
        <strong>${esc(REPORT_KINDS[r.kind] || r.kind)}</strong>
        <span>${esc(r.reason_label || r.reason || '')}</span>
        ${r.resolved ? '<em>Yopilgan</em>' : ''}
      </div>
      ${media}
      ${r.note ? `<p class="settings-hint">${esc(r.note)}</p>` : ''}
      <p class="settings-hint">Kimdan: <a href="#/users/${r.reporter_id}">@${esc(r.reporter)}</a>
        · Kim: <a href="#/users/${r.target_id}">@${esc(r.target)}</a></p>
      ${targetPage ? `<a class="btn-secondary" href="${href}">Profilni ochish</a>` : ''}
    </article>`;
}

async function renderUser(id) {
  const u = await API.get(API.endpoints.dashUser(id));
  const focus = hashQuery().get('r') || '';
  const L = u.locks || {};
  const ban = u.ban || {};
  const reports = u.reports || [];
  const filed = u.filed || [];
  const open = reports.filter((r) => !r.resolved);
  const joined = (u.date_joined || '').slice(0, 10);
  const publicHref = `/u/${encodeURIComponent(u.username)}/`;
  root.innerHTML = shell('users', `
    <p class="dash-crumb"><a href="#/users">Userlar</a> / @${esc(u.username)}</p>
    ${pageHead('PROFIL', userName(u), 'Avval ko‘rib chiqing, keyin chora. Ban — hisobni yopadi; so‘rovga ruxsatni o‘zingiz belgilaysiz.')}
    <div class="dash-mod-hero" style="${u.banner ? `background-image:url('${esc(u.banner)}')` : ''}">
      <div class="dash-mod-hero-in">
        <span class="dash-user-card-ava is-lg">${avatarHtml(u, 'dash-user-ava')}</span>
        <div>
          <h2>@${esc(u.username)}</h2>
          <p>${esc(u.first_name || '—')}</p>
          <div class="dash-user-card-meta">${statusPills(u)}</div>
        </div>
        <a class="btn-secondary" href="${publicHref}" target="_blank" rel="noreferrer">Ochiq profil</a>
      </div>
    </div>
    <div class="dash-mod-grid">
      <section class="dash-panel">
        <h3>Nima ko‘rinadi</h3>
        <dl class="dash-facts">
          <div><dt>Email</dt><dd>${esc(u.email || '—')}</dd></div>
          <div><dt>Tavsif</dt><dd>${esc(u.bio || '—')}</dd></div>
          <div><dt>Status</dt><dd>${esc(u.status_line || '—')}</dd></div>
          <div><dt>Qo‘shilgan</dt><dd>${esc(joined || '—')}</dd></div>
          <div><dt>Telegram</dt><dd>${esc(u.telegram || '—')}</dd></div>
        </dl>
        ${u.photo ? `<img class="dash-mod-media" src="${esc(u.photo)}" alt="Avatar"/>` : ''}
        ${u.banner ? `<img class="dash-mod-media is-wide" src="${esc(u.banner)}" alt="Banner"/>` : ''}
      </section>
      <section class="dash-panel">
        <h3>Shikoyatlar ${open.length ? `<em>${open.length} ochiq</em>` : ''}</h3>
        ${reports.length ? reports.map((r) => reportCard(r, { highlight: String(r.id) === String(focus) })).join('') : '<p class="settings-hint">Bu userga shikoyat yo‘q.</p>'}
        ${open.length ? `<div class="dash-inline dash-mod-report-acts">
          ${open.map((r) => `
            <button type="button" class="btn-secondary" data-report-act="dismiss" data-id="${r.id}">${esc(REPORT_KINDS[r.kind] || r.kind)}ni yopish</button>
            <button type="button" class="btn-secondary" data-report-act="clear" data-id="${r.id}">${esc(REPORT_KINDS[r.kind] || r.kind)}ni o‘chirish</button>
          `).join('')}
        </div>` : ''}
      </section>
    </div>
    <div class="dash-mod-grid">
      <form class="dash-panel dash-form" id="banForm">
        <h3>Ban</h3>
        <p class="settings-hint">${u.banned ? `Hozir: ${esc(ban.reason || 'Ban')}.` : 'Hisob ochiq. Ban qo‘yilsa, User kirganda sababni ko‘radi.'}</p>
        <label>Sabab <input name="reason" required value="${esc(ban.reason || '')}" placeholder="Nima uchun"/></label>
        <label class="settings-check"><input type="checkbox" name="allow_appeal" ${u.ban_allow_appeal === false ? '' : 'checked'}/> Bandan ozod so‘roviga ruxsat</label>
        <div class="dash-inline">
          <button class="btn-primary" type="submit">${u.banned ? 'Ban ni yangilash' : 'Ban'}</button>
          ${u.banned ? '<button class="btn-secondary" type="button" id="unbanBtn">Ozod qilish</button>' : ''}
        </div>
      </form>
      <form class="dash-panel dash-form" id="lockForm">
        <h3>Cheklovlar</h3>
        <label class="settings-check"><input type="checkbox" name="username" ${L.username ? 'checked' : ''}/> Username o‘zgarmasin</label>
        <label class="settings-check"><input type="checkbox" name="photo" ${L.photo ? 'checked' : ''}/> Avatar o‘zgarmasin</label>
        <label class="settings-check"><input type="checkbox" name="photo_keep" ${L.photo_keep ? 'checked' : ''}/> Avatarni olib tashlab bo‘lmasin</label>
        <label class="settings-check"><input type="checkbox" name="banner" ${L.banner ? 'checked' : ''}/> Banner o‘zgarmasin</label>
        <label class="settings-check"><input type="checkbox" name="banner_keep" ${L.banner_keep ? 'checked' : ''}/> Bannerni olib tashlab bo‘lmasin</label>
        <label class="settings-check"><input type="checkbox" name="bio" ${L.bio ? 'checked' : ''}/> Tavsif o‘zgarmasin</label>
        <label class="settings-check"><input type="checkbox" name="bio_keep" ${L.bio_keep ? 'checked' : ''}/> Tavsifni olib tashlab bo‘lmasin</label>
        <label class="settings-check"><input type="checkbox" name="comments" ${L.comments ? 'checked' : ''}/> Izoh yoza olmasin</label>
        <button class="btn-primary" type="submit">Cheklovni saqlash</button>
      </form>
    </div>
    <div class="dash-mod-grid">
      <form class="dash-panel dash-form" id="setForm">
        <h3>O‘zgartirish</h3>
        <p class="settings-hint">Saqlanganda Userga xabar ketadi.</p>
        <label>Username <input name="username" value="${esc(u.username)}" /></label>
        <label>Ism <input name="first_name" value="${esc(u.first_name || '')}" /></label>
        <label>Tavsif <textarea name="bio" maxlength="280">${esc(u.bio || '')}</textarea></label>
        <button class="btn-primary" type="submit">Saqlash</button>
      </form>
      <section class="dash-panel">
        <h3>Olib tashlash</h3>
        <p class="settings-hint">Userga xabar ketadi.</p>
        <div class="dash-inline">
          <button type="button" class="btn-secondary" data-clear="photo">Avatar</button>
          <button type="button" class="btn-secondary" data-clear="banner">Banner</button>
          <button type="button" class="btn-secondary" data-clear="bio">Tavsif</button>
          <button type="button" class="btn-secondary" data-clear="nick">Nick</button>
          <button type="button" class="btn-secondary" data-clear="comments">Izohlar</button>
        </div>
        <h3 style="margin-top:1.2rem">Rol</h3>
        <div class="dash-inline">
          <button type="button" class="btn-secondary" data-role="admin">Admin</button>
          <button type="button" class="btn-secondary" data-role="moderator">Moderator</button>
          <button type="button" class="btn-secondary" data-role="user">User</button>
          <button type="button" class="btn-secondary" id="activeBtn">${u.is_active ? 'Hisobni to‘xtatish' : 'Hisobni yoqish'}</button>
        </div>
        ${filed.length || u.report_strikes || u.report_muted ? `
          <h3 style="margin-top:1.2rem">Shikoyatchi</h3>
          <p class="settings-hint">${u.report_strikes || 0} ogohlantirish${u.report_muted ? ' · hozir yopiq' : ''}</p>
          ${filed.map((r) => reportCard(r, { targetPage: true })).join('')}
          <div class="dash-inline">
            <button type="button" class="btn-secondary" id="warnRep">Ogohlantirish</button>
            <button type="button" class="btn-secondary" id="muteRep">Shikoyat yuborishni yopish</button>
          </div>
        ` : ''}
      </section>
    </div>
  `);
  document.getElementById('banForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await patchUser(u.id, { ban: { reason: fd.get('reason'), allow_appeal: fd.get('allow_appeal') === 'on' } });
      Utils.toast('Ban qo‘yildi', 'success');
      render();
    } catch (ex) { err(ex); }
  });
  document.getElementById('unbanBtn')?.addEventListener('click', async () => {
    try {
      await patchUser(u.id, { unban: true });
      Utils.toast('Ban olindi', 'success');
      render();
    } catch (ex) { err(ex); }
  });
  document.getElementById('lockForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const locks = {};
    ['username', 'photo', 'photo_keep', 'banner', 'banner_keep', 'bio', 'bio_keep', 'comments'].forEach((key) => {
      locks[key] = fd.get(key) === 'on';
    });
    try {
      await patchUser(u.id, { locks });
      Utils.toast('Cheklov saqlandi', 'success');
      render();
    } catch (ex) { err(ex); }
  });
  document.getElementById('setForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await patchUser(u.id, {
        set: {
          username: (fd.get('username') || '').trim(),
          first_name: fd.get('first_name'),
          bio: fd.get('bio'),
        },
      });
      Utils.toast('O‘zgartirildi, xabar ketdi', 'success');
      render();
    } catch (ex) { err(ex); }
  });
  root.querySelectorAll('[data-clear]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      try {
        await patchUser(u.id, { clear: btn.dataset.clear });
        Utils.toast('O‘chirildi, xabar ketdi', 'success');
        render();
      } catch (ex) { err(ex); }
    });
  });
  root.querySelectorAll('[data-role]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const to = btn.dataset.role;
      const body = to === 'admin'
        ? { is_admin: true, is_moderator: false }
        : to === 'moderator'
          ? { is_admin: false, is_moderator: true }
          : { is_admin: false, is_moderator: false };
      try {
        await patchUser(u.id, body);
        render();
      } catch (ex) { err(ex); }
    });
  });
  document.getElementById('activeBtn')?.addEventListener('click', async () => {
    try {
      await patchUser(u.id, { is_active: !u.is_active });
      render();
    } catch (ex) { err(ex); }
  });
  document.getElementById('warnRep')?.addEventListener('click', async () => {
    try {
      await patchUser(u.id, { warn_reporter: true });
      Utils.toast('Ogohlantirish ketdi', 'success');
      render();
    } catch (ex) { err(ex); }
  });
  document.getElementById('muteRep')?.addEventListener('click', async () => {
    try {
      await patchUser(u.id, { mute_reporter: true });
      Utils.toast('Shikoyat yuborish yopildi', 'success');
      render();
    } catch (ex) { err(ex); }
  });
  root.querySelectorAll('[data-report-act]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      try {
        await API.patch(API.endpoints.dashReport(btn.dataset.id), { action: btn.dataset.reportAct });
        Utils.toast(btn.dataset.reportAct === 'clear' ? 'O‘chirildi' : 'Yopildi', 'success');
        render();
      } catch (ex) { err(ex); }
    });
  });
  if (focus) {
    document.querySelector(`[data-report="${focus}"]`)?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }
}

async function renderReports() {
  const data = await API.get(API.endpoints.dashReports());
  const open = (data.results || []).filter((r) => !r.resolved);
  const closed = (data.results || []).filter((r) => r.resolved);
  const card = (r) => `
    <a class="dash-report-card dash-card-link${r.resolved ? ' is-done' : ''}" href="#/users/${r.target_id}?r=${r.id}">
      <div class="dash-report-top">
        <strong>@${esc(r.target)}</strong>
        <span>${esc(REPORT_KINDS[r.kind] || r.kind)} · ${esc(r.reason_label || r.reason || '')}</span>
      </div>
      ${isSnapUrl(r.snapshot) ? `<img class="dash-report-snap" src="${esc(r.snapshot)}" alt=""/>` : (r.snapshot ? `<p class="dash-report-quote">${esc(r.snapshot)}</p>` : '')}
      ${r.note ? `<p class="settings-hint">${esc(r.note)}</p>` : ''}
      <p class="settings-hint">Kimdan @${esc(r.reporter)} · Profilni ochib tekshiring</p>
    </a>`;
  root.innerHTML = shell('reports', `
    ${pageHead('SHIKOYATLAR', 'Tekshirish', 'Avval userning profilini oching. Chora shu yerda emas, profil sahifasida.')}
    <div class="dash-report-list">${open.map(card).join('') || '<p class="dash-empty">Ochiq shikoyat yo‘q</p>'}</div>
    ${closed.length ? `<h3 class="dash-sub">Yopilgan</h3><div class="dash-report-list">${closed.map(card).join('')}</div>` : ''}
  `);
}

async function renderAppeals() {
  const data = await API.get(API.endpoints.dashAppeals());
  const rows = (data.results || []).map((r) => `
    <tr>
      <td><a href="#/users/${r.user_id}"><strong>@${esc(r.username)}</strong></a><div class="settings-hint">${esc(r.reason || '')}</div></td>
      <td>${esc(r.body)}</td>
      <td>${r.resolved ? (r.accepted ? 'Qabul' : 'Rad') : `
        <button type="button" class="btn-secondary" data-ok="${r.id}">Qabul</button>
        <button type="button" class="btn-secondary" data-no="${r.id}">Rad</button>
      `}</td>
    </tr>`).join('');
  root.innerHTML = shell('appeals', `
    ${pageHead('SO‘ROVLAR', 'Bandan ozod', 'Qabul qilinsa ban olinadi.')}
    <div class="dash-table-wrap">
    <table class="dash-table">
      <thead><tr><th>User</th><th>Matn</th><th></th></tr></thead>
      <tbody>${rows || '<tr><td colspan="3">So‘rov yo‘q</td></tr>'}</tbody>
    </table>
    </div>
  `);
  root.querySelectorAll('[data-ok]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      try {
        await API.patch(API.endpoints.dashAppeal(btn.dataset.ok), { accepted: true });
        render();
      } catch (ex) { err(ex); }
    });
  });
  root.querySelectorAll('[data-no]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      try {
        await API.patch(API.endpoints.dashAppeal(btn.dataset.no), { accepted: false });
        render();
      } catch (ex) { err(ex); }
    });
  });
}

async function renderNews() {
  const titles = await API.get(API.endpoints.dashCatalog());
  const opts = (titles.results || []).map((a) => `<option value="${a.id}">${esc(a.title)}</option>`).join('');
  root.innerHTML = shell('news', `
    ${pageHead('NOTICE', 'Yangilik yuborish', 'Hamma User inboxiga tushadi. Telegram ulanganlarga ham ketadi.')}
    <form class="dash-form dash-panel dash-form-narrow" id="newsForm">
      <label>Sarlavha <input name="title" required/></label>
      <label>Matn <textarea name="body" required></textarea></label>
      <label>Katalog (ixtiyoriy)
        <select name="anime"><option value="">—</option>${opts}</select>
      </label>
      <button class="btn-primary" type="submit">Yuborish</button>
    </form>
  `);
  document.getElementById('newsForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      const res = await API.post(API.endpoints.dashNotices(), {
        title: fd.get('title'),
        body: fd.get('body'),
        anime: fd.get('anime') || null,
      });
      Utils.toast(`${res.sent} ta inbox, ${res.telegram} ta Telegram`, 'success');
      e.target.reset();
    } catch (ex) { err(ex); }
  });
}

async function renderRooms() {
  const data = await API.get(API.endpoints.dashParties());
  const rows = (data.results || []).map((p) => `
    <tr>
      <td><code>${esc(p.code)}</code></td>
      <td>${esc(p.anime_title)} · ${p.episode}-qism</td>
      <td>${esc(p.host)}</td>
      <td>${p.closed ? 'Yopiq' : (p.playing ? 'Ketmoqda' : 'Ochiq')}</td>
      <td>${p.closed ? '' : `
        <button type="button" class="btn-secondary" data-next="${esc(p.code)}">Keyingi qism</button>
        <button type="button" class="btn-secondary" data-close="${esc(p.code)}">Yopish</button>
      `}</td>
    </tr>`).join('');
  root.innerHTML = shell('rooms', `
    ${pageHead('WATCH PARTY', 'Birgalikda', 'Ochiq xonalarni keyingi qismga o‘tkazish yoki yopish.')}
    <div class="dash-table-wrap">
    <table class="dash-table">
      <thead><tr><th>Kod</th><th>Qism</th><th>Host</th><th>Holat</th><th></th></tr></thead>
      <tbody>${rows || '<tr><td colspan="5">Xona yo‘q</td></tr>'}</tbody>
    </table>
    </div>
  `);
  root.querySelectorAll('[data-next]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      try { await API.patch(API.endpoints.dashParty(btn.dataset.next), { action: 'next' }); render(); }
      catch (ex) { err(ex); }
    });
  });
  root.querySelectorAll('[data-close]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      try { await API.delete(API.endpoints.dashParty(btn.dataset.close)); render(); }
      catch (ex) { err(ex); }
    });
  });
}

async function renderPlayerPoster() {
  const data = await API.get(API.endpoints.dashPlayerPoster());
  const src = data.player_poster || '';
  root.innerHTML = shell('poster', `
    ${pageHead('PLEYER', 'Sayt posteri', 'Har bir video Play bosilguniga qadar shu rasm chiqadi.')}
    <div class="dash-panel" style="max-width:52rem">
      ${src ? `<img class="dash-player-poster" src="${esc(src)}" alt="Sayt posteri"/>` : '<p class="settings-hint">Hali poster yo‘q</p>'}
      <form class="dash-inline" id="posterForm" style="margin-top:.85rem">
        <label class="btn-secondary">Rasm tanlash <input id="sitePosterFile" type="file" accept="image/png,image/jpeg,image/webp,image/gif" hidden/></label>
        <span class="settings-hint" id="posterFileName"></span>
      </form>
    </div>
  `);
  const input = document.getElementById('sitePosterFile');
  input?.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const nameEl = document.getElementById('posterFileName');
    if (nameEl) nameEl.textContent = file.name;
    const fd = new FormData();
    fd.append('poster', file);
    try {
      await API.upload(API.endpoints.dashPlayerPoster(), fd);
      Utils.toast('Poster yangilandi', 'success');
      render();
    } catch (ex) { err(ex); }
  });
}

window.addEventListener('hashchange', render);
Auth.syncFromMe().finally(render);
