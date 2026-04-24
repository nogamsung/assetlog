"use client";

import { useRef, useState } from "react";
import { isAxiosError } from "axios";
import { useImportTransactionsCsv } from "@/hooks/use-transactions";
import { Button } from "@/components/ui/button";
import type { CsvImportError, TransactionResponse } from "@/types/transaction";

// ── CSV 샘플 ─────────────────────────────────────────────────────────────────

const SAMPLE_CSV =
  `type,quantity,price,traded_at,memo\n` +
  `buy,1.5,50000,2026-01-15T10:00:00+09:00,"첫 매수"\n` +
  `buy,0.5,48000,2026-02-10T09:00:00+09:00,\n` +
  `sell,0.5,55000,2026-03-20T14:30:00+09:00,"수익 실현"\n`;

// ── 간단한 CSV 파서 (따옴표 이스케이프 기본 지원) ──────────────────────────

function parseCsvLine(line: string): string[] {
  const result: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        // 이스케이프된 따옴표 ""
        current += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (ch === "," && !inQuotes) {
      result.push(current);
      current = "";
    } else {
      current += ch;
    }
  }
  result.push(current);
  return result;
}

function parseCsvPreview(text: string): { headers: string[]; rows: string[][] } {
  const lines = text
    .split("\n")
    .map((l) => l.trimEnd())
    .filter((l) => l.length > 0);

  if (lines.length === 0) return { headers: [], rows: [] };

  const headers = parseCsvLine(lines[0]);
  const rows = lines
    .slice(1, 11) // 최대 10행
    .map((line) => parseCsvLine(line));

  return { headers, rows };
}

// ── Props ─────────────────────────────────────────────────────────────────────

interface TransactionImportProps {
  userAssetId: number;
  onSuccess?: () => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function TransactionImport({ userAssetId, onSuccess }: TransactionImportProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<{ headers: string[]; rows: string[][] } | null>(null);
  const [csvErrors, setCsvErrors] = useState<CsvImportError[]>([]);
  const [successPreview, setSuccessPreview] = useState<TransactionResponse[] | null>(null);

  const importMutation = useImportTransactionsCsv();

  // 파일 선택 시 로컬 미리보기 파싱
  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setSelectedFile(file);
    setCsvErrors([]);
    setSuccessPreview(null);

    if (!file) {
      setPreview(null);
      return;
    }

    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result;
      if (typeof text === "string") {
        setPreview(parseCsvPreview(text));
      }
    };
    reader.readAsText(file, "utf-8");
  }

  // 샘플 CSV 다운로드
  function handleDownloadSample() {
    const blob = new Blob([SAMPLE_CSV], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "transactions_sample.csv";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  // 제출
  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedFile) return;

    setCsvErrors([]);
    setSuccessPreview(null);

    importMutation.mutate(
      { userAssetId, file: selectedFile },
      {
        onSuccess: (result) => {
          setSuccessPreview(result.preview);
          setSelectedFile(null);
          setPreview(null);
          if (fileInputRef.current) fileInputRef.current.value = "";
          onSuccess?.();
        },
        onError: (err) => {
          if (isAxiosError(err) && err.response?.status === 422) {
            const body = err.response.data as {
              detail: string;
              errors: CsvImportError[];
            };
            setCsvErrors(body.errors ?? []);
          }
        },
      },
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" aria-label="CSV 가져오기 폼" noValidate>
      {/* 안내 + 샘플 다운로드 */}
      <div className="flex flex-col gap-1 text-sm text-muted-foreground">
        <p>
          CSV 파일을 업로드하면 거래 내역을 일괄 추가할 수 있습니다.
          파일은 UTF-8 인코딩, 최대 1 MB입니다.
        </p>
        <p>
          필드 순서:{" "}
          <code className="rounded bg-muted px-1 text-xs">
            type, quantity, price, traded_at, memo
          </code>
        </p>
        <button
          type="button"
          onClick={handleDownloadSample}
          aria-label="샘플 CSV 다운로드"
          className="self-start rounded text-xs font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          샘플 CSV 다운로드
        </button>
      </div>

      {/* 파일 선택 */}
      <div className="space-y-2">
        <label
          htmlFor="csv-file-input"
          className="text-sm font-medium leading-none"
        >
          CSV 파일 선택
        </label>
        <input
          id="csv-file-input"
          ref={fileInputRef}
          type="file"
          accept=".csv,text/csv"
          aria-label="CSV 파일 선택"
          onChange={handleFileChange}
          className="block w-full text-sm text-muted-foreground
            file:mr-3 file:rounded file:border-0
            file:bg-muted file:px-3 file:py-1.5
            file:text-sm file:font-medium
            file:text-foreground
            hover:file:bg-muted/80
            cursor-pointer"
        />
      </div>

      {/* 로컬 미리보기 */}
      {preview && preview.headers.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground">
            미리보기 (최대 10행)
          </p>
          <div className="overflow-x-auto rounded-md border">
            <table className="w-full text-xs" aria-label="CSV 미리보기 테이블">
              <thead>
                <tr className="border-b bg-muted/50">
                  {preview.headers.map((h) => (
                    <th
                      key={h}
                      className="px-3 py-2 text-left font-medium text-muted-foreground"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows.map((row, ri) => (
                  <tr key={`row-${ri}`} className="border-b last:border-0">
                    {row.map((cell, ci) => (
                      <td key={`cell-${ri}-${ci}`} className="px-3 py-1.5 text-foreground">
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 422 검증 에러 목록 */}
      {csvErrors.length > 0 && (
        <div className="space-y-1" role="alert" aria-label="CSV 오류 목록">
          <p className="text-xs font-medium text-destructive">
            {csvErrors.length}개 행에 오류가 있습니다. 파일을 수정 후 다시 업로드하세요.
          </p>
          <div className="overflow-x-auto rounded-md border border-destructive/30">
            <table className="w-full text-xs" aria-label="CSV 오류 상세">
              <thead>
                <tr className="border-b bg-destructive/5">
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">행</th>
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">필드</th>
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">오류</th>
                </tr>
              </thead>
              <tbody>
                {csvErrors.map((err, i) => (
                  <tr key={`csv-err-${i}`} className="border-b last:border-0">
                    <td className="px-3 py-1.5">{err.row}</td>
                    <td className="px-3 py-1.5">{err.field ?? "—"}</td>
                    <td className="px-3 py-1.5 text-destructive">{err.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 성공 미리보기 */}
      {successPreview && successPreview.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-emerald-600">
            추가된 거래 미리보기 (최대 5건)
          </p>
          <div className="overflow-x-auto rounded-md border border-emerald-200">
            <table className="w-full text-xs" aria-label="추가된 거래 미리보기">
              <thead>
                <tr className="border-b bg-emerald-50/50">
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">유형</th>
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">수량</th>
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">단가</th>
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">거래일</th>
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">메모</th>
                </tr>
              </thead>
              <tbody>
                {successPreview.slice(0, 5).map((tx) => (
                  <tr key={tx.id} className="border-b last:border-0">
                    <td className="px-3 py-1.5">{tx.type === "buy" ? "매수" : "매도"}</td>
                    <td className="px-3 py-1.5">{tx.quantity}</td>
                    <td className="px-3 py-1.5">{tx.price}</td>
                    <td className="px-3 py-1.5">{new Date(tx.tradedAt).toLocaleDateString("ko-KR")}</td>
                    <td className="px-3 py-1.5">{tx.memo ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 제출 버튼 */}
      <Button
        type="submit"
        disabled={!selectedFile || importMutation.isPending}
        aria-busy={importMutation.isPending}
        aria-label="CSV 파일 가져오기 제출"
        className="w-full"
      >
        {importMutation.isPending ? "가져오는 중..." : "가져오기"}
      </Button>
    </form>
  );
}
