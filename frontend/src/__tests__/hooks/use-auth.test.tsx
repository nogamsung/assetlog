import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useCurrentUser, useLogin, useLogout } from "@/hooks/use-auth"; // {/* MODIFIED */}
import * as authApi from "@/lib/api/auth";

// Next.js router mock
const mockPush = jest.fn();
const mockReplace = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  useSearchParams: () => ({ get: () => null }),
}));

// API mock
jest.mock("@/lib/api/auth");
const mockedGetMe = jest.mocked(authApi.getMe);
const mockedLogin = jest.mocked(authApi.login);
const mockedLogout = jest.mocked(authApi.logout);

// sonner toast mock {/* ADDED */}
jest.mock("sonner", () => ({
  toast: Object.assign(jest.fn(), { error: jest.fn() }),
}));
import { toast } from "sonner";
const mockedToastError = jest.mocked(toast.error);

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  return { Wrapper, queryClient };
}

const fakeUser: authApi.UserResponse = {
  id: 1,
  email: "test@example.com",
  createdAt: "2024-01-01T00:00:00Z",
};

describe("useCurrentUser", () => {
  it("성공 시 UserResponse 를 반환한다", async () => {
    mockedGetMe.mockResolvedValueOnce(fakeUser);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useCurrentUser(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(fakeUser);
  });

  it("401 에러 시 null 을 반환한다 (조용히 처리)", async () => {
    const error = Object.assign(new Error("Unauthorized"), {
      response: { status: 401 },
    });
    mockedGetMe.mockRejectedValueOnce(error);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useCurrentUser(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeNull();
  });
});

describe("useLogin", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("성공 시 queryData 세팅 후 push 호출한다", async () => {
    mockedLogin.mockResolvedValueOnce(fakeUser);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useLogin(), { wrapper: Wrapper });

    result.current.mutate({ password: "secret123" }); // {/* MODIFIED */}

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPush).toHaveBeenCalledWith("/");
  });

  it("redirectTo 가 있으면 해당 경로로 push 한다", async () => {
    mockedLogin.mockResolvedValueOnce(fakeUser);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useLogin(), { wrapper: Wrapper });

    result.current.mutate({ password: "secret123", redirectTo: "/dashboard" }); // {/* MODIFIED */}

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPush).toHaveBeenCalledWith("/dashboard");
  });

  it("401 에러 시 toast.error('비밀번호가 올바르지 않습니다.') 를 호출한다", async () => { // {/* ADDED */}
    const axiosError = Object.assign(new Error("Unauthorized"), {
      response: { status: 401, data: { detail: "Invalid password" }, headers: {} },
    });
    mockedLogin.mockRejectedValueOnce(axiosError);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useLogin(), { wrapper: Wrapper });

    result.current.mutate({ password: "wrong" });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(mockedToastError).toHaveBeenCalledWith("비밀번호가 올바르지 않습니다.");
  });

  it("429 에러 시 Retry-After 헤더로 toast.error 를 호출한다", async () => { // {/* ADDED */}
    const axiosError = Object.assign(new Error("Too Many Requests"), {
      response: {
        status: 429,
        data: { detail: "Too many login attempts. Try again in 60 seconds." },
        headers: { "retry-after": "60" },
      },
    });
    mockedLogin.mockRejectedValueOnce(axiosError);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useLogin(), { wrapper: Wrapper });

    result.current.mutate({ password: "anypass" });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(mockedToastError).toHaveBeenCalledWith("60초 후 다시 시도해주세요.");
  });

  it("503 에러 시 관리자 문의 toast.error 를 호출한다", async () => { // {/* ADDED */}
    const axiosError = Object.assign(new Error("Service Unavailable"), {
      response: {
        status: 503,
        data: { detail: "Owner password not configured" },
        headers: {},
      },
    });
    mockedLogin.mockRejectedValueOnce(axiosError);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useLogin(), { wrapper: Wrapper });

    result.current.mutate({ password: "anypass" });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(mockedToastError).toHaveBeenCalledWith(
      "서버 비밀번호 미설정. 관리자에게 문의하세요.",
    );
  });
});

describe("useLogout", () => {
  it("성공 시 push('/login') 호출한다", async () => {
    mockedLogout.mockResolvedValueOnce(undefined);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useLogout(), { wrapper: Wrapper });

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPush).toHaveBeenCalledWith("/login");
  });
});
