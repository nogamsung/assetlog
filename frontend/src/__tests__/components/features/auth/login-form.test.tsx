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
  email: "test@example.com",
  createdAt: "2024-01-01T00:00:00Z",
};

describe("LoginForm", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("이메일, 비밀번호, 로그인 버튼이 렌더된다", () => {
    renderLoginForm();
    expect(screen.getByLabelText("이메일")).toBeInTheDocument();
    expect(screen.getByLabelText("비밀번호")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /로그인/ }),
    ).toBeInTheDocument();
  });

  it("회원가입 링크가 있다", () => {
    renderLoginForm();
    expect(screen.getByRole("link", { name: /회원가입/ })).toBeInTheDocument();
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

  it("올바른 입력 시 login mutation 을 호출한다", async () => {
    mockedLogin.mockResolvedValueOnce(fakeUser);
    const user = userEvent.setup();
    renderLoginForm();

    await user.type(screen.getByLabelText("이메일"), "test@example.com");
    await user.type(screen.getByLabelText("비밀번호"), "password123");
    await user.click(screen.getByRole("button", { name: /로그인/ }));

    await waitFor(() => {
      expect(mockedLogin).toHaveBeenCalledWith(
        expect.objectContaining({
          email: "test@example.com",
          password: "password123",
        }),
      );
    });
  });

  it("API 에러 시 에러 메시지를 표시한다", async () => {
    const axiosError = Object.assign(new Error("Unauthorized"), {
      response: { data: { detail: "이메일 또는 비밀번호가 올바르지 않습니다." } },
    });
    mockedLogin.mockRejectedValueOnce(axiosError);
    const user = userEvent.setup();
    renderLoginForm();

    await user.type(screen.getByLabelText("이메일"), "test@example.com");
    await user.type(screen.getByLabelText("비밀번호"), "wrongpass1");
    await user.click(screen.getByRole("button", { name: /로그인/ }));

    await waitFor(() => {
      expect(
        screen.getByText("이메일 또는 비밀번호가 올바르지 않습니다."),
      ).toBeInTheDocument();
    });
  });
});
