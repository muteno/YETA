// Cloudflare Pages Function — yeta 캐릭터 챗 게이트웨이 (260703 v2 · 랜덤 페르소나 + 다이얼 + 프리웜)
// 세션 = 단일 스레드 sessions/main.json (대화 맥락 공유 · 페르소나는 sess.persona 로 랜덤 뽑기/재뽑기).
// ops(POST 단일 — 폴링도 POST = originOk 대칭):
//   chars {}                       : 페르소나 로스터(apps/yeta/characters/roster.json raw · 5분 캐시)
//   get   {}                       : 세션 반환(뷰어 폴)
//   send  {text, model, effort}    : 유저 턴 append(다이얼 턴별 박제 · 화이트리스트) → yeta-chat.yml dispatch
//   draw  {persona, name}          : 페르소나 뽑기/재뽑기 — sess.persona 갱신(+대화 중이면 sys 턴)
//   warm  {}                       : 프리웜 — dispatch만(러너 선부팅 → 첫 답장 30초 목표 · 쿼터 소비 0[NOPENDING 웜대기])
//   reset {}                       : 세션 초기화(페르소나도 비움 → 다음 진입 시 재뽑기)
// 저장 = R2 비공개 버킷 바인딩 env.YETA_R2 (⚠️ 대화는 public 레포 커밋 절대 금지 — 계획안 D2).
// 게이트: Cloudflare Access(도메인 전체 자동 계승) + originOk(CSRF) + 일 상한 = D4 무제한(env YETA_MAX_PER_DAY 양수로만 발동).
// env: GH_TOKEN(Actions write) · YETA_R2(R2 바인딩) · YETA_MAX_PER_DAY(선택).
const REPO = 'muteno/yeta';
const ID_RE = /^[a-z0-9_-]{1,24}$/;
const KEY = 'sessions/main.json';
const MODELS = new Set(['claude-opus-4-8', 'claude-sonnet-5']);          // §기틀 정확 ID — 집합 확장은 운영자 확인
const EFFORTS = new Set(['', 'low', 'medium', 'high', 'max']);           // '' = --effort 생략(CLI 기본)

export async function onRequestPost({ request, env }) {
  const json = (o, s = 200) =>
    new Response(JSON.stringify(o), { status: s, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });

  if (!originOk(request)) return json({ error: '허용되지 않은 출처' }, 403);
  let body;
  try { body = await request.json(); } catch { return json({ error: '잘못된 요청' }, 400); }
  const op = String(body.op || '');

  // 로스터는 R2 불필요(레포 raw) — 셋업 전에도 목록·안내를 그릴 수 있게 R2 가드보다 앞.
  if (op === 'chars') {
    const r = await fetch(`https://raw.githubusercontent.com/${REPO}/main/apps/yeta/characters/roster.json`,
      { headers: { 'user-agent': 'nomute-viewer' }, cf: { cacheTtl: 60, cacheEverything: true } });
    if (!r.ok) return json({ error: `로스터 로드 실패(${r.status})` }, 502);
    return json({ ok: true, chars: await r.json(), ready: !!env.YETA_R2 });
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

  if (op === 'reset') {
    const cur = await env.YETA_R2.get(KEY);   // 삭제 직전 1세대 백업(reset 비가역 완화 — R2엔 copy 없어 get→put) · 비공개 버킷
    if (cur) { try { await env.YETA_R2.put('sessions/main.prev.json', await cur.arrayBuffer(), { httpMetadata: { contentType: 'application/json' } }); } catch {} }
    await putSess({ turns: [], note: '', state: 'idle', updated: Date.now() });   // 페르소나도 비움 → 재뽑기
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

  // 일 상한 — D4 무제한(기본 0) · env YETA_MAX_PER_DAY(양수)로만 발동 · 카운터는 관측용 상시 기록(KST 일자 키)
  const cap = parseInt(env.YETA_MAX_PER_DAY || '0', 10) || 0;
  const kst = new Date(Date.now() + 9 * 3600e3).toISOString().slice(2, 10).replace(/-/g, '');
  const qkey = `quota/${kst}.json`;
  let used = 0;
  const qo = await env.YETA_R2.get(qkey);
  if (qo) { try { used = (await qo.json()).n || 0; } catch { used = 0; } }
  if (cap > 0 && used >= cap) return json({ error: `오늘 대화 상한(${cap}턴) 도달 — 내일 다시`, remain: 0 }, 429);

  const sess = await readSess();
  if (!ID_RE.test(String(sess.persona || ''))) return json({ error: '페르소나가 없어 — 🎲 먼저 뽑아줘' }, 409);
  sess.turns = sess.turns || [];
  sess.turns.push({ role: 'user', text, ts: Date.now(), model, effort });   // 다이얼 = 턴별 박제(중간 변경 정확 반영 · 아이데이션④⑤)
  if (sess.turns.length > 400) sess.turns = sess.turns.slice(-400);
  sess.pref = { model, effort };                                            // 뷰어 재진입 복원용 미러
  sess.state = 'awaiting'; sess.awaiting_since = Date.now(); delete sess.err;
  await putSess(sess);
  await env.YETA_R2.put(qkey, JSON.stringify({ n: used + 1 }), { httpMetadata: { contentType: 'application/json' } });

  const st = await dispatch(env);
  const remain = cap > 0 ? cap - used - 1 : -1;
  if (st === 204) return json({ ok: true, remain });
  // dispatch 실패 = 답장 올 런이 없음 → awaiting 고착 방지: state=error 롤백(평의회②)
  sess.state = 'error'; sess.err = `발사 실패(GitHub ${st}) — 다시 보내면 재시도`; delete sess.awaiting_since;
  await putSess(sess);
  return json({ error: `GitHub dispatch ${st}`, remain }, 502);
}

async function dispatch(env) {   // yeta-chat.yml 기동(단일 스레드 = char 'main' 고정 → concurrency 직렬)
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/yeta-chat.yml/dispatches`, {
    method: 'POST',
    headers: {
      authorization: `Bearer ${env.GH_TOKEN}`,
      accept: 'application/vnd.github+json',
      'user-agent': 'nomute-viewer',
      'x-github-api-version': '2022-11-28',
    },
    body: JSON.stringify({ ref: 'main', inputs: { char: 'main' } }),
  });
  return r.status;
}

function originOk(request) {   // publish.js originOk 계승 — 상태변경 POST 는 동일출처만(CSRF)
  const o = request.headers.get('origin');
  if (!o) return false;
  try { const h = new URL(o).hostname; return h.endsWith('.pages.dev') || h === 'yeta.nomute.kr'; } catch { return false; }   // 커스텀 도메인 = yeta.nomute.kr(260704) · 추가 도메인은 || h === '…' 이어붙임
}
