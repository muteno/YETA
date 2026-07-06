// Cloudflare Pages Function — yeta 캐릭터 챗 게이트웨이 (260703 v2 · 랜덤 페르소나 + 다이얼 + 프리웜)
// 세션 = 단일 스레드 sessions/main.json (대화 맥락 공유 · 페르소나는 sess.persona 로 랜덤 뽑기/재뽑기).
// ops(POST 단일 — 폴링도 POST = originOk 대칭):
//   chars {}                       : 페르소나 로스터(apps/yeta/characters/roster.json raw · 5분 캐시)
//   get   {}                       : 세션 반환(뷰어 폴)
//   send  {text, model, effort}    : 유저 턴 append(다이얼 턴별 박제 · 화이트리스트) → yeta-chat.yml dispatch
//   draw  {persona, name}          : 페르소나 뽑기/재뽑기 — sess.persona 갱신(+대화 중이면 sys 턴)
//   warm  {}                       : 프리웜 — dispatch만(러너 선부팅 → 첫 답장 30초 목표 · 쿼터 소비 0[NOPENDING 웜대기])
//   retry {}                       : 원탭 재시도 — 실패(state=error) pending 유저 턴 재발사(새 턴 추가 X)
//   ring  {persona?}               : 걸려오는 전화 요청 → yeta-call.yml dispatch(⚠️ TTS 유료 → 일 상한 기본 3 · YETA_CALL_MAX_PER_DAY)
//   voice {key}                    : 통화 음성 스트림 — 비공개 버킷 voice/ 만(대사=대화 내용 → 공개 버킷 금지 · 동일출처 게이트)
//   stt   {audio}                  : 무전기 STT 폴백(base64 webm/ogg → 텍스트) — iOS 설치형 PWA 는 Web Speech 불가(실측 260704)
//                                    → Workers AI Whisper(env.AI 바인딩 게이트 · 미설정 501 = 뷰어가 타이핑 폴백 안내)
//   phone {}                       : ☎️ 실전화(PSTN·Vapi) 스캐폴드 — 등록 번호로 실제 발신(⚠️분당 과금 · env 3종 게이트 · 일 상한 기본 2)
//   vapikey {}                     : 보이스톡(브라우저 통화 · Vapi Web SDK) 공개키 — env VAPI_PUBLIC_KEY(공개 축 · Origins 제한 권장)
//   reset {}                       : 세션 초기화(페르소나도 비움 → 다음 진입 시 재뽑기)
// 저장 = R2 비공개 버킷 바인딩 env.YETA_R2 (⚠️ 대화는 public 레포 커밋 절대 금지 — 계획안 D2).
// 게이트: Cloudflare Access(도메인 전체 자동 계승) + originOk(CSRF) + 일 상한 = D4 무제한(env YETA_MAX_PER_DAY 양수로만 발동).
// env: GH_TOKEN(Actions write) · YETA_R2(R2 바인딩) · YETA_MAX_PER_DAY(선택) · YETA_CALL_MAX_PER_DAY(선택·기본 3 — 유료 TTS 가드)
//      AI(선택 · Workers AI 바인딩 = op stt) · VAPI_API_KEY+VAPI_PHONE_ID+YETA_PHONE_TO(선택 3종 = op phone · 번호는 시크릿 — 코드 박제 금지)
//      YETA_PHONE_MAX_PER_DAY(선택·기본 2 — 실전화 분당 과금 가드).
const REPO = 'muteno/yeta';
const ID_RE = /^[a-z0-9_-]{1,24}$/;
const KEY = 'sessions/main.json';
const MODELS = new Set(['claude-opus-4-8', 'claude-sonnet-5']);          // §기틀 정확 ID — 집합 확장은 운영자 확인
const EFFORTS = new Set(['', 'low', 'medium', 'high', 'max']);           // '' = --effort 생략(CLI 기본)

export async function onRequestPost({ request, env }) {
  const json = (o, s = 200) =>
    new Response(JSON.stringify(o), { status: s >= 500 ? 424 : s, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });
  // ⚠️ 5xx → 424 강등: 커스텀 도메인(soong.kr 존)이 5xx 응답을 자체 에러 페이지("error code: 502")로 덮어
  //    게이트웨이 JSON 에러 사유가 유저에게 소실됨(실측 — pages.dev는 JSON 통과·soong.kr은 생 502).
  //    뷰어(yApi)는 HTTP 코드가 아니라 JSON error/ok/setup 필드만 판독 = 코드 강등 무영향(4xx는 존이 안 덮음).

  if (!originOk(request)) return json({ error: '허용되지 않은 출처' }, 403);
  let body;
  try { body = await request.json(); } catch { return json({ error: '잘못된 요청' }, 400); }
  const op = String(body.op || '');

  // 로스터는 R2 불필요(레포 raw) — 셋업 전에도 목록·안내를 그릴 수 있게 R2 가드보다 앞.
  if (op === 'chars') {
    const r = await fetch(`https://raw.githubusercontent.com/${REPO}/main/apps/yeta/characters/roster.json`,
      { headers: { 'user-agent': 'nomute-viewer' }, cf: { cacheTtl: 60, cacheEverything: true } });
    if (!r.ok) return json({ error: `로스터 로드 실패(${r.status})` }, 502);
    let world = null;   // 시즌제 세계관(운영자 260706 롤토체스식 — 성격 불변·역할군 리스킨) — 실패는 비치명(헤더만 생략)
    try {
      const w = await fetch(`https://raw.githubusercontent.com/${REPO}/main/apps/yeta/worlds.json`,
        { headers: { 'user-agent': 'nomute-viewer' }, cf: { cacheTtl: 60, cacheEverything: true } });
      if (w.ok) { const j = await w.json(); world = (j.seasons || []).find(s => s.id === j.active) || null; }
    } catch {}
    return json({ ok: true, chars: await r.json(), world, ready: !!env.YETA_R2 });
  }

  if (op === 'vapikey') {   // 보이스톡(브라우저 실시간 통화 · Vapi Web SDK) 공개키 — PUBLIC key = 클라이언트 설계상 공개 가능 축.
    // ⚠️ 남용 가드는 Vapi 대시보드에서: 이 Public key 의 Origins 를 yeta.soong.kr 로 제한 권장(기본 All domains = 아무 사이트나 통화 과금 가능).
    if (!env.VAPI_PUBLIC_KEY) return json({ error: '보이스톡 미설정 — Pages env VAPI_PUBLIC_KEY 필요', setup: true }, 501);
    return json({ ok: true, pub: env.VAPI_PUBLIC_KEY });
  }

  // 프리웜 — 세션·R2 안 건드리고 워크플로만 선기동(빈 런은 NOPENDING 웜대기 = 다음 메시지 즉답 준비).
  if (op === 'warm') {
    if (!env.GH_TOKEN || !env.YETA_R2) return json({ ok: false });   // 미설정이면 조용히 무시(비치명)
    const r = await dispatch(env);
    return json({ ok: r === 204 });
  }

  if (!env.YETA_R2) return json({ error: '미설정 — Pages R2 바인딩(YETA_R2 · 비공개 버킷) 필요', setup: true }, 501);

  const readSess = async () => {
    const o = await env.YETA_R2.get(KEY);
    if (!o) return { turns: [], note: '', state: 'idle' };
    try { return await o.json(); } catch { return { turns: [], note: '', state: 'idle' }; }
  };
  const putSess = (s) => env.YETA_R2.put(KEY, JSON.stringify(s), { httpMetadata: { contentType: 'application/json' } });

  if (op === 'get') return json({ ok: true, sess: await readSess() });

  if (op === 'voice') {   // 통화 음성 스트림(걸려오는 전화 v1) — 비공개 세션 버킷 voice/ 프리픽스만 · POST 유지(originOk 대칭)
    const key = String(body.key || '');
    if (!/^voice\/[a-z0-9_-]+\.mp3$/.test(key)) return json({ error: '잘못된 음성 키' }, 400);
    const o = await env.YETA_R2.get(key);
    if (!o) return json({ error: '음성 없음' }, 404);
    return new Response(o.body, { headers: { 'content-type': 'audio/mpeg', 'cache-control': 'private, max-age=3600' } });   // 같은 통화 재청취 = 재다운로드 방지(비공개 캐시만)
  }

  if (op === 'stt') {   // 무전기 STT 폴백 — Web Speech 불가 환경(iOS 설치형 PWA). Workers AI Whisper(무료 티어 넉넉 · env.AI 미바인딩 = 501)
    if (!env.AI) return json({ error: 'STT 미설정 — Pages Functions AI 바인딩(env.AI) 필요', setup: true }, 501);
    const b64 = String(body.audio || '');
    if (!b64 || b64.length > 1400000) return json({ error: '음성이 없거나 너무 길어(최대 ~1MB·30초)' }, 400);   // 무전기 = 짧은 발화 전제
    try {
      const model = env.YETA_STT_MODEL || '@cf/openai/whisper-large-v3-turbo';   // 입력 규격 변화 대비 env 노브
      const r = await env.AI.run(model, { audio: b64 });                          // turbo = base64 입력·한국어 지원
      const text = String((r && (r.text || (r.result && r.result.text))) || '').trim();
      if (!text) return json({ error: '못 알아들었어 — 다시 말해줘' }, 422);
      return json({ ok: true, text });
    } catch (e) {
      return json({ error: 'STT 실패 — 잠시 후 다시' }, 502);
    }
  }

  if (op === 'calllog') {   // 🩺 진단 — 최근 Vapi 통화 *메타데이터만* 서버측 조회(무음/실패 원인 자가진단 · CLAUDE.md §운영 태도 g)).
    // ⚠️ 무인증 공개 게이트웨이(originOk=CSRF만) → **대화/통화 transcript·PII 반환 금지**(§📰·§운영 태도 g) 바) — 노출 시 대화 유출).
    //    반환 = 상태·종료사유·타입·시각·비용·메시지 건수뿐(원인 판정에 필요한 최소 메타).
    if (!env.VAPI_API_KEY) return json({ error: 'VAPI_API_KEY 필요', setup: true }, 501);
    let r, arr;
    try {
      r = await fetch('https://api.vapi.ai/call?limit=5', { headers: { authorization: `Bearer ${env.VAPI_API_KEY}` } });
      arr = await r.json();
    } catch (e) { return json({ error: `Vapi 조회 실패 — ${String(e).slice(0, 120)}` }, 502); }
    if (!r.ok) return json({ error: `Vapi ${r.status}` }, 502);   // 원문 바디 미노출(에러에도 민감정보 새지 않게)
    const calls = (Array.isArray(arr) ? arr : []).map(c => ({
      id: c.id, status: c.status, endedReason: c.endedReason, type: c.type,
      created: c.createdAt, ended: c.endedAt, cost: c.cost,
      msgs: Array.isArray(c.messages) ? c.messages.length : 0,   // 건수만(내용 X)
    }));
    return json({ ok: true, calls });
  }

  if (op === 'phone') {   // ☎️ 실전화(PSTN) — Vapi 아웃바운드(등록 번호 발신 · 실시간 대화 ~1초대 = 전화 판정 통과 축).
    // ⚠️ 분당 과금(실질 $0.15~0.35/분 · Twilio KR 모바일 $0.052/분 포함) + 별도 유료 인프라(구독 OAuth 밖) →
    //    env 3종(VAPI_API_KEY·VAPI_PHONE_ID·YETA_PHONE_TO) 전부 있어야 활성 · 페르소나별 Vapi assistant id = roster "phone" 필드.
    if (!env.VAPI_API_KEY || !env.VAPI_PHONE_ID || !env.YETA_PHONE_TO)
      return json({ error: '실전화 미설정 — VAPI_API_KEY·VAPI_PHONE_ID·YETA_PHONE_TO 시크릿 필요(CLAUDE.md §🗺 yeta-call)', setup: true }, 501);
    const pcap0 = parseInt(env.YETA_PHONE_MAX_PER_DAY ?? '2', 10);
    const pcap = Number.isFinite(pcap0) ? pcap0 : 2;   // 빈값·오타 = 보수 기본 2(분당 과금 가드)
    const pkst = new Date(Date.now() + 9 * 3600e3).toISOString().slice(2, 10).replace(/-/g, '');
    const pqkey = `quota/phone-${pkst}.json`;
    let pused = 0;
    const pqo = await env.YETA_R2.get(pqkey);
    if (pqo) { try { pused = (await pqo.json()).n || 0; } catch { pused = 0; } }
    if (pcap > 0 && pused >= pcap) return json({ error: `오늘 전화 상한(${pcap}통) 도달 — 내일 다시`, remain: 0 }, 429);
    const sessP = await readSess();
    const persona = String(sessP.persona || '');
    const rc = await fetch(`https://raw.githubusercontent.com/${REPO}/main/apps/yeta/characters/roster.json`,
      { headers: { 'user-agent': 'nomute-viewer' }, cf: { cacheTtl: 300, cacheEverything: true } });
    if (!rc.ok) return json({ error: '로스터 로드 실패' }, 502);
    let roster;
    try { roster = await rc.json(); } catch { return json({ error: '로스터 파싱 실패(raw)' }, 502); }
    const ch = Array.isArray(roster) ? roster.find(c => c.id === persona) : null;
    if (!ch || !ch.phone) return json({ error: '이 캐릭터는 아직 전화 미지원 — 프리미엄(전용 음색+phone 등재) 캐릭터만' }, 409);
    // Vapi 아웃바운드 — 예외/에러바디 방어(미방어 시 Function throw = Cloudflare 생 502 자폭 · 국제발신 차단 사유도 여기서 노출)
    let vr, vbody;
    try {
      vr = await fetch('https://api.vapi.ai/call', {
        method: 'POST',
        headers: { authorization: `Bearer ${env.VAPI_API_KEY}`, 'content-type': 'application/json' },
        body: JSON.stringify({ assistantId: ch.phone, phoneNumberId: env.VAPI_PHONE_ID, customer: { number: env.YETA_PHONE_TO } }),
      });
      vbody = await vr.text();
    } catch (e) {
      return json({ error: `Vapi 연결 실패 — ${String(e).slice(0, 120)}` }, 502);
    }
    if (vr.ok) {
      await env.YETA_R2.put(pqkey, JSON.stringify({ n: pused + 1 }), { httpMetadata: { contentType: 'application/json' } });   // 성공분만 카운트(실패=쿼터 소모 0)
      return json({ ok: true, remain: pcap > 0 ? pcap - pused - 1 : -1 });
    }
    let vmsg = vbody || '';
    try { const j = JSON.parse(vbody); vmsg = Array.isArray(j.message) ? j.message.join(' · ') : (j.message || j.error || vbody); } catch {}
    return json({ error: `전화 발신 실패(Vapi ${vr.status}): ${String(vmsg).slice(0, 300)}` }, 502);
  }

  if (op === 'ring') {   // 전화 걸어달라(수신 UI·테스트 훅) → yeta-call.yml dispatch. ⚠️ TTS 유료 종량제 + 무인증 공개 사이트 → 일 상한 기본 3(보수 기본)
    if (!env.GH_TOKEN) return json({ error: '서버 미설정 — GH_TOKEN 필요' }, 500);
    const persona = String(body.persona || '');
    if (persona && !ID_RE.test(persona)) return json({ error: '잘못된 페르소나 id' }, 400);
    let cap = parseInt(env.YETA_CALL_MAX_PER_DAY ?? '3', 10);
    if (!Number.isFinite(cap)) cap = 3;   // 미설정·빈값·오타 = 보수 기본 3(유료 가드가 조용히 풀리는 구멍 차단 · 0 = 명시적 무제한)
    const kst = new Date(Date.now() + 9 * 3600e3).toISOString().slice(2, 10).replace(/-/g, '');
    const qkey = `quota/call-${kst}.json`;
    let used = 0;
    const qo = await env.YETA_R2.get(qkey);
    if (qo) { try { used = (await qo.json()).n || 0; } catch { used = 0; } }
    if (cap > 0 && used >= cap) return json({ error: `오늘 통화 상한(${cap}통) 도달 — 내일 다시`, remain: 0 }, 429);
    await env.YETA_R2.put(qkey, JSON.stringify({ n: used + 1 }), { httpMetadata: { contentType: 'application/json' } });
    const st = await dispatch(env, 'yeta-call.yml', persona ? { persona } : {});
    if (st === 204) return json({ ok: true, remain: cap > 0 ? cap - used - 1 : -1 });
    return json({ error: `GitHub dispatch ${st}` }, 502);
  }

  if (op === 'auth') {   // PIN 로그인(운영자 260706 권한 2계층) — admin = Pages env YETA_PIN_ADMIN(레포 무노출·서버 강제) · guest = apps/yeta/users.json(깃 SSOT — 사용자 추가 = 커밋). 반환 = 역할뿐(민감필드 0)
    const pin = String(body.pin || '');
    if (!/^\d{4,8}$/.test(pin)) return json({ ok: false });
    const APIN = String(env.YETA_PIN_ADMIN || '');
    if (APIN && pin === APIN) return json({ ok: true, role: 'admin', name: '운영자' });
    try {   // users.json 대조 — pin_h = sha256('<PIN>:yeta') (뷰어 잠금 해시 규약과 동일)
      const u = await fetch(`https://raw.githubusercontent.com/${REPO}/main/apps/yeta/users.json`,
        { headers: { 'user-agent': 'nomute-viewer' }, cf: { cacheTtl: 60, cacheEverything: true } });
      if (u.ok) {
        const db = await u.json();
        const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(`${pin}:yeta`));
        const h = [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');
        const hit = (db.users || []).find(x => x && x.pin_h === h);
        if (hit) return json({ ok: true, role: hit.role === 'admin' ? 'guest' : String(hit.role || 'guest'), name: String(hit.name || '') });   // users.json의 admin 참칭 차단 — admin은 env 단일 경로
      }
    } catch {}
    return json({ ok: false });
  }

  if (op === 'policy') {   // 3계층 정책(운영자 260706) — GET(정의+현재값 · 무인증) / SET(L0 토글+L1 축 = 관리자 PIN 필수 · enum 정수만 = 프롬프트 주입 원천 차단 · 라벨/문구 정본 = apps/yeta/policy.json, 러너가 직접 읽음)
    const sess = await readSess();
    if (body.p !== undefined) {   // SET — admin 가드 → {key: 0~2} 객체만 · key 화이트폼 · 최대 8축
      const APIN = String(env.YETA_PIN_ADMIN || '');
      if (!APIN) return json({ error: '관리자 PIN 미설정 — Cloudflare Pages env YETA_PIN_ADMIN 필요' }, 501);
      if (String(body.pin || '') !== APIN) return json({ error: '권한 없음 — 관리자 PIN 필요' }, 403);
      const raw = body.p;
      if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return json({ error: '정책은 {key:0~2} 객체' }, 400);
      const p = {};
      for (const [k, v] of Object.entries(raw)) {
        if (Object.keys(p).length >= 8) break;   // 8축 캡 도달 = 조기 종료(초대형 페이로드 전량 순회 컷 · 기틀검증 보안 권고)
        if (!/^[a-z]{1,16}$/.test(k)) continue;
        p[k] = Math.max(0, Math.min(2, Math.round(Number(v) || 0)));
      }
      sess.policy = p; sess.updated = Date.now();
      await putSess(sess);
      return json({ ok: true, p });
    }
    let def = null;   // GET — 정의(policy.json raw)+세션 현재값. 뷰어 설정 탭이 이걸로 렌더 = 축·라벨·문구 전부 문서 의존(뷰어 하드코딩 0)
    try {
      const d = await fetch(`https://raw.githubusercontent.com/${REPO}/main/apps/yeta/policy.json`,
        { headers: { 'user-agent': 'nomute-viewer' }, cf: { cacheTtl: 60, cacheEverything: true } });
      if (d.ok) def = await d.json();
    } catch {}
    if (!def) return json({ error: '정책 정의 로드 실패' }, 502);
    return json({ ok: true, def, p: sess.policy || {} });
  }

  if (op === 'tune') {   // 캐릭터별 성향 게이지(16축 0~10 · 운영자 260706) — 숫자 배열만 수용 = 프롬프트 주입 원천 차단(라벨은 러너 상수)
    const persona = String(body.persona || '');
    if (!ID_RE.test(persona)) return json({ error: '잘못된 페르소나 id' }, 400);
    const raw = Array.isArray(body.g) ? body.g : null;
    if (!raw || raw.length !== 16) return json({ error: '게이지는 16개 숫자 배열' }, 400);
    const g = raw.map(v => Math.max(0, Math.min(10, Math.round(Number(v) || 0))));
    const sess = await readSess();
    sess.tunes = sess.tunes || {}; sess.tunes[persona] = g; sess.updated = Date.now();
    await putSess(sess);
    return json({ ok: true, g });
  }

  if (op === 'reset') {
    const cur = await env.YETA_R2.get(KEY);   // 삭제 직전 1세대 백업(reset 비가역 완화 — R2엔 copy 없어 get→put) · 비공개 버킷
    let keepTunes = {}, keepPolicy = {};
    if (cur) { try { const buf = await cur.arrayBuffer(); await env.YETA_R2.put('sessions/main.prev.json', buf, { httpMetadata: { contentType: 'application/json' } }); const prev = JSON.parse(new TextDecoder().decode(buf)); keepTunes = prev.tunes || {}; keepPolicy = prev.policy || {}; } catch {} }
    await putSess({ turns: [], note: '', state: 'idle', tunes: keepTunes, policy: keepPolicy, updated: Date.now() });   // 페르소나는 비움 → 재뽑기 · 게이지·시즌 정책은 설정이라 승계(운영자 260706)
    return json({ ok: true });
  }

  if (op === 'draw') {   // 페르소나 뽑기/재뽑기 — 대화 맥락(턴·노트)은 유지, 화자만 교체
    const persona = String(body.persona || '');
    if (!ID_RE.test(persona)) return json({ error: '잘못된 페르소나 id' }, 400);
    const sani = s => String(s || '').replace(/<<\s*\/?\s*(?:NOTE|MOOD)(?:\s*:\s*\w+)?\s*>>/gi, '').replace(/<\/?user_message>/gi, '');
    const name = sani(body.name).slice(0, 24);
    const enter = sani(body.enter).slice(0, 60);       // 등장 연출 문구(roster enter_line · 아이데이션②)
    const greeting = sani(body.greeting).slice(0, 300);   // 첫인사 — 첫 진입 시 실제 assistant 턴으로 박제(증발·모델 문맥 누락 동시 해결)
    const sess = await readSess();
    sess.turns = sess.turns || [];
    if (sess.persona && sess.persona !== persona && sess.turns.length) {
      sess.turns.push({ role: 'sys', text: enter || `${name || persona} 등장`, ts: Date.now() });   // 대화 중 교체 = 합류 신호(enter_line 연출 우선 · 프롬프트 문맥에도 실림)
    } else if (!sess.turns.length && greeting) {
      sess.turns.push({ role: 'assistant', text: greeting, persona, ts: Date.now() });   // 첫 진입 = 첫인사를 턴으로(뷰어 재렌더에도 유지 + HIST에 실려 캐릭터가 자기 인사를 앎)
    }
    sess.persona = persona;
    sess.updated = Date.now();
    await putSess(sess);
    return json({ ok: true, sess });
  }

  if (op === 'retry') {   // 원탭 재시도 — 실패(state=error)한 pending 유저 턴을 재타이핑 없이 재발사(새 유저 턴 추가 X)
    if (!env.GH_TOKEN) return json({ error: '서버 미설정 — GH_TOKEN 필요' }, 500);
    const sess = await readSess();
    const turns = sess.turns || [];
    const lastA = turns.map(t => t.role).lastIndexOf('assistant');
    if (!turns.slice(lastA + 1).some(t => t.role === 'user')) return json({ error: '재시도할 메시지가 없어' }, 409);
    sess.state = 'awaiting'; sess.awaiting_since = Date.now(); delete sess.err;
    await putSess(sess);
    const rst = await dispatch(env);
    if (rst === 204) return json({ ok: true });
    sess.state = 'error'; sess.err = `재발사 실패(GitHub ${rst})`; delete sess.awaiting_since;
    await putSess(sess);
    return json({ error: `GitHub dispatch ${rst}` }, 502);
  }

  if (op !== 'send') return json({ error: '알 수 없는 op' }, 400);
  if (!env.GH_TOKEN) return json({ error: '서버 미설정 — GH_TOKEN 필요' }, 500);

  // 유저 텍스트 절제 + 프롬프트 델리미터 위장 무력화(yeta_chat.sh 관대 파서와 짝)
  const text = String(body.text || '').slice(0, 4000)
    .replace(/<\/?user_message>/gi, '').replace(/<<\s*\/?\s*(?:NOTE|MOOD)(?:\s*:\s*\w+)?\s*>>/gi, '').trim();   // NOTE·MOOD 위장 무력화(draw 새니타이즈와 동형)
  if (!text) return json({ error: '빈 메시지' }, 400);

  // 다이얼(모델×노력) — 화이트리스트 강제(오타·주입 = 기본 폴백 · 30초 목표라 effort 기본 low)
  let model = String(body.model || '');
  let effort = String(body.effort ?? 'low');
  if (!MODELS.has(model)) model = 'claude-opus-4-8';
  if (!EFFORTS.has(effort)) effort = 'low';

  // 채팅 상한 폐지(운영자 260706 — env YETA_MAX_PER_DAY 축 제거·무제한. 사용자별 상한은 후속 보류) · 카운터는 관측용 상시 기록 유지(KST 일자 키)
  const kst = new Date(Date.now() + 9 * 3600e3).toISOString().slice(2, 10).replace(/-/g, '');
  const qkey = `quota/${kst}.json`;
  let used = 0;
  const qo = await env.YETA_R2.get(qkey);
  if (qo) { try { used = (await qo.json()).n || 0; } catch { used = 0; } }

  const sess = await readSess();
  if (!ID_RE.test(String(sess.persona || ''))) return json({ error: '페르소나가 없어 — 🎲 먼저 뽑아줘' }, 409);
  sess.turns = sess.turns || [];
  const turn = { role: 'user', text, ts: Date.now(), model, effort };   // 다이얼 = 턴별 박제(중간 변경 정확 반영 · 아이데이션④⑤)
  if (body.ptt) turn.ptt = 1;   // 무전기(PTT) 턴 박제 — yeta_chat.sh 가 답장 반영 후 음성 합성(ptt_voice)
  sess.turns.push(turn);
  if (sess.turns.length > 400) sess.turns = sess.turns.slice(-400);
  sess.pref = { model, effort };                                            // 뷰어 재진입 복원용 미러
  sess.state = 'awaiting'; sess.awaiting_since = Date.now(); delete sess.err;
  await putSess(sess);
  await env.YETA_R2.put(qkey, JSON.stringify({ n: used + 1 }), { httpMetadata: { contentType: 'application/json' } });

  const st = await dispatch(env);
  if (st === 204) return json({ ok: true });
  // dispatch 실패 = 답장 올 런이 없음 → awaiting 고착 방지: state=error 롤백(평의회②)
  sess.state = 'error'; sess.err = `발사 실패(GitHub ${st}) — 다시 보내면 재시도`; delete sess.awaiting_since;
  await putSess(sess);
  return json({ error: `GitHub dispatch ${st}` }, 502);
}

async function dispatch(env, wf = 'yeta-chat.yml', inputs = { char: 'main' }) {   // 워크플로 기동(기본 = 챗 · 단일 스레드 = char 'main' 고정 → concurrency 직렬 / ring = yeta-call.yml)
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${wf}/dispatches`, {
    method: 'POST',
    headers: {
      authorization: `Bearer ${env.GH_TOKEN}`,
      accept: 'application/vnd.github+json',
      'user-agent': 'nomute-viewer',
      'x-github-api-version': '2022-11-28',
    },
    body: JSON.stringify({ ref: 'main', inputs }),
  });
  return r.status;
}

function originOk(request) {   // publish.js originOk 계승 — 상태변경 POST 는 동일출처만(CSRF)
  const o = request.headers.get('origin');
  if (!o) return false;
  try { const h = new URL(o).hostname; return h.endsWith('.pages.dev') || h === 'soong.kr' || h.endsWith('.soong.kr'); } catch { return false; }   // 커스텀 도메인 = soong.kr(루트+서브 · 260704 · nomute 도메인 미사용) · 도메인 추가 시 || 이어붙임
}
