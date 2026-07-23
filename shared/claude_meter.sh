#!/usr/bin/env bash
# claude_meter.sh — claude -p 토큰 사용량 계측 래퍼(SSOT). muteno 구독 OAuth 토큰이 "어디서 얼마나"
# 쓰이는지 추적하려고, 모든 claude -p 호출을 이 래퍼로 감싸 호출당 토큰을 metrics/ 에 남긴다.
# claude_transient.sh(재시도 판정)·claude_py.py(파이썬판 계정 폴오버)와 같은 결의 공용 헬퍼 — 로직 한 곳.
#
# 동작:
#   out="$(printf '%s' "$prompt" | METER_SRC=analyze METER_REF="$base" \
#          claude_meter 900 --model "$MODEL" --effort max --allowedTools ... --disallowedTools ... --max-turns 40 \
#          2> "$errfile")"
#   rc=$?
#   → claude -p 를 --output-format json 으로 돌려 .result(=원래 plain text 출력)만 stdout 으로 흘리고,
#     .usage(input/output/cache 토큰)·total_cost_usd·num_turns·duration_ms 를 잡 단위 shard 파일에 1줄 append.
#   ∴ 호출부의 out= 는 *예전과 똑같이 마크다운 본문*을 받는다(파싱 무변경). rc·stderr 도 그대로 보존.
#
# ⚠️ 안전(파이프라인 절대 안 깨지게):
#   · jq 없거나 METER_OFF=1 이면 → plain `claude -p`(--output-format json 미부착)로 폴백 = 옛 동작 그대로(계측만 생략).
#   · --output-format json 출력이 파싱 안 되면(크래시·과부하·인증오류 등 비정상) → raw 출력을 그대로 흘려보냄
#     (호출부의 is_quota/is_transient/실패판정이 옛날과 동일하게 동작 = 폴오버·재시도 무손상).
#   · shard 기록 실패는 || true 로 삼킴(분석물 유실 0).
#
# shard 경로 = metrics/usage/<run>-<job>-<attempt>.jsonl (잡마다 고유 → 동시 잡 충돌 0; 잡 내 순차 append).
#   롤업(shared/token_report.py)이 이 shard 들을 10분 버킷으로 집계하고 오래된 건 metrics/token-usage.jsonl 로 접는다.

_meter_shard() {
  local run="${GITHUB_RUN_ID:-local}" job="${GITHUB_JOB:-job}" att="${GITHUB_RUN_ATTEMPT:-1}"
  printf 'metrics/usage/%s-%s-%s.jsonl' "$run" "$job" "$att"
}

# _meter_record <json> <rc> — JSON result 객체에서 토큰·비용을 뽑아 shard 에 1줄 append(jq).
_meter_record() {
  local raw="$1" rc="$2" shard ts
  # METER_LAST(옵트인) — 호출부 지정 파일에 이 호출의 usage 요약({in,out})을 덮어씀(yeta 답장 턴 tok 박제 = 뷰어 누적 미터 · 260709). 실패 = 무해(|| true).
  if [ -n "${METER_LAST:-}" ]; then
    printf '%s' "$raw" | jq -c '{in:((.usage.input_tokens // .usage.inputTokens) // 0), out:((.usage.output_tokens // .usage.outputTokens) // 0), cr:(.usage.cache_read_input_tokens // 0), cw:(.usage.cache_creation_input_tokens // 0)}' > "$METER_LAST" 2>/dev/null || true   # cr = 캐시 히트 토큰(260721 Q.36 — kimi 실비 환산: 히트는 1/10가라 분리 필요) · cw = 캐시 적재(260723 — 클로드 턴 실부피: input_tokens만 보면 i=2 착시)
  fi
  shard="$(_meter_shard)"
  mkdir -p metrics/usage 2>/dev/null || return 0
  ts="$(TZ='Asia/Seoul' date +%FT%T%:z 2>/dev/null)"   # KST(§📐 시각=KST)
  printf '%s' "$raw" | jq -c \
    --arg ts "$ts" --arg src "${METER_SRC:-?}" --arg ref "${METER_REF:-}" \
    --arg model "${METER_MODEL:-}" --arg effort "${METER_EFFORT:-}" \
    --arg run "${GITHUB_RUN_ID:-}" --arg job "${GITHUB_JOB:-local}" \
    --arg wf "${GITHUB_WORKFLOW:-local}" --argjson rc "${rc:-0}" '
    {
      ts:$ts, src:$src, ref:$ref,
      model:(if $model=="" then (.modelUsage|keys[0]? // "") else $model end), effort:$effort,
      in:((.usage.input_tokens // .usage.inputTokens) // 0),
      out:((.usage.output_tokens // .usage.outputTokens) // 0),
      cache_r:(.usage.cache_read_input_tokens // 0),
      cache_w:(.usage.cache_creation_input_tokens // 0),
      cost:(.total_cost_usd // .cost_usd // 0),
      turns:(.num_turns // 0), dur_ms:(.duration_ms // 0),
      run:$run, job:$job, wf:$wf, rc:$rc
    }' >> "$shard" 2>/dev/null || true
}

# claude_meter <timeout_s> [claude args after 'claude -p' ...]   (프롬프트는 stdin)
claude_meter() {
  local to="$1"; shift
  local raw rc bare=""
  # --bare 게이트 (생성경로 CLAUDE.md auto-discovery 스킵 = 안 읽는 라우터 ~37k 토큰 컨텍스트 누수 차단 · 260701).
  # 기본 ON · 품질 규칙은 stdin(inject_guidelines 주입)이 결정하므로 무영향 · 롤백 = env CLAUDE_BARE=0. judge(GATE_BARE·py)와 동형.
  case "${CLAUDE_BARE:-0}" in 0|false|no|off|"") ;; *) bare="--bare" ;; esac
  # 폴백 1 — 계측 끄기(METER_OFF) 또는 jq 부재: 옛 동작 그대로(--output-format json 미부착 = 마크다운 stdout).
  if [ "${METER_OFF:-0}" = "1" ] || ! command -v jq >/dev/null 2>&1; then
    timeout "$to" claude -p $bare "$@"
    return $?
  fi
  # 스트리밍 모드(옵트인 · METER_STREAM=필터 경로 — yeta 챗 전용 260714): stream-json 델타를 필터가 R2 draft로 흘리고
  #   최종 result 이벤트(JSON 1개 = json 모드와 동형)만 stdout에 남김 → 아래 기존 파서(.result)·계측·실패판정 전부 그대로 호환.
  #   구 CLI가 stream 플래그를 거부하면 json 모드 1회 폴백(stdin은 버퍼해 재공급 · 호출처 yeta_chat = pipefail로 rc 보존).
  #   미설정(기본) = 이 분기 자체가 없던 일 — 타 호출처 무영향.
  if [ -n "${METER_STREAM:-}" ] && [ -f "${METER_STREAM}" ]; then
    local _pin _serr=/tmp/claude_meter_stream.err; _pin="$(cat)"
    # ⚠️ 플래그 거부는 stderr로 나온다 — stdout($raw) grep은 미발화 + --verbose 진단 라인 오탐(평의회 260714 플랫폼 HIGH) → stderr 파일 포집으로 판정.
    raw="$(printf '%s' "$_pin" | timeout "$to" claude -p $bare --output-format stream-json --include-partial-messages --verbose "$@" 2>"$_serr" | python3 "$METER_STREAM")"
    rc=$?
    if ! printf '%s' "$raw" | jq -e '.result | type == "string"' >/dev/null 2>&1 && grep -qiE 'unknown option|unrecognized|requires --verbose' "$_serr" 2>/dev/null; then
      raw="$(printf '%s' "$_pin" | timeout "$to" claude -p $bare --output-format json "$@")"
      rc=$?
    fi
    cat "$_serr" >&2 2>/dev/null || true   # stderr 원류 재방류 — 호출부(gen_out /tmp/yeta.err) effort/system-prompt 거부·폴오버 매칭 계약 보존
  else
    raw="$(timeout "$to" claude -p $bare --output-format json "$@")"
    rc=$?
  fi
  # 정상 JSON(.result 가 문자열) → 계측 + .result 만 흘림(호출부 파싱 무변경).
  if printf '%s' "$raw" | jq -e '.result | type == "string"' >/dev/null 2>&1; then
    _meter_record "$raw" "$rc"
    printf '%s' "$raw" | jq -r '.result' 2>/dev/null
  else
    # 비정상(크래시·과부하·인증오류 등) → raw 그대로(호출부 실패판정·폴오버가 옛날처럼 작동).
    printf '%s' "$raw"
  fi
  return $rc
}
