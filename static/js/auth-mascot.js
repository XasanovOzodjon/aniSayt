/* global THREE */
class AuthMascot {
  constructor(root, options = {}) {
    this.root = root;
    this.canvas = root.querySelector('[data-mascot-canvas]');
    this.submits = options.submits || [];
    this.reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.coarse = window.matchMedia('(pointer: coarse)').matches
      || window.matchMedia('(hover: none)').matches;
    this.state = 'idle';
    this.failedAttempts = 0;
    this._peeking = false;
    this._focusedPass = false;
    this._mx = window.innerWidth * 0.62;
    this._my = window.innerHeight * 0.42;
    this._look = { x: 0, y: 0 };
    this._lookT = { x: 0, y: 0 };
    this._lidL = 0;
    this._lidR = 0;
    this._lidTL = 0;
    this._lidTR = 0;
    this._blink = 0;
    this._nextBlink = 2.4;
    this._t = 0;
    this._fallY = 0;
    this._fallV = 0;
    this._fallSpin = 0;
    this._ropeScale = 1;
    this._shake = 0;
    this._hue = 0;
    this._labels = new Map();
    this.submits.forEach((btn) => this._labels.set(btn, btn.textContent));

    if (!this.canvas || typeof THREE === 'undefined') return;

    this._bootScene();
    this._buildRig();
    this._resize();
    this._ro = new ResizeObserver(() => this._resize());
    this._ro.observe(this.root);

    if (!this.reduce && !this.coarse) {
      document.addEventListener('mousemove', (e) => this.trackMouse(e), { passive: true });
    }
    document.addEventListener('focusin', (e) => {
      if (e.target.matches && e.target.matches('[data-mascot-pass]')) this.onPasswordFocus();
    });
    document.addEventListener('focusout', (e) => {
      if (!e.target.matches || !e.target.matches('[data-mascot-pass]')) return;
      requestAnimationFrame(() => {
        const a = document.activeElement;
        if (!a || !a.matches('[data-mascot-pass]')) this.onPasswordBlur();
      });
    });

    this._loop = this._loop.bind(this);
    this._raf = requestAnimationFrame(this._loop);
  }

  _bootScene() {
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 40);
    camera.position.set(0, 0.55, 5.6);
    camera.lookAt(0, 0.45, 0);

    const renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      alpha: true,
      antialias: true,
      powerPreference: 'high-performance',
    });
    renderer.setClearColor(0x000000, 0);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.22;

    const key = new THREE.DirectionalLight(0xfff4ff, 2.6);
    key.position.set(1.4, 2.8, 5.2);
    const rim = new THREE.DirectionalLight(0xff4ae0, 3.4);
    rim.position.set(-3.2, 1.8, -2.6);
    const fill = new THREE.DirectionalLight(0x7af4ff, 1.35);
    fill.position.set(2.2, -0.4, 4.2);
    const face = new THREE.SpotLight(0xffe8dc, 8, 12, 0.55, 0.45, 1);
    face.position.set(0, 1.4, 4.5);
    face.target.position.set(0, 0.6, 0);
    const hemi = new THREE.HemisphereLight(0xc4b0ff, 0x1a0820, 1.05);
    const glow = new THREE.PointLight(0xff2bd6, 4.2, 9, 1.4);
    glow.position.set(0, 0.8, 1.6);
    scene.add(key, rim, fill, face, face.target, hemi, glow);

    this.scene = scene;
    this.camera = camera;
    this.renderer = renderer;
    this._glow = glow;
  }

  _mat(color, extra = {}) {
    return new THREE.MeshStandardMaterial({
      color,
      roughness: extra.roughness ?? 0.48,
      metalness: extra.metalness ?? 0.04,
      emissive: extra.emissive ?? 0x000000,
      emissiveIntensity: extra.emissiveIntensity ?? 0,
    });
  }

  _mesh(geo, mat, outline = 1.055) {
    const m = new THREE.Mesh(geo, mat);
    if (outline) {
      const o = new THREE.Mesh(geo, this._outline);
      o.scale.setScalar(outline);
      m.add(o);
    }
    return m;
  }

  _buildRig() {
    this._outline = new THREE.MeshBasicMaterial({ color: 0x070016, side: THREE.BackSide });

    const skin = this._mat(0xf3d2bc, { roughness: 0.52 });
    const skinDeep = this._mat(0xe8b89a, { roughness: 0.55 });
    const hair = this._mat(0x2a1540, { roughness: 0.58 });
    const mag = this._mat(0xff2bd6, { roughness: 0.35, emissive: 0xff2bd6, emissiveIntensity: 0.42 });
    const jacket = this._mat(0x251433, { roughness: 0.44, metalness: 0.08 });
    const trim = this._mat(0xff2bd6, { roughness: 0.35, emissive: 0x7a1458, emissiveIntensity: 0.2 });
    const gold = this._mat(0xffd36a, { roughness: 0.28, metalness: 0.55 });
    const ropeMat = this._mat(0xff2bd6, { roughness: 0.3, emissive: 0xff2bd6, emissiveIntensity: 0.7 });

    const pivot = new THREE.Group();
    pivot.position.set(0, 1.72, 0);
    this.scene.add(pivot);
    this.pivot = pivot;

    const rope = this._mesh(new THREE.CylinderGeometry(0.04, 0.048, 1.25, 12), ropeMat, 1.15);
    rope.position.y = -0.62;
    pivot.add(rope);
    this.rope = rope;

    const ring = this._mesh(new THREE.TorusGeometry(0.085, 0.02, 10, 20), gold, 1.12);
    ring.rotation.x = Math.PI / 2;
    ring.position.y = -1.14;
    pivot.add(ring);

    const character = new THREE.Group();
    character.position.y = -1.72;
    character.scale.setScalar(1.12);
    pivot.add(character);
    this.character = character;

    const body = this._mesh(new THREE.CapsuleGeometry(0.42, 0.38, 6, 16), jacket, 1.05);
    body.position.set(0, -0.22, 0);
    character.add(body);

    const collar = this._mesh(new THREE.TorusGeometry(0.34, 0.055, 8, 20), trim, 1.08);
    collar.rotation.x = 1.15;
    collar.position.set(0, 0.22, 0.04);
    character.add(collar);

    const button = this._mesh(new THREE.SphereGeometry(0.055, 12, 12), gold, 1.1);
    button.position.set(0, -0.02, 0.4);
    character.add(button);

    const pin = new THREE.Group();
    pin.position.set(0.28, 0.02, 0.36);
    pin.rotation.y = -0.35;
    for (let i = 0; i < 5; i += 1) {
      const petal = this._mesh(new THREE.SphereGeometry(0.055, 12, 10), gold, 1.08);
      petal.scale.set(1, 0.45, 0.8);
      const a = (i / 5) * Math.PI * 2;
      petal.position.set(Math.cos(a) * 0.07, Math.sin(a) * 0.07, 0);
      pin.add(petal);
    }
    pin.add(this._mesh(new THREE.SphereGeometry(0.035, 10, 10), mag, 0));
    character.add(pin);

    const armGeo = new THREE.CapsuleGeometry(0.12, 0.22, 4, 10);
    const armL = this._mesh(armGeo, jacket, 1.06);
    armL.position.set(-0.52, -0.18, 0.02);
    armL.rotation.z = 0.55;
    const armR = this._mesh(armGeo, jacket, 1.06);
    armR.position.set(0.52, -0.18, 0.02);
    armR.rotation.z = -0.55;
    character.add(armL, armR);
    this._armL = armL;
    this._armR = armR;

    const handL = this._mesh(new THREE.SphereGeometry(0.11, 12, 12), skin, 1.06);
    handL.position.set(-0.62, -0.42, 0.06);
    const handR = this._mesh(new THREE.SphereGeometry(0.11, 12, 12), skin, 1.06);
    handR.position.set(0.62, -0.42, 0.06);
    character.add(handL, handR);

    const legL = this._mesh(new THREE.CapsuleGeometry(0.13, 0.18, 4, 10), jacket, 1.06);
    legL.position.set(-0.2, -0.72, 0.02);
    const legR = this._mesh(new THREE.CapsuleGeometry(0.13, 0.18, 4, 10), jacket, 1.06);
    legR.position.set(0.2, -0.72, 0.02);
    character.add(legL, legR);

    const head = new THREE.Group();
    head.position.set(0, 0.78, 0);
    character.add(head);
    this.head = head;

    const skull = this._mesh(new THREE.SphereGeometry(0.74, 42, 32), skin, 1.035);
    skull.scale.set(1.02, 0.98, 0.9);
    head.add(skull);

    const jaw = this._mesh(new THREE.SphereGeometry(0.4, 24, 18), skinDeep, 1.04);
    jaw.scale.set(1.08, 0.7, 0.88);
    jaw.position.set(0, -0.4, 0.1);
    head.add(jaw);

    const blushL = this._mesh(new THREE.SphereGeometry(0.11, 12, 10), this._mat(0xff8eb8, { roughness: 0.75 }), 0);
    blushL.scale.set(1.35, 0.62, 0.35);
    blushL.position.set(-0.4, -0.14, 0.55);
    const blushR = blushL.clone();
    blushR.position.x *= -1;
    head.add(blushL, blushR);

    const mouth = this._mesh(new THREE.TorusGeometry(0.085, 0.016, 8, 18, Math.PI), this._mat(0x4a2030, { roughness: 0.4 }), 0);
    mouth.position.set(0, -0.24, 0.64);
    mouth.rotation.set(0.35, 0, Math.PI);
    mouth.scale.set(1, 0.65, 1);
    head.add(mouth);

    this.eyes = [this._makeEye(-1, skin, hair), this._makeEye(1, skin, hair)];
    this.eyes.forEach((eye) => head.add(eye.root));

    this._addHair(head, hair, mag);

    const ahoge = this._mesh(
      new THREE.TubeGeometry(
        new THREE.CatmullRomCurve3([
          new THREE.Vector3(0.05, 0.62, 0.1),
          new THREE.Vector3(0.12, 0.95, 0.05),
          new THREE.Vector3(0.02, 1.22, -0.05),
          new THREE.Vector3(-0.18, 1.12, -0.12),
        ]),
        24,
        0.045,
        6,
        false,
      ),
      mag,
      1.18,
    );
    head.add(ahoge);
  }

  _makeEye(side, skin, hair) {
    const root = new THREE.Group();
    root.position.set(side * 0.27, 0.05, 0.58);
    root.rotation.y = side * 0.18;

    const ball = new THREE.Group();
    const sclera = new THREE.Mesh(
      new THREE.SphereGeometry(0.195, 28, 20),
      this._mat(0xfffaf6, { roughness: 0.32 }),
    );
    sclera.scale.set(1.05, 1.12, 0.42);
    ball.add(sclera);

    const iris = new THREE.Mesh(
      new THREE.CircleGeometry(0.125, 28),
      this._mat(0x1ae4ff, { roughness: 0.16, emissive: 0x00a0b8, emissiveIntensity: 0.65, metalness: 0.08 }),
    );
    iris.position.z = 0.086;
    ball.add(iris);

    const pupil = new THREE.Mesh(
      new THREE.CircleGeometry(0.055, 18),
      new THREE.MeshBasicMaterial({ color: 0x0a0614 }),
    );
    pupil.position.z = 0.09;
    ball.add(pupil);

    const shine = new THREE.Mesh(
      new THREE.CircleGeometry(0.028, 12),
      new THREE.MeshBasicMaterial({ color: 0xffffff }),
    );
    shine.position.set(-0.04, 0.045, 0.094);
    ball.add(shine);
    const shine2 = shine.clone();
    shine2.scale.setScalar(0.45);
    shine2.position.set(0.038, -0.02, 0.094);
    ball.add(shine2);
    root.add(ball);

    const upper = this._mesh(
      new THREE.SphereGeometry(0.21, 20, 12, 0, Math.PI * 2, 0, Math.PI * 0.48),
      hair,
      1.03,
    );
    upper.scale.set(1.08, 1, 0.55);
    const lower = this._mesh(
      new THREE.SphereGeometry(0.2, 20, 10, 0, Math.PI * 2, Math.PI * 0.68, Math.PI * 0.32),
      skin,
      1.03,
    );
    lower.scale.set(1.08, 1, 0.5);
    root.add(upper, lower);

    return { root, ball, upper, lower };
  }

  _addHair(head, hair, mag) {
    const cap = this._mesh(new THREE.SphereGeometry(0.78, 28, 22), hair, 1.03);
    cap.scale.set(1.06, 0.72, 1.02);
    cap.position.set(0, 0.34, -0.12);
    head.add(cap);

    const back = this._mesh(new THREE.SphereGeometry(0.7, 24, 18), hair, 1.03);
    back.position.set(0, 0.08, -0.42);
    back.scale.set(1.05, 0.9, 0.7);
    head.add(back);

    const sideL = this._mesh(new THREE.SphereGeometry(0.28, 18, 14), hair, 1.04);
    sideL.position.set(-0.62, 0.18, -0.08);
    const sideR = sideL.clone();
    sideR.position.x *= -1;
    head.add(sideL, sideR);

    const fringeL = this._mesh(new THREE.SphereGeometry(0.16, 14, 12), hair, 1.05);
    fringeL.position.set(-0.34, 0.42, 0.42);
    fringeL.scale.set(1.1, 0.7, 0.7);
    const fringeR = fringeL.clone();
    fringeR.position.x *= -1;
    head.add(fringeL, fringeR);

    const tips = [
      [0.04, 0.72, 0.0, 0.1, 0.32, 0.12],
      [-0.5, 0.52, 0.12, 0.08, 0.22, 0.7],
      [0.52, 0.5, 0.1, 0.08, 0.22, -0.7],
    ];
    tips.forEach(([x, y, z, r, h, rot]) => {
      const spike = this._mesh(new THREE.ConeGeometry(r, h, 8), mag, 1.07);
      spike.position.set(x, y, z);
      spike.rotation.z = rot;
      head.add(spike);
    });
  }

  _resize() {
    if (!this.renderer) return;
    const w = Math.max(1, this.root.clientWidth);
    const h = Math.max(1, this.root.clientHeight);
    this.renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  _loop(now) {
    const dt = Math.min(0.033, (now - (this._last || now)) / 1000);
    this._last = now;
    this._t += dt;
    this._tick(dt);
    this.renderer.render(this.scene, this.camera);
    this._raf = requestAnimationFrame(this._loop);
  }

  _tick(dt) {
    const idle = this.state === 'idle';
    const writing = this.state === 'writing';
    const peeking = this.state === 'peeking';
    const angry = this.state === 'angry';
    const falling = this.state === 'falling';
    const returning = this.state === 'returning';

    if (!this.reduce && idle && !this.coarse) {
      const rect = this.root.getBoundingClientRect();
      const nx = ((this._mx - rect.left) / Math.max(rect.width, 1)) * 2 - 1;
      const ny = -(((this._my - rect.top) / Math.max(rect.height, 1)) * 2 - 1);
      this._lookT.x = THREE.MathUtils.clamp(nx * 0.42, -0.46, 0.46);
      this._lookT.y = THREE.MathUtils.clamp(ny * 0.32, -0.3, 0.3);
    } else if (peeking) {
      this._lookT.x = 0.22;
      this._lookT.y = -0.18;
    } else {
      this._lookT.x = 0;
      this._lookT.y = writing ? -0.08 : 0;
    }
    this._look.x += (this._lookT.x - this._look.x) * (1 - Math.exp(-10 * dt));
    this._look.y += (this._lookT.y - this._look.y) * (1 - Math.exp(-10 * dt));

    this._nextBlink -= dt;
    if (this._nextBlink < 0 && idle) {
      this._blink = 1;
      this._nextBlink = 2.2 + Math.random() * 3.2;
    }
    this._blink = Math.max(0, this._blink - dt * 7);

    let shutL = writing ? 1 : 0;
    let shutR = writing ? 1 : 0;
    if (peeking) { shutL = 0.1; shutR = 0.78; }
    if (this._blink > 0 && idle) {
      const b = Math.sin(this._blink * Math.PI);
      shutL = Math.max(shutL, b);
      shutR = Math.max(shutR, b);
    }
    const lidK = 1 - Math.exp((writing ? -26 : -14) * dt);
    this._lidL += (shutL - this._lidL) * lidK;
    this._lidR += (shutR - this._lidR) * lidK;

    this.eyes.forEach((eye, i) => {
      const lid = i === 0 ? this._lidL : this._lidR;
      eye.ball.rotation.set(-this._look.y * 0.85, this._look.x * 0.9, 0);
      eye.ball.visible = lid < 0.82;
      eye.upper.rotation.x = -1.22 + lid * 1.38;
      eye.lower.rotation.x = 0.28 + lid * 0.22;
    });

    this.head.rotation.set(-this._look.y * 0.35, this._look.x * 0.55, this._look.x * -0.08);

    let sway = 0;
    if (!this.reduce && !falling) {
      sway = Math.sin(this._t * 1.7) * 0.11;
    }
    if (angry) {
      this._shake = 1;
      this._hue = 1;
    }
    this._shake = Math.max(0, this._shake - dt * 2.4);
    this._hue = Math.max(0, this._hue - dt * 2.1);
    const jolt = this._shake * Math.sin(this._t * 48) * 0.08;

    if (falling) {
      this._fallV += 18 * dt;
      this._fallY -= this._fallV * dt;
      this._fallSpin += 4.2 * dt;
      this._ropeScale = Math.max(0, this._ropeScale - dt * 8);
    } else if (returning) {
      this._fallY += (0 - this._fallY) * (1 - Math.exp(-8 * dt));
      this._fallSpin += (0 - this._fallSpin) * (1 - Math.exp(-8 * dt));
      this._fallV = 0;
      this._ropeScale += (1 - this._ropeScale) * (1 - Math.exp(-10 * dt));
    } else {
      this._fallY += (0 - this._fallY) * (1 - Math.exp(-8 * dt));
      this._fallSpin += (0 - this._fallSpin) * (1 - Math.exp(-8 * dt));
      this._ropeScale += (1 - this._ropeScale) * (1 - Math.exp(-10 * dt));
    }

    this.pivot.rotation.z = sway + jolt;
    this.pivot.rotation.y = this._look.x * 0.18;
    this.pivot.position.y = 1.72 + this._fallY;
    this.character.rotation.z = this._fallSpin;
    this.rope.scale.y = Math.max(0.02, this._ropeScale);
    this.rope.visible = this._ropeScale > 0.04;
    this._armL.rotation.z = 0.55 + sway * 0.4;
    this._armR.rotation.z = -0.55 + sway * 0.4;
    this._glow.intensity = 2.6 + Math.sin(this._t * 2.2) * 0.5 + this._hue * 2;
    this.renderer.toneMappingExposure = 1.22 + this._hue * 0.35;
  }

  setState(name) {
    if (this.state === name && this.root.classList.contains(name)) return;
    this.state = name;
    this.root.classList.remove('idle', 'writing', 'peeking', 'angry', 'falling', 'returning');
    this.root.classList.add(name);
    if (name === 'writing') { this._lidL = 1; this._lidR = 1; }
    else if (name === 'peeking') { this._lidL = 0.1; this._lidR = 0.78; }
    else if (name === 'idle' || name === 'returning') { this._lidL = 0; this._lidR = 0; }
    if (name === 'angry') this._shake = 1;
    if (name === 'falling') {
      this._fallV = 0.4;
      this._ropeScale = 1;
    }
    if (name === 'returning') this._fallV = 0;
  }

  trackMouse(e) {
    if (this.coarse || this.reduce) return;
    this._mx = e.clientX;
    this._my = e.clientY;
  }

  _syncFace() {
    if (this.state === 'falling') return;
    if (this._peeking) this.setState('peeking');
    else if (this._focusedPass) this.setState('writing');
    else this.setState('idle');
  }

  onPasswordFocus() {
    this._focusedPass = true;
    this._syncFace();
  }

  onPasswordBlur() {
    this._focusedPass = false;
    this._syncFace();
  }

  setPeeking(on) {
    this._peeking = Boolean(on);
    this._syncFace();
  }

  bindPasswordFields(inputs) {
    inputs.forEach((el) => {
      el.addEventListener('focus', () => this.onPasswordFocus());
      el.addEventListener('blur', () => this.onPasswordBlur());
    });
  }

  bindPeekButtons(buttons) {
    buttons.forEach((btn) => {
      btn.addEventListener('mousedown', (e) => e.preventDefault());
      btn.addEventListener('click', () => {
        const form = btn.closest('form');
        const fields = [...(form?.querySelectorAll('[data-mascot-pass]') || [])];
        const formBtns = [...(form?.querySelectorAll('[data-mascot-peek]') || [btn])];
        const show = fields.some((f) => f.type === 'password');
        fields.forEach((f) => { f.type = show ? 'text' : 'password'; });
        formBtns.forEach((b) => {
          b.textContent = show ? 'abc' : '***';
          b.setAttribute('aria-pressed', show ? 'true' : 'false');
        });
        this.setPeeking(show);
      });
    });
  }

  onWrongPassword() {
    if (this.state === 'falling' || this.state === 'returning') return;
    this.failedAttempts += 1;
    if (this.failedAttempts >= 5) {
      this.onMaxAttempts();
      return;
    }
    this.setState('angry');
    setTimeout(() => {
      if (this.state === 'angry') this._syncFace();
    }, 480);
  }

  onMaxAttempts() {
    if (this.state === 'falling' || this.state === 'returning') return;
    this.failedAttempts = 0;
    this._lockSubmits(true);
    if (this.reduce) {
      this.setState('angry');
      setTimeout(() => {
        this._lockSubmits(false);
        this._syncFace();
      }, 1400);
      return;
    }
    this.setState('falling');
    setTimeout(() => this._returnFromFall(), 1500);
  }

  _returnFromFall() {
    if (this.state !== 'falling') return;
    this.setState('returning');
    this._fallY = 0.35;
    this._fallSpin = 0;
    setTimeout(() => {
      if (this.state === 'returning') {
        this._lockSubmits(false);
        this._syncFace();
      }
    }, 700);
  }

  _lockSubmits(lock) {
    document.body.classList.toggle('mascot-dropping', lock);
    this.submits.forEach((btn) => {
      btn.disabled = lock;
      btn.textContent = lock ? 'Biroz kuting...' : (this._labels.get(btn) || btn.textContent);
    });
  }

  resetAttempts() {
    this.failedAttempts = 0;
  }
}

window.AuthMascot = AuthMascot;
