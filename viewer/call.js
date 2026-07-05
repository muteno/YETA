// call.js — yeta 음성 모듈: 걸려오는 전화 수신 + 무전기(PTT) + 프리미엄 배지 (플러그인 · 260704 · CLAUDE.md §🗺 yeta-call 항목이 정본)
//
// [설치 = index.html 훅 · 제거 = 훅 삭제(본체 무손상 = 붙였다 뗄 수 있는 모듈)]
//   ① <script src="call.js" defer></script>            (본체 스크립트 뒤 — 전역 yApi/esc/yAva/YCHARS 계승)
//   ② yLoad()의 `YSESS = r.sess` 직후 1줄:  if (window.YCALL) YCALL.onSess(YSESS);
//   ③ (선택) 캐릭터 이름 옆 프리미엄 배지 = 템플릿에 `window.yPremBadge ? yPremBadge(c) : ''` — 모듈 제거 시 자동 소멸
//   본체 전역이 없으면(다른 페이지에 실수 로드) 모듈은 스스로 비활성(no-op).
//
// [서버 계약 — yeta_call.sh · yeta_chat.sh(ptt_voice) · functions/api/yeta.js]
//   sess.call = {ts, persona, text, voice}  (voice = 비공개 R2 키 'voice/….mp3' · ''=무음 전화)
//   답장 턴.voice = 무전기 답장 음성 키(텍스트 반영 후 수 초 뒤 부착 — "무전기 수신" 페이스)
//   음성 재생 = POST api/yeta {op:'voice', key}  → audio/mpeg 스트림(동일출처 게이트)
//   무전 STT 폴백 = POST {op:'stt', audio:<base64>} → {text} (Workers AI Whisper · 미설정 501)
//   무전 전송 = {op:'send', text, model:'claude-sonnet-5', effort:'low', ptt:1} — 낮은 모델 = 응답속도(운영자 요구)
//   전화 요청 = {op:'ring'} · 실전화(PSTN) = {op:'phone'} · 보이스톡 공개키 = {op:'vapikey'}
//   보이스톡 = 헤더 수화기(모듈 주입) → 벨 연출 → 받기 → Vapi Web SDK(esm.sh 동적 import) 실시간 통화 —
//     assistant = roster "phone" 재사용(PSTN과 동일 배선) · ⚠️분당 과금 = 2탭 재확인 · 키는 Pages env(Origins 제한 권장)
//
// [소비 규약 — 기틀 CLAUDE.md §🗺]
//   seen = localStorage 'yeta_call_seen'(ts) — call.ts ≤ seen = 무시(기기별 각자 울림 = 자연스러움)
//   신선도 TTL 120s — 지난 call 은 조용히 부재중 처리(대사는 이미 챗 로그에 있음) · 벨 타임아웃 45s
//   자체 폴 20s — 문서 visible + 챗 폴(_yPoll) 비활성일 때만(이중 폴 방지 · 메인 화면에서도 울림)
//   무전 STT = Web Speech(ko-KR·무료·즉시) → 불가 환경(⚠️ iOS 설치형 PWA 실측 260704)은 MediaRecorder→op stt → 그마저 없으면 타이핑
//   벨소리 = WebAudio 합성(에셋 0) — 첫 제스처 후에만 소리(자동재생 정책) · 진동 = 항상 시도
//   답장 음성 자동재생 = WebAudio(제스처로 unlock 된 컨텍스트 = 자동재생 정책 통과) · <audio> 폴백
//
// [디자인 — 절대명령#1 계승] 값 = :root 토큰만(신규 토큰 0) · 컴포넌트 = CII 계승:
//   dialog 결 = #yetadlg(글래스 엣지·::backdrop·모바일 margin:auto 교정) · 아바타/이름/태그 = .yintro-*
//   받기/거절 = .yeta-send 원형 CTA 스펙 계승(크기만 토큰 조합 확대) · 마이크 = .yeta-send 스펙·무채 글래스 플레이트
//   눌림 = --press-m · 파동 링/녹음 점멸 = 키프레임(안무 raw 예외) · 배지 = --r-pill + accent 12%(.dlbtn 결)
//   수화기·마이크·파형 아이콘 = SVG 단일 path(거절 = 같은 path 회전 135° — "같은 의미 = 같은 path")
(() => {
'use strict';
if (typeof window === 'undefined') return;

const SEEN_KEY = 'yeta_call_seen';
const RING_TTL = 120000;      // 이 안에 도착한 call 만 벨(스테일 = 부재중)
const RING_TIMEOUT = 45000;   // 벨 자동 종료(부재중)
const POLL_MS = 20000;        // 자체 폴(챗 폴 비활성 시 백스톱)

const PHONE = 'M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 2 .7 2.9a2 2 0 0 1-.5 2.1L8.1 10a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.5c.9.3 1.9.6 2.9.7a2 2 0 0 1 1.7 2z';
const PHONE_SVG = `<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${PHONE}"/></svg>`;
const MIC_SVG = '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 2a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/><path d="M19 11a7 7 0 0 1-14 0"/><path d="M12 18v4"/></svg>';
const WAVE_SVG = '<svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M4 10v4M8 7v10M12 4v16M16 7v10M20 10v4"/></svg>';

// ── 스타일 주입(토큰만 · 신규 raw = 키프레임 안무·기하 계산·::backdrop[#yetadlg 동값]뿐) ──
const css = `
#calldlg { width:min(420px,96vw); height:min(88dvh,720px); padding:0; border:1px solid var(--glass-line); border-radius:var(--r-modal);
  background:var(--bg); color:var(--fg); overflow:hidden; box-shadow:inset 0 1px 0 var(--glass-line), var(--shadow-card);
  backdrop-filter:none; -webkit-backdrop-filter:none; }   /* 불투명 bg — 전역 dialog blur 상속 낭비 차단(#yetadlg 동형) */
#calldlg::backdrop { background:rgba(0,0,0,.6); }          /* #yetadlg::backdrop 동값 계승 */
@media (max-width:640px) { #calldlg { margin:auto; } }     /* 모바일 좌상단 쏠림 교정(#yetadlg 동형) */
.ycall-wrap { position:relative; height:100%; display:flex; flex-direction:column; align-items:center; justify-content:space-between; padding:var(--sp-3); }
.ycall-bg { position:absolute; inset:0; background-size:cover; background-position:center; }
.ycall-bg::after { content:''; position:absolute; inset:0; background:var(--bg-scrim); }   /* 하단 딤 = 버튼 가독(토큰) */
.ycall-top { position:relative; display:flex; flex-direction:column; align-items:center; gap:6px; padding-top:var(--sp-3); text-align:center; }
.ycall-status { font-size:var(--fs-label); font-weight:var(--fw-b); color:var(--mut); }
.ycall-ava { position:relative; margin:var(--sp-2); display:grid; place-items:center; }
.ycall-ava::before, .ycall-ava::after { content:''; position:absolute; inset:calc(var(--sp-2) * -1);
  border:1px solid rgba(var(--accent-rgb),.55); border-radius:50%; animation:ycallPulse 2s var(--ease) infinite; pointer-events:none; }
.ycall-ava::after { animation-delay:1s; }
#calldlg.talk .ycall-ava::before, #calldlg.talk .ycall-ava::after { animation:none; opacity:0; }
@keyframes ycallPulse { 0% { transform:scale(.92); opacity:.9; } 100% { transform:scale(1.55); opacity:0; } }
@media (prefers-reduced-motion:reduce) { .ycall-ava::before, .ycall-ava::after { animation:none; opacity:0; } }
.ycall-line { position:relative; max-width:34ch; background:var(--glass); border:1px solid var(--glass-line); border-radius:var(--r-l);
  backdrop-filter:blur(var(--blur-m)); -webkit-backdrop-filter:blur(var(--blur-m));
  padding:var(--sp-2); font-size:var(--fs-body); line-height:var(--lh-base); }   /* 통화 자막 = 글래스 카드 */
.ycall-line[hidden] { display:none; }
.ycall-line i.yn { font-style:italic; color:var(--fg-2); opacity:.75; }   /* *지문* 이탤릭 = .yb 결 계승 */
.ycall-btns { position:relative; display:flex; gap:calc(var(--sp-3) * 3); padding-bottom:var(--sp-3); }
.ycall-act { display:flex; flex-direction:column; align-items:center; gap:8px; }
.ycall-act > span { font-size:var(--fs-xs); color:var(--mut); font-weight:var(--fw-b); }
.ycall-btn { width:calc(var(--btn) + var(--sp-3) * 2); height:calc(var(--btn) + var(--sp-3) * 2); border-radius:50%; border:none;
  display:grid; place-items:center; cursor:pointer; touch-action:manipulation; }   /* .yeta-send 원형 CTA 스펙 계승(토큰 조합 확대) */
.ycall-btn:active { transform:scale(var(--press-m,.9)); }
.ycall-btn.take { background:var(--accent); color:var(--bg); }
.ycall-btn.drop { background:var(--danger); color:var(--fg); }
.ycall-btn.drop svg { transform:rotate(135deg); }   /* 거절 = 같은 path 회전(같은 의미 = 같은 path) */
.ycall-act[hidden] { display:none; }
.ycall-mic { flex:none; width:var(--btn); height:var(--btn); align-self:flex-end; border-radius:50%;
  border:none; background:none; color:var(--accent);
  display:grid; place-items:center; cursor:pointer; touch-action:manipulation; }   /* 무전 마이크 = 픽토그램-온리·강조색 라임(운영자 260705 · 도형[글래스 원] 제거) */
.ycall-mic:active { transform:scale(var(--press-m,.9)); }
.ycall-mic svg { width:21px; height:21px; }   /* 픽토 온리라 약간 키움(도형 없는 만큼 존재감) */
.ycall-mic.rec { color:var(--danger); animation:ycallRec 1.2s ease-in-out infinite; }   /* 녹음 = 픽토 danger 점멸(도형 없음) */
@keyframes ycallRec { 0%,100% { opacity:1; } 50% { opacity:.55; } }
@media (prefers-reduced-motion:reduce) { .ycall-mic.rec { animation:none; } }
.yprem { display:inline-flex; align-items:center; gap:4px; margin-left:6px; padding:1px 8px; border-radius:var(--r-pill);
  background:rgba(var(--accent-rgb),.12); border:1px solid rgba(var(--accent-rgb),.4); color:var(--accent);
  font-size:var(--fs-xs); font-weight:var(--fw-b); vertical-align:middle; white-space:nowrap; }   /* 프리미엄(전용 음색) 배지 = accent 10%대 플레이트(.dlbtn 결) */
#yetaCallBtn.armed { color:var(--arm); }   /* 2탭 재확인(통화 = 유료 발동) — .yh-reset.armed 패턴 계승 */
#calldlg.talk .ycall-status { font-variant-numeric:tabular-nums; }   /* 보이스톡 타이머 = tabular(.yb-cap 결) */`;

// ── 상태 ──
let dlg = null, cur = null, ringT = 0, vibT = 0, toneT = 0, audio = null, actx = null;
let vapiSdk = null, vapiInst = null, vapiPub = null, webTick = 0, webSec = 0;   // 보이스톡(Vapi Web SDK — 운영자 목업 이식 260705)
const fmtSec = s => String(s / 60 | 0).padStart(2, '0') + ':' + String(s % 60 | 0).padStart(2, '0');

const seen = () => { try { return +localStorage.getItem(SEEN_KEY) || 0; } catch { return 0; } };
const markSeen = ts => { try { localStorage.setItem(SEEN_KEY, String(Math.max(seen(), +ts || 0))); } catch {} };
const alive = () => typeof yApi === 'function' && typeof esc === 'function';   // 본체 전역 부재 = 모듈 비활성

function ensureCss() {   // 스타일 주입 = 로드 시(입력행 마이크 즉시 스타일) + 콜 생성 시 공용 · 멱등(id 가드) — 옛 버그: ensureDom(콜 때만)에만 있어 마이크가 전화 전까지 기본 버튼(흰 박스)로 렌더됐음(운영자 260705)
  if (document.getElementById('ycallCss')) return;
  const st = document.createElement('style'); st.id = 'ycallCss'; st.textContent = css; document.head.appendChild(st);
}
function ensureDom() {
  if (dlg) return;
  ensureCss();
  dlg = document.createElement('dialog'); dlg.id = 'calldlg'; dlg.setAttribute('aria-label', '걸려오는 전화');
  dlg.innerHTML = `<div class="ycall-wrap">
  <div class="ycall-bg" id="ycallBg" aria-hidden="true"></div>
  <div class="ycall-top">
    <span class="ycall-status" id="ycallStatus"></span>
    <span class="ycall-ava" id="ycallAva"></span>
    <span class="yintro-name" id="ycallName"></span>
    <span class="yintro-tag" id="ycallTag"></span>
  </div>
  <div class="ycall-line" id="ycallLine" hidden></div>
  <div class="ycall-btns">
    <span class="ycall-act"><button type="button" class="ycall-btn drop" id="ycallDrop" aria-label="거절">${PHONE_SVG}</button><span id="ycallDropLbl">거절</span></span>
    <span class="ycall-act" id="ycallTakeWrap"><button type="button" class="ycall-btn take" id="ycallTake" aria-label="받기">${PHONE_SVG}</button><span>받기</span></span>
  </div>
</div>`;
  document.body.appendChild(dlg);
  dlg.querySelector('#ycallTake').addEventListener('click', accept);
  dlg.querySelector('#ycallDrop').addEventListener('click', decline);
  dlg.addEventListener('cancel', e => { e.preventDefault(); decline(); });          // Esc = 거절
  window.addEventListener('popstate', () => { if (dlg.open) decline(); });          // 폰 뒤로가기 = 거절(본체 yetadlg 회수와 병행 무해)
}

// ── 벨 연출(진동 = 항상 시도 · 소리 = WebAudio 합성, 첫 제스처 후에만) ──
document.addEventListener('pointerdown', () => {   // 자동재생 정책 — 제스처 1회로 오디오 컨텍스트 해제
  try { if (!actx) actx = new (window.AudioContext || window.webkitAudioContext)(); if (actx.state === 'suspended') actx.resume(); } catch {}
}, { once: true, capture: true });
function beep(f, at, dur) {
  const o = actx.createOscillator(), g = actx.createGain();
  o.frequency.value = f; o.type = 'sine'; o.connect(g); g.connect(actx.destination);
  g.gain.setValueAtTime(0, at); g.gain.linearRampToValueAtTime(.12, at + .02); g.gain.exponentialRampToValueAtTime(.001, at + dur);
  o.start(at); o.stop(at + dur + .05);
}
function ringFx() {
  const vib = () => { try { navigator.vibrate && navigator.vibrate([500, 250, 500]); } catch {} };
  vib(); vibT = setInterval(vib, 2000);
  const tone = () => { try { if (actx && actx.state === 'running') { const t = actx.currentTime; beep(740, t, .35); beep(880, t + .45, .5); } } catch {} };
  tone(); toneT = setInterval(tone, 2200);
}
function stopFx() {
  clearInterval(vibT); clearInterval(toneT); clearTimeout(ringT); vibT = toneT = ringT = 0;
  try { navigator.vibrate && navigator.vibrate(0); } catch {}
}

// ── 수신 화면 ──
async function open(call) {
  if (!alive() || !call) return;
  ensureDom();
  if (dlg.open && cur && cur.ts === call.ts) return;   // 같은 통화 재진입 = no-op(폴 재트리거 방지)
  cur = call;
  if (typeof YCHARS !== 'undefined' && !YCHARS.length) {   // 메인 화면(챗 미진입)에서 울릴 때 로스터 셀프 로드
    const r = await yApi('chars').catch(() => null);
    if (r && r.ok) YCHARS = r.chars || [];
  }
  const p = (typeof yPersona === 'function' && yPersona(call.persona)) || { name: call.persona || '?', initial: '?' };
  dlg.querySelector('#ycallBg').style.backgroundImage = p.bg ? `url('${p.bg}')` : '';
  dlg.querySelector('#ycallAva').innerHTML = typeof yAva === 'function' ? yAva(p, 'yintro-ava') : '';
  dlg.querySelector('#ycallName').textContent = p.name || '';
  dlg.querySelector('#ycallTag').textContent = p.tagline || '';
  dlg.querySelector('#ycallStatus').innerHTML = '전화가 오고 있어<span class="gdots"><i>.</i><i>.</i><i>.</i></span>';   // gdots = 본체 점 애니 계승
  dlg.querySelector('#ycallLine').hidden = true;
  dlg.querySelector('#ycallTakeWrap').hidden = false;
  dlg.querySelector('#ycallDropLbl').textContent = '거절';
  dlg.classList.remove('talk');
  if (!dlg.open) dlg.showModal();
  stopFx(); ringFx();
  if (call.web) vapiPreload();   // 보이스톡 = 벨 우는 동안 키+SDK 미리 로드(받기 탭 순간 iOS 제스처 소실 회피 = 핵심)
  ringT = setTimeout(() => { if (dlg.open && !dlg.classList.contains('talk')) decline(); }, RING_TIMEOUT);   // 부재중
}
// ── 음성 재생 유틸(공용) — WebAudio 우선(제스처로 unlock 된 actx = 무전 답장 *자동*재생 허용) · <audio> 폴백 ──
let srcNode = null;
async function fetchVoiceBuf(key) {
  try {
    const r = await fetch('api/yeta', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ op: 'voice', key }) });
    if (r.ok && (r.headers.get('content-type') || '').includes('audio')) return await r.arrayBuffer();
  } catch {}
  return null;
}
function stopVoice() {
  if (srcNode) { try { srcNode.onended = null; srcNode.stop(); } catch {} srcNode = null; }
  if (audio) { try { audio.pause(); } catch {} audio = null; }
}
async function playVoice(key, onended) {
  const buf = await fetchVoiceBuf(key);
  if (!buf) return false;
  try {
    if (actx && actx.state === 'running') {
      const ab = await actx.decodeAudioData(buf.slice(0));
      stopVoice();
      srcNode = actx.createBufferSource(); srcNode.buffer = ab; srcNode.connect(actx.destination);
      srcNode.onended = () => { srcNode = null; onended && onended(); };
      srcNode.start(); return true;
    }
  } catch {}
  try {   // 폴백 — 제스처 문맥(전화 받기 탭)에서는 <audio> 재생 허용
    stopVoice();
    audio = new Audio(URL.createObjectURL(new Blob([buf], { type: 'audio/mpeg' })));
    if (onended) audio.addEventListener('ended', onended);
    await audio.play(); return true;
  } catch {}
  return false;
}

function closeDlg() {
  stopFx(); stopVoice();
  clearInterval(webTick); webTick = 0;
  if (vapiInst) { try { vapiInst.stop(); } catch {} vapiInst = null; }   // 보이스톡 세션 종료(과금 차단)
  cur = null; if (dlg && dlg.open) dlg.close();
}
function decline() { if (cur && cur.ts && !cur.web) markSeen(cur.ts); closeDlg(); }

// ── 보이스톡(브라우저 실시간 통화) — Vapi Web SDK · 벨 우는 동안 프리로드(iOS 제스처 소실 회피) · 운영자 목업 이식 ──
let vapiPreloading = null;
function vapiPreload() {   // 벨 시점 = 키 fetch + SDK import 백그라운드 완료(받기 탭 땐 await 0 = 제스처 안에서 마이크 즉시)
  if (vapiPreloading) return vapiPreloading;
  vapiPreloading = (async () => {
    try {
      if (!vapiPub) { const r = await yApi('vapikey').catch(() => null); if (r && r.ok && r.pub) vapiPub = r.pub; }
      if (!vapiSdk) vapiSdk = (await import('https://esm.sh/@vapi-ai/web')).default;
    } catch {}
  })();
  return vapiPreloading;
}
async function webAccept(call) {
  const st = dlg.querySelector('#ycallStatus');
  let stage = 'load', ended = false;
  const fail = m => { if (ended) return; ended = true; st.textContent = '연결 실패 — ' + m; setTimeout(closeDlg, 3000); };
  const guard = setTimeout(() => fail(stage === 'mic' ? '마이크 권한을 확인해줘' : '응답 없음(네트워크·권한 확인)'), 20000);   // 무한 '연결 중' 차단
  try {
    // ① 마이크 먼저 — 받기 탭 제스처 안에서 동기적으로 잡아야 iOS 가 hang 안 함(제스처 소실 방지의 핵심)
    stage = 'mic'; st.textContent = '마이크 여는 중…';
    try { const ms = await navigator.mediaDevices.getUserMedia({ audio: true }); ms.getTracks().forEach(t => t.stop()); }
    catch { clearTimeout(guard); return fail('마이크 권한이 필요해 — 브라우저 설정에서 허용'); }
    // ② 키·SDK — 벨 때 프리로드됐으면 즉시 완료
    stage = 'sdk'; st.textContent = '연결 중…';
    await vapiPreload();
    if (!vapiPub) { clearTimeout(guard); return fail('보이스톡 미설정(VAPI_PUBLIC_KEY)'); }
    if (!vapiSdk) { clearTimeout(guard); return fail('음성 모듈 로드 실패'); }
    // ③ 통화 시작
    stage = 'start';
    vapiInst = new vapiSdk(vapiPub);
    vapiInst.on('call-start', () => { clearTimeout(guard); ended = true; webSec = 0; clearInterval(webTick); webTick = setInterval(() => { st.textContent = fmtSec(++webSec); }, 1000); });
    vapiInst.on('speech-start', () => { if (webTick) st.textContent = fmtSec(webSec) + ' · 말하는 중…'; });
    vapiInst.on('speech-end', () => { if (webTick) st.textContent = fmtSec(webSec); });
    vapiInst.on('call-end', () => closeDlg());
    vapiInst.on('error', e => { clearTimeout(guard); fail((e && (e.errorMsg || e.error || e.message)) || '연결 오류'); });
    await vapiInst.start(call.assistant);
  } catch (e) {
    clearTimeout(guard); fail((e && e.message) || '알 수 없는 오류');
  }
}

async function accept() {
  if (!cur) return closeDlg();
  const call = cur;
  stopFx();
  dlg.classList.add('talk');
  dlg.querySelector('#ycallStatus').textContent = '통화 중';
  dlg.querySelector('#ycallTakeWrap').hidden = true;
  dlg.querySelector('#ycallDropLbl').textContent = '끊기';
  const line = dlg.querySelector('#ycallLine');
  if (call.web) { line.hidden = true; return webAccept(call); }   // 보이스톡 = 실시간 대화(자막·mp3 없음)
  markSeen(call.ts);
  line.innerHTML = typeof yFmt === 'function' ? yFmt(call.text || '') : esc(call.text || '');   // 자막(무음 전화 폴백 겸용)
  line.hidden = !call.text;
  const played = call.voice ? await playVoice(call.voice, () => setTimeout(closeDlg, 1200)) : false;   // 받기 탭 = 제스처(재생 허용)
  if (!played) setTimeout(() => { if (dlg.classList.contains('talk')) closeDlg(); }, 5000);   // 무음 전화 = 자막 5초 후 종료(대사는 챗에 남음)
}

// ── 무전기(PTT) — 마이크 버튼을 입력행에 *주입*(본체 마크업 무수정) · Web Speech → 서버 STT → 타이핑 3단 폴백 ──
const PTT_DIAL = { model: 'claude-sonnet-5', effort: 'low' };   // 낮은 모델 = 응답속도 우선(운영자 요구⑥ · 웜 루프 후속턴 ~10~20s = "무전기 수신" 페이스)
let pttPending = false, lastVoiceTs = Date.now(), voiceWait = 0;
let recOnFlag = false, sr = null, rec = null, recT = 0;
const toast = m => { try { typeof miniToast === 'function' ? miniToast(m) : console.warn(m); } catch {} };

function initPtt() {
  const row = document.querySelector('#yetaIn');
  if (!row || document.querySelector('#yetaMic')) return;
  const b = document.createElement('button');
  b.type = 'button'; b.id = 'yetaMic'; b.className = 'ycall-mic';
  b.setAttribute('aria-label', '무전 — 탭해서 말하기(끝나면 자동 전송)'); b.title = '무전';
  b.innerHTML = MIC_SVG;
  row.insertBefore(b, row.firstChild);
  b.addEventListener('click', () => { recOnFlag ? pttStop() : pttStart(); });
}
function recUi(on, hint) {
  recOnFlag = on;
  const b = document.querySelector('#yetaMic'), ta = document.querySelector('#yetaText');
  if (b) b.classList.toggle('rec', on);
  if (ta) ta.placeholder = on ? (hint || '듣는 중…') : '메시지';
}
function pttStart() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const ta = document.querySelector('#yetaText');
  if (SR) {   // 1순위 = 기기 내장 인식(무료·즉시 · ko-KR)
    try {
      sr = new SR(); sr.lang = 'ko-KR'; sr.interimResults = true; sr.continuous = false;
      let fin = '';
      sr.onresult = e => { let s = ''; for (const res of e.results) { s += res[0].transcript; if (res.isFinal) fin = s; } if (ta) ta.value = s; };
      sr.onerror = ev => { recUi(false); if (ev && ev.error === 'not-allowed') toast('마이크 권한을 허용해줘'); };
      sr.onend = () => { recUi(false); const t = (fin || (ta && ta.value) || '').trim(); sr = null; if (t) pttSend(t); };
      sr.start(); recUi(true, '듣는 중… 말이 끝나면 자동 전송'); return;
    } catch { sr = null; }
  }
  recStart();   // 2순위 = 녹음 → 서버 STT(op stt · iOS 설치형 PWA — Web Speech 불가 실측 260704)
}
function recStart() {
  if (!navigator.mediaDevices || !window.MediaRecorder) { toast('이 기기는 음성 인식 미지원 — 입력해줘'); return; }
  navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
    const chunks = [];
    rec = new MediaRecorder(stream);
    rec.ondataavailable = e => { if (e.data && e.data.size) chunks.push(e.data); };
    rec.onstop = async () => {
      stream.getTracks().forEach(t => t.stop()); recUi(false); clearTimeout(recT);
      const blob = new Blob(chunks, { type: rec.mimeType || 'audio/webm' }); rec = null;
      if (blob.size < 1200) return;                       // 빈 탭(실수) 무시
      if (blob.size > 1000000) { toast('너무 길어 — 30초 안으로 말해줘'); return; }
      const b64 = await new Promise(res => { const fr = new FileReader(); fr.onload = () => res(String(fr.result).split(',')[1] || ''); fr.readAsDataURL(blob); });
      const r = await yApi('stt', { audio: b64 }).catch(() => null);
      if (r && r.ok && r.text) pttSend(r.text);
      else if (r && r.setup) toast('서버 음성 인식 미설정(AI 바인딩) — 일단 입력해줘');
      else toast((r && r.error) || '못 알아들었어 — 다시');
    };
    rec.start(); recUi(true, '녹음 중 — 다시 탭하면 보냄');
    recT = setTimeout(() => pttStop(), 30000);            // 무전 = 짧은 발화(서버 상한과 짝)
  }).catch(() => toast('마이크를 못 열었어 — 권한 확인'));
}
function pttStop() { try { if (sr) { sr.stop(); return; } } catch {} try { if (rec && rec.state !== 'inactive') rec.stop(); } catch {} recUi(false); }
async function pttSend(text) {
  const ta = document.querySelector('#yetaText'); if (ta) ta.value = '';
  pttPending = true; voiceWait = 0;
  const r = await yApi('send', { text, model: PTT_DIAL.model, effort: PTT_DIAL.effort, ptt: 1 }).catch(() => null);
  if (!r || !r.ok) { pttPending = false; toast((r && r.error) || '무전 전송 실패'); if (ta) ta.value = text; return; }
  if (typeof yLoad === 'function') yLoad();               // 내 턴 즉시 반영(낙관 버블 대신 확정 렌더 — 이미 R2 반영됨)
  if (typeof yStartPoll === 'function') yStartPoll();
}
function checkReplyVoice(sess) {   // 무전 답장 음성 자동재생 — 텍스트 먼저, 음성 키(turn.voice)는 수 초 뒤 부착
  if (!pttPending) return;
  const turns = (sess && sess.turns) || [];
  for (let i = turns.length - 1; i >= 0; i--) {
    const t = turns[i];
    if (t.role === 'user') return;                        // 아직 답장 전(sys 는 스킵하고 계속)
    if (t.role !== 'assistant') continue;
    if (t.voice && t.ts > lastVoiceTs) { lastVoiceTs = t.ts; pttPending = false; playVoice(t.voice); return; }
    // 답장 텍스트는 왔는데 음성 미부착 — 챗 폴은 idle 로 멈추므로 모듈이 짧게 재확인(최대 ~30s)
    if (!t.voice && voiceWait < 12) {
      voiceWait += 1;
      setTimeout(async () => { const r = await yApi('get').catch(() => null); if (r && r.ok) checkReplyVoice(r.sess); }, 2500);
    } else if (voiceWait >= 12) { pttPending = false; }   // 음성 실패(fail-soft) = 텍스트만으로 종료
    return;
  }
}

// ── 프리미엄(전용 음색) 배지 — 본체 템플릿 훅(③): 이름 옆 `yPremBadge(c)` · 모듈 제거 시 자동 소멸 ──
window.yPremBadge = c => (c && c.voice) ? `<span class="yprem" title="전용 음색(프리미엄)">${WAVE_SVG}보이스</span>` : '';

// ── 헤더 수화기 버튼(모듈 주입 · 본체 무수정) ──
// 정책(260705 실측 결정): phone 배선 캐릭터 = **실전화(op phone)** 발신 = 네 폰이 울림.
//   근거 = Vapi 통화 로그 실측: outboundPhoneCall = 정상 대화(transcript 있음·클론 음색) /
//          webCall(보이스톡) = 'assistant-did-not-receive-customer-audio'(모바일 WebRTC 오디오 미전달) 반복 실패.
//   → 흔들리는 브라우저 통화 대신 증명된 PSTN 로. 보이스톡(open web:1)은 코드 잔존하나 버튼 기본 경로에서 제외.
//   phone 미배선 캐릭터 = op ring 폴백(인앱 걸려오는 전화·첫마디 TTS).
let callArm = 0, callArmT = 0;
function initCallBtn() {
  const hr = document.querySelector('#yetadlg .yh-r');
  if (!hr || document.querySelector('#yetaCallBtn')) return;
  const b = document.createElement('button');
  b.type = 'button'; b.id = 'yetaCallBtn'; b.className = 'tool-x';   // 헤더 아이콘 버튼 = .tool-x 정본 계승(CII)
  b.setAttribute('aria-label', '통화'); b.title = '통화';
  b.innerHTML = `<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="${PHONE}"/></svg>`;
  hr.insertBefore(b, hr.firstChild);
  b.addEventListener('click', async () => {
    const pid = (typeof YSESS !== 'undefined' && YSESS && YSESS.persona) || '';
    const p = (typeof yPersona === 'function' && yPersona(pid)) || {};
    const real = !!p.phone;
    if (!callArm) {   // 1탭 = 무장(유료 발동 실수 방지 — yh-reset 2탭 패턴)
      callArm = 1; b.classList.add('armed');
      toast(real ? '한 번 더 누르면 내 폰으로 전화가 와(유료)' : '한 번 더 누르면 전화 요청(유료)');
      clearTimeout(callArmT); callArmT = setTimeout(() => { callArm = 0; b.classList.remove('armed'); }, 2600);
      return;
    }
    callArm = 0; b.classList.remove('armed'); clearTimeout(callArmT);
    if (real) {   // 실전화 — 등록된 내 번호로 발신(Vapi 아웃바운드 · 로그 실측 정상)
      toast('📞 곧 전화가 울려 — 받으면 통화돼');
      const r = await yApi('phone').catch(() => null);
      if (!(r && r.ok)) toast((r && r.error) || '전화 발신 실패');
      return;
    }
    toast('📞 전화 요청 — 준비되면 앱에서 울려(30초쯤)');   // 배선 없는 캐릭터 = 인앱 걸려오는 전화(첫마디 TTS)
    const r = await yApi('ring').catch(() => null);
    if (!(r && r.ok)) toast((r && r.error) || '전화 요청 실패');
  });
}

// ── 감지 — 본체 yLoad 훅(①) + 자체 백스톱 폴(챗 폴 비활성·visible 시만) ──
function onSess(sess) {
  if (!alive()) return;
  checkReplyVoice(sess);
  const call = sess && sess.call;
  if (!call || !call.ts || call.ts <= seen()) return;
  if (Date.now() - call.ts > RING_TTL) { markSeen(call.ts); return; }   // 스테일 = 부재중(대사는 챗 로그에)
  open(call);
}
async function check() {
  if (!alive() || document.visibilityState !== 'visible') return;
  if (typeof _yPoll !== 'undefined' && _yPoll) return;   // 챗 적응형 폴이 도는 중 = yLoad 훅이 감지(이중 폴 방지)
  const r = await yApi('get').catch(() => null);
  if (r && r.ok && r.sess) onSess(r.sess);
}
setInterval(check, POLL_MS);
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') setTimeout(check, 600); });   // 푸시 탭 복귀 = 즉시 픽업
setTimeout(check, 1500);   // 첫 로드(딥링크 /?yeta=main&call=1 포함) — 기존 ?yeta= 오픈에 편승 + 벨은 여기서
const initInject = () => { ensureCss(); initPtt(); initCallBtn(); };   // 스타일 주입 먼저(마이크 즉시 스타일) + 입력행 마이크 + 헤더 수화기(둘 다 모듈 주입 = 본체 무수정)
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initInject); else initInject();

window.YCALL = { onSess, open, playVoice };   // open/playVoice = 테스트 훅 · onSess = 본체 yLoad 훅 계약
})();
