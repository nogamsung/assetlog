import { z } from "zod";

export const loginSchema = z.object({
  password: z.string().min(1, "비밀번호를 입력하세요."), // {/* MODIFIED */}
});

export type LoginInput = z.infer<typeof loginSchema>;
