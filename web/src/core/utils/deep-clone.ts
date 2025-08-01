// SPDX-License-Identifier: MIT

export function deepClone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value));
}
