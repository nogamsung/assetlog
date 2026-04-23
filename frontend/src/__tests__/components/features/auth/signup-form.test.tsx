import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { SignupForm } from "@/components/features/auth/signup-form";
import * as authApi from "@/lib/api/auth";

const mockPush = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  useSearchParams: () => new URLSearchParams(),
}));

jest.mock("@/lib/api/auth");
const mockedSignup = jest.mocked(authApi.signup);

function renderSignupForm() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <SignupForm />
    </QueryClientProvider>,
  );
}

const fakeUser: authApi.UserResponse = {
  id: 1,
  email: "new@example.com",
  createdAt: "2024-01-01T00:00:00Z",
};

describe("SignupForm", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("이메일, 비밀번호, 회원가입 버튼이 렌더된다", () => {
    renderSignupForm();
    expect(screen.getByLabelText("이메일")).toBeInTheDocument();
    expect(screen.getByLabelText("비밀번호")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /회원가입/ }),
    ).toBeInTheDocument();
  });

  it("로그인 링크가 있다", () => {
    renderSignupForm();
    expect(screen.getByRole("link", { name: /로그인/ })).toBeInTheDocument();
  });

  it("짧은 비밀번호 제출 시 유효성 에러를 표시한다", async () => {
    const user = userEvent.setup();
    renderSignupForm();

    await user.type(screen.getByLabelText("이메일"), "new@example.com");
    await user.type(screen.getByLabelText("비밀번호"), "short");
    await user.click(screen.getByRole("button", { name: /회원가입/ }));

    await waitFor(() => {
      expect(
        screen.getByText("비밀번호는 8자 이상이어야 합니다"),
      ).toBeInTheDocument();
    });
    expect(mockedSignup).not.toHaveBeenCalled();
  });

  it("숫자 미포함 비밀번호 제출 시 유효성 에러를 표시한다", async () => {
    const user = userEvent.setup();
    renderSignupForm();

    await user.type(screen.getByLabelText("이메일"), "new@example.com");
    await user.type(screen.getByLabelText("비밀번호"), "passwordonly");
    await user.click(screen.getByRole("button", { name: /회원가입/ }));

    await waitFor(() => {
      expect(screen.getByText("숫자 1자 이상 포함")).toBeInTheDocument();
    });
  });

  it("올바른 입력 시 signup mutation 을 호출한다", async () => {
    mockedSignup.mockResolvedValueOnce(fakeUser);
    const user = userEvent.setup();
    renderSignupForm();

    await user.type(screen.getByLabelText("이메일"), "new@example.com");
    await user.type(screen.getByLabelText("비밀번호"), "password1");
    await user.click(screen.getByRole("button", { name: /회원가입/ }));

    await waitFor(() => {
      expect(mockedSignup).toHaveBeenCalledWith(
        expect.objectContaining({
          email: "new@example.com",
          password: "password1",
        }),
        expect.anything(),
      );
    });
  });

  it("409 중복 이메일 에러 시 에러 메시지를 표시한다", async () => {
    const axiosError = Object.assign(new Error("Conflict"), {
      response: { data: { detail: "이미 사용 중인 이메일입니다." } },
    });
    mockedSignup.mockRejectedValueOnce(axiosError);
    const user = userEvent.setup();
    renderSignupForm();

    await user.type(screen.getByLabelText("이메일"), "existing@example.com");
    await user.type(screen.getByLabelText("비밀번호"), "password1");
    await user.click(screen.getByRole("button", { name: /회원가입/ }));

    await waitFor(() => {
      expect(
        screen.getByText("이미 사용 중인 이메일입니다."),
      ).toBeInTheDocument();
    });
  });
});
