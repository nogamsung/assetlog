"use client";

import { useState } from "react";
import { COMMON_CURRENCIES } from "@/lib/constants/currencies";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface CurrencySelectProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  id?: string;
  "aria-invalid"?: boolean;
}

export function CurrencySelect({
  value,
  onChange,
  disabled = false,
  id = "currency-select",
  "aria-invalid": ariaInvalid,
}: CurrencySelectProps) {
  const isCustom =
    value !== "" &&
    !COMMON_CURRENCIES.some((c) => c.code === value);
  const [showCustom, setShowCustom] = useState(isCustom);

  function handleSelectChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const selected = e.target.value;
    if (selected === "__other__") {
      setShowCustom(true);
      onChange("");
    } else {
      setShowCustom(false);
      onChange(selected);
    }
  }

  function handleCustomChange(e: React.ChangeEvent<HTMLInputElement>) {
    onChange(e.target.value);
  }

  const selectValue = showCustom ? "__other__" : (value || "");

  return (
    <div className="space-y-2">
      <select
        id={id}
        value={selectValue}
        onChange={handleSelectChange}
        disabled={disabled}
        aria-invalid={ariaInvalid}
        aria-label="통화 선택"
        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
      >
        <option value="" disabled>
          통화 선택...
        </option>
        {COMMON_CURRENCIES.map((c) => (
          <option key={c.code} value={c.code}>
            {c.label}
          </option>
        ))}
        <option value="__other__">기타 (직접 입력)</option>
      </select>

      {showCustom && (
        <div className="space-y-1">
          <Label htmlFor={`${id}-custom`} className="text-xs text-muted-foreground">
            통화 코드 직접 입력 (예: THB)
          </Label>
          <Input
            id={`${id}-custom`}
            type="text"
            placeholder="예: THB"
            value={value}
            onChange={handleCustomChange}
            disabled={disabled}
            maxLength={4}
            aria-label="통화 코드 직접 입력"
            aria-invalid={ariaInvalid}
            className="uppercase"
          />
        </div>
      )}
    </div>
  );
}
