/* 平面镜实时反射：仿 three.js Reflector 的投影纹理方案，附加污渍层与故障扭曲 */
import * as THREE from 'three';

const VERT = /* glsl */`
uniform mat4 textureMatrix;
varying vec4 vUvProj;
varying vec2 vUv;
void main() {
  vUv = uv;
  vUvProj = textureMatrix * vec4(position, 1.0);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

const FRAG = /* glsl */`
precision highp float;
uniform sampler2D tMirror;
uniform sampler2D tGrime;
uniform float uTime;
uniform vec3 uTint;
uniform float uGrimeStrength;
uniform float uGlitch;
uniform float uVignette;
varying vec4 vUvProj;
varying vec2 vUv;

float hash(vec2 p) {
  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void main() {
  vec2 uv = vUvProj.xy / max(vUvProj.w, 0.0001);
  // 轻微故障抖动
  uv.x += sin(uv.y * 60.0 + uTime * 3.0) * 0.0015 * uGlitch;
  uv.y += hash(vec2(floor(uTime * 8.0), uv.y)) * 0.002 * uGlitch;

  vec3 col = texture2D(tMirror, uv).rgb;
  float g = texture2D(tGrime, vUv).r;
  vec3 grime = col * 0.35 + vec3(0.02, 0.035, 0.028);
  col = mix(col, grime, clamp(g * uGrimeStrength, 0.0, 0.9));

  col *= uTint;
  // 镜面暗角
  vec2 d = vUv - 0.5;
  float vig = smoothstep(0.92, 0.2, length(d) * 1.5);
  col *= mix(1.0 - uVignette, 1.0, vig);
  gl_FragColor = vec4(col, 1.0);
  #include <colorspace_fragment>
}
`;

function defaultTexture() {
  const c = document.createElement('canvas');
  c.width = c.height = 2;
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, 2, 2);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.NoColorSpace;
  return t;
}

export class PlanarMirror {
  constructor({ mesh, renderer, camera, getScene, resolutionScale = 0.55, grime = null, tint = 0x9fb0a8, grimeStrength = 0.55 }) {
    this.mesh = mesh;
    this.renderer = renderer;
    this.camera = camera;
    this.getScene = getScene;
    this.resolutionScale = resolutionScale;
    this.virtualCamera = new THREE.PerspectiveCamera();
    this.textureMatrix = new THREE.Matrix4();
    this.clipPlane = new THREE.Plane();
    this._normal = new THREE.Vector3();
    this._mirrorPos = new THREE.Vector3();
    this._camPos = new THREE.Vector3();
    this._view = new THREE.Vector3();
    this._target = new THREE.Vector3();
    this._lookAt = new THREE.Vector3();
    this._rot = new THREE.Matrix4();
    this._q = new THREE.Quaternion();

    const size = new THREE.Vector2();
    renderer.getSize(size);
    const w = Math.max(64, Math.round(size.x * resolutionScale));
    const h = Math.max(64, Math.round(size.y * resolutionScale));
    this.rt = new THREE.WebGLRenderTarget(w, h, {
      minFilter: THREE.LinearFilter,
      magFilter: THREE.LinearFilter,
      depthBuffer: true,
      colorSpace: THREE.SRGBColorSpace,
    });
    this.rt.texture.colorSpace = THREE.SRGBColorSpace;

    this.uniforms = {
      tMirror: { value: this.rt.texture },
      tGrime: { value: grime || defaultTexture() },
      textureMatrix: { value: this.textureMatrix },
      uTime: { value: 0 },
      uTint: { value: new THREE.Color(tint) },
      uGrimeStrength: { value: grimeStrength },
      uGlitch: { value: 0 },
      uVignette: { value: 0.35 },
    };
    this.material = new THREE.ShaderMaterial({
      uniforms: this.uniforms,
      vertexShader: VERT,
      fragmentShader: FRAG,
      side: THREE.FrontSide,
    });
    this.originalMaterial = mesh.material;
    mesh.material = this.material;
    mesh.matrixAutoUpdate = false;
    mesh.updateMatrixWorld(true);
    this._dummy = new THREE.Mesh();

    // 让镜面不参与自身渲染
    this.hiddenName = mesh.name;
    this.glitch = 0;
    this.time = 0;
  }

  setGrime(texture) {
    if (texture) {
      texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
      this.uniforms.tGrime.value = texture;
    }
  }

  setResolutionScale(s) {
    this.resolutionScale = s;
    this.resize();
  }

  resize() {
    const size = new THREE.Vector2();
    this.renderer.getSize(size);
    const w = Math.max(64, Math.round(size.x * this.resolutionScale));
    const h = Math.max(64, Math.round(size.y * this.resolutionScale));
    this.rt.setSize(w, h);
  }

  /** 每帧在渲染主场景前调用 */
  update(time, dt) {
    this.time = time;
    this.uniforms.uTime.value = time;
    this.glitch = Math.max(0, this.glitch - dt * 0.6);
    this.uniforms.uGlitch.value = this.glitch;

    const mesh = this.mesh;
    mesh.updateMatrixWorld(true);
    // 资产可能把顶点烘焙在世界坐标、节点平移为 0，因此用包围盒中心作为镜面位置
    if (!this._box) this._box = new THREE.Box3();
    this._box.setFromObject(mesh);
    this._box.getCenter(this._mirrorPos);
    this.camera.getWorldPosition(this._camPos);
    this._normal.set(0, 0, 1).applyQuaternion(mesh.getWorldQuaternion(this._q)).normalize();
    // 法线朝向相机一侧（与 three.js Reflector 一致：view = mirrorPos - camPos，view·n > 0 时翻转）
    this._view.subVectors(this._mirrorPos, this._camPos);
    if (this._normal.dot(this._view) > 0) this._normal.negate();
    this._view.subVectors(this._mirrorPos, this._camPos).reflect(this._normal).negate().add(this._mirrorPos);

    // 目标点：相机视线的镜像
    this._rot.extractRotation(this.camera.matrixWorld);
    this._lookAt.set(0, 0, -1).applyMatrix4(this._rot).add(this._camPos);
    this._target.subVectors(this._mirrorPos, this._lookAt).reflect(this._normal).negate().add(this._mirrorPos);

    const vc = this.virtualCamera;
    vc.position.copy(this._view);
    vc.up.set(0, 1, 0).applyMatrix4(this._rot).reflect(this._normal);
    vc.lookAt(this._target);
    vc.far = this.camera.far;
    vc.near = this.camera.near;
    vc.updateMatrixWorld();
    vc.projectionMatrix.copy(this.camera.projectionMatrix);

    this.textureMatrix.set(
      0.5, 0.0, 0.0, 0.5,
      0.0, 0.5, 0.0, 0.5,
      0.0, 0.0, 0.5, 0.5,
      0.0, 0.0, 0.0, 1.0
    );
    this.textureMatrix.multiply(vc.projectionMatrix);
    this.textureMatrix.multiply(vc.matrixWorldInverse);
    this.textureMatrix.multiply(mesh.matrixWorld);

    const scene = this.getScene();
    if (!scene) return;
    const hidden = scene.getObjectByName(this.hiddenName);
    const prevHidden = hidden ? hidden.visible : null;
    if (hidden) hidden.visible = false;

    // 世界空间裁剪面：保留镜面朝向房间的一侧
    this.clipPlane.setFromNormalAndCoplanarPoint(this._normal, this._mirrorPos);
    const r = this.renderer;
    const prevRT = r.getRenderTarget();
    const prevClip = r.clippingPlanes;
    const prevClearAlpha = r.getClearAlpha();
    r.clippingPlanes = [this.clipPlane];
    r.setRenderTarget(this.rt);
    r.clear();
    r.render(scene, vc);
    r.setRenderTarget(prevRT);
    r.clippingPlanes = prevClip;
    r.setClearAlpha(prevClearAlpha);
    if (hidden) hidden.visible = prevHidden;
  }

  /** 让镜面产生一次故障（死亡/惊吓时） */
  glitchPulse(amount = 1) {
    this.glitch = Math.min(2.5, this.glitch + amount);
  }
}
