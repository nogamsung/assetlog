"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { BulkCsvTab } from "./bulk-csv-tab";
import { BulkGridTab } from "./bulk-grid-tab";

type TabId = "csv" | "grid";

interface BulkImportDialogProps {
  open: boolean;
  onClose: () => void;
}

export function BulkImportDialog({ open, onClose }: BulkImportDialogProps) {
  const [activeTab, setActiveTab] = useState<TabId>("csv");

  if (!open) return null;

  function handleSuccess() {
    onClose();
  }

  return (
    /* backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="일괄 등록 다이얼로그"
    >
      <div
        className="relative w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-xl border bg-background shadow-lg mx-4"
        role="document"
      >
        {/* 헤더 */}
        <div className="sticky top-0 z-10 flex items-center justify-between border-b bg-background px-6 py-4">
          <h2 className="text-lg font-semibold">일괄 등록</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="다이얼로그 닫기"
            className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        {/* 탭 */}
        <div className="border-b px-6">
          <div role="tablist" aria-label="일괄 등록 방법 선택" className="flex gap-0">
            <button
              type="button"
              role="tab"
              id="tab-csv"
              aria-selected={activeTab === "csv"}
              aria-controls="tabpanel-csv"
              onClick={() => setActiveTab("csv")}
              className={`min-h-11 border-b-2 px-4 py-3 text-sm font-medium transition-colors ${ /* MODIFIED: min-h-11 */
                activeTab === "csv"
                  ? "border-toss-blue text-toss-blue"
                  : "border-transparent text-toss-textWeak hover:text-toss-text"
              }`}
            >
              CSV 업로드
            </button>
            <button
              type="button"
              role="tab"
              id="tab-grid"
              aria-selected={activeTab === "grid"}
              aria-controls="tabpanel-grid"
              onClick={() => setActiveTab("grid")}
              className={`min-h-11 border-b-2 px-4 py-3 text-sm font-medium transition-colors ${ /* MODIFIED: min-h-11 */
                activeTab === "grid"
                  ? "border-toss-blue text-toss-blue"
                  : "border-transparent text-toss-textWeak hover:text-toss-text"
              }`}
            >
              직접 입력
            </button>
          </div>
        </div>

        {/* 탭 패널 */}
        <div className="px-6 py-5">
          <div
            id="tabpanel-csv"
            role="tabpanel"
            aria-labelledby="tab-csv"
            hidden={activeTab !== "csv"}
          >
            <BulkCsvTab onSuccess={handleSuccess} />
          </div>

          <div
            id="tabpanel-grid"
            role="tabpanel"
            aria-labelledby="tab-grid"
            hidden={activeTab !== "grid"}
          >
            <BulkGridTab onSuccess={handleSuccess} />
          </div>
        </div>

        {/* 하단 취소 버튼 */}
        <div className="sticky bottom-0 border-t bg-background px-6 py-4 pb-[env(safe-area-inset-bottom)] flex justify-end"> {/* MODIFIED: safe-area */}
          <Button type="button" variant="outline" size="sm" onClick={onClose}>
            닫기
          </Button>
        </div>
      </div>
    </div>
  );
}
