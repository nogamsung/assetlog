import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React, { Suspense } from "react";
import { LoginForm } from "@/components/features/auth/login-form";
import * as authApi from "@/lib/api/auth";

const mockPush = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  useSearchParams: () => new URLSearchParams(),
}));

jest.mock("@/lib/api/auth");
const mockedLogin = jest.mocked(authApi.login);

jest.mock("sonner", () => ({
  toast: Object.assign(jest.fn(), { error: jest.fn() }),
}));
import { toast } from "sonner";
const mockedToastError = jest.mocked(toast.error);

function renderLoginForm() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <Suspense>
        <LoginForm />
      </Suspense>
    </QueryClientProvider>,
  );
}

const fakeUser: authApi.UserResponse = {
  id: 1,
  email: "owner@example.com",
  createdAt: "2024-01-01T00:00:00Z",
};

describe("LoginForm", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("비밀번호 입력과 로그인 버튼이 렌더된다", () => {
    renderLoginForm();
    expect(screen.getByLabelText("비밀번호")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /로그인/ }),
    ).toBeInTheDocument();
  });

  it("이메일 입력이 없다", () => {
    renderLoginForm();
    expect(screen.queryByLabelText("이메일")).not.toBeInTheDocument();
  });

  it("회원가입 링크가 없다", () => {
    renderLoginForm();
    expect(screen.queryByRole("link", { name: /회원가입/ })).not.toBeInTheDocument();
  });

  it("빈 폼 제출 시 유효성 에러를 표시한다", async () => {
    const user = userEvent.setup();
    renderLoginForm();

    await user.click(screen.getByRole("button", { name: /로그인/ }));

    await waitFor(() => {
      expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
    });
    expect(mockedLogin).not.toHaveBeenCalled();
  });

  it("비밀번호 입력 후 login mutation 을 password 만 담아 호출한다", async () => {
    mockedLogin.mockResolvedValueOnce(fakeUser);
    const user = userEvent.setup();
    renderLoginForm();

    await user.type(screen.getByLabelText("비밀번호"), "secret123");
    await user.click(screen.getByRole("button", { name: /로그인/ }));

    await waitFor(() => {
      expect(mockedLogin).toHaveBeenCalledWith({ password: "secret123" });
    });
  });

  it("401 에러 시 toast.error('비밀번호가 올바르지 않습니다.') 를 호출한다", async () => {
    const axiosError = Object.assign(new Error("Unauthorized"), {
      response: {
        status: 401,
        data: { detail: "Invalid password" },
        headers: {},
      },
    });
    mockedLogin.mockRejectedValueOnce(axiosError);
    const user = userEvent.setup();
    renderLoginForm();

    await user.type(screen.getByLabelText("비밀번호"), "wrong");
    await user.click(screen.getByRole("button", { name: /로그인/ }));

    await waitFor(() => {
      expect(mockedToastError).toHaveBeenCalledWith(
        "비밀번호가 올바르지 않습니다.",
      );
    });
  });

  it("429 에러 시 Retry-After 헤더를 사용해 toast.error 를 호출한다", async () => {
    const axiosError = Object.assign(new Error("Too Many Requests"), {
      response: {
        status: 429,
        data: { detail: "Too many login attempts. Try again in 30 seconds." },
        headers: { "retry-after": "30" },
      },
    });
    mockedLogin.mockRejectedValueOnce(axiosError);
    const user = userEvent.setup();
    renderLoginForm();

    await user.type(screen.getByLabelText("비밀번호"), "anypass");
    await user.click(screen.getByRole("button", { name: /로그인/ }));

    await waitFor(() => {
      expect(mockedToastError).toHaveBeenCalledWith("30초 후 다시 시도해주세요.");
    });
  });

  it("503 에러 시 서버 미설정 toast.error 를 호출한다", async () => {
    const axiosError = Object.assign(new Error("Service Unavailable"), {
      response: {
        status: 503,
        data: { detail: "Owner password not configured" },
        headers: {},
      },
    });
    mockedLogin.mockRejectedValueOnce(axiosError);
    const user = userEvent.setup();
    renderLoginForm();

    await user.type(screen.getByLabelText("비밀번호"), "anypass");
    await user.click(screen.getByRole("button", { name: /로그인/ }));

    await waitFor(() => {
      expect(mockedToastError).toHaveBeenCalledWith(
        "서버 비밀번호 미설정. 관리자에게 문의하세요.",
      );
    });
  });
});
