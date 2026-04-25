"use client";

import { useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { loginSchema, type LoginInput } from "@/lib/schemas/auth";
import { useLogin } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";

export function LoginForm() {
  const searchParams = useSearchParams();
  const redirectTo = searchParams.get("from") ?? "/";

  const form = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
    defaultValues: { password: "" }, // MODIFIED
  });

  const loginMutation = useLogin();

  function onSubmit(data: LoginInput) {
    loginMutation.mutate({ ...data, redirectTo }); // MODIFIED
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="space-y-4">
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>비밀번호</FormLabel>
              <FormControl>
                <Input
                  {...field}
                  type="password"
                  placeholder="비밀번호 입력"
                  autoComplete="current-password"
                  aria-label="비밀번호"
                  aria-required="true"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button
          type="submit"
          className="w-full"
          disabled={loginMutation.isPending}
          aria-busy={loginMutation.isPending}
        >
          {loginMutation.isPending ? "로그인 중..." : "로그인"}
        </Button>
      </form>
    </Form>
  );
}
