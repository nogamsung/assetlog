import { downloadExport } from "@/lib/api/export";
import { apiClient } from "@/lib/api-client";

jest.mock("@/lib/api-client", () => ({
  apiClient: {
    get: jest.fn(),
  },
}));

const mockedGet = jest.mocked(apiClient.get);

// jsdom 에서 URL.createObjectURL / revokeObjectURL 이 없으므로 mock
const mockCreateObjectURL = jest.fn(() => "blob:http://localhost/fake-url");
const mockRevokeObjectURL = jest.fn();

Object.defineProperty(URL, "createObjectURL", {
  writable: true,
  value: mockCreateObjectURL,
});
Object.defineProperty(URL, "revokeObjectURL", {
  writable: true,
  value: mockRevokeObjectURL,
});

// document.body.appendChild / a.click mock
const mockClick = jest.fn();
const mockRemove = jest.fn();
const mockAppendChild = jest.fn();

describe("downloadExport", () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // anchor element mock
    jest
      .spyOn(document, "createElement")
      .mockReturnValue(
        Object.assign(document.createElement("a"), {
          click: mockClick,
          remove: mockRemove,
        }),
      );
    jest.spyOn(document.body, "appendChild").mockImplementation(mockAppendChild);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe("JSON 포맷", () => {
    it("GET /api/export?format=json 을 responseType blob 으로 호출한다", async () => {
      mockedGet.mockResolvedValueOnce({
        data: new Blob(["{}"], { type: "application/json" }),
        headers: {
          "content-disposition":
            'attachment; filename="assetlog-export-20240101T000000Z.json"',
        },
      });

      await downloadExport("json");

      expect(mockedGet).toHaveBeenCalledWith("/api/export?format=json", {
        responseType: "blob",
      });
    });

    it("Content-Disposition 헤더에서 filename 을 추출한다", async () => {
      mockedGet.mockResolvedValueOnce({
        data: new Blob(["{}"], { type: "application/json" }),
        headers: {
          "content-disposition":
            'attachment; filename="assetlog-export-20240101T000000Z.json"',
        },
      });

      await downloadExport("json");

      const anchor = mockAppendChild.mock.calls[0][0] as HTMLAnchorElement;
      expect(anchor.download).toBe("assetlog-export-20240101T000000Z.json");
    });

    it("Content-Disposition 헤더 없을 때 fallback filename 을 사용한다", async () => {
      mockedGet.mockResolvedValueOnce({
        data: new Blob(["{}"], { type: "application/json" }),
        headers: {},
      });

      await downloadExport("json");

      const anchor = mockAppendChild.mock.calls[0][0] as HTMLAnchorElement;
      expect(anchor.download).toBe("assetlog-export.json");
    });

    it("URL.createObjectURL 을 호출하고 완료 후 revokeObjectURL 을 호출한다", async () => {
      mockedGet.mockResolvedValueOnce({
        data: new Blob(["{}"], { type: "application/json" }),
        headers: {},
      });

      await downloadExport("json");

      expect(mockCreateObjectURL).toHaveBeenCalledTimes(1);
      expect(mockRevokeObjectURL).toHaveBeenCalledWith("blob:http://localhost/fake-url");
    });
  });

  describe("CSV 포맷", () => {
    it("GET /api/export?format=csv 를 responseType blob 으로 호출한다", async () => {
      mockedGet.mockResolvedValueOnce({
        data: new Blob(["zip-binary"], { type: "application/zip" }),
        headers: {
          "content-disposition":
            'attachment; filename="assetlog-export-20240101T000000Z.zip"',
        },
      });

      await downloadExport("csv");

      expect(mockedGet).toHaveBeenCalledWith("/api/export?format=csv", {
        responseType: "blob",
      });
    });

    it("Content-Disposition 헤더에서 zip filename 을 추출한다", async () => {
      mockedGet.mockResolvedValueOnce({
        data: new Blob(["zip-binary"], { type: "application/zip" }),
        headers: {
          "content-disposition":
            'attachment; filename="assetlog-export-20240101T000000Z.zip"',
        },
      });

      await downloadExport("csv");

      const anchor = mockAppendChild.mock.calls[0][0] as HTMLAnchorElement;
      expect(anchor.download).toBe("assetlog-export-20240101T000000Z.zip");
    });

    it("Content-Disposition 헤더 없을 때 fallback filename assetlog-export.zip 을 사용한다", async () => {
      mockedGet.mockResolvedValueOnce({
        data: new Blob(["zip-binary"], { type: "application/zip" }),
        headers: {},
      });

      await downloadExport("csv");

      const anchor = mockAppendChild.mock.calls[0][0] as HTMLAnchorElement;
      expect(anchor.download).toBe("assetlog-export.zip");
    });
  });
});
