# tests/ — yeta_v3 세션 어댑터 회귀 + 대화 품질 스냅샷

> **대상**: `.github/scripts/yeta_v3.py`(러너 세션 로직 = 마이그레이션·방·스레드 선택 SSOT).
> **왜**: 이 로직이 "대화가 **어떤 방·페르소나·기억**으로 풀리는지"를 좌우하는데 회귀 테스트가 0이었다 → 리팩터 때 대화 품질이 **조용히** 바뀌어도 안 잡혔다. 이 테스트는 그 변화를 **전/후로 눈에 보이게** 만든다.
> **의존성 0**: pytest 불요 — 파이썬 stdlib만. `python3 tests/test_yeta_v3.py`.

## "대화 품질"을 어떻게 보나
`yeta_v3.py`는 LLM 답변 텍스트가 아니라 **대화의 뼈대**(어떤 방이 열리고, 어떤 페르소나가 나오고, 대기 중 유저가 무시되지 않고, 타 방 비밀이 안 새는지)를 정한다. 이 뼈대 = '풀린 대화 상태' 스냅샷 = 대화 품질의 관측 가능한 대리지표.

## 3층 방어
1. **스펙 불변식** (박제 아님 — docstring + JS 쌍둥이 `functions/api/yeta.js:migrateV3`에서 도출)
   - `멱등` 재마이그레이션이 세션 안 망침 · `턴무손실` 대화 안 사라짐 · `cur유효` · `방≤2` · `비밀누수차단`(`_others`에 턴 텍스트 없음).
2. **골든 스냅샷** — 시나리오별 '풀린 대화 상태'(cur·threads·pick·view)를 `yeta_v3_golden.json`에 박제. 코드가 바뀌면 **읽을 수 있는 before/after diff**로 노출 (예: `pick : 'a' → 'b'` = 풀리는 대화가 바뀜).
3. **parity** — JS `migrateV3` 실물을 추출·node로 실행해 PY와 대조(동형 붕괴 자동 포착). *알려진 차이 1건*: `null` 입력 — JS는 상류 `EMPTY()`가 처리(`migrateV3(null)=null`), PY는 인라인 골격. 문서화됨.

## 실행
```
python3 tests/test_yeta_v3.py            # 체크(불변식+골든) · rc=0 통과 / rc=1 회귀
python3 tests/test_yeta_v3.py --report   # 대화 품질 상태를 사람이 읽게 출력(전/후 눈으로)
python3 tests/test_yeta_v3.py --update   # 골든 재생성(= 의도된 변경 승인 · diff 확인 후에만)
python3 tests/test_yeta_v3.py --parity   # JS↔PY 동형 대조(node 필요)
```

## 전/후 워크플로
1. 로직 바꾸기 전 = 현재 골든이 **before**.
2. 바꾼 뒤 `python3 tests/test_yeta_v3.py` → 변화가 있으면 **after diff** 출력.
3. 그 diff가 **의도한 개선**이면 `--update`로 골든 갱신(=승인), **의도 안 한 회귀**면 코드 되돌림.
4. 사람이 통째로 보려면 `--report`(전 시나리오 상태를 라벨로).

## 시나리오(픽스처)
`01` 신규(null)·`02` v2단일→v3(대화 무손실)·`03` persona 무턴 엣지·`04` v3 멱등·`05` 다중방 FIFO(기아방지)·`06` invite 분기·`07` 타방 비밀누수차단.

## CI/커밋 게이트로 물리기(옵션)
`rc=1`이라 그대로 게이트에 걸 수 있다 — `shared/check_refs.py`에 한 줄 추가(하드 or WARN)하거나 워크플로로. 자동 부착은 운영자 승인 후(기틀 변경 = `[9]`). 참고: 사망/부활 로직은 JS(`functions/api/yeta.js`)라 이 PY 테스트 범위 밖 → JS측 테스트는 후속.
