// Cloudflare Pages Function — yeta 캐릭터 챗 게이트웨이 (260707 v3 · 캐릭터별 다중 채팅방 + 다이얼 + 프리웜)
// 세션 = sessions/main.json 단일 R2 객체 안에 캐릭터별 스레드(threads[<id>]) — 방 = 캐릭터 · 신설 = draw 단일 경로(로스터 대조·캡 12) · 쓰기 = etag CAS(casPut).
//   op 추가: pin {t,on} = 채팅방 고정 토글 · reset {t} = 그 방만 나가기(t 無 = 전체 초기화) · 스레드 op(send/retry/invite/kick)는 {t} 동봉(미지정 = cur).
// ops(POST 단일 — 폴링도 POST = originOk 대칭):
//   chars {}                       : 페르소나 로스터(apps/yeta/characters/roster.json raw · 5분 캐시)
//   get   {}                       : 세션 반환(뷰어 폴)
//   send  {text, model, effort}    : 유저 턴 append(다이얼 턴별 박제 · 화이트리스트) → yeta-chat.yml dispatch
//   draw  {persona, name}          : 페르소나 뽑기/재뽑기 — sess.persona 갱신(+대화 중이면 sys 턴) · room=[persona] 리셋(단톡 해산)
//   invite {persona, name}         : 합석 초대(단톡 · 정원 MAX_ROOM) — sess.invite 마커+sys 턴 → dispatch(수락/거절 판정 = 러너가 카드·상태로)
//   kick  {persona, name}          : 합석 내보내기/초대 철회 — room 제거·invite 취소 + 퇴장 sys(dispatch 없음)
//   warm  {}                       : 프리웜 — dispatch만(러너 선부팅 → 첫 답장 30초 목표 · 쿼터 소비 0[NOPENDING 웜대기])
//   retry {}                       : 원탭 재시도 — 실패(state=error) pending 유저 턴 재발사(새 턴 추가 X)
//   ring  {persona?}               : 걸려오는 전화 요청 → yeta-call.yml dispatch(⚠️ TTS 유료 → 일 상한 기본 3 · YETA_CALL_MAX_PER_DAY)
//   voice {key}                    : 통화 음성 스트림 — 비공개 버킷 voice/ 만(대사=대화 내용 → 공개 버킷 금지 · 동일출처 게이트)
//   stt   {audio}                  : 무전기 STT 폴백(base64 webm/ogg → 텍스트) — iOS 설치형 PWA 는 Web Speech 불가(실측 260704)
//                                    → Workers AI Whisper(env.AI 바인딩 게이트 · 미설정 501 = 뷰어가 타이핑 폴백 안내)
//   phone {}                       : ☎️ 실전화(PSTN·Vapi) 스캐폴드 — 등록 번호로 실제 발신(⚠️분당 과금 · env 3종 게이트 · 일 상한 기본 2)
//   vapikey {}                     : 보이스톡(브라우저 통화 · Vapi Web SDK) 공개키 — env VAPI_PUBLIC_KEY(공개 축 · Origins 제한 권장)
//   calllog {}                     : 🩺 통화 진단 — Vapi 메타데이터만(상태·종료사유·비용 — transcript/PII 반환 금지)
//   tune  {persona, g[16]}         : 캐릭터 성향 게이지(L2 · 숫자 배열만 = 프롬프트 주입 차단)
//   policy {} | {p, pin}           : 3계층 정책 — GET 정의+현재값(무인증) / SET enum 정수만(⚠️ 관리자 PIN 필수)
//   auth  {pin}                    : PIN 로그인 — admin = env YETA_PIN_ADMIN(레포 무노출) / guest = apps/yeta/users.json 해시(깃 SSOT)
//   reset {}                       : 세션 초기화(페르소나도 비움 → 재뽑기 · tunes/policy 승계)
// 저장 = R2 비공개 버킷 바인딩 env.YETA_R2 (⚠️ 대화는 public 레포 커밋 절대 금지 — 계획안 D2).
// 게이트: 무인증 공개(originOk=CSRF만 · Access 미부착) · 채팅 상한 없음(운영자 260706 폐지 — quota 카운터는 관측용, 소비처 없음·후속 users.cap 연동 후보) · 유료 축(ring/phone)만 일 상한.
// env: GH_TOKEN(Actions write) · YETA_R2(R2 바인딩) · YETA_PIN_ADMIN(슈퍼관리자 PIN — 설정 SET 강제) · YETA_CALL_MAX_PER_DAY(선택·기본 3 — 유료 TTS 가드)
//      AI(선택 · Workers AI 바인딩 = op stt) · VAPI_API_KEY+VAPI_PHONE_ID+YETA_PHONE_TO(선택 3종 = op phone · 번호는 시크릿 — 코드 박제 금지)
//      YETA_PHONE_MAX_PER_DAY(선택·기본 2 — 실전화 분당 과금 가드).
const REPO = 'muteno/yeta';
const ID_RE = /^[a-z0-9_-]{1,24}$/;
const KEY = 'sessions/main.json';
const MAX_ROOM = 2;                 // 합석 정원(나 제외 캐릭터 수 · 운영자 260707 "한 명 정도는") — 3 확장은 실험 축
const INVITE_TTL = 600000;          // 초대 pending 10분 — 러너 사망 시 스테일 마커가 다음 초대를 영구 차단하지 않게
const josa = (s, a, b) => { const c = String(s || '').charCodeAt(String(s || '').length - 1); return c >= 0xAC00 && c <= 0xD7A3 && (c - 0xAC00) % 28 > 0 ? a : b; };   // 받침 → 을/은, 무받침 → 를/는
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

  // ═══ v3 다중 스레드(운영자 260707 · 5인 기틀검증 반영) — 세션 = { v:3, cur, barge_day, call, threads:{<id>:{turns,state,opening,...,pin,updated}}, note_pub, notes, tunes, policy, pref } ═══
  const migrateV3 = (s) => {   // 멱등 순수 랩(v>=3 or threads 존재 = no-op) — 러너 파이썬과 동형 유지(마이그 감사① · 시뮬 대조)
    if (!s || (s.v >= 3) || s.threads) { if (s && !s.threads) s.threads = {}; if (s) s.v = 3; return s; }
    const t = String(s.persona || '');
    const th = {};
    if (t && Array.isArray(s.turns) && s.turns.length) {
      th[t] = { turns: s.turns, state: s.state || 'idle', opening: s.opening || 0, awaiting_since: s.awaiting_since || 0, err: s.err || '',
        room: Array.isArray(s.room) && s.room.length ? s.room : [t], invite: s.invite || null, barged: s.barged || 0, declined: s.declined || {},
        pin: 0, updated: s.turns[s.turns.length - 1]?.ts || Date.now(), last_sp: t, char_ver: s.char_ver || '', nudge: s.nudge || null };   // updated = 마지막 턴 ts 백필(정렬 최하단 방지 · UX감사)
    }
    return { v: 3, cur: t || '', barge_day: s.barge_day || '', call: s.call || null, threads: th,
      note_pub: s.note_pub || s.note || '', notes: s.notes || {}, tunes: s.tunes || {}, policy: s.policy || {}, pref: s.pref || {} };
  };
  const EMPTY = () => ({ v: 3, cur: '', barge_day: '', call: null, threads: {}, note_pub: '', notes: {}, tunes: {}, policy: {}, pref: {} });
  const readSessE = async () => {   // etag 동반 read + lazy 마이그레이션(메모리) — CAS 짝(레이스 감사① BLOCK 해제)
    const o = await env.YETA_R2.get(KEY);
    if (!o) return { sess: EMPTY(), etag: null, legacy: false };
    let raw; try { raw = await o.json(); } catch { return { sess: EMPTY(), etag: o.etag, legacy: false }; }
    const legacy = !(raw.v >= 3) && !raw.threads && !!(raw.turns || raw.persona);
    return { sess: migrateV3(raw), etag: o.etag, legacy };   // etag = raw(따옴표 없음) — putSessIf의 onlyIf.etagMatches는 원시 etag 비교(httpEtag는 따옴표 포함이라 상시 불일치=조건부 put 전멸)
  };
  const readSess = async () => (await readSessE()).sess;   // 호환 셔틀(read-only 소비처)
  const putSessIf = async (s, etag) => {   // 조건부 put — etag 불일치 = false(호출부 재적용) · null etag = 최초 생성
    s.updated = Date.now();
    try {
      const r = await env.YETA_R2.put(KEY, JSON.stringify(s), { httpMetadata: { contentType: 'application/json' },
        onlyIf: etag ? { etagMatches: etag } : undefined });
      return r !== null;   // R2 조건부 put 실패 = null 반환
    } catch { return false; }
  };
  const putSess = (s) => { s.updated = Date.now(); return env.YETA_R2.put(KEY, JSON.stringify(s), { httpMetadata: { contentType: 'application/json' } }); };   // 무조건 put(마이그레이션 백업 등 비경합 축만)
  const casPut = async (mut) => {   // CAS 루프(4회) — mut(sess) = undefined(쓰기) | {abort:Response값}(무쓰기 중단) · 교차 스레드 LWW 소실 봉합(레이스 감사①④⑤)
    for (let i = 0; i < 4; i++) {
      const { sess, etag, legacy } = await readSessE();
      if (legacy) { try { const prev = await env.YETA_R2.get('sessions/main.v2.json'); if (!prev) { const orig = await env.YETA_R2.get(KEY); if (orig) await env.YETA_R2.put('sessions/main.v2.json', await orig.arrayBuffer(), { httpMetadata: { contentType: 'application/json' } }); } } catch {} }   // v2 백업 = 전용 키 write-once(마이그 감사②)
      const r = mut(sess);
      if (r && r.abort) return { sess, abort: r.abort };
      if (await putSessIf(sess, etag)) return { sess };
    }
    return { sess: null, abort: { error: '세션 경합 — 잠시 후 다시' } };
  };
  const TH = (s, t) => (s.threads || {})[t];   // 스레드 접근(없으면 undefined — 신설은 draw 단일 경로 · 보안 감사①)

  if (op === 'get') {   // 폴 — lazy 리퍼(전 스레드 순회): awaiting 10분 초과 = 러너 사망 판정 → 스레드별 error 플립/오프닝 idle 강등
    let sess = await readSess();
    const stale = Object.values(sess.threads || {}).some(th => th.state === 'awaiting' && th.awaiting_since && Date.now() - th.awaiting_since > 600000);
    if (stale) {   // 변경 있을 때만 CAS 쓰기(폴 다발 = 무변경 put 금지 · 보안 감사④)
      const { sess: s2 } = await casPut(s => {
        for (const th of Object.values(s.threads || {})) {
          if (th.state === 'awaiting' && th.awaiting_since && Date.now() - th.awaiting_since > 600000) {
            if (th.opening) { th.opening = 0; th.awaiting_since = 0; th.state = 'idle'; }   // 멈춘 오프닝 = 정적 폴백(뷰어 yGreet · 기틀검증 UX2)
            else { th.state = 'error'; th.err = '응답이 오지 않았어 — 다시 보내면 재시도'; th.awaiting_since = 0; }
          }
        }
      });
      if (s2) sess = s2;
    }
    const cur = sess.cur;   // 비활성 스레드 turns = 꼬리 2턴 절단(목록 미리보기 분량 · 페이로드 ×5 방지 · 보안 감사④)
    const out = { ...sess, threads: Object.fromEntries(Object.entries(sess.threads || {}).map(([id, th]) =>
      [id, id === cur ? th : { ...th, turns: (th.turns || []).slice(-2), trim: (th.turns || []).length }])) };   // trim = 원 턴수(뷰어 unread ts 판정 보조)
    return json({ ok: true, sess: out });
  }

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
    const persona = String(sessP.cur || '');   // v3 = 현재 스레드 캐릭터(마이그 감사④)
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
      const { abort } = await casPut(s => { s.policy = p; });
      if (abort) return json(abort, 409);
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
    const { abort } = await casPut(s => { s.tunes = s.tunes || {}; s.tunes[persona] = g; });
    if (abort) return json(abort, 409);
    return json({ ok: true, g });
  }

  if (op === 'pin') {   // 채팅방 고정 토글(운영자 260707 롱프레스 액티브) — 숫자/불리언만 수용 · 스레드 실존 요구(신설 금지 · 보안 감사①)
    const t = String(body.t || '');
    if (!ID_RE.test(t)) return json({ error: '잘못된 스레드 id' }, 400);
    const on = !!body.on;
    const { sess, abort } = await casPut(s => {
      const th = TH(s, t); if (!th) return { abort: { error: '없는 대화방이야' } };
      th.pin = on ? Date.now() : 0;
    });
    if (abort) return json(abort, 409);
    return json({ ok: true, pin: !!(TH(sess, t) || {}).pin });
  }

  if (op === 'reset') {   // t 有 = 그 스레드만 나가기(threads[t]+notes[t] 삭제 · 관계 리셋) / t 無 = 전체 초기화. 직전 whole 백업 유지(레이스 감사④·보안 감사③)
    const t = String(body.t || '');
    if (t && !ID_RE.test(t)) return json({ error: '잘못된 스레드 id' }, 400);
    const curO = await env.YETA_R2.get(KEY);   // 삭제 직전 1세대 백업(비가역 완화)
    if (curO) { try { await env.YETA_R2.put('sessions/main.prev.json', await curO.arrayBuffer(), { httpMetadata: { contentType: 'application/json' } }); } catch {} }
    if (t) {
      const { sess, abort } = await casPut(s => {
        if (!TH(s, t)) return { abort: { error: '없는 대화방이야' } };
        delete s.threads[t];
        if (s.notes) delete s.notes[t];   // 관계 리셋(한계: note_pub 속 잔향은 존치 — 설계 명기)
        if (s.cur === t) s.cur = Object.keys(s.threads)[0] || '';
      });
      if (abort) return json(abort, 409);
      return json({ ok: true, sess });
    }
    let keepTunes = {}, keepPolicy = {};
    if (curO) { try { const prev = migrateV3(JSON.parse(new TextDecoder().decode(await (await env.YETA_R2.get(KEY)).arrayBuffer()))); keepTunes = prev.tunes || {}; keepPolicy = prev.policy || {}; } catch {} }
    const fresh = EMPTY(); fresh.tunes = keepTunes; fresh.policy = keepPolicy;
    await putSess(fresh);   // 전체 초기화 = 무조건 put(의도된 전량 대체)
    return json({ ok: true });
  }

  if (op === 'draw') {   // v3 = 그 캐릭터의 대화방 열기(스레드 신설 = 이 op 단일 경로 · 보안 감사①) — 기존 방 = cur 전환만
    const persona = String(body.persona || '');
    if (!ID_RE.test(persona)) return json({ error: '잘못된 페르소나 id' }, 400);
    const sani = s => String(s || '').replace(/<<\s*\/?\s*(?:NOTE|MOOD)(?:\s*:\s*\w+)?\s*>>/gi, '').replace(/<\/?user_message>/gi, '');
    const greeting = sani(body.greeting).slice(0, 300);   // 정적 폴백 사다리용(동적 실패·GH_TOKEN 無)
    const pre = await readSess();
    if (!TH(pre, persona)) {   // 신설 = 로스터 대조(임의 id 무한 스레드·PAT 소진 DoS 차단 · 보안 감사①)
      const rc = await fetch(`https://raw.githubusercontent.com/${REPO}/main/apps/yeta/characters/roster.json`,
        { headers: { 'user-agent': 'nomute-viewer' }, cf: { cacheTtl: 300, cacheEverything: true } });
      if (!rc.ok) return json({ error: '로스터 로드 실패' }, 502);
      let roster; try { roster = await rc.json(); } catch { return json({ error: '로스터 파싱 실패' }, 502); }
      if (!Array.isArray(roster) || !roster.some(c => c && c.id === persona)) return json({ error: '로스터에 없는 캐릭터야' }, 400);
    }
    const mkTh = () => ({ turns: [], state: 'idle', opening: 0, awaiting_since: 0, err: '', room: [persona], invite: null, barged: 0, declined: {}, pin: 0, updated: Date.now(), last_sp: persona, char_ver: '', nudge: null });
    // 1) 기존 방(턴 有) 또는 오프닝 인플라이트 = cur 전환만(멱등 — 재dispatch 금지 · 보안⑤/비용가드1)
    let need = null;   // 'dispatch' | 'static'
    const { sess, abort } = await casPut(s => {
      let th = TH(s, persona);
      if (!th) {
        if (Object.keys(s.threads).length >= 12) return { abort: { error: '방이 가득 찼어' } };   // 하드 캡(로스터 대조 이중 방어)
        th = s.threads[persona] = mkTh();
      }
      s.cur = persona;
      if (th.turns.length || (th.state === 'awaiting' && th.opening)) { need = null; return; }
      if (env.GH_TOKEN) {   // 동적 오프닝 — nonce = reset/재드로 레이스 방어(러너 finish 일치검사 · 75차 가드 스레드 스코프)
        const nonce = Date.now();
        th.state = 'awaiting'; th.awaiting_since = nonce; th.opening = nonce; th.err = '';
        need = 'dispatch';
      } else need = 'static';
    });
    if (abort) return json(abort, 409);
    if (need === 'dispatch') {
      const okst = new Date(Date.now() + 9 * 3600e3).toISOString().slice(2, 10).replace(/-/g, '');   // 오프닝 일일 카운터(보안 감사② — 관측+상한 30)
      const oqk = `quota/opening-${okst}.json`;
      let oused = 0; const oqo = await env.YETA_R2.get(oqk);
      if (oqo) { try { oused = (await oqo.json()).n || 0; } catch { oused = 0; } }
      let st = 0;
      if (oused < 30) { await env.YETA_R2.put(oqk, JSON.stringify({ n: oused + 1 }), { httpMetadata: { contentType: 'application/json' } }); st = await dispatch(env); }
      if (st !== 204) {   // dispatch 실패·상한 = 정적 greeting 폴백 강등(비-empty 보장 = 루프 차단 · 비용가드2)
        const { sess: s3 } = await casPut(s => {
          const th = TH(s, persona); if (!th) return { abort: { error: '없는 대화방' } };
          th.state = 'idle'; th.opening = 0; th.awaiting_since = 0;
          if (greeting && !th.turns.length) { th.turns.push({ role: 'assistant', text: greeting, persona, ts: Date.now() }); th.updated = Date.now(); }
        });
        return json({ ok: true, sess: s3 || sess });
      }
      return json({ ok: true, sess });
    }
    if (need === 'static') {   // GH_TOKEN 無(로컬/프리뷰) = 정적 greeting(현행 온존 · UX가드4)
      const { sess: s4 } = await casPut(s => {
        const th = TH(s, persona); if (!th) return { abort: { error: '없는 대화방' } };
        if (greeting && !th.turns.length) { th.turns.push({ role: 'assistant', text: greeting, persona, ts: Date.now() }); th.updated = Date.now(); }
      });
      return json({ ok: true, sess: s4 || sess });
    }
    return json({ ok: true, sess });
  }

  if (op === 'invite') {   // 합석 초대(단톡 · 운영자 260707) — 마커+sys만 서버가 쓰고, 올지 말지는 러너가 그 캐릭터 카드·시각·관계로 판정(거절 = 콘텐츠)
    if (!env.GH_TOKEN) return json({ error: '서버 미설정 — GH_TOKEN 필요' }, 500);
    const persona = String(body.persona || '');
    if (!ID_RE.test(persona)) return json({ error: '잘못된 페르소나 id' }, 400);
    const sani = s => String(s || '').replace(/<<\s*\/?\s*(?:NOTE|MOOD)(?:\s*:\s*\w+)?\s*>>/gi, '').replace(/<\/?user_message>/gi, '');
    const name = sani(body.name).slice(0, 24) || persona;
    const t = String(body.t || (await readSess()).cur || '');   // 대상 스레드(초대 = 열린 방으로)
    if (!ID_RE.test(t)) return json({ error: '먼저 대화 상대를 뽑아줘' }, 409);
    const { sess, abort } = await casPut(s => {
      const th = TH(s, t); if (!th) return { abort: { error: '없는 대화방이야' } };
      const room = Array.isArray(th.room) && th.room.length ? th.room : [t];
      if (room.includes(persona)) return { abort: { error: '이미 같이 있어' } };
      if (room.length >= MAX_ROOM) return { abort: { error: '자리가 없어 — 한 명을 보내고 불러줘' } };
      if (th.invite && Date.now() - (th.invite.ts || 0) < INVITE_TTL) return { abort: { error: '이미 누굴 부르는 중이야' } };
      th.room = room;
      th.invite = { to: persona, ts: Date.now() };
      th.turns.push({ role: 'sys', text: `${name}${josa(name, '을', '를')} 불렀어…`, ts: Date.now(), kind: 'invite' });
      if (th.turns.length > 200) th.turns = th.turns.slice(-200);   // 스레드 캡(보안 감사⑤)
      th.updated = Date.now();
    });
    if (abort) return json(abort, 409);
    const st = await dispatch(env);
    if (st === 204) return json({ ok: true, sess });
    await casPut(s => { const th = TH(s, t); if (th) th.invite = null; });   // 판정 런 불발 = 마커 회수
    return json({ error: `GitHub dispatch ${st}` }, 502);
  }

  if (op === 'kick') {   // 합석 내보내기/초대 철회 — 유저 쪽 거절권(난입의 대칭). 퇴장도 세계관 연출(sys)
    const persona = String(body.persona || '');
    if (!ID_RE.test(persona)) return json({ error: '잘못된 페르소나 id' }, 400);
    const sani = s => String(s || '').replace(/<<\s*\/?\s*(?:NOTE|MOOD)(?:\s*:\s*\w+)?\s*>>/gi, '').replace(/<\/?user_message>/gi, '');
    const name = sani(body.name).slice(0, 24) || persona;
    const t = String(body.t || (await readSess()).cur || '');
    if (!ID_RE.test(t)) return json({ error: '잘못된 스레드 id' }, 400);
    const { sess, abort } = await casPut(s => {
      const th = TH(s, t); if (!th) return { abort: { error: '없는 대화방이야' } };
      if (th.invite && th.invite.to === persona) {   // 아직 판정 전 = 부르기 취소
        th.invite = null;
        th.turns.push({ role: 'sys', text: `부르기를 관뒀어`, ts: Date.now() });
        th.updated = Date.now(); return;
      }
      const room = Array.isArray(th.room) && th.room.length ? th.room : [t];
      if (!room.includes(persona)) return { abort: { error: '지금 방에 없는 사람이야' } };
      if (room.length <= 1) return { abort: { error: '마지막 한 명은 못 내보내' } };
      th.room = room.filter(id => id !== persona);
      if (th.last_sp === persona) th.last_sp = th.room[0];   // 주 화자가 나가면 남은 사람이 이어받음(v3 = last_sp)
      if (th.barged && th.barged.id === persona) th.barged = 0;
      th.turns.push({ role: 'sys', text: `${name}${josa(name, '은', '는')} 다음을 기약하며 물러갔다`, ts: Date.now() });
      if (th.turns.length > 200) th.turns = th.turns.slice(-200);
      th.updated = Date.now();
    });
    if (abort) return json(abort, 409);
    return json({ ok: true, sess });
  }

  if (op === 'retry') {   // 원탭 재시도 — 실패(state=error) 스레드의 pending 유저 턴 재발사(새 턴 추가 X)
    if (!env.GH_TOKEN) return json({ error: '서버 미설정 — GH_TOKEN 필요' }, 500);
    const t = String(body.t || (await readSess()).cur || '');
    if (!ID_RE.test(t)) return json({ error: '잘못된 스레드 id' }, 400);
    const { abort } = await casPut(s => {
      const th = TH(s, t); if (!th) return { abort: { error: '없는 대화방이야' } };
      const turns = th.turns || [];
      const lastA = turns.map(x => x.role).lastIndexOf('assistant');
      if (!turns.slice(lastA + 1).some(x => x.role === 'user')) return { abort: { error: '재시도할 메시지가 없어' } };
      th.state = 'awaiting'; th.awaiting_since = Date.now(); th.err = '';
    });
    if (abort) return json(abort, 409);
    const rst = await dispatch(env);
    if (rst === 204) return json({ ok: true });
    await casPut(s => { const th = TH(s, t); if (th) { th.state = 'error'; th.err = `재발사 실패(GitHub ${rst})`; th.awaiting_since = 0; } });
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

  const t = String(body.t || (await readSess()).cur || '');   // 대상 스레드(v3) — 미지정 = 현재 방
  if (!ID_RE.test(t)) return json({ error: '페르소나가 없어 — 🎲 먼저 뽑아줘' }, 409);
  const { abort } = await casPut(s => {
    const th = TH(s, t); if (!th) return { abort: { error: '없는 대화방이야 — 캐릭터 탭에서 열어줘' } };
    const turn = { role: 'user', text, ts: Date.now(), model, effort };   // 다이얼 = 턴별 박제
    if (body.ptt) turn.ptt = 1;   // 무전기(PTT) 턴 박제
    th.turns.push(turn);
    if (th.turns.length > 200) th.turns = th.turns.slice(-200);   // 스레드 캡(보안 감사⑤)
    th.state = 'awaiting'; th.awaiting_since = Date.now(); th.err = '';
    th.updated = Date.now();
    s.cur = t;   // 발신 = 현재 방 확정(푸시 딥링크·phone 발신자 정본 · 러너 감사⑤B)
    s.pref = { model, effort };
  });
  if (abort) return json(abort, 409);
  await env.YETA_R2.put(qkey, JSON.stringify({ n: used + 1 }), { httpMetadata: { contentType: 'application/json' } });

  const st = await dispatch(env);
  if (st === 204) return json({ ok: true });
  // dispatch 실패 = 답장 올 런이 없음 → awaiting 고착 방지: 스레드 error 롤백
  await casPut(s => { const th = TH(s, t); if (th) { th.state = 'error'; th.err = `발사 실패(GitHub ${st}) — 다시 보내면 재시도`; th.awaiting_since = 0; } });
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
