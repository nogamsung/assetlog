import { signup, login, logout, getMe } from "@/lib/api/auth";
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
  email: "test@example.com",
  created_at: "2024-01-01T00:00:00Z",
};

const expectedUser: UserResponse = {
  id: 1,
  email: "test@example.com",
  createdAt: "2024-01-01T00:00:00Z",
};

describe("auth API", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("signup", () => {
    it("POST /api/auth/signup 를 호출하고 UserResponse 를 반환한다", async () => {
      mockedPost.mockResolvedValueOnce({ data: rawUser });
      const result = await signup({
        email: "test@example.com",
        password: "password1",
      });
      expect(mockedPost).toHaveBeenCalledWith("/api/auth/signup", {
        email: "test@example.com",
        password: "password1",
      });
      expect(result).toEqual(expectedUser);
    });

    it("에러 시 throw 한다", async () => {
      mockedPost.mockRejectedValueOnce(new Error("Network error"));
      await expect(
        signup({ email: "test@example.com", password: "password1" }),
      ).rejects.toThrow("Network error");
    });
  });

  describe("login", () => {
    it("POST /api/auth/login 를 호출하고 UserResponse 를 반환한다", async () => {
      mockedPost.mockResolvedValueOnce({ data: rawUser });
      const result = await login({
        email: "test@example.com",
        password: "password1",
      });
      expect(mockedPost).toHaveBeenCalledWith("/api/auth/login", {
        email: "test@example.com",
        password: "password1",
      });
      expect(result).toEqual(expectedUser);
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
