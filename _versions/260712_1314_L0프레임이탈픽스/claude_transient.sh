#!/usr/bin/env bash
# claude_transient.sh — is_transient(): claude -p 출력/에러가 '서버측 일시 과부하(5xx·Overloaded·게이트웨이)'인지 판정.
# analyze.sh·ask.sh·cardmake.sh 공용 단일 출처(SSOT) = 재시도 판정 정규식이 셋으로 갈라지는 드리프트 차단(260622).
#
# ⚠️ 좁게 잡음 = 오직 서버 과부하(공짜·일시)만. 429/쿼터/인증은 제외(재시도해도 그대로라 격리·프로필 점등이 맞음).
#   ANALYSIS_FAILED(입력 막다른길)·정상출력도 여기 안 걸림(호출부에서 따로 즉시 탈출).
#   ① 5xx 전체(502 Bad Gateway·504 Gateway Timeout·520 등 게이트웨이 포함 — Anthropic 앞단 일시장애) 커버.
#   ② 출력 '앞부분(8줄)'만 검사 = CLI 에러는 맨 앞 줄 → 기사 본문 산문의 '503호'·'Service Unavailable' 인용 오탐 억제.
is_transient() {
  local s; s="$(printf '%s\n' "${1:-}" | head -n 8)"
  grep -qiE 'API Error: 5[0-9][0-9]|overloaded_error|Overloaded|"status": ?5[0-9][0-9]|Service (Unavailable|Temporarily Unavailable)|Bad Gateway|Gateway Time-?out' <<<"$s"
}

# is_quota(): claude -p 출력/에러가 '계정 사용량 한도(쿼터·레이트리밋·429)'인지 — *다른 계정으로 전환* 트리거.
#   인증죽음(401/oauth만료)·5xx 과부하와 구분(그건 전환해도 무의미·is_transient/health 담당). 앞 8줄만 검사(본문 인용 오탐 억제).
is_quota() {
  local s; s="$(printf '%s\n' "${1:-}" | head -n 8)"
  # ⚠️ 'weekly limit'·'hit your … limit'·'limit … resets <날짜>' 추가(260629·동시세션 합본) = Claude Code 주간 한도 메시지 "You've hit your weekly limit · resets Jul 3" 포착.
  #   이게 빠져 있어 주간한도 시 failover가 안 걸리고 활성계정에서 즉시 실패(서브계정 미시도)했음 — ask/analyze/card 전부 영향(SSOT).
  grep -qiE 'usage limit|weekly limit|hit your .{0,40}limit|rate.?limit|rate_limit|429|too many requests|quota|limit reached|limit.{0,40}reset|resets? (at|in)' <<<"$s"
}

# claude_failover(): 출력이 쿼터 한도면 *대체 계정 토큰*으로 1단계씩 전환(4계정 체인 = 메인1 + 세부3).
#   1차 = CLAUDE_CODE_OAUTH_TOKEN_ALT(서브1) · 2차 = CLAUDE_CODE_OAUTH_TOKEN_ALT2(서브2) · 3차 = CLAUDE_CODE_OAUTH_TOKEN_ALT3(서브3).
#   전환함=0(호출부가 같은 프롬프트로 재시도) / 못 함(쿼터 아님·다음 대체 없음·체인 소진)=1.
#   _CLAUDE_SWAPPED = 지금까지 전환 횟수(0→1→2→3). ⚠️ ALT2/ALT3 미설정이면 그 단계에서 멈춤 = 옛 동작(하위호환).
claude_failover() {
  is_quota "${1:-}" || return 1
  local n="${_CLAUDE_SWAPPED:-0}"
  if [ "$n" = "0" ] && [ -n "${CLAUDE_CODE_OAUTH_TOKEN_ALT:-}" ]; then
    export CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_CODE_OAUTH_TOKEN_ALT"; _CLAUDE_SWAPPED=1
    echo "  🔄 계정 사용량 한도 — 서브1 계정으로 전환 후 재시도(account failover 1/3)"
    return 0
  fi
  if [ "$n" = "1" ] && [ -n "${CLAUDE_CODE_OAUTH_TOKEN_ALT2:-}" ]; then
    export CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_CODE_OAUTH_TOKEN_ALT2"; _CLAUDE_SWAPPED=2
    echo "  🔄 서브1도 한도 — 서브2 계정으로 전환 후 재시도(account failover 2/3)"
    return 0
  fi
  if [ "$n" = "2" ] && [ -n "${CLAUDE_CODE_OAUTH_TOKEN_ALT3:-}" ]; then
    export CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_CODE_OAUTH_TOKEN_ALT3"; _CLAUDE_SWAPPED=3
    echo "  🔄 서브2도 한도 — 서브3 계정으로 전환 후 재시도(account failover 3/3)"
    return 0
  fi
  return 1
}
