window.PartyMedia = {
  key: 'animee_party_media',
  take(code) {
    try {
      const row = JSON.parse(sessionStorage.getItem(this.key) || 'null');
      if (!row || row.code !== code) return { cam: false, mic: false };
      return { cam: !!row.cam, mic: !!row.mic };
    } catch {
      return { cam: false, mic: false };
    }
  },
};

window.PartyRoom = {
  active: false,
  code: '',
  me: null,
  party: null,
  members: [],
  ice: [{ urls: 'stun:stun.l.google.com:19302' }],
  ws: null,
  pcs: {},
  localStream: null,
  camOn: false,
  micOn: false,
  applying: false,
  pending: null,
  _buf: false,
  _closedByUs: false,
  _retries: 0,
  _stateAt: 0,
  peerAudio: {},
  remoteStreams: {},
  _audioWatch: {},
  _speakUntil: {},
  _speakRaf: 0,
  _helloReady: null,
  _helloResolve: null,

  loginNext() {
    const next = location.pathname + location.search;
    if (window.Auth?.rememberNext) Auth.rememberNext(next);
    location.href = (window.ANIMEE_URLS?.auth || '/auth/') + '?next=' + encodeURIComponent(next);
  },

  inviteHref() {
    if (!this.code) return this.party?.invite_url || location.href;
    return `${location.origin}/party/${this.code}/`;
  },

  async startFromPlayer() {
    if (!Auth.user()) { this.loginNext(); return; }
    const lobby = window.ANIMEE_URLS?.party || '/party/';
    location.href = lobby + (lobby.includes('?') ? '&' : '?') + 'create=1';
  },

  async join(code) {
    if (!Auth.user()) {
      const path = `/party/${code}/`;
      Auth.rememberNext(path);
      location.href = (window.ANIMEE_URLS?.auth || '/auth/') + '?next=' + encodeURIComponent(path);
      return;
    }
    this.code = code;
    let data;
    try {
      await Auth.ensureAccess();
      data = await API.get(API.endpoints.partyDetail(code));
    } catch (err) {
      if (err.status === 401 || !localStorage.getItem('animee_access')) {
        this.loginNext();
        return;
      }
      Utils.toast(err.payload?.message || err.message || 'Xona ochilmadi', 'error');
      location.href = ANIMEE_URLS.party || '/party/';
      return;
    }
    const me = Auth.user() || {};
    const isHost = data.host?.username && data.host.username === me.username;
    const granted = window.PartyMedia.take(code);
    if (!isHost && data.require_camera && !granted.cam) {
      location.href = `/party/${code}/`;
      return;
    }
    if (!isHost && data.require_mic && !granted.mic) {
      location.href = `/party/${code}/`;
      return;
    }
    if (typeof loadEpisode === 'function') {
      await loadEpisode(data.episode.id, { silent: true });
    }
    await this.connect(code);
    try {
      await Promise.race([
        this._helloReady,
        new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 8000)),
      ]);
    } catch {
      Utils.toast('Xonaga ulanmadi', 'error');
      return;
    }
    if (granted.cam || granted.mic) {
      this.camOn = granted.cam;
      this.micOn = granted.mic;
      await this.syncMedia();
      this.sendMedia();
      document.getElementById('partyCamBtn')?.classList.toggle('is-on', this.camOn);
      document.getElementById('partyMicBtn')?.classList.toggle('is-on', this.micOn);
    } else {
      await this.ensureMesh();
    }
  },

  async connect(code) {
    const token = await Auth.ensureAccess();
    if (!token) { this.loginNext(); return; }
    this.code = code;
    this.active = true;
    this._closedByUs = false;
    this._helloReady = new Promise((resolve) => { this._helloResolve = resolve; });
    this.layout(true);
    this.setPill(this._retries ? 'ULANMOQDA…' : 'BIRGALIKDA');
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${proto}://${location.host}/ws/party/${encodeURIComponent(code)}/?token=${encodeURIComponent(token)}`;
    if (this.ws) {
      try { this.ws.close(); } catch { /* ignore */ }
    }
    const ws = new WebSocket(url);
    this.ws = ws;
    ws.onopen = () => {
      this._retries = 0;
      this.setPill('BIRGALIKDA');
      this._startHeartbeat();
    };
    ws.onmessage = (ev) => {
      try { this.onMessage(JSON.parse(ev.data)); }
      catch { /* ignore */ }
    };
    ws.onclose = (ev) => {
      if (this.ws !== ws) return;
      this._stopHeartbeat();
      if (this._closedByUs) {
        this.active = false;
        this.layout(false);
        return;
      }
      if (ev.code === 4401) { this.loginNext(); return; }
      if (ev.code === 4403) {
        Utils.toast('Xona to‘la (8 kishi)', 'error');
        this.active = false;
        this.layout(false);
        return;
      }
      if (ev.code === 4404) {
        Utils.toast('Xona topilmadi', 'error');
        this.active = false;
        this.layout(false);
        return;
      }
      this.scheduleReconnect();
    };
    ws.onerror = () => {};
  },

  scheduleReconnect() {
    if (this._closedByUs || !this.code) return;
    this._retries = Math.min((this._retries || 0) + 1, 8);
    const wait = Math.min(10000, 600 * (2 ** (this._retries - 1)));
    this.setPill('ULANMOQDA…');
    clearTimeout(this._reTimer);
    this._reTimer = setTimeout(() => {
      this.connect(this.code).catch(() => this.scheduleReconnect());
    }, wait);
  },

  _startHeartbeat() {
    this._stopHeartbeat();
    this._beat = setInterval(() => this.send({ type: 'ping' }), 8000);
  },

  _stopHeartbeat() {
    clearInterval(this._beat);
    this._beat = null;
  },

  setPill(text) {
    const el = document.getElementById('partyLivePill');
    if (el) el.textContent = text || 'BIRGALIKDA';
  },

  send(payload) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    }
  },

  onMessage(msg) {
    switch (msg.type) {
      case 'hello':
        this.me = msg.you?.id;
        this.ice = msg.ice || this.ice;
        this.members = msg.members || [];
        this.party = msg.party;
        this._stateAt = Date.now();
        this.applyState(msg.party, { force: true });
        (msg.messages || []).forEach((row) => this.appendChat(row, false));
        this.renderMembers();
        Object.keys(this.pcs).forEach((id) => {
          const pc = this.pcs[id];
          try { pc.close(); } catch { /* ignore */ }
          delete this.pcs[id];
        });
        this.remoteStreams = {};
        if (this.localStream) this.attachLocalTile();
        this.ensureMesh();
        this.layoutFaces();
        this._helloResolve?.();
        break;
      case 'pong':
      case 'state':
        this.applyState(msg.party, { soft: msg.type === 'pong' });
        break;
      case 'member-join':
      case 'member-leave':
        this.members = msg.members || this.members;
        if (msg.type === 'member-leave' && msg.user_id) this.dropPeer(msg.user_id);
        if (msg.party) this.applyState(msg.party);
        this.renderMembers();
        this.ensureMesh();
        this.layoutFaces();
        break;
      case 'episode':
        this.party = msg.party || this.party;
        if (msg.party?.episode?.id && typeof loadEpisode === 'function') {
          const path = Utils.watchHref(msg.party.episode, this.code);
          if (path && location.pathname + location.search !== path) {
            history.replaceState(null, '', path);
          }
          loadEpisode(msg.party.episode.id, { silent: true });
        }
        break;
      case 'closed':
        this._closedByUs = true;
        this.ws?.close();
        this.active = false;
        this.layout(false);
        Utils.toast('Xona yopildi', 'info');
        break;
      case 'chat':
        this.appendChat(msg.message, true);
        break;
      case 'signal':
        this.onSignal(msg.from, msg.data || {});
        break;
      case 'camera':
        this.members = msg.members || this.members;
        this.renderMembers();
        if (msg.user_id && msg.user_id !== this.me) {
          const row = (this.members || []).find((m) => m.id === msg.user_id);
          if (row && !row.camera && !row.mic) this.clearRemoteTile(msg.user_id);
        }
        this.ensureMesh();
        break;
      case 'error':
        if (/yopilgan/i.test(msg.message || '')) {
          this.onMessage({ type: 'closed', party: { closed: true } });
          break;
        }
        Utils.toast(msg.message || 'Xato', 'error');
        break;
      default:
        break;
    }
  },

  expectedPosition() {
    const party = this.party;
    if (!party) return 0;
    let pos = Number(party.position) || 0;
    if (party.playing && this._stateAt) {
      pos += Math.max(0, (Date.now() - this._stateAt) / 1000);
    }
    return pos;
  },

  applyState(party, opts = {}) {
    if (!party) return;
    this.party = party;
    this._stateAt = Date.now();
    this.pending = party;
    this.flushState(opts);
    this.renderHud();
  },

  flushState(opts = {}) {
    const party = this.pending || this.party;
    const video = document.getElementById('videoEl');
    if (!party || !video) return;
    video.playbackRate = 1;
    const target = opts.force ? Number(party.position) : this.expectedPosition();
    const gap = Math.abs((video.currentTime || 0) - target);
    const limit = opts.soft ? 2.5 : 1.2;
    const needSeek = Number.isFinite(target) && (opts.force ? gap > 0.4 : gap > limit);
    this.applying = true;
    clearTimeout(this._applyTimer);
    const finish = () => {
      this._applyTimer = setTimeout(() => { this.applying = false; }, 350);
    };
    const applyPlay = () => {
      if (party.playing) {
        const play = video.play();
        if (play && play.catch) {
          play.catch(() => document.getElementById('bigPlay')?.classList.remove('hidden'));
        }
      } else {
        video.pause();
      }
      finish();
    };
    if (needSeek) {
      const onSeeked = () => {
        video.removeEventListener('seeked', onSeeked);
        applyPlay();
      };
      video.addEventListener('seeked', onSeeked);
      try { video.currentTime = target; } catch { applyPlay(); }
      this._applyTimer = setTimeout(() => {
        video.removeEventListener('seeked', onSeeked);
        applyPlay();
      }, 1400);
    } else {
      applyPlay();
    }
    const wait = document.getElementById('partyWait');
    if (wait) wait.hidden = !(party.buffering || []).length;
  },

  requestPlayToggle() {
    const video = document.getElementById('videoEl');
    if (!video) return;
    if (this.party?.playing && video.paused) {
      video.play().catch(() => {});
      return;
    }
    if (video.paused) {
      this.send({ type: 'play', position: video.currentTime || 0 });
      video.play().catch(() => {});
    } else {
      this.send({ type: 'pause', position: video.currentTime || 0 });
      video.pause();
    }
  },

  requestSeek(time) {
    const video = document.getElementById('videoEl');
    const t = Math.max(0, Number(time) || 0);
    if (video) {
      this.applying = true;
      video.currentTime = t;
      this._applyTimer = setTimeout(() => { this.applying = false; }, 400);
    }
    this.send({ type: 'seek', position: t });
  },

  requestSkip(delta) {
    const video = document.getElementById('videoEl');
    const t = Math.max(0, (video?.currentTime || 0) + delta);
    this.requestSeek(t);
  },

  noteBuffer(waiting) {
    if (!this.active || this.applying) return;
    if (this._buf === waiting) return;
    this._buf = waiting;
    clearTimeout(this._bufTimer);
    this._bufTimer = setTimeout(() => {
      if (!this.active || this.applying) return;
      this.send({ type: waiting ? 'buffering' : 'ready' });
    }, 180);
  },

  layout(on) {
    document.getElementById('playerPage')?.classList.toggle('party-on', on);
    document.getElementById('partyStartBtn')?.classList.toggle('hidden', on);
    document.getElementById('partyChatBtn')?.classList.toggle('hidden', !on);
    document.getElementById('partyLivePill')?.classList.toggle('hidden', !on);
    if (!on) {
      Object.keys(this._audioWatch || {}).forEach((id) => this.unwatchAudio(id));
      document.getElementById('partyFaces')?.replaceChildren();
      this.layoutFaces();
    }
  },

  renderHud() {
    const codeEl = document.getElementById('partyCodeLabel');
    if (codeEl) codeEl.textContent = this.party?.code || this.code || '';
    const closeBtn = document.getElementById('partyCloseBtn');
    if (closeBtn) closeBtn.hidden = this.party?.host_id !== this.me;
    const ctrl = document.getElementById('partyControlBtn');
    if (ctrl) {
      ctrl.hidden = this.party?.host_id !== this.me;
      ctrl.textContent = this.party?.control === 'host' ? 'Boshqaruv: host' : 'Boshqaruv: hammaga';
    }
    const opts = document.getElementById('partyHostOpts');
    if (opts) opts.hidden = this.party?.host_id !== this.me;
    const reqCam = document.getElementById('partyReqCam');
    const reqMic = document.getElementById('partyReqMic');
    if (reqCam && this.party) reqCam.checked = Boolean(this.party.require_camera);
    if (reqMic && this.party) reqMic.checked = Boolean(this.party.require_mic);
  },

  renderMembers() {
    const box = document.getElementById('partyMembers');
    if (!box) return;
    box.innerHTML = (this.members || []).map((m) => {
      const photo = Utils.safeUrl(m.photo);
      const name = Utils.escapeHtml(m.username || 'User');
      return `<div class="party-member${m.id === this.me ? ' is-me' : ''}">
        <span class="party-member-ava">${photo ? `<img src="${photo}" alt="">` : name.slice(0, 1)}</span>
        <span>${name}${m.host ? ' · host' : ''}${m.camera ? ' · kamera' : ''}${m.mic ? ' · mik' : ''}</span>
      </div>`;
    }).join('');
  },

  appendChat(msg, scroll) {
    if (!msg) return;
    const list = document.getElementById('partyChatList');
    if (!list) return;
    if (msg.id && list.querySelector(`[data-mid="${msg.id}"]`)) return;
    const mine = msg.user_id === this.me;
    const el = document.createElement('div');
    el.className = 'party-msg' + (mine ? ' is-mine' : '');
    if (msg.id) el.dataset.mid = String(msg.id);
    el.innerHTML = `<strong>${Utils.escapeHtml(msg.username || '')}</strong><p>${Utils.escapeHtml(msg.body || '')}</p>`;
    list.appendChild(el);
    if (scroll !== false) list.scrollTop = list.scrollHeight;
  },

  async copyInvite(quiet) {
    const href = this.inviteHref();
    if (!quiet && navigator.share) {
      try {
        await navigator.share({ title: 'Animee Birgalikda', url: href });
        return;
      } catch { /* copy instead */ }
    }
    try {
      await navigator.clipboard.writeText(href);
      Utils.toast(quiet ? 'Taklif havolasi nusxalandi' : 'Havola nusxalandi', 'success');
    } catch {
      Utils.toast(href, 'info');
    }
  },

  async toggleCamera() {
    this.camOn = !this.camOn;
    await this.syncMedia();
    this.sendMedia();
    document.getElementById('partyCamBtn')?.classList.toggle('is-on', this.camOn);
  },

  async toggleMic() {
    this.micOn = !this.micOn;
    await this.syncMedia();
    this.sendMedia();
    document.getElementById('partyMicBtn')?.classList.toggle('is-on', this.micOn);
  },

  sendMedia() {
    this.send({ type: 'camera', on: this.camOn, mic: this.micOn });
  },

  facesWanted() {
    return this.camOn || this.micOn || (this.members || []).some((m) => m.camera && m.id !== this.me);
  },

  async syncMedia() {
    if (!this.camOn && !this.micOn) {
      this.stopLocal();
      await this.ensureMesh();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: this.camOn ? { facingMode: 'user' } : false,
        audio: this.micOn ? { echoCancellation: true, noiseSuppression: true, autoGainControl: true } : false,
      });
      this.stopLocal(true);
      this.localStream = stream;
      this.attachLocalTile();
      await this.ensureMesh();
    } catch {
      this.camOn = false;
      this.micOn = false;
      Utils.toast('Kamera yoki mikrofon ruxsati yo‘q', 'error');
      document.getElementById('partyCamBtn')?.classList.remove('is-on');
      document.getElementById('partyMicBtn')?.classList.remove('is-on');
    }
  },

  stopLocal(keepFlag) {
    if (this.localStream) {
      this.localStream.getTracks().forEach((t) => t.stop());
      this.localStream = null;
    }
    Object.values(this.pcs).forEach((pc) => {
      pc.getSenders().forEach((s) => {
        if (s.track) pc.removeTrack(s);
      });
    });
    if (!keepFlag) this.clearLocalTile();
  },

  attachLocalTile() {
    if (!this.me || !this.localStream) return;
    const meRow = (this.members || []).find((m) => m.id === this.me);
    const video = this.ensureTile(this.me, meRow || { username: Auth.user()?.username || 'Siz' }, true);
    if (!video) return;
    video.srcObject = this.localStream;
    video.muted = true;
    video.playsInline = true;
    video.setAttribute('playsinline', '');
    video.setAttribute('webkit-playsinline', '');
    this.playTile(video);
    this.watchAudio(this.me, this.localStream);
    this.layoutFaces();
  },

  clearLocalTile() {
    if (this.me) {
      this.unwatchAudio(this.me);
      document.getElementById('partyTile-' + this.me)?.remove();
    }
    this.layoutFaces();
  },

  clearRemoteTile(userId) {
    if (userId && userId !== this.me) {
      this.unwatchAudio(userId);
      document.getElementById('partyTile-' + userId)?.remove();
    }
    this.layoutFaces();
  },

  layoutFaces() {
    const faces = document.getElementById('partyFaces');
    if (!faces) return;
    const n = faces.querySelectorAll('.party-tile').length;
    faces.dataset.count = String(n);
    faces.classList.toggle('is-on', n > 0);
    let cols = 1;
    if (n >= 5) cols = 2;
    const rows = Math.ceil(Math.max(n, 1) / cols);
    faces.style.setProperty('--party-cols', String(cols));
    faces.style.setProperty('--party-rows', String(rows));
    const tiles = [...faces.querySelectorAll('.party-tile')];
    tiles.forEach((tile) => { tile.style.gridColumn = ''; });
  },

  peerAudioRow(id) {
    if (!this.peerAudio[id]) this.peerAudio[id] = { muted: false, volume: 1 };
    return this.peerAudio[id];
  },

  applyPeerAudio(id) {
    if (!id || id === this.me) return;
    const video = document.querySelector(`#partyTile-${id} video`);
    if (!video) return;
    const row = this.peerAudioRow(id);
    const muted = row.muted || row.volume <= 0;
    video.muted = muted;
    video.volume = muted ? 0 : row.volume;
    this.syncTileAudioUi(id);
  },

  togglePeerMute(id) {
    const row = this.peerAudioRow(id);
    row.muted = !row.muted;
    this.applyPeerAudio(id);
  },

  setPeerVolume(id, volume) {
    const row = this.peerAudioRow(id);
    row.volume = Math.min(1, Math.max(0, Number(volume) || 0));
    if (row.volume > 0) row.muted = false;
    this.applyPeerAudio(id);
  },

  syncTileAudioUi(id) {
    const wrap = document.getElementById('partyTile-' + id);
    if (!wrap) return;
    const row = this.peerAudioRow(id);
    const muted = row.muted || row.volume <= 0;
    wrap.classList.toggle('is-muted', muted);
    const btn = wrap.querySelector('.party-tile-mute');
    if (btn) {
      btn.setAttribute('aria-label', muted ? 'Ovozni yoqish' : 'Ovozni o‘chirish');
      btn.title = muted ? 'Ovozni yoqish (faqat sizda)' : 'Ovozni o‘chirish (faqat sizda)';
      btn.innerHTML = muted
        ? '<svg viewBox="0 0 24 24"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M23 9l-6 6M17 9l6 6"/></svg>'
        : '<svg viewBox="0 0 24 24"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M15.5 8.5a5 5 0 010 7"/><path d="M19 5a9 9 0 010 14"/></svg>';
    }
    const sl = wrap.querySelector('.party-tile-vol');
    if (sl && document.activeElement !== sl) sl.value = String(Math.round((muted ? 0 : row.volume) * 100));
  },

  audioContext() {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return null;
    if (!this._audioCtx) this._audioCtx = new Ctx();
    if (this._audioCtx.state === 'suspended') this._audioCtx.resume().catch(() => {});
    return this._audioCtx;
  },

  watchAudio(userId, stream) {
    if (!userId || !stream || !stream.getAudioTracks().length) return;
    this.unwatchAudio(userId);
    const ctx = this.audioContext();
    if (!ctx) return;
    try {
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 1024;
      analyser.smoothingTimeConstant = 0.35;
      source.connect(analyser);
      this._audioWatch[userId] = {
        source,
        analyser,
        data: new Uint8Array(analyser.fftSize),
      };
      this.startSpeakLoop();
    } catch {
      /* ignore */
    }
  },

  unwatchAudio(userId) {
    const row = this._audioWatch[userId];
    if (row) {
      try { row.source.disconnect(); } catch { /* ignore */ }
      delete this._audioWatch[userId];
    }
    delete this._speakUntil[userId];
    document.getElementById('partyTile-' + userId)?.classList.remove('is-speaking');
  },

  startSpeakLoop() {
    if (this._speakRaf) return;
    const tick = () => {
      const ids = Object.keys(this._audioWatch);
      if (!ids.length) {
        this._speakRaf = 0;
        return;
      }
      const now = Date.now();
      ids.forEach((id) => {
        const row = this._audioWatch[id];
        row.analyser.getByteTimeDomainData(row.data);
        let sum = 0;
        for (let i = 0; i < row.data.length; i += 1) {
          const v = (row.data[i] - 128) / 128;
          sum += v * v;
        }
        const rms = Math.sqrt(sum / row.data.length);
        if (rms > 0.045) this._speakUntil[id] = now + 340;
        const on = (this._speakUntil[id] || 0) > now;
        document.getElementById('partyTile-' + id)?.classList.toggle('is-speaking', on);
      });
      this._speakRaf = requestAnimationFrame(tick);
    };
    this._speakRaf = requestAnimationFrame(tick);
  },

  ensureTile(id, member, isLocal) {
    const faces = document.getElementById('partyFaces');
    let wrap = document.getElementById('partyTile-' + id);
    if (!wrap && faces) {
      wrap = document.createElement('div');
      wrap.id = 'partyTile-' + id;
      wrap.className = 'party-tile' + (isLocal ? ' is-local' : '');
      const photo = Utils.safeUrl(member?.photo);
      if (photo) wrap.style.backgroundImage = `url("${photo}")`;
      wrap.innerHTML = isLocal
        ? `<video playsinline autoplay muted></video><div class="party-tile-bar"><span class="party-tile-name"></span></div>`
        : `<video playsinline autoplay></video>
           <div class="party-tile-bar">
             <span class="party-tile-name"></span>
             <div class="party-tile-audio">
               <button type="button" class="party-tile-mute" aria-label="Ovozni o‘chirish"></button>
               <input type="range" class="party-tile-vol" min="0" max="100" value="100" aria-label="Ovoz"/>
             </div>
           </div>`;
      if (isLocal) faces.prepend(wrap);
      else faces.appendChild(wrap);
      if (!isLocal) {
        wrap.querySelector('.party-tile-mute')?.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          this.togglePeerMute(id);
        });
        const sl = wrap.querySelector('.party-tile-vol');
        sl?.addEventListener('input', (e) => {
          e.stopPropagation();
          this.setPeerVolume(id, Number(e.target.value) / 100);
        });
        sl?.addEventListener('click', (e) => e.stopPropagation());
        sl?.addEventListener('pointerdown', (e) => e.stopPropagation());
        this.syncTileAudioUi(id);
      }
    }
    const name = wrap?.querySelector('.party-tile-name');
    if (name) {
      const base = member?.username || (isLocal ? 'Siz' : '');
      name.textContent = isLocal ? (base === 'Siz' ? 'Siz' : `${base} · siz`) : base;
    }
    const videoEl = wrap?.querySelector('video');
    if (videoEl) {
      videoEl.playsInline = true;
      videoEl.setAttribute('playsinline', '');
      videoEl.setAttribute('webkit-playsinline', '');
      videoEl.autoplay = true;
    }
    this.layoutFaces();
    return videoEl;
  },

  playTile(video) {
    if (!video) return;
    const play = video.play();
    if (play && play.catch) {
      play.catch(() => { this._needUnlock = true; });
    }
  },

  unlockMedia() {
    if (this._audioCtx?.state === 'suspended') this._audioCtx.resume().catch(() => {});
    document.querySelectorAll('#partyFaces video').forEach((el) => {
      const play = el.play();
      if (play && play.catch) play.catch(() => {});
    });
    this._needUnlock = false;
  },

  async ensurePeer(userId) {
    if (this.pcs[userId]) return this.pcs[userId];
    const pc = new RTCPeerConnection({ iceServers: this.ice });
    this.pcs[userId] = pc;
    if (this.localStream) {
      this.localStream.getTracks().forEach((track) => pc.addTrack(track, this.localStream));
    }
    pc.onicecandidate = (e) => {
      if (e.candidate) {
        this.send({
          type: 'signal',
          to: userId,
          data: { kind: 'ice', candidate: e.candidate.toJSON() },
        });
      }
    };
    pc.ontrack = (e) => {
      let stream = e.streams && e.streams[0];
      if (!stream) {
        stream = this.remoteStreams[userId] || new MediaStream();
        if (![...stream.getTracks()].includes(e.track)) stream.addTrack(e.track);
      }
      this.remoteStreams[userId] = stream;
      const member = (this.members || []).find((m) => m.id === userId) || { username: '' };
      const video = this.ensureTile(userId, member, false);
      if (video) {
        if (video.srcObject !== stream) video.srcObject = stream;
        video.muted = true;
        const play = video.play();
        if (play && play.then) {
          play.then(() => this.applyPeerAudio(userId)).catch(() => { this._needUnlock = true; });
        } else {
          this.applyPeerAudio(userId);
        }
      }
      if (stream.getAudioTracks().length) this.watchAudio(userId, stream);
    };
    pc.onconnectionstatechange = () => {
      if (pc.connectionState === 'failed') {
        pc.restartIce();
      }
      if (pc.connectionState === 'closed') {
        this.dropPeer(userId);
      }
    };
    return pc;
  },

  addLocalTracks(pc) {
    if (!this.localStream) return;
    const senders = pc.getSenders();
    this.localStream.getTracks().forEach((track) => {
      const existing = senders.find((s) => s.track && s.track.kind === track.kind);
      if (existing) existing.replaceTrack(track);
      else pc.addTrack(track, this.localStream);
    });
  },

  async renegotiate(userId) {
    const pc = await this.ensurePeer(userId);
    this.addLocalTracks(pc);
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    this.send({
      type: 'signal',
      to: userId,
      data: { kind: 'offer', sdp: { type: offer.type, sdp: offer.sdp } },
    });
  },

  async ensureMesh() {
    if (!this.active || !this.me) return;
    for (const member of this.members || []) {
      if (member.id === this.me) continue;
      try {
        if (this.me < member.id) await this.renegotiate(member.id);
        else {
          const pc = await this.ensurePeer(member.id);
          this.addLocalTracks(pc);
        }
      } catch {
        /* ignore */
      }
    }
  },

  async onSignal(from, data) {
    if (!this.facesWanted() && data.kind !== 'ice') {
      /* still answer offers so the other side does not hang */
    }
    const pc = await this.ensurePeer(from);
    try {
      if (data.kind === 'offer' && data.sdp) {
        await pc.setRemoteDescription(new RTCSessionDescription(data.sdp));
        this.addLocalTracks(pc);
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        this.send({
          type: 'signal',
          to: from,
          data: { kind: 'answer', sdp: { type: answer.type, sdp: answer.sdp } },
        });
      } else if (data.kind === 'answer' && data.sdp) {
        await pc.setRemoteDescription(new RTCSessionDescription(data.sdp));
      } else if (data.kind === 'ice' && data.candidate) {
        await pc.addIceCandidate(new RTCIceCandidate(data.candidate));
      }
    } catch {
      /* ignore */
    }
  },

  dropPeer(userId) {
    const pc = this.pcs[userId];
    if (pc) {
      try { pc.close(); } catch { /* ignore */ }
      delete this.pcs[userId];
    }
    this.clearRemoteTile(userId);
  },

  async closeRoom() {
    if (!this.code) return;
    try {
      await API.delete(API.endpoints.partyDetail(this.code));
    } catch (err) {
      Utils.toast(err.message || 'Yopilmadi', 'error');
      return;
    }
    this._closedByUs = true;
    this.ws?.close();
    this.active = false;
    this.layout(false);
    Utils.toast('Xona yopildi', 'info');
  },

  async saveRequirements() {
    if (!this.code || this.party?.host_id !== this.me) return;
    const require_camera = Boolean(document.getElementById('partyReqCam')?.checked);
    const require_mic = Boolean(document.getElementById('partyReqMic')?.checked);
    try {
      const data = await API.patch(API.endpoints.partyDetail(this.code), { require_camera, require_mic });
      this.party = { ...this.party, ...data };
      Utils.toast('Taklif sozlamasi saqlandi', 'success');
    } catch (err) {
      Utils.toast(err.message || 'Saqlanmadi', 'error');
    }
  },

  toggleControl() {
    const next = this.party?.control === 'host' ? 'shared' : 'host';
    this.send({ type: 'control', mode: next });
  },

  bindUi() {
    if (this._bound) return;
    this._bound = true;
    document.getElementById('partyStartBtn')?.addEventListener('click', () => {
      this.startFromPlayer().catch((err) => Utils.toast(err.message || 'Xona ochilmadi', 'error'));
    });
    document.getElementById('partyInviteBtn')?.addEventListener('click', () => this.copyInvite());
    document.getElementById('partyCamBtn')?.addEventListener('click', () => this.toggleCamera());
    document.getElementById('partyMicBtn')?.addEventListener('click', () => this.toggleMic());
    document.getElementById('partyCloseBtn')?.addEventListener('click', () => this.closeRoom());
    document.getElementById('partyControlBtn')?.addEventListener('click', () => this.toggleControl());
    document.getElementById('partyReqCam')?.addEventListener('change', () => this.saveRequirements());
    document.getElementById('partyReqMic')?.addEventListener('change', () => this.saveRequirements());
    document.getElementById('partyChatBtn')?.addEventListener('click', () => {
      document.getElementById('partyDock')?.classList.toggle('open');
      document.getElementById('epScrim')?.classList.toggle('show');
    });
    document.getElementById('partyDockClose')?.addEventListener('click', () => {
      document.getElementById('partyDock')?.classList.remove('open');
      document.getElementById('epScrim')?.classList.remove('show');
    });
    document.getElementById('partyChatForm')?.addEventListener('submit', (e) => {
      e.preventDefault();
      const input = document.getElementById('partyChatInput');
      const body = (input?.value || '').trim();
      if (!body) return;
      this.send({ type: 'chat', body });
      input.value = '';
    });
    document.getElementById('videoWrapper')?.addEventListener('pointerdown', () => this.unlockMedia(), { passive: true });
    window.addEventListener('online', () => {
      if (this.active && this.code && (!this.ws || this.ws.readyState !== WebSocket.OPEN)) {
        this.scheduleReconnect();
      }
    });
  },
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => PartyRoom.bindUi());
} else {
  PartyRoom.bindUi();
}
