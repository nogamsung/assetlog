"use client";

import { useState } from "react";
import { Layers } from "lucide-react";
import { Button } from "@/components/ui/button";
import { BulkImportDialog } from "./bulk-import-dialog";

export function BulkImportButton() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button
        type="button"
        variant="outline"
        onClick={() => setOpen(true)}
        aria-label="여러 종목 일괄 등록"
        className="gap-2"
      >
        <Layers className="h-4 w-4" aria-hidden="true" />
        일괄 등록
      </Button>
      <BulkImportDialog open={open} onClose={() => setOpen(false)} />
    </>
  );
}
