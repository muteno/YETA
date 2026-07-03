# Pexels 감정 배경 큐레이션 — 설계 정본 (대기 큐 · 운영자 확정 260703)

> **상태 = 큐잉(미구현).** 운영자 확정: 감정(무드) 배경 소스 = **Pexels API**. 키 등록(아래 §운영자 액션) 후
> 이 문서대로 구현한다. ⚠️ 이 파일은 프롬프트 주입 체인(00→10→카드) 밖 = 지침 해시 무영향.

## 0. 전제 (이미 라이브 — 재작업 금지)
- 무드 체인 = **소스 무관으로 이미 완성**(#1398): 답장 `<<MOOD:base|warm|tense|blue>>` → `yeta_chat.sh`가 턴에 `mood` 박제 → 뷰어 `yStage()`가 배경 크로스페이드. **Pexels는 yStage의 이미지 공급자만 교체/추가**하면 됨(태그·파서·턴 스키마 재설계 0).
- Gemini 자산(base 8 + 배리언트 24 · R2 `yeta_bg/`) = **폴백으로 유지**(운영자 "이미 쏜 건 어쩔 수 없고" → 오프라인 안전망으로 활용). 삭제 금지.

## 1. 큐레이션 3층 (핵심 고민의 답)
"무드로 검색하면 장소가 중구난방"이 스톡 큐레이션의 최대 함정 — **무대(stage) 축을 쿼리에 같이 박아** 장소 통제, 품질은 API 파라미터 + 응답 메타(avg_color)로 거른다. LLM 추가 콜 0.

### 1층 — 쿼리 테이블 (정확도 · stage × mood 고정 매핑)
영문 쿼리(Pexels는 영문 검색 질이 압도적). 테이블은 **프록시(functions/api/pexels.js) 안에 상수로** — 뷰어가 임의 쿼리를 못 보냄(남용 차단) + 운영자가 문구만 조정 가능.
| stage | warm | tense | blue |
|---|---|---|---|
| tea(찻집) | cozy tea house cafe night warm lamp | empty cafe night dark moody window | rainy cafe window night quiet |
| teacorner | laptop cafe corner night warm light | dim cafe late night shadow | empty cafe table rain night |
| office(편집국) | newsroom desk lamp night warm | dark office night blinds moody | empty office night city lights rain |
| studio(연습실) | dance studio mirror soft light | dark dance studio dramatic light | empty dance studio night blue |
| alley(골목) | night alley string lights warm | dark narrow alley night rain moody | rainy alley neon reflection lonely |
| dojo(검도장) | wooden dojo warm lantern night | dark dojo moonlight dramatic | empty dojo rain night blue |
| gym(체육관) | boxing gym warm light evening | dark gym dramatic shadow | empty gym dawn blue light |
| radio(부스) | radio studio warm glow night | dark studio red light moody | empty radio booth night blue |
- **base 무드는 Pexels 안 씀** — roster의 Gemini base 8장 유지(무대 정체성 앵커). Pexels는 warm/tense/blue 전환시에만.

### 2층 — API 파라미터 (구조 필터)
`GET https://api.pexels.com/v1/search` · 헤더 `Authorization: <key>` · `query=<테이블>` · **`orientation=portrait`**(9:16 결 · 뷰어 cover+center가 중앙 크롭) · `size=large` · `per_page=15`.

### 3층 — 클라 선별 (품질 · 응답 메타 = 공짜 신호)
Pexels 응답의 `avg_color`(사진 평균색 hex)로 후보 15장을 거른다:
1. **루마 컷**: `0.2126R+0.7152G+0.0722B > 110` → 컷(채팅 배경 = 어두운 사진만 — 다크 그라데 .72/.86를 얹어도 밝은 사진은 글자 대비 해침).
2. **무드-색 정합 보너스**: warm = R>B 우선 / tense·blue = B≥R 우선(정렬 가중, 하드컷 아님).
3. **신선도**: 최근 사용 photo id(localStorage 최근 10개) 제외 후 상위권 **랜덤 픽** = "매번 새 사진"(운영자가 Pexels 고른 이유).
4. **빈손 폴백 체인**: 통과 0장 → Gemini 배리언트(`yeta_bg/<stage>_<mood>.png`) → base → 색 틴트(기존 yStage 체인 그대로 뒤에 붙음).
- 이미지 URL은 `photo.src.large2x`(핫링크 = Pexels CDN 허용·권장) — R2 재호스팅 불요.

## 2. 호출 경로 (키 보안 — 이 구조 필수)
- ⚠️ **키를 뷰어 JS에 박으면 안 됨**(공개 레포+공개 페이지 = 유출·쿼터 도둑).
- **`functions/api/pexels.js` 프록시 신설**: `originOk`(publish.js 계승·CSRF) · 입력 = `{stage, mood}` **키만**(서버측 테이블에서 쿼리 조립 = 임의 쿼리 봉쇄) · `cf: {cacheTtl: 3600}`(같은 stage×mood 1h 엣지 캐시) · `env.PEXELS_API_KEY` 없으면 `{ok:false}`(뷰어 = 조용히 Gemini 폴백).
- 뷰어 `yStage()`: mood 있고 프록시 응답 ok면 Pexels 픽 → 프리로드 성공 시 크로스페이드(기존 im.onload 패턴 그대로) · 실패/빈손 = 기존 배리언트 경로.

## 3. rate (여유 실증 계산)
무료 200콜/h · 2만/월. 호출 = **무드 전환시에만**(같은 무드 연속 = yStage 키 가드 no-op) + 1h 엣지 캐시 → 실사용 하루 수십 콜 이하. 여유 큼 — 상한 설계 불요.

## 4. 어트리뷰션 (라이선스 정직)
Pexels 라이선스 = 무료·상업 OK·크레딧 **권장(필수 아님)**·핫링크 허용. 크레딧 표기는 운영자 선택 — 붙일 경우 배경 우하단에 사진작가명 아주 작게(`photo.photographer`).

## 5. 운영자 액션 (이것만 하면 켜짐)
1. https://www.pexels.com/api/ 가입 → API 키 발급(즉시·무료).
2. Cloudflare Pages 대시보드 → 프로젝트 환경변수 `PEXELS_API_KEY` 등록 → 재배포.
3. 아무 세션에서 `git yeta pexels 붙여줘` → 이 문서대로 구현(프록시 + 뷰어 yStage 분기 + 쿼리 테이블).
