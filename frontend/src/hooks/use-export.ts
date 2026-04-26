"use client";

import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import type { AxiosError } from "axios";
import { downloadExport } from "@/lib/api/export";

interface ApiErrorDetail {
  detail: string;
}

export function useExportData() {
  return useMutation<void, AxiosError<ApiErrorDetail>, "json" | "csv">({
    mutationFn: (format) => downloadExport(format),
    onSuccess: () => {
      toast.success("데이터 다운로드를 시작했습니다.");
    },
    onError: (error) => {
      toast.error(
        error.response?.data?.detail ?? "다운로드에 실패했습니다.",
      );
    },
  });
}
