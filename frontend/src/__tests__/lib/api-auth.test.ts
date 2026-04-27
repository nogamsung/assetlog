import { login, logout, getMe } from "@/lib/api/auth"; // {/* MODIFIED */}
import { apiClient } from "@/lib/api-client";
import type { UserResponse } from "@/lib/api/auth";

jest.mock("@/lib/api-client", () => ({
  apiClient: {
    post: jest.fn(),
    get: jest.fn(),
  },
}));

const mockedPost = jest.mocked(apiClient.post);
const mockedGet = jest.mocked(apiClient.get);

const rawUser = {
  id: 1,
};

const expectedUser: UserResponse = {
  id: 1,
};

describe("auth API", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("login", () => {
    it("POST /api/auth/login 을 password 만 담아 호출하고 UserResponse 를 반환한다", async () => { // {/* MODIFIED */}
      mockedPost.mockResolvedValueOnce({ data: rawUser });
      const result = await login({ password: "secret123" }); // {/* MODIFIED */}
      expect(mockedPost).toHaveBeenCalledWith("/api/auth/login", {
        password: "secret123", // {/* MODIFIED */}
      });
      expect(result).toEqual(expectedUser);
    });

    it("email 필드를 body 에 포함하지 않는다", async () => { // {/* ADDED */}
      mockedPost.mockResolvedValueOnce({ data: rawUser });
      await login({ password: "secret123" });
      const callArg = (mockedPost.mock.calls[0] as [string, unknown])[1] as Record<string, unknown>;
      expect(callArg).not.toHaveProperty("email");
    });

    it("429 응답 시 에러를 throw 한다 (Retry-After 헤더는 호출자가 처리)", async () => { // {/* ADDED */}
      const retryError = Object.assign(new Error("Too Many Requests"), {
        response: {
          status: 429,
          data: { detail: "Too many login attempts. Try again in 30 seconds." },
          headers: { "retry-after": "30" },
        },
      });
      mockedPost.mockRejectedValueOnce(retryError);
      await expect(login({ password: "any" })).rejects.toThrow("Too Many Requests");
    });
  });

  describe("logout", () => {
    it("POST /api/auth/logout 를 호출한다", async () => {
      mockedPost.mockResolvedValueOnce({ data: undefined });
      await logout();
      expect(mockedPost).toHaveBeenCalledWith("/api/auth/logout", {});
    });
  });

  describe("getMe", () => {
    it("GET /api/auth/me 를 호출하고 UserResponse 를 반환한다", async () => {
      mockedGet.mockResolvedValueOnce({ data: rawUser });
      const result = await getMe();
      expect(mockedGet).toHaveBeenCalledWith("/api/auth/me");
      expect(result).toEqual(expectedUser);
    });

    it("401 에러 시 throw 한다", async () => {
      const error = Object.assign(new Error("Unauthorized"), {
        response: { status: 401 },
      });
      mockedGet.mockRejectedValueOnce(error);
      await expect(getMe()).rejects.toThrow("Unauthorized");
    });
  });
});
