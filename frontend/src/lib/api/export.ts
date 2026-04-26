import { apiClient } from "@/lib/api-client";

export async function downloadExport(format: "json" | "csv"): Promise<void> {
  const response = await apiClient.get(`/api/export?format=${format}`, {
    responseType: "blob",
  });

  const cd = response.headers["content-disposition"] as string | undefined;
  const match = cd?.match(/filename="(.+?)"/);
  const fallback =
    format === "json" ? "assetlog-export.json" : "assetlog-export.zip";
  const filename = match?.[1] ?? fallback;

  const mimeType =
    format === "json" ? "application/json" : "application/zip";
  const blob = new Blob([response.data as BlobPart], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
