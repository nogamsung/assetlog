/**
 * Unit tests for useFocusTrap hook.
 * The hook is exercised indirectly via BottomSheet in bottom-sheet.test.tsx,
 * but these tests verify the hook's isolated behavior.
 */
import { render, act, fireEvent } from "@testing-library/react";
import { useRef } from "react";
import { useFocusTrap } from "@/hooks/use-focus-trap";

// ── Helper component ──────────────────────────────────────────────────────

function TrapFixture({ isOpen, extraButton = false }: { isOpen: boolean; extraButton?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  useFocusTrap(ref, isOpen);
  return (
    <div>
      <button id="outside">Outside</button>
      <div ref={ref} tabIndex={-1} id="container">
        <button id="first">First</button>
        <button id="second">Second</button>
        {extraButton && <button id="third">Third</button>}
      </div>
    </div>
  );
}

describe("useFocusTrap", () => {
  it("열릴 때 첫 번째 포커스 가능 요소로 포커스를 이동한다", async () => {
    render(<TrapFixture isOpen={true} />);
    // useEffect fires after render; wait for it.
    await act(async () => {});
    expect(document.activeElement?.id).toBe("first");
  });

  it("isOpen=false 이면 포커스를 이동하지 않는다", async () => {
    const outside = document.createElement("button");
    outside.id = "pre-focus";
    document.body.appendChild(outside);
    outside.focus();

    render(<TrapFixture isOpen={false} />);
    await act(async () => {});
    // Focus should remain outside the trap.
    expect(document.activeElement?.id).toBe("pre-focus");
    document.body.removeChild(outside);
  });

  it("마지막 요소에서 Tab 누르면 첫 번째로 순환한다", async () => {
    render(<TrapFixture isOpen={true} />);
    await act(async () => {});

    const second = document.getElementById("second")!;
    second.focus();
    expect(document.activeElement?.id).toBe("second");

    act(() => {
      fireEvent.keyDown(document, { key: "Tab", shiftKey: false });
    });
    expect(document.activeElement?.id).toBe("first");
  });

  it("첫 번째 요소에서 Shift+Tab 누르면 마지막으로 순환한다", async () => {
    render(<TrapFixture isOpen={true} />);
    await act(async () => {});

    const first = document.getElementById("first")!;
    first.focus();
    expect(document.activeElement?.id).toBe("first");

    act(() => {
      fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
    });
    expect(document.activeElement?.id).toBe("second");
  });

  it("닫힐 때 이전 포커스 요소로 복원한다", async () => {
    const outside = document.createElement("button");
    outside.id = "restore-target";
    document.body.appendChild(outside);
    outside.focus();

    const { rerender } = render(<TrapFixture isOpen={true} />);
    await act(async () => {});
    expect(document.activeElement?.id).toBe("first");

    rerender(<TrapFixture isOpen={false} />);
    await act(async () => {});
    expect(document.activeElement?.id).toBe("restore-target");

    document.body.removeChild(outside);
  });

  it("컨테이너가 없을 때 오류 없이 실행된다", async () => {
    // ref never attached — containerRef.current is null initially,
    // but the effect checks for null before proceeding.
    function NullRefFixture() {
      const ref = useRef<HTMLDivElement>(null);
      useFocusTrap(ref, true);
      return <div>no container attached to ref</div>;
    }
    expect(() => render(<NullRefFixture />)).not.toThrow();
  });

  it("포커스 가능 요소가 없으면 컨테이너 자체에 포커스된다", async () => {
    function EmptyTrapFixture({ isOpen }: { isOpen: boolean }) {
      const ref = useRef<HTMLDivElement>(null);
      useFocusTrap(ref, isOpen);
      return (
        <div ref={ref} tabIndex={-1} id="empty-container">
          <p>No focusable elements</p>
        </div>
      );
    }
    render(<EmptyTrapFixture isOpen={true} />);
    await act(async () => {});
    expect(document.activeElement?.id).toBe("empty-container");
  });

  it("Tab 이 중간 요소에서 눌리면 기본 동작만 처리된다 (순환 없음)", async () => {
    render(<TrapFixture isOpen={true} extraButton={true} />);
    await act(async () => {});

    const first = document.getElementById("first")!;
    first.focus();

    // Tab from first (not last) — should not wrap; keydown handler does nothing.
    act(() => {
      fireEvent.keyDown(document, { key: "Tab", shiftKey: false });
    });
    // Focus remains on "first" because we didn't programmatically move it.
    expect(document.activeElement?.id).toBe("first");
  });
});
