import { snakeToCamel } from "@/lib/case";

describe("snakeToCamel", () => {
  it("단순 snake_case 키를 camelCase 로 변환한다", () => {
    const input = { created_at: "2024-01-01", user_name: "alice" };
    const result = snakeToCamel(input);
    expect(result).toEqual({ createdAt: "2024-01-01", userName: "alice" });
  });

  it("중첩 객체의 키도 변환한다", () => {
    const input = { user_info: { first_name: "Alice", last_name: "Smith" } };
    const result = snakeToCamel(input);
    expect(result).toEqual({
      userInfo: { firstName: "Alice", lastName: "Smith" },
    });
  });

  it("배열 안의 객체도 변환한다", () => {
    const input = [{ created_at: "2024-01-01" }, { updated_at: "2024-02-01" }];
    const result = snakeToCamel(input);
    expect(result).toEqual([
      { createdAt: "2024-01-01" },
      { updatedAt: "2024-02-01" },
    ]);
  });

  it("camelCase 키는 그대로 유지한다", () => {
    const input = { email: "test@example.com", id: 1 };
    const result = snakeToCamel(input);
    expect(result).toEqual({ email: "test@example.com", id: 1 });
  });

  it("값(value)은 변환하지 않는다", () => {
    const input = { key: "snake_case_value" };
    const result = snakeToCamel(input);
    expect(result).toEqual({ key: "snake_case_value" });
  });

  it("null 을 그대로 반환한다", () => {
    expect(snakeToCamel(null)).toBeNull();
  });

  it("원시값(string)을 그대로 반환한다", () => {
    expect(snakeToCamel("hello_world")).toBe("hello_world");
  });

  it("빈 객체를 처리한다", () => {
    expect(snakeToCamel({})).toEqual({});
  });
});
