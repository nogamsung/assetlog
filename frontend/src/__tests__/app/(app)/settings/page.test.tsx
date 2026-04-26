import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SettingsPage from "@/app/(app)/settings/page";
import * as useAuthModule from "@/hooks/use-auth";
import * as useExportModule from "@/hooks/use-export"; // ADDED
import type { UserResponse } from "@/lib/api/auth";

const mockPush = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

jest.mock("@/hooks/use-auth");
jest.mock("@/hooks/use-export"); // ADDED
jest.mock("@/stores/theme", () => ({
  useThemeStore: jest.fn(() => ({
    theme: "system",
    setTheme: jest.fn(),
  })),
}));

// lucide icons used in ThemeToggle and export buttons
jest.mock("lucide-react", () => ({
  Sun: () => <svg data-testid="icon-sun" />,
  Moon: () => <svg data-testid="icon-moon" />,
  Monitor: () => <svg data-testid="icon-monitor" />,
  Settings: () => <svg data-testid="icon-settings" />,
  Download: () => <svg data-testid="icon-download" />, // ADDED
}));

const mockedUseCurrentUser = jest.mocked(useAuthModule.useCurrentUser);
const mockedUseLogout = jest.mocked(useAuthModule.useLogout);
const mockedUseExportData = jest.mocked(useExportModule.useExportData); // ADDED

const fakeUser: UserResponse = {
  id: 1,
  email: "test@example.com",
  createdAt: "2024-01-01T00:00:00Z",
};

function setupMocks({
  user = fakeUser,
  logoutPending = false,
  exportPending = false, // ADDED
}: {
  user?: UserResponse | null;
  logoutPending?: boolean;
  exportPending?: boolean; // ADDED
} = {}) {
  mockedUseCurrentUser.mockReturnValue({
    data: user ?? undefined,
    isLoading: false,
    isError: false,
    error: null,
  } as unknown as ReturnType<typeof useAuthModule.useCurrentUser>);

  const mockMutate = jest.fn();
  mockedUseLogout.mockReturnValue({
    mutate: mockMutate,
    isPending: logoutPending,
    isError: false,
    isSuccess: false,
    error: null,
  } as unknown as ReturnType<typeof useAuthModule.useLogout>);

  const mockExportMutate = jest.fn(); // ADDED
  mockedUseExportData.mockReturnValue({ // ADDED
    mutate: mockExportMutate,
    isPending: exportPending,
    isError: false,
    isSuccess: false,
    error: null,
  } as unknown as ReturnType<typeof useExportModule.useExportData>);

  return { mockMutate, mockExportMutate }; // MODIFIED
}

describe("SettingsPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("페이지 제목 '설정' 을 렌더링한다", () => {
    setupMocks();
    render(<SettingsPage />);
    expect(screen.getByRole("heading", { name: "설정" })).toBeInTheDocument();
  });

  it("계정 카드가 렌더링된다", () => {
    setupMocks();
    render(<SettingsPage />);
    expect(screen.getByText("계정")).toBeInTheDocument();
    expect(screen.getByText("단일 사용자 계정")).toBeInTheDocument();
  });

  it("유저 이메일과 가입일을 표시한다", () => {
    setupMocks({ user: fakeUser });
    render(<SettingsPage />);
    expect(screen.getByText("test@example.com")).toBeInTheDocument();
    // createdAt 포맷팅 확인 (한국 날짜 포맷)
    expect(screen.getByText(/2024/)).toBeInTheDocument();
  });

  it("로그아웃 버튼이 렌더링된다", () => {
    setupMocks();
    render(<SettingsPage />);
    expect(screen.getByRole("button", { name: "로그아웃" })).toBeInTheDocument();
  });

  it("로그아웃 버튼 클릭 시 mutate 가 호출된다", async () => {
    const user = userEvent.setup();
    const { mockMutate } = setupMocks();
    render(<SettingsPage />);
    await user.click(screen.getByRole("button", { name: "로그아웃" }));
    expect(mockMutate).toHaveBeenCalled();
  });

  it("isPending=true 면 로그아웃 버튼이 비활성화된다", () => {
    setupMocks({ logoutPending: true });
    render(<SettingsPage />);
    const btn = screen.getByRole("button", { name: "로그아웃" });
    expect(btn).toBeDisabled();
    expect(btn).toHaveTextContent("로그아웃 중...");
  });

  it("테마 카드가 렌더링된다", () => {
    setupMocks();
    render(<SettingsPage />);
    expect(screen.getByText("테마")).toBeInTheDocument();
    expect(screen.getByText(/System은 OS 설정을 따릅니다/)).toBeInTheDocument();
  });

  it("ThemeToggle (테마 선택 group) 이 렌더링된다", () => {
    setupMocks();
    render(<SettingsPage />);
    expect(screen.getByRole("group", { name: "테마 선택" })).toBeInTheDocument();
  });

  it("보안 카드가 렌더링된다", () => {
    setupMocks();
    render(<SettingsPage />);
    expect(screen.getByText("보안")).toBeInTheDocument();
    expect(screen.getByText("비밀번호는 서버 환경변수로 관리됩니다.")).toBeInTheDocument();
    expect(screen.getByText("비밀번호 변경은 서버 재배포가 필요합니다.")).toBeInTheDocument();
  });

  // ADDED
  it("데이터 백업 카드와 JSON 다운로드 버튼이 렌더링된다", () => {
    setupMocks();
    render(<SettingsPage />);
    expect(screen.getByText("데이터 백업")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "데이터를 JSON 으로 내려받기" }),
    ).toBeInTheDocument();
  });

  // ADDED
  it("데이터 백업 카드와 CSV (ZIP) 다운로드 버튼이 렌더링된다", () => {
    setupMocks();
    render(<SettingsPage />);
    expect(
      screen.getByRole("button", { name: "데이터를 CSV(ZIP) 로 내려받기" }),
    ).toBeInTheDocument();
  });

  // ADDED
  it("JSON 다운로드 버튼 클릭 시 exportMutation.mutate('json') 가 호출된다", async () => {
    const user = userEvent.setup();
    const { mockExportMutate } = setupMocks();
    render(<SettingsPage />);
    await user.click(
      screen.getByRole("button", { name: "데이터를 JSON 으로 내려받기" }),
    );
    expect(mockExportMutate).toHaveBeenCalledWith("json");
  });

  // ADDED
  it("CSV (ZIP) 다운로드 버튼 클릭 시 exportMutation.mutate('csv') 가 호출된다", async () => {
    const user = userEvent.setup();
    const { mockExportMutate } = setupMocks();
    render(<SettingsPage />);
    await user.click(
      screen.getByRole("button", { name: "데이터를 CSV(ZIP) 로 내려받기" }),
    );
    expect(mockExportMutate).toHaveBeenCalledWith("csv");
  });

  // ADDED
  it("exportPending=true 면 다운로드 버튼이 비활성화된다", () => {
    setupMocks({ exportPending: true });
    render(<SettingsPage />);
    expect(
      screen.getByRole("button", { name: "데이터를 JSON 으로 내려받기" }),
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "데이터를 CSV(ZIP) 로 내려받기" }),
    ).toBeDisabled();
  });
});
