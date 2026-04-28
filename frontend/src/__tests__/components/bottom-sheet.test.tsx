import { render, screen, fireEvent, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  BottomSheet,
  BottomSheetTrigger,
  BottomSheetContent,
  BottomSheetHeader,
  BottomSheetTitle,
  BottomSheetFooter,
} from "@/components/ui/bottom-sheet";

function TestSheet({ onOpenChange }: { onOpenChange?: (v: boolean) => void }) {
  return (
    <BottomSheet onOpenChange={onOpenChange}>
      <BottomSheetTrigger>열기</BottomSheetTrigger>
      <BottomSheetContent>
        <BottomSheetHeader>
          <BottomSheetTitle>시트 제목</BottomSheetTitle>
        </BottomSheetHeader>
        <p>시트 내용</p>
        <BottomSheetFooter>
          <button>확인</button>
        </BottomSheetFooter>
      </BottomSheetContent>
    </BottomSheet>
  );
}

describe("BottomSheet", () => {
  it("기본 상태에서 콘텐츠가 숨겨진다", () => {
    render(<TestSheet />);
    expect(screen.queryByText("시트 제목")).not.toBeInTheDocument();
    expect(screen.queryByText("시트 내용")).not.toBeInTheDocument();
  });

  it("Trigger 클릭 시 콘텐츠가 표시된다", () => {
    render(<TestSheet />);
    fireEvent.click(screen.getByText("열기"));
    expect(screen.getByText("시트 제목")).toBeInTheDocument();
    expect(screen.getByText("시트 내용")).toBeInTheDocument();
  });

  it("backdrop 클릭 시 닫힌다", () => {
    render(<TestSheet />);
    fireEvent.click(screen.getByText("열기"));
    expect(screen.getByText("시트 제목")).toBeInTheDocument();

    // Click backdrop (aria-hidden div before the sheet)
    const backdrop = document.querySelector("[aria-hidden='true']");
    if (backdrop) fireEvent.click(backdrop);
    expect(screen.queryByText("시트 제목")).not.toBeInTheDocument();
  });

  it("Escape 키 누르면 닫힌다", () => {
    render(<TestSheet />);
    fireEvent.click(screen.getByText("열기"));
    expect(screen.getByText("시트 제목")).toBeInTheDocument();

    act(() => {
      fireEvent.keyDown(document, { key: "Escape" });
    });
    expect(screen.queryByText("시트 제목")).not.toBeInTheDocument();
  });

  it("onOpenChange 콜백이 호출된다", () => {
    const onOpenChange = jest.fn();
    render(<TestSheet onOpenChange={onOpenChange} />);
    fireEvent.click(screen.getByText("열기"));
    expect(onOpenChange).toHaveBeenCalledWith(true);
  });

  it("열릴 때 role=dialog aria-modal=true 가 있다", () => {
    render(<TestSheet />);
    fireEvent.click(screen.getByText("열기"));
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
  });

  it("BottomSheetHeader 가 렌더링된다", () => {
    render(<TestSheet />);
    fireEvent.click(screen.getByText("열기"));
    expect(screen.getByText("시트 제목")).toBeInTheDocument();
  });

  it("BottomSheetFooter 가 렌더링된다", () => {
    render(<TestSheet />);
    fireEvent.click(screen.getByText("열기"));
    expect(screen.getByText("확인")).toBeInTheDocument();
  });

  it("controlled 모드 — open prop 으로 제어된다", () => {
    const { rerender } = render(
      <BottomSheet open={false}>
        <BottomSheetContent>
          <p>내용</p>
        </BottomSheetContent>
      </BottomSheet>,
    );
    expect(screen.queryByText("내용")).not.toBeInTheDocument();

    rerender(
      <BottomSheet open={true}>
        <BottomSheetContent>
          <p>내용</p>
        </BottomSheetContent>
      </BottomSheet>,
    );
    expect(screen.getByText("내용")).toBeInTheDocument();
  });

  it("시트에 handle bar 가 포함된다 (sm:hidden 클래스)", () => {
    render(<TestSheet />);
    fireEvent.click(screen.getByText("열기"));
    // Handle bar is aria-hidden with specific classes
    const handleBar = document.querySelector(".sm\\:hidden.h-1\\.5.w-12.rounded-full");
    expect(handleBar).toBeInTheDocument();
  });

  // ── M2: aria-labelledby ─────────────────────────────────────────────────

  it("M2: BottomSheetTitle 이 렌더링될 때 dialog 에 aria-labelledby 가 연결된다", () => {
    render(<TestSheet />);
    fireEvent.click(screen.getByText("열기"));

    const dialog = screen.getByRole("dialog");
    const title = screen.getByText("시트 제목");

    const labelledById = dialog.getAttribute("aria-labelledby");
    expect(labelledById).toBeTruthy();
    expect(title.id).toBe(labelledById);
  });

  it("M2: aria-label prop 만 전달하면 dialog 에 aria-label 이 설정된다", () => {
    render(
      <BottomSheet>
        <BottomSheetTrigger>열기</BottomSheetTrigger>
        <BottomSheetContent aria-label="접근성 레이블">
          <p>내용</p>
        </BottomSheetContent>
      </BottomSheet>,
    );
    fireEvent.click(screen.getByText("열기"));
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-label", "접근성 레이블");
    expect(dialog.getAttribute("aria-labelledby")).toBeNull();
  });

  // ── L1: focus trap ──────────────────────────────────────────────────────

  it("L1: 열릴 때 포커스가 시트 내부로 이동한다", async () => {
    render(
      <BottomSheet>
        <BottomSheetTrigger>열기</BottomSheetTrigger>
        <BottomSheetContent>
          <button>첫 번째 버튼</button>
          <button>두 번째 버튼</button>
        </BottomSheetContent>
      </BottomSheet>,
    );
    const trigger = screen.getByText("열기");
    trigger.focus();
    await act(async () => {
      fireEvent.click(trigger);
    });
    // Focus should have moved to first focusable element inside sheet.
    expect(document.activeElement).toBe(screen.getByText("첫 번째 버튼"));
  });

  it("L1: 마지막 포커스 요소에서 Tab 누르면 첫 번째로 순환된다", async () => {
    const user = userEvent.setup();
    render(
      <BottomSheet>
        <BottomSheetTrigger>열기</BottomSheetTrigger>
        <BottomSheetContent>
          <button>버튼 A</button>
          <button>버튼 B</button>
        </BottomSheetContent>
      </BottomSheet>,
    );
    await act(async () => {
      fireEvent.click(screen.getByText("열기"));
    });

    // Focus last button explicitly, then press Tab.
    const buttonB = screen.getByText("버튼 B");
    buttonB.focus();
    expect(document.activeElement).toBe(buttonB);

    await user.tab();
    expect(document.activeElement).toBe(screen.getByText("버튼 A"));
  });

  it("L1: 첫 번째 포커스 요소에서 Shift+Tab 누르면 마지막으로 순환된다", async () => {
    const user = userEvent.setup();
    render(
      <BottomSheet>
        <BottomSheetTrigger>열기</BottomSheetTrigger>
        <BottomSheetContent>
          <button>버튼 A</button>
          <button>버튼 B</button>
        </BottomSheetContent>
      </BottomSheet>,
    );
    await act(async () => {
      fireEvent.click(screen.getByText("열기"));
    });

    // Focus first button explicitly, then Shift+Tab.
    const buttonA = screen.getByText("버튼 A");
    buttonA.focus();
    expect(document.activeElement).toBe(buttonA);

    await user.tab({ shift: true });
    expect(document.activeElement).toBe(screen.getByText("버튼 B"));
  });

  it("L1: 닫힐 때 포커스가 트리거로 복원된다", async () => {
    render(
      <BottomSheet>
        <BottomSheetTrigger>열기</BottomSheetTrigger>
        <BottomSheetContent>
          <button>내부 버튼</button>
        </BottomSheetContent>
      </BottomSheet>,
    );
    const trigger = screen.getByText("열기");
    trigger.focus();
    await act(async () => {
      fireEvent.click(trigger);
    });

    // Close via Escape.
    await act(async () => {
      fireEvent.keyDown(document, { key: "Escape" });
    });

    expect(document.activeElement).toBe(trigger);
  });
});
