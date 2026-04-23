import { z } from "zod";

export const signupSchema = z.object({
  email: z.string().email("유효한 이메일을 입력하세요"),
  password: z
    .string()
    .min(8, "비밀번호는 8자 이상이어야 합니다")
    .max(128, "128자 이하로 입력하세요")
    .regex(/[A-Za-z]/, "영문 1자 이상 포함")
    .regex(/[0-9]/, "숫자 1자 이상 포함"),
});

export const loginSchema = z.object({
  email: z.string().email("유효한 이메일을 입력하세요"),
  password: z.string().min(1, "비밀번호를 입력하세요"),
});

export type SignupInput = z.infer<typeof signupSchema>;
export type LoginInput = z.infer<typeof loginSchema>;
