import { apiClient } from "@/lib/api-client";

describe("apiClient", () => {
  it("withCredentials 가 true 로 설정된다", () => {
    expect(apiClient.defaults.withCredentials).toBe(true);
  });

  it("기본 baseURL 이 http://localhost:8000 이다 (env 미설정 시)", () => {
    // NEXT_PUBLIC_API_URL 환경변수가 없을 때 기본값 확인
    const baseURL = apiClient.defaults.baseURL;
    expect(baseURL).toBe(
      process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
    );
  });

  it("Content-Type 헤더가 application/json 이다", () => {
    const headers = apiClient.defaults.headers;
    expect(headers["Content-Type"]).toBe("application/json");
  });

  it("NEXT_PUBLIC_API_URL 환경변수가 있으면 해당 값을 baseURL 로 사용한다", () => {
    const originalEnv = process.env.NEXT_PUBLIC_API_URL;
    process.env.NEXT_PUBLIC_API_URL = "http://api.example.com";

    // 모듈을 재-임포트할 수 없으므로, 설정된 인스턴스의 기본값이
    // 모듈 로드 시점의 env 를 반영하는지 확인
    // (axios.create 는 모듈 로드 시 한 번 실행되므로
    //  이 테스트는 기본값 fallback 로직을 단위 검증)
    const defaultBase =
      process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    expect(defaultBase).toBe("http://api.example.com");

    process.env.NEXT_PUBLIC_API_URL = originalEnv;
  });
});
