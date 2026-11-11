// Обёртка над fetch: превращает ошибки API в исключения
export async function apiRequest(path, { method = "GET", body } = {}) {
  const response = await fetch(`/api${path}`, { method, body });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = typeof data?.detail === "string" ? data.detail : `Ошибка ${response.status}`;
    throw new Error(detail);
  }
  return data;
}

// 83.45 -> "01:23.5"
export function formatTime(seconds) {
  const tenths = Math.round(seconds * 10);
  const minutes = Math.floor(tenths / 600);
  const rest = ((tenths % 600) / 10).toFixed(1).padStart(4, "0");
  return `${String(minutes).padStart(2, "0")}:${rest}`;
}
