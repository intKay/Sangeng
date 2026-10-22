/* PS1 风格后处理：低分辨率渲染 + 颗粒 + 扫描线 + 暗角 + 色差 + 抖动 + 理智扭曲 */
import * as THREE from 'three';

const VERT = /* glsl */`
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = vec4(position.xy, 0.0, 1.0);
}
`;

const FRAG = /* glsl */`
precision highp float;
varying vec2 vUv;
uniform sampler2D tDiffuse;
uniform vec2 uResolution;
uniform float uTime;
uniform float uGrain;
uniform float uVignette;
uniform float uScanline;
uniform float uChroma;
uniform float uSanity;
uniform float uThreat;
uniform float uFade;
uniform float uContrast;
uniform vec3 uTint;
uniform float uDither;

float hash21(vec2 p) {
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}

void main() {
  vec2 uv = vUv;
  // 理智低时的轻微空间扭曲
  float wob = uSanity * 0.0035 + uThreat * 0.0018;
  uv.x += sin(uv.y * 31.0 + uTime * 1.7) * wob;
  uv.y += cos(uv.x * 23.0 + uTime * 1.3) * wob * 0.7;

  float ca = uChroma * (0.5 + uSanity * 2.2 + uThreat * 1.0) / uResolution.x;
  vec3 col;
  col.r = texture2D(tDiffuse, uv + vec2(ca, 0.0)).r;
  col.g = texture2D(tDiffuse, uv).g;
  col.b = texture2D(tDiffuse, uv - vec2(ca, 0.0)).b;

  // 调色：对比 + 轻微偏色
  col = (col - 0.5) * uContrast + 0.5;
  col *= uTint;

  // 胶片颗粒
  float grain = hash21(uv * uResolution + vec2(uTime * 61.7, uTime * 37.3));
  col += (grain - 0.5) * uGrain;

  // 扫描线（暗线随低分辨率放大）
  float scan = sin(uv.y * uResolution.y * 1.5707963);
  col *= 1.0 - uScanline * 0.35 * (0.5 + 0.5 * scan);

  // 暗角
  vec2 d = uv - 0.5;
  float vig = smoothstep(0.92, 0.28, length(d) * 1.35);
  col *= mix(1.0 - uVignette, 1.0, vig);

  // 理智：降饱和、色偏、心跳压迫
  float lum = dot(col, vec3(0.299, 0.587, 0.114));
  vec3 drained = mix(vec3(lum), col, 1.0 - uSanity * 0.55);
  drained = mix(drained, drained * vec3(1.08, 0.92, 0.9), uSanity * 0.6 + uThreat * 0.4);
  drained += uThreat * 0.025 * sin(uTime * 6.0 + uv.y * 40.0);
  col = drained;

  // 轻微抖动/噪点量化（PS1 感）
  float dith = hash21(uv * uResolution * 0.5 + uTime) - 0.5;
  col += dith * uDither;

  // 淡入淡出
  col = mix(col, vec3(0.0), clamp(uFade, 0.0, 1.0));

  gl_FragColor = vec4(max(col, vec3(0.0)), 1.0);
  #include <colorspace_fragment>
}
`;

export class PostFX {
  constructor(renderer, opts = {}) {
    this.renderer = renderer;
    this.renderScale = opts.renderScale || 0.6;
    this.scene = new THREE.Scene();
    this.camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    this.rt = new THREE.WebGLRenderTarget(2, 2, {
      minFilter: THREE.NearestFilter,
      magFilter: THREE.NearestFilter,
      depthBuffer: true,
      stencilBuffer: false,
    });
    this.rt.texture.colorSpace = THREE.SRGBColorSpace;
    this.uniforms = {
      tDiffuse: { value: this.rt.texture },
      uResolution: { value: new THREE.Vector2(2, 2) },
      uTime: { value: 0 },
      uGrain: { value: 0.035 },
      uVignette: { value: 0.44 },
      uScanline: { value: 0.035 },
      uChroma: { value: 1.1 },
      uSanity: { value: 0 },
      uThreat: { value: 0 },
      uFade: { value: 0 },
      uContrast: { value: 1.06 },
      uTint: { value: new THREE.Color(0xffffff) },
      uDither: { value: 0.002 },
    };
    this.material = new THREE.ShaderMaterial({
      uniforms: this.uniforms,
      vertexShader: VERT,
      fragmentShader: FRAG,
      depthTest: false,
      depthWrite: false,
    });
    this.quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.material);
    this.quad.frustumCulled = false;
    this.scene.add(this.quad);
    this.size = new THREE.Vector2(2, 2);
  }

  setSize(w, h) {
    this.size.set(w, h);
    const rw = Math.max(2, Math.round(w * this.renderScale));
    const rh = Math.max(2, Math.round(h * this.renderScale));
    this.rt.setSize(rw, rh);
    this.uniforms.uResolution.value.set(rw, rh);
  }

  setScale(scale) {
    this.renderScale = scale;
    this.setSize(this.size.x, this.size.y);
  }

  setBackdrop(color) {
    this.renderer.setClearColor(color || 0x000000, 1);
  }

  render(scene, camera) {
    const r = this.renderer;
    r.setRenderTarget(this.rt);
    r.clear();
    r.render(scene, camera);
    r.setRenderTarget(null);
    r.clear();
    r.render(this.scene, this.camera);
  }
}
