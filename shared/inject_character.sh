#!/usr/bin/env bash
# inject_character.sh — yeta 캐릭터 챗 지침 주입 SSOT (inject_guidelines.sh 기법 이식 · 260703)
# ⚠️ 뉴스 inject_guidelines.sh 는 apps/news 경로 하드코딩(뉴스 파이프 기틀)이라 직접 재사용 금지 —
#    "강제주입(떠먹임) + 내용 해시 도장(드리프트 감지) + R6 정규화(겉모양 면제)" 기법만 여기로 복제.
# 사용: source 후  character_block <id>  /  character_version <id>
#   블록 = 공통지침(00_지침_캐릭터챗.md · 메타발화 차단/안전/출력계약 — 전 캐릭터 공통) + 캐릭터 카드 전문.
#   버전 = 블록 의미내용 sha256 12자 → 세션에 도장 → 카드 편집 시 뷰어가 "캐릭터 업데이트됨" 감지.

_yc_files() {
  local id="$1"
  echo "apps/yeta/00_지침_캐릭터챗.md"
  # 세계관(월드 바이블) = 존재할 때만 자동 활성(운영자가 _TEMPLATE_세계관.md 채워 이 이름으로 승격하면 켜짐 · 260703).
  # ⚠️ 순서 계약: 00(하드룰) → 10(세계 공통 — 페르소나 불변 = 캐시 접두 안정) → 카드(맨 뒤·말투 제1규칙이 최종 우선).
  [ -f "apps/yeta/10_세계관.md" ] && echo "apps/yeta/10_세계관.md"
  if [ -f "apps/yeta/characters/${id}.md" ]; then echo "apps/yeta/characters/${id}.md"
  else echo "viewer/characters/epic/${id}/CLAUDE.md"; fi   # 에픽 캐릭터 = 자산 폴더 동거 카드(운영자 260707 — 카드+이미지 한 폴더 · characters/epic/<id>/)
}

character_block() {
  local id="$1" f
  echo "===== [캐릭터 지침 — 아래 내용이 너의 전부다. 별도 파일을 읽을 필요 없다] ====="
  while IFS= read -r f; do
    [ -f "$f" ] || { echo "⚠️ inject_character: 파일 없음 $f" >&2; return 1; }
    echo ""
    echo "----- ${f} -----"
    cat "$f"
  done < <(_yc_files "$id")
  echo ""
  echo "===== [캐릭터 지침 끝] ====="
}

# R6 정규화(inject_guidelines.sh guidelines_version 동형): 경로 헤더·줄끝 공백·빈 줄 제외 =
# rename·공백만 바뀌면 같은 버전(불필요 "업데이트됨" 배지 방지) · 문장이 바뀌면 해시 변경(드리프트 감지 유지).
character_version() {
  character_block "$1" \
    | sed -e 's/[[:space:]]*$//' \
    | grep -vE '^----- .* -----$' \
    | sed -e '/^[[:space:]]*$/d' \
    | sha256sum | cut -c1-12
}
