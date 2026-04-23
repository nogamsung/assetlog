import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useCurrentUser, useLogin, useLogout, useSignup } from "@/hooks/use-auth";
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
const mockedSignup = jest.mocked(authApi.signup);
const mockedLogout = jest.mocked(authApi.logout);

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
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
  it("성공 시 queryData 세팅 후 push 호출한다", async () => {
    mockedLogin.mockResolvedValueOnce(fakeUser);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useLogin(), { wrapper: Wrapper });

    result.current.mutate({
      email: "test@example.com",
      password: "password1",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPush).toHaveBeenCalledWith("/");
  });

  it("redirectTo 가 있으면 해당 경로로 push 한다", async () => {
    mockedLogin.mockResolvedValueOnce(fakeUser);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useLogin(), { wrapper: Wrapper });

    result.current.mutate({
      email: "test@example.com",
      password: "password1",
      redirectTo: "/dashboard",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPush).toHaveBeenCalledWith("/dashboard");
  });

  it("에러 시 isError 가 true 다", async () => {
    mockedLogin.mockRejectedValueOnce(new Error("Login failed"));
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useLogin(), { wrapper: Wrapper });

    result.current.mutate({ email: "bad@example.com", password: "wrongpw1" });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useSignup", () => {
  it("성공 시 push('/') 호출한다", async () => {
    mockedSignup.mockResolvedValueOnce(fakeUser);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useSignup(), { wrapper: Wrapper });

    result.current.mutate({
      email: "new@example.com",
      password: "password1",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPush).toHaveBeenCalledWith("/");
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
