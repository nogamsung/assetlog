import { render, screen, fireEvent, act } from "@testing-library/react";
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
});
