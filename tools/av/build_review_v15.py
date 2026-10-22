"""Build the comparison deliverable; all media are real runtime captures."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/av-v1.5'
cards=[]
for id,title,sound in [('door','门后','door/ambience/corridor_hum.ogg'),('mirror','镜中','mirror/ambience/distant_water.ogg'),('nightroad','夜路','nightroad/ambience/wind_field.ogg')]:
    cards.append(f'''<section id="{id}"><h2>{title}</h2><div class="compare">
    <img src="before/{id}-entry.jpg" alt="{title}上一版入口"><img class="new" src="after/{id}-entry.jpg" alt="{title}新版入口">
    <span class="old-label">1.4 · 上一版</span><span class="new-label">1.5 · 新版</span><div class="line"></div></div>
    <label class="slider">拖动对照<input aria-label="{title}前后画面对照" type="range" min="0" max="100" value="50"></label>
    <div class="actions"><button data-src="audio-before/{sound}">听上一版环境声</button><button data-src="../../assets/audio/{sound}">听新版环境声</button><button data-stop>停止</button><a href="../../games/{id}/">进入这一篇 →</a></div>
    <details><summary>查看新版物件近景</summary><img src="after/{id}-detail.jpg" alt="{title}辅助机位近景"></details></section>''')
html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>三更 · 1.5 音画对照</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#101511;color:#dddcd0;font:16px/1.8 system-ui}main{max-width:1280px;margin:auto;padding:40px 24px}h1{font:clamp(34px,6vw,58px)/1.25 Georgia,'SimSun',serif;color:#dac391;margin:10px 0 24px}h2{font-weight:400;color:#d2be8e;font-size:30px}.kicker{color:#8f9d8b;letter-spacing:.25em;font-size:13px}.intro{max-width:850px;color:#afb7aa}a{color:#d7c599}nav{display:flex;gap:24px;flex-wrap:wrap;margin:26px 0}.compare{position:relative;background:#050605;overflow:hidden}.compare>img{display:block;width:100%}.compare .new{position:absolute;inset:0;clip-path:inset(0 0 0 50%)}.line{position:absolute;top:0;bottom:0;left:50%;width:2px;background:#e8dcb2;pointer-events:none}.old-label,.new-label{position:absolute;top:18px;background:#111b;padding:5px 12px;font-size:14px}.old-label{left:14px}.new-label{right:14px}.slider{display:flex;gap:20px;align-items:center;padding:15px 0;color:#b7c2b0}.slider input{flex:1;accent-color:#c9ae75}section{padding:26px 0;border-top:1px solid #354031}.actions{display:flex;gap:10px;align-items:center;flex-wrap:wrap}button{background:#283426;border:1px solid #617157;color:#e5ddc4;padding:11px 16px;font:inherit;cursor:pointer;border-radius:3px}button:hover{background:#3a4934}summary{cursor:pointer;padding:15px 0;color:#aebba6}details img{width:100%;max-width:1000px}.scope{color:#96a18f;font-size:14px;max-width:1000px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:12px}.pair img{width:100%}audio{width:100%;max-width:640px}footer{margin-top:40px;border-top:1px solid #354031;padding-top:20px;color:#94a08d}@media(max-width:650px){main{padding:25px 14px}.pair{grid-template-columns:1fr}.old-label,.new-label{font-size:11px;top:8px;padding:2px 6px}}
</style><main><div class="kicker">SANGENG · AUDIOVISUAL STUDY 02</div><h1>旧屋的表面，<br>空间里的声音。</h1>
<p class="intro">这一轮以实际游戏表现为目标：11 份 Z-Image 生成源形成 16 种替换材质，加入表面凹凸与受光、静态接触遮蔽、局部阴影和湿面；五条环境床重混，三篇采用不同混响，并增加窗雨与水声的空间方位。</p>
<nav><a href="../../index.html">游玩 1.5 候选 →</a><a href="#door">门后</a><a href="#mirror">镜中</a><a href="#nightroad">夜路</a><a href="../../docs/av_iteration_v1.5.md">制作与验收记录</a></nav>
<audio controls id="player" preload="none"></audio><div id="status" role="status">点击下方按钮试听，同一时间只播放一条。</div>
<p class="scope">入口对照来自真实运行，时序颗粒与光线并非完全锁帧。1.4 截图为软件渲染，1.5 为本机 RTX 3050 / Edge；此处比较表现，不比较两者帧率。近景为辅助定位。音频按钮比较单条环境素材，完整游戏另含音乐、空间定位与混响。尚待真人听感和完整游玩验收。</p>
'''+''.join(cards)+'''<section><h2>走进去之后</h2><p>两版均从起点以实际按键、鼠标拖动和 E 开门进入，无 teleport。位置存在正常输入与停步误差。</p><div class="pair"><div><p>1.4 · 上一版</p><img src="route/before/03-apartment.jpg" alt="旧版正常路线室内"></div><div><p>1.5 · 新版</p><img src="route/after/03-apartment.jpg" alt="新版正常路线室内"></div></div></section>
<footer>基线 f669c15 · 标签 codex/av-v1.4-before-upgrade<br>候选分支 codex/v1.5.0-audiovisual · 未替换线上稳定版本</footer></main><script>
for(const section of document.querySelectorAll('section')){const slider=section.querySelector('input');if(slider)slider.oninput=()=>{section.querySelector('.new').style.clipPath=`inset(0 0 0 ${slider.value}%)`;section.querySelector('.line').style.left=slider.value+'%'}}
const player=document.querySelector('#player'),status=document.querySelector('#status');
document.querySelectorAll('[data-src]').forEach(b=>b.onclick=async()=>{player.pause();player.src=b.dataset.src;try{await player.play();status.textContent=b.closest('section').querySelector('h2').textContent+' · '+b.textContent}catch(e){status.textContent='播放失败：'+e.message}});
document.querySelectorAll('[data-stop]').forEach(b=>b.onclick=()=>{player.pause();player.currentTime=0;status.textContent='已停止'});
</script></html>'''
(OUT/'index.html').write_text(html,encoding='utf-8')
print(OUT/'index.html')
