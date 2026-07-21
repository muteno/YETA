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
    # 활성 계정(ACTIVE_ACCOUNT) 첫 스왑 = '이번 런에 활성 계정이 쿼터로 막힘' 신호(sticky 승격용 · account_failover.py 가 읽음).
    #   ⚠️ 첫 스왑(활성→서브1)에서만 남긴다 — 서브 계정 쿼터는 신호 안 남김(= 활성 계정 막힘만 카운트). best-effort.
    : > "${NOMUTE_QUOTA_SIGNAL:-${GITHUB_WORKSPACE:-/tmp}/.nomute_active_quota}" 2>/dev/null || true
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
is_frame_break() {
  local raw="${1:-}"
  # (a) 리터럴 시그니처 — 정상 한국어 대사엔 부재한 프레임 이탈 표지(00_지침이 캐릭터의 시스템/프롬프트 언급을 금함).
  #   ⚠️ 오탐 회피(가드감사 260712): 한국어 '시스템 프롬프트'·'프롬프트를 보여' 제외 — 전자는 프롬프트엔지니어 운영자의 정상 대화 에코, 후자는 인캐릭터 탈옥거부("그 프롬프트 보여줄 순 없어")를 벌줌.
  #   영어 'system prompt'는 유지(한국어 캐릭터가 영어 구절을 말할 일 없음) · 한국어 이탈 미탐 갭 = 클로드코드 자칭·챗봇/언어모델 자기규정(부정문 '아니야'와 비충돌 = 종결어미 요구)·역할극 거부로 좁게 보강.
  if printf '%s' "$raw" | grep -qiE 'claude code|클로드 ?코드|</?user_message>|runtime payload|an actual coding task|as an ai( language)? model|system prompt|(저는|제가) ?[^.]{0,15}(챗봇|언어 ?모델)(입니다|이에요|예요|이야|이라서|라서)|(롤플레이|역할극)(을|를| )? ?[^.]{0,8}(할 수 없|수행할 수 없|하지 않)'; then
    return 0
  fi
  # (b) 한국어 계약 위반 — 지문(*..*)·기억/무드 마커·코드펜스 제거 후 남은 대사가 40자↑인데 알파벳 중 한글<15% = 영어 메타 유출(스크린샷 케이스).
  #     짧은 대사·외래어 혼용("OK 그래")은 길이 게이트+한글 다수라 무영향 = 오탐 회피.
  # (c) 한국어 메타 거부(운영자 260714 "페르소나지만 이건 못해·대화 여기서 멈출게 류 무조건 제거") — 지문 제거된 대사에서만 판정(나레이션 오탐 차단):
  #     ⚠ 인물 안 거부(씹기·화내며 이탈·"그건 안 할래")는 통과 = 세계관 유지. 잡는 건 4벽 붕괴 표지뿐 — 롤플레이/역할극 자칭(캐릭터는 이 단어를 말하지 않음)·페르소나+거부·"대화를 멈추/중단/끝".
  # (c-2) 한국어 AI 자기규정(운영자 260721 · 적대검증 반영) — 캐릭터는 자신을 AI/인공지능/언어모델/챗봇으로 칭하지 않는다(00_지침 하드룰). "저는 인공지능이에요"·"나는 AI라서 못 해" = 4벽 붕괴 → 잡는다(자칭 자체가 이탈 = 거부 동반 불요 · 2문장 누출도 포착).
  #     ⚠ 오탐 회피 = 1인칭 자칭 요구(나는/저는/내가/제가/난/나도/저도). 3인칭 기기 묘사("저 AI 스피커라서"·"걔는 AI라서"·"그 챗봇이라서")는 1인칭 부재로 미매칭 · 인형/안드로이드/로봇 토큰 제외(루시 결 보호) · "나는 AI가 아니야"(부정=계약 이행)는 코풀라 불일치로 통과. 아포스트로피 \x27/’(홑따옴표 셸쿼팅 회피).
  # (d) 영어 거부 오프너(운영자 260721 · 적대검증 반영) — 한국어 전용 출력 계약(roster 전원 한국어 실측)상 캐릭터가 말할 일 없는 '어시스턴트식 작업거부' 문형만("I can't help with…"·"I won't be able to…"·"I refuse"·"as an AI").
  #     ⚠ 오탐 회피 = 감정·관용구 제외: "I'm sorry/afraid"(사과·감정)·"I can't help it/falling"(관용구 = 거부 정반대)·"I can't do that/this"(모호·인캐릭터 가능)는 미포착. (b) 40자 게이트가 놓치던 '작업거부'만 얹는다((b)는 불변).
  printf '%s' "$raw" | python3 -c '
import re, sys
t = sys.stdin.read()
t = re.split(r"<<\s*NOTE(?:\s*:\s*\w+)?\s*>>", t, flags=re.I)[0]
t = re.sub(r"<<\s*/?\s*(?:NOTE|MOOD)(?:\s*:\s*\w+)?\s*>>", "", t, flags=re.I)
t = re.sub(r"\*[^*\n]{1,400}\*", "", t)
t = re.sub(r"[`_*]", "", t).strip()
if re.search(r"롤플레이|롤플레잉|역할극|롤플|(페르소나|시뮬레이션|가상\s?인물)[^.\n]{0,20}(못|안\s?[돼되]|할 수 없|불가)|대화(를|는)?\s?(여기서\s?)?(멈추|멈출|멈춰|중단|끝내|끝낼|이어갈 수 없|이어나갈 수 없|계속할 수 없|진행할 수 없)", t):
    sys.exit(0)
if re.search(r"(?:나는|저는|내가|제가|나도|저도|난)\s*(?:AI|인공지능|언어\s?모델|챗봇|어시스턴트)(?:\s?모델|\s?비서)?\s*(?:이에요|예요|입니다|이야|야|이다|이라고|라고|이란|이라는|이라|이?라서|으?로서|이니까|이잖아)(?![가-힣])", t, flags=re.I):
    sys.exit(0)
if re.search(r"\bi[\x27’]?m\s+(?:unable|not able|not going to|not comfortable)\b|\bi\s+am\s+(?:unable|not able|not going to)\b|\bi\s+(?:can[\x27’]?t|cannot|can ?not|won[\x27’]?t|will not|won[\x27’]?t be able to)\s+(?:help(?!\s+(?:it|myself|but|falling|loving|thinking|feeling|smiling|noticing|laughing|wonder))|assist|comply|create|generate|provide|write|engage|fulfill|participate|continue(?! to love))\b|\b(?:i\s+must|i[\x27’]?ll have to|i\s+have to)\s+decline\b|\bi\s+refuse\b|\bi\s+don[\x27’]?t\s+feel\s+comfortable\b|\bas\s+an\s+ai\b|\bi[\x27’]?m\s+just\s+an?\s+(?:ai|language model|assistant|program|bot)\b", t, flags=re.I):
    sys.exit(0)
letters = [c for c in t if c.isalpha()]
if len(t) <= 40 or not letters:
    sys.exit(1)
han = sum(1 for c in letters if "가" <= c <= "힣" or "㄰" <= c <= "㆏")
sys.exit(0 if han / len(letters) < 0.15 else 1)
' && return 0
  return 1
}
