"use client";

import { useRef, useState } from "react";
import Papa from "papaparse";
import { Button } from "@/components/ui/button";
import { BulkErrorList } from "./bulk-error-list";
import { useBulkImportTransactions, extractBulkErrors } from "@/hooks/use-bulk-import-transactions";
import { REQUIRED_CSV_HEADERS } from "@/lib/schemas/bulk-transaction";
import type { BulkTransactionError } from "@/types/bulk-transaction";

const MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024; // 1MB
const MAX_ROWS = 500;
const PREVIEW_ROWS = 10;

interface CsvPreview {
  headers: string[];
  rows: string[][];
  totalRows: number;
  fileSizeKb: number;
}

interface BulkCsvTabProps {
  onSuccess?: () => void;
}

export function BulkCsvTab({ onSuccess }: BulkCsvTabProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<CsvPreview | null>(null);
  const [clientError, setClientError] = useState<string | null>(null);
  const [serverErrors, setServerErrors] = useState<BulkTransactionError[]>([]);
  const [rowErrorMap, setRowErrorMap] = useState<Map<number, BulkTransactionError[]>>(
    new Map(),
  );

  const mutation = useBulkImportTransactions();

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setClientError(null);
    setServerErrors([]);
    setRowErrorMap(new Map());
    setPreview(null);
    setSelectedFile(null);

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setClientError(
        `파일 크기가 너무 큽니다 (${(file.size / 1024).toFixed(1)} KB). 최대 1MB 이하 파일만 업로드할 수 있습니다.`,
      );
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    Papa.parse<string[]>(file, {
      skipEmptyLines: true,
      complete: (result) => {
        const rawRows = result.data;
        if (rawRows.length < 2) {
          setClientError("CSV 파일에 헤더와 데이터 행이 있어야 합니다.");
          if (fileInputRef.current) fileInputRef.current.value = "";
          return;
        }

        const headers = rawRows[0].map((h) => h.trim().toLowerCase());
        const missingHeaders = REQUIRED_CSV_HEADERS.filter(
          (req) => !headers.includes(req),
        );
        if (missingHeaders.length > 0) {
          setClientError(
            `CSV 헤더가 누락되었습니다: ${missingHeaders.join(", ")}. 필수 헤더: ${REQUIRED_CSV_HEADERS.join(", ")}`,
          );
          if (fileInputRef.current) fileInputRef.current.value = "";
          return;
        }

        const dataRows = rawRows.slice(1);
        if (dataRows.length > MAX_ROWS) {
          setClientError(
            `데이터 행이 너무 많습니다 (${dataRows.length}행). 최대 ${MAX_ROWS}행까지 업로드할 수 있습니다.`,
          );
          if (fileInputRef.current) fileInputRef.current.value = "";
          return;
        }

        setSelectedFile(file);
        setPreview({
          headers: rawRows[0].map((h) => h.trim()),
          rows: dataRows.slice(0, PREVIEW_ROWS),
          totalRows: dataRows.length,
          fileSizeKb: file.size / 1024,
        });
      },
      error: () => {
        setClientError("CSV 파일을 파싱하는 중 오류가 발생했습니다.");
        if (fileInputRef.current) fileInputRef.current.value = "";
      },
    });
  }

  async function handleSubmit() {
    if (!selectedFile) return;

    setServerErrors([]);
    setRowErrorMap(new Map());

    try {
      await mutation.mutateAsync({ mode: "csv", file: selectedFile });
      onSuccess?.();
    } catch (err) {
      if (err instanceof Error) {
        const errors = extractBulkErrors(err);
        if (errors) {
          setServerErrors(errors);
          const map = new Map<number, BulkTransactionError[]>();
          for (const e of errors) {
            if (e.row > 0) {
              const existing = map.get(e.row) ?? [];
              existing.push(e);
              map.set(e.row, existing);
            }
          }
          setRowErrorMap(map);
        }
      }
    }
  }

  function handleCancel() {
    setSelectedFile(null);
    setPreview(null);
    setClientError(null);
    setServerErrors([]);
    setRowErrorMap(new Map());
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  return (
    <div className="space-y-4">
      {/* 파일 선택 */}
      <div className="space-y-2">
        <label htmlFor="bulk-csv-file" className="text-sm font-medium">
          CSV 파일 선택
        </label>
        <div className="flex items-center gap-3 h-32 sm:h-40"> {/* MODIFIED: responsive drop zone height */}
          <input
            id="bulk-csv-file"
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            onChange={handleFileChange}
            aria-label="CSV 파일 업로드"
            aria-describedby={clientError ? "csv-client-error" : undefined}
            className="flex-1 h-full rounded-xl border border-toss-border bg-toss-card px-3 py-1 text-base file:border-0 file:bg-transparent file:text-sm file:font-medium focus:outline-none focus:ring-2 focus:ring-toss-blue/20" /* MODIFIED: toss tokens + text-base */
          />
        </div>
        <p className="text-xs text-muted-foreground">
          필수 헤더: {REQUIRED_CSV_HEADERS.join(", ")} | 선택: memo, tag | 최대 1MB / 500행
        </p>
      </div>

      {/* 클라이언트 오류 */}
      {clientError && (
        <p id="csv-client-error" role="alert" className="text-sm text-destructive">
          {clientError}
        </p>
      )}

      {/* 서버 422 오류 요약 */}
      {serverErrors.length > 0 && (
        <BulkErrorList errors={serverErrors} />
      )}

      {/* 미리보기 */}
      {preview && (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">
            <span className="font-medium text-foreground">{preview.fileSizeKb.toFixed(1)} KB</span>,{" "}
            총 <span className="font-medium text-foreground">{preview.totalRows}행</span>
            {preview.totalRows > PREVIEW_ROWS && ` (처음 ${PREVIEW_ROWS}행 미리보기)`}
          </p>

          <div className="overflow-x-auto rounded-md border">
            <table className="w-full text-xs" aria-label="CSV 미리보기">
              <thead className="bg-muted/50">
                <tr>
                  <th className="border-b px-2 py-1.5 text-left font-medium text-muted-foreground">
                    #
                  </th>
                  {preview.headers.map((h) => (
                    <th
                      key={h}
                      className="border-b px-2 py-1.5 text-left font-medium text-muted-foreground whitespace-nowrap"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows.map((row, rowIdx) => {
                  const rowNumber = rowIdx + 1;
                  const hasError = rowErrorMap.has(rowNumber);
                  return (
                    <tr
                      key={`row-${rowNumber}`}
                      className={hasError ? "bg-destructive/10" : "hover:bg-muted/30"}
                      aria-invalid={hasError}
                    >
                      <td className="border-b px-2 py-1.5 font-mono text-muted-foreground">
                        {hasError && (
                          <span className="mr-1 text-destructive" aria-hidden="true">
                            ●
                          </span>
                        )}
                        {rowNumber}
                      </td>
                      {preview.headers.map((h, colIdx) => {
                        const cellValue = row[colIdx] ?? "";
                        return (
                          <td
                            key={`${rowNumber}-${h}`}
                            className="border-b px-2 py-1.5 whitespace-nowrap"
                          >
                            {cellValue}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* 행별 에러 상세 */}
          {rowErrorMap.size > 0 && (
            <div className="space-y-1">
              {Array.from(rowErrorMap.entries()).map(([rowNum, errs]) => (
                <div key={`detail-${rowNum}`} className="text-xs text-destructive">
                  <span className="font-medium">{rowNum}행:</span>{" "}
                  {errs.map((e) => e.message).join(", ")}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 버튼 */}
      <div className="flex justify-end gap-2 pt-2">
        {selectedFile && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleCancel}
            disabled={mutation.isPending}
          >
            취소
          </Button>
        )}
        <Button
          type="button"
          size="sm"
          onClick={handleSubmit}
          disabled={!selectedFile || mutation.isPending}
          aria-busy={mutation.isPending}
        >
          {mutation.isPending ? "업로드 중..." : "저장"}
        </Button>
      </div>
    </div>
  );
}
