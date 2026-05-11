import type { AppSettings, LineAnalysis, ModelStatus, Phrase, Poem, PoemVersion } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers
    },
    ...init
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  listPoems: () => request<Poem[]>("/api/poems"),
  listDeletedPoems: () => request<Poem[]>("/api/poems/deleted"),
  getPoem: (id: string) => request<Poem>(`/api/poems/${id}`),
  createPoem: (title: string, text: string) =>
    request<Poem>("/api/poems", {
      method: "POST",
      body: JSON.stringify({ title, text })
    }),
  updatePoem: (id: string, title: string, text: string) =>
    request<Poem>(`/api/poems/${id}`, {
      method: "PUT",
      body: JSON.stringify({ title, text })
    }),
  deletePoem: (id: string) => request<void>(`/api/poems/${id}`, { method: "DELETE" }),
  restorePoem: (id: string) => request<Poem>(`/api/poems/${id}/restore`, { method: "POST" }),
  lockPoem: (id: string) => request<Poem>(`/api/poems/${id}/lock`, { method: "POST" }),
  listVersions: (id: string) => request<PoemVersion[]>(`/api/poems/${id}/versions`),
  exportMarkdownUrl: (id: string) => `${API_BASE_URL}/api/poems/${id}/export.md`,
  changePassword: (oldPassword: string | null, newPassword: string) =>
    request<{ changed: boolean }>("/api/profile/password", {
      method: "POST",
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
    }),
  unlockSession: (password: string) =>
    request<{ session_unlocked: boolean }>("/api/profile/unlock-session", {
      method: "POST",
      body: JSON.stringify({ password })
    }),
  listPhrases: () => request<Phrase[]>("/api/phrases"),
  createPhrase: (payload: {
    text: string;
    poem_id: string;
    start_line: number;
    end_line: number;
    note: string | null;
  }) =>
    request<Phrase>("/api/phrases", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  getSettings: () => request<AppSettings>("/api/app-settings"),
  updateSettings: (settings: AppSettings) =>
    request<AppSettings>("/api/app-settings", {
      method: "PUT",
      body: JSON.stringify(settings)
    }),
  analyzeText: (text: string) =>
    request<{ line_count: number; lines: LineAnalysis[] }>("/api/text-tools/analyze", {
      method: "POST",
      body: JSON.stringify({ text })
    }),
  findRhymes: (word: string, context: string) =>
    request<{ word: string; candidates: string[] }>("/api/text-tools/rhyme", {
      method: "POST",
      body: JSON.stringify({ word, context })
    }),
  draft: (text: string, mode: string) =>
    request<{ line_count: number; variants: string[] }>("/api/text-tools/draft", {
      method: "POST",
      body: JSON.stringify({ text, mode })
    }),
  modelStatus: () => request<ModelStatus>("/api/system/models"),
  flushTelegramOutbox: () =>
    request<{ sent: number; failed: number }>("/api/system/telegram-outbox/flush", {
      method: "POST"
    })
};
