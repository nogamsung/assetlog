"use client";

import { useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useImportFile } from "@/hooks/use-import-file";
import { formatDateTimeKST } from "@/lib/datetime";
import type { ImportFileResult, ImportSource } from "@/lib/api/integrations";

const SOURCE_OPTIONS: { value: ImportSource; label: string }[] = [
  { value: "toss_securities", label: "토스증권 거래내역서 PDF" },
  { value: "shinhan", label: "신한투자증권 거래내역서 PDF" },
];

export function FileImportSection() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropzoneRef = useRef<HTMLDivElement>(null);

  const [source, setSource] = useState<ImportSource>("toss_securities");
  const [file, setFile] = useState<File | null>(null);
  const [password, setPassword] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [previewResult, setPreviewResult] = useState<ImportFileResult | null>(null);

  const mutation = useImportFile();

  function applyFile(f: File | null) {
    setFile(f);
    setPreviewResult(null);
  }

  function handleFileInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    applyFile(e.target.files?.[0] ?? null);
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
    const dropped = e.dataTransfer.files?.[0];
    if (dropped?.type === "application/pdf") {
      applyFile(dropped);
    }
  }

  function handleDropzoneClick() {
    fileInputRef.current?.click();
  }

  function handlePreview() {
    if (!file) return;
    mutation.mutate(
      { source, file, password: password || undefined, dryRun: true },
      {
        onSuccess: (result) => {
          setPreviewResult(result);
        },
      },
    );
  }

  function handleImport() {
    if (!file) return;
    mutation.mutate(
      { source, file, password: password || undefined, dryRun: false },
      {
        onSuccess: (result) => {
          setPreviewResult(result);
          setFile(null);
          setPassword("");
          if (fileInputRef.current) fileInputRef.current.value = "";
        },
      },
    );
  }

  function handleResetResult() {
    setPreviewResult(null);
  }

  const isPending = mutation.isPending;
  const fileSizeKb = file ? (file.size / 1024).toFixed(1) : null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>파일에서 거래내역 가져오기</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* Source 선택 */}
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

        {/* 드롭존 */}
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
            {file ? (
              <div className="space-y-1">
                <p className="text-sm font-medium text-toss-textStrong">{file.name}</p>
                <p className="text-xs text-muted-foreground">{fileSizeKb} KB</p>
              </div>
            ) : (
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">
                  클릭하거나 파일을 드래그하여 업로드
                </p>
                <p className="text-xs text-muted-foreground">PDF 파일만 지원</p>
              </div>
            )}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            aria-hidden="true"
            tabIndex={-1}
            className="sr-only"
            onChange={handleFileInputChange}
          />
        </div>

        {/* 비밀번호 */}
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

        {/* 버튼 */}
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button
            type="button"
            variant="outline"
            onClick={handlePreview}
            disabled={!file || isPending}
            aria-busy={isPending}
            aria-label="미리보기"
            className="w-full sm:w-auto"
          >
            {isPending && mutation.variables?.dryRun ? "미리보는 중..." : "미리보기"}
          </Button>
          <Button
            type="button"
            onClick={handleImport}
            disabled={!file || isPending}
            aria-busy={isPending}
            aria-label="가져오기"
            className="w-full sm:w-auto"
          >
            {isPending && !mutation.variables?.dryRun ? "가져오는 중..." : "가져오기"}
          </Button>
        </div>

        {/* 결과 패널 */}
        {previewResult && (
          <div
            className={[
              "space-y-4 rounded-xl border p-4",
              previewResult.dryRun
                ? "border-toss-border"
                : "border-toss-up/40 bg-toss-up/5",
            ].join(" ")}
            role="region"
            aria-label={previewResult.dryRun ? "미리보기 결과" : "가져오기 결과"}
          >
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm font-medium">
                {previewResult.dryRun
                  ? "미리보기 결과 — 아래 '가져오기' 버튼을 눌러 실제 import 하세요"
                  : "✅ 가져오기 완료"}
              </p>
              {!previewResult.dryRun && (
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
            <div className="space-y-2">
              <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-3">
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">거래</dt>
                  <dd className="font-medium">{previewResult.insertedTrades}건</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">배당</dt>
                  <dd className="font-medium">{previewResult.insertedDividends}건</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">입출금</dt>
                  <dd className="font-medium">{previewResult.insertedCashTxs}건</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">중복 건너뜀</dt>
                  <dd className="font-medium">{previewResult.skippedDuplicate}건</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">미지원 건너뜀</dt>
                  <dd className="font-medium">{previewResult.skippedUnsupported}건</dd>
                </div>
              </dl>
            </div>

            {/* 미리보기 테이블 */}
            {previewResult.preview.length > 0 && (
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
                      {previewResult.preview.map((item) => (
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
