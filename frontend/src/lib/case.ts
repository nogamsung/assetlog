/**
 * snake_case 키를 camelCase 로 변환하는 유틸리티.
 * 값(value)은 변경하지 않으며, 키만 변환합니다.
 */

type SnakeToCamelCase<S extends string> =
  S extends `${infer Head}_${infer Tail}`
    ? `${Head}${Capitalize<SnakeToCamelCase<Tail>>}`
    : S;

type CamelCaseKeys<T> =
  T extends Array<infer Item>
    ? Array<CamelCaseKeys<Item>>
    : T extends Record<string, unknown>
      ? {
          [K in keyof T as SnakeToCamelCase<K & string>]: CamelCaseKeys<T[K]>;
        }
      : T;

function toCamelCase(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter: string) =>
    letter.toUpperCase(),
  );
}

export function snakeToCamel<T>(data: T): CamelCaseKeys<T> {
  if (Array.isArray(data)) {
    return data.map((item) => snakeToCamel(item)) as CamelCaseKeys<T>;
  }

  if (data !== null && typeof data === "object") {
    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(
      data as Record<string, unknown>,
    )) {
      result[toCamelCase(key)] = snakeToCamel(value);
    }
    return result as CamelCaseKeys<T>;
  }

  return data as CamelCaseKeys<T>;
}
