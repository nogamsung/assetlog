import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useExportData } from "@/hooks/use-export";
import * as exportApi from "@/lib/api/export";

jest.mock("@/lib/api/export");
const mockedDownloadExport = jest.mocked(exportApi.downloadExport);

jest.mock("sonner", () => ({
  toast: Object.assign(jest.fn(), {
    success: jest.fn(),
    error: jest.fn(),
  }),
}));
import { toast } from "sonner";
const mockedToastSuccess = jest.mocked(toast.success);
const mockedToastError = jest.mocked(toast.error);

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  return { Wrapper };
}

describe("useExportData", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("json 포맷으로 성공 시 toast.success 를 호출한다", async () => {
    mockedDownloadExport.mockResolvedValueOnce(undefined);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useExportData(), { wrapper: Wrapper });

    act(() => {
      result.current.mutate("json");
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedDownloadExport).toHaveBeenCalledWith("json");
    expect(mockedToastSuccess).toHaveBeenCalledWith("데이터 다운로드를 시작했습니다.");
  });

  it("csv 포맷으로 성공 시 toast.success 를 호출한다", async () => {
    mockedDownloadExport.mockResolvedValueOnce(undefined);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useExportData(), { wrapper: Wrapper });

    act(() => {
      result.current.mutate("csv");
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedDownloadExport).toHaveBeenCalledWith("csv");
    expect(mockedToastSuccess).toHaveBeenCalledWith("데이터 다운로드를 시작했습니다.");
  });

  it("실패 시 toast.error 를 호출한다", async () => {
    const axiosError = Object.assign(new Error("Network error"), {
      response: {
        status: 500,
        data: { detail: "서버 오류" },
      },
    });
    mockedDownloadExport.mockRejectedValueOnce(axiosError);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useExportData(), { wrapper: Wrapper });

    act(() => {
      result.current.mutate("json");
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(mockedToastError).toHaveBeenCalledWith("서버 오류");
  });

  it("response.data.detail 없을 때 기본 메시지로 toast.error 를 호출한다", async () => {
    const networkError = new Error("Network error");
    mockedDownloadExport.mockRejectedValueOnce(networkError);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useExportData(), { wrapper: Wrapper });

    act(() => {
      result.current.mutate("csv");
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(mockedToastError).toHaveBeenCalledWith("다운로드에 실패했습니다.");
  });
});
