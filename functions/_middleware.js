// [yeta 분리] pages.dev 우회 차단용 강제 리다이렉트 자리 — 커스텀 도메인 + Cloudflare Access 를 붙일 때 활성화.
// 지금은 도메인 미정이라 통과(yeta.pages.dev 직접 접속 허용). 도메인 정하면 아래 2줄 주석 해제 + hostname 교체.
// (원본 nomute 패턴: production `*.pages.dev` 는 Access 가 기본으로 못 막음 → 커스텀 도메인으로 301 강제해
//  반드시 Access 인증을 거치게 했다. yeta 대화도 비공개로 두려면 도메인 확정 후 동일 패턴 재활성.)
export async function onRequest(context) {
  // const url = new URL(context.request.url);
  // if (url.hostname.endsWith('.pages.dev')) { url.hostname = 'YETA_커스텀도메인'; return Response.redirect(url.toString(), 301); }
  return context.next();
}
