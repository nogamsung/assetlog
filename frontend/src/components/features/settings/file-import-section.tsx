"use client";

import { useRef, useState } from "react";
import { X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useImportFile } from "@/hooks/use-import-file";
import { useBackfillPortfolioHistory } from "@/hooks/use-portfolio-history";
import { formatDateTimeKST } from "@/lib/datetime";
import type { ImportFileResult, ImportSource } from "@/lib/api/integrations";

const SOURCE_OPTIONS: { value: ImportSource; label: string }[] = [
  { value: "toss_investment", label: "토스증권" },
  { value: "shinhan_investment", label: "신한투자증권" },
  { value: "k_bank", label: "케이뱅크" },
];

interface AggregateResult {
  insertedTrades: number;
  insertedDividends: number;
  insertedCashTxs: number;
  skippedDuplicate: number;
  skippedUnsupported: number;
  fileCount: number;
  preview: ImportFileResult["preview"];
  dryRun: boolean;
}

function emptyAggregate(dryRun: boolean): AggregateResult {
  return {
    insertedTrades: 0,
    insertedDividends: 0,
    insertedCashTxs: 0,
    skippedDuplicate: 0,
    skippedUnsupported: 0,
    fileCount: 0,
    preview: [],
    dryRun,
  };
}

function aggregate(agg: AggregateResult, r: ImportFileResult): AggregateResult {
  return {
    insertedTrades: agg.insertedTrades + r.insertedTrades,
    insertedDividends: agg.insertedDividends + r.insertedDividends,
    insertedCashTxs: agg.insertedCashTxs + r.insertedCashTxs,
    skippedDuplicate: agg.skippedDuplicate + r.skippedDuplicate,
    skippedUnsupported: agg.skippedUnsupported + r.skippedUnsupported,
    fileCount: agg.fileCount + 1,
    preview: [...agg.preview, ...r.preview].slice(0, 20),
    dryRun: agg.dryRun,
  };
}

export function FileImportSection() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropzoneRef = useRef<HTMLDivElement>(null);

  const [source, setSource] = useState<ImportSource>("toss_investment");
  const [files, setFiles] = useState<File[]>([]);
  const [password, setPassword] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [aggResult, setAggResult] = useState<AggregateResult | null>(null);
  const [busy, setBusy] = useState<"preview" | "import" | null>(null);

  const mutation = useImportFile();
  const backfillMutation = useBackfillPortfolioHistory();

  function addFiles(incoming: FileList | File[] | null) {
    if (!incoming) return;
    const arr = Array.from(incoming).filter(
      (f) => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf"),
    );
    if (arr.length === 0) return;
    setFiles((prev) => {
      const merged = [...prev];
      for (const f of arr) {
        if (!merged.some((m) => m.name === f.name && m.size === f.size)) {
          merged.push(f);
        }
      }
      return merged;
    });
    setAggResult(null);
  }

  function removeFile(idx: number) {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
    setAggResult(null);
  }

  function handleFileInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    addFiles(e.target.files);
    // Allow re-selecting the same files next time
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function handleDragOver(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave(e: React.DragEvent<HTMLDivElement>) {
    if (!dropzoneRef.current?.contains(e.relatedTarget as Node)) {
      setIsDragging(false);
    }
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragging(false);
    addFiles(e.dataTransfer.files);
  }

  function handleDropzoneClick() {
    fileInputRef.current?.click();
  }

  async function runFiles(dryRun: boolean) {
    if (files.length === 0) return;
    setBusy(dryRun ? "preview" : "import");
    let agg = emptyAggregate(dryRun);
    for (const file of files) {
      try {
        const r = await mutation.mutateAsync({
          source,
          file,
          password: password || undefined,
          dryRun,
        });
        agg = aggregate(agg, r);
      } catch {
        // useImportFile already shows a toast for the failing file —
        // continue with the remainder rather than abandoning the batch.
      }
    }
    setAggResult(agg);
    setBusy(null);
    if (!dryRun) {
      setFiles([]);
      setPassword("");
      if (fileInputRef.current) fileInputRef.current.value = "";
      backfillMutation.mutate(undefined, { onError: () => {} });
    }
  }

  function handleResetResult() {
    setAggResult(null);
  }

  const isPending = busy !== null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>거래내역 가져오기</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="space-y-1.5">
          <label htmlFor="import-source" className="text-sm font-medium">
            증권사
          </label>
          <select
            id="import-source"
            value={source}
            onChange={(e) => setSource(e.target.value as ImportSource)}
            aria-label="증권사 선택"
            className="flex h-12 w-full rounded-xl border border-toss-border bg-toss-card px-4 text-base text-toss-textStrong focus:border-toss-blue focus:outline-none focus:ring-2 focus:ring-toss-blue/20 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {SOURCE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5">
          <label className="text-sm font-medium">PDF 파일</label>
          <div
            ref={dropzoneRef}
            role="button"
            tabIndex={0}
            aria-label="PDF 파일 선택 또는 드래그 앤 드롭"
            onClick={handleDropzoneClick}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") handleDropzoneClick();
            }}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={[
              "flex min-h-[100px] cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-6 text-center transition-colors",
              isDragging
                ? "border-toss-blue bg-toss-blue/5"
                : "border-toss-border bg-toss-card hover:border-toss-blue/50",
            ].join(" ")}
          >
            <p className="text-sm text-muted-foreground">
              클릭하거나 파일을 드래그하여 업로드 (여러 개 가능)
            </p>
            <p className="text-xs text-muted-foreground">PDF 파일만 지원</p>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            multiple
            aria-hidden="true"
            tabIndex={-1}
            className="sr-only"
            onChange={handleFileInputChange}
          />

          {files.length > 0 && (
            <ul
              className="space-y-1.5 pt-1"
              aria-label={`선택된 PDF ${files.length}개`}
            >
              {files.map((f, idx) => (
                <li
                  key={`${f.name}-${f.size}-${idx}`}
                  className="flex items-center justify-between gap-2 rounded-lg border border-toss-border bg-toss-card px-3 py-2"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-toss-textStrong">
                      {f.name}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {(f.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeFile(idx)}
                    disabled={isPending}
                    aria-label={`${f.name} 제거`}
                    className="rounded-full p-1 text-muted-foreground transition-[background-color,transform] duration-150 hover:bg-muted hover:text-foreground active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <X className="h-4 w-4" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="space-y-1.5">
          <label htmlFor="import-password" className="text-sm font-medium">
            PDF 비밀번호{" "}
            <span className="text-xs font-normal text-muted-foreground">(선택)</span>
          </label>
          <Input
            id="import-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="비밀번호 보호 PDF 인 경우 입력"
            aria-label="PDF 비밀번호"
            autoComplete="off"
          />
        </div>

        <div className="flex flex-col gap-2 sm:flex-row">
          <Button
            type="button"
            variant="outline"
            onClick={() => runFiles(true)}
            disabled={files.length === 0 || isPending}
            aria-busy={isPending}
            aria-label="미리보기"
            className="w-full sm:w-auto"
          >
            {busy === "preview" ? "미리보는 중..." : "미리보기"}
          </Button>
          <Button
            type="button"
            onClick={() => runFiles(false)}
            disabled={files.length === 0 || isPending}
            aria-busy={isPending}
            aria-label="가져오기"
            className="w-full sm:w-auto"
          >
            {busy === "import" ? "가져오는 중..." : "가져오기"}
          </Button>
        </div>

        {aggResult && (
          <div
            className={[
              "space-y-4 rounded-xl border p-4",
              aggResult.dryRun
                ? "border-toss-border"
                : "border-toss-up/40 bg-toss-up/5",
            ].join(" ")}
            role="region"
            aria-label={aggResult.dryRun ? "미리보기 결과" : "가져오기 결과"}
          >
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm font-medium">
                {aggResult.dryRun
                  ? `미리보기 결과 — ${aggResult.fileCount}개 파일`
                  : `✅ 가져오기 완료 — ${aggResult.fileCount}개 파일`}
              </p>
              {!aggResult.dryRun && (
                <button
                  type="button"
                  onClick={handleResetResult}
                  aria-label="결과 닫기"
                  className="text-xs text-muted-foreground hover:text-toss-textStrong"
                >
                  닫기
                </button>
              )}
            </div>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-3">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">거래</dt>
                <dd className="font-medium">{aggResult.insertedTrades}건</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">배당</dt>
                <dd className="font-medium">{aggResult.insertedDividends}건</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">입출금</dt>
                <dd className="font-medium">{aggResult.insertedCashTxs}건</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">중복 건너뜀</dt>
                <dd className="font-medium">{aggResult.skippedDuplicate}건</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">미지원 건너뜀</dt>
                <dd className="font-medium">{aggResult.skippedUnsupported}건</dd>
              </div>
            </dl>

            {aggResult.preview.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs font-medium text-muted-foreground">
                  미리보기 (최대 20건)
                </p>
                <div className="overflow-x-auto rounded-md border">
                  <table className="w-full text-xs" aria-label="가져오기 미리보기 테이블">
                    <thead>
                      <tr className="border-b bg-muted/50">
                        <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                          유형
                        </th>
                        <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                          거래ID
                        </th>
                        <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                          거래일시 (KST)
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {aggResult.preview.map((item) => (
                        <tr key={item.externalId} className="border-b last:border-0">
                          <td className="px-3 py-1.5">{item.type}</td>
                          <td className="px-3 py-1.5 font-mono">{item.externalId}</td>
                          <td className="px-3 py-1.5">{formatDateTimeKST(item.tradedAt)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
