import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Archive,
  Check,
  Download,
  FilePlus2,
  History,
  Keyboard,
  Lock,
  LockOpen,
  Mic,
  RefreshCw,
  RotateCcw,
  Save,
  Search,
  Settings,
  Sparkles,
  Trash2,
  Wand2,
  X
} from "lucide-react";
import { api } from "./api";
import type {
  AppSettings,
  LineAnalysis,
  ModelStatus,
  Phrase,
  Poem,
  PoemVersion,
  ProtectedFragment,
  SpeechRecognizer
} from "./types";
import "./styles.css";

type View = "active" | "deleted" | "archive" | "settings";
type Mode = "studio" | "idle";
type AutocompleteScope = "personal" | "general";
type SaveState = "saved" | "editing" | "saving" | "local" | "error";
type LineRange = { start: number; end: number; count: number };
type TextRange = { start: number; end: number };
type DraftPanel = {
  mode: "recommendation" | "transformation";
  source: string;
  range: TextRange;
  lineRange: LineRange;
  variants: string[];
  status: "loading" | "ready" | "empty" | "error";
  message: string;
};
type RhymePanel = { word: string; candidates: string[]; status: "loading" | "ready" | "error" };

const DEFAULT_SETTINGS: AppSettings = {
  studio_background: "#050505",
  studio_text: "#f7f7f4",
  studio_font_size: 22,
  speech_recognizer: "local_whisper"
};

const LOCAL_NEW_DRAFT_KEY = "stihia.localDraft";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

function formatBytes(value: number) {
  if (!value) return "0 Б";
  const units = ["Б", "КБ", "МБ", "ГБ"];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  return `${(value / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function hasRealContent(title: string, text: string) {
  return Boolean(text.trim() || (title.trim() && title.trim() !== "Новый стих"));
}

function draftKey(poemId: string) {
  return `stihia.draft.${poemId}`;
}

function readDraft(poem: Poem): { title: string; text: string; localUpdatedAt: string } | null {
  const raw = localStorage.getItem(draftKey(poem.id));
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as { title?: string; text?: string; localUpdatedAt?: string; serverUpdatedAt?: string };
    if (!parsed.title || parsed.text === undefined || !parsed.localUpdatedAt) return null;
    if (parsed.serverUpdatedAt && new Date(parsed.serverUpdatedAt) >= new Date(parsed.localUpdatedAt)) return null;
    if (parsed.title === poem.title && parsed.text === poem.text) return null;
    return { title: parsed.title, text: parsed.text, localUpdatedAt: parsed.localUpdatedAt };
  } catch {
    return null;
  }
}

function readLocalNewDraft() {
  const raw = localStorage.getItem(LOCAL_NEW_DRAFT_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as { title?: string; text?: string };
    if (!hasRealContent(parsed.title ?? "", parsed.text ?? "")) return null;
    return { title: parsed.title || "Новый стих", text: parsed.text ?? "" };
  } catch {
    return null;
  }
}

function offsetForLine(text: string, line: number) {
  if (line <= 1) return 0;
  let offset = 0;
  for (let current = 1; current < line; current += 1) {
    const nextBreak = text.indexOf("\n", offset);
    if (nextBreak < 0) return text.length;
    offset = nextBreak + 1;
  }
  return offset;
}

function lineRangeForOffsets(text: string, startOffset: number, endOffset: number): LineRange {
  const start = Math.min(startOffset, endOffset);
  const end = Math.max(startOffset, endOffset);
  const lineStart = text.slice(0, start).split("\n").length;
  const selected = text.slice(start, end);
  const count = Math.max(1, selected ? selected.split("\n").length : 1);
  return { start: lineStart, end: lineStart + count - 1, count };
}

function expandCollapsedSelectionToLine(text: string, start: number, end: number): TextRange {
  if (start !== end) return { start, end };
  const lineStart = text.lastIndexOf("\n", Math.max(0, start - 1)) + 1;
  const lineEndIndex = text.indexOf("\n", start);
  return { start: lineStart, end: lineEndIndex < 0 ? text.length : lineEndIndex };
}

function lineBeforeCursor(value: string, cursor: number) {
  const before = value.slice(0, cursor);
  return before.slice(before.lastIndexOf("\n") + 1);
}

function completionTextForInsert(value: string, cursor: number, completion: string) {
  const trimmed = completion.trim();
  if (!trimmed) return "";
  const before = value.slice(0, cursor);
  if (!before || before.endsWith("\n") || /\s$/.test(before) || /^[,.;:!?-]/.test(trimmed)) return trimmed;
  return ` ${trimmed}`;
}

function wordNearCursor(value: string, cursor: number) {
  const before = value.slice(0, cursor).match(/[A-Za-zА-Яа-яЁё-]+$/)?.[0] ?? "";
  const after = value.slice(cursor).match(/^[A-Za-zА-Яа-яЁё-]+/)?.[0] ?? "";
  return `${before}${after}`.trim();
}

function lastWord(value: string) {
  return value.match(/[A-Za-zА-Яа-яЁё-]+(?=[^A-Za-zА-Яа-яЁё-]*$)/)?.[0] ?? "";
}

function saveStateLabel(state: SaveState, lastSavedAt: string | null, localDraft: boolean) {
  if (localDraft) return state === "saving" ? "создаю" : "локальный черновик";
  if (state === "saving") return "сохраняю";
  if (state === "editing") return "есть изменения";
  if (state === "local") return "локально";
  if (state === "error") return "ошибка";
  return lastSavedAt ? `сохранено ${formatDate(lastSavedAt)}` : "сохранено";
}

function lineTone(line: LineAnalysis | undefined) {
  if (!line || line.flags.includes("empty")) return "empty";
  if (line.flags.includes("rhythm")) return "rhythm";
  if (line.flags.includes("near_rhythm")) return "near";
  if (line.rhyme_group) return "clean";
  return "plain";
}

function lineIssueLabel(line: LineAnalysis | undefined) {
  if (!line) return "";
  if (line.flags.includes("rhythm")) return "ритм";
  if (line.flags.includes("near_rhythm")) return "спорно";
  return line.rhyme_group ?? "";
}

function App() {
  const [view, setView] = useState<View>("active");
  const [mode, setMode] = useState<Mode>("studio");
  const [poems, setPoems] = useState<Poem[]>([]);
  const [deletedPoems, setDeletedPoems] = useState<Poem[]>([]);
  const [selectedPoem, setSelectedPoem] = useState<Poem | null>(null);
  const [localDraft, setLocalDraft] = useState(false);
  const [title, setTitle] = useState("Новый стих");
  const [text, setText] = useState("");
  const [versions, setVersions] = useState<PoemVersion[]>([]);
  const [protectedFragments, setProtectedFragments] = useState<ProtectedFragment[]>([]);
  const [phrases, setPhrases] = useState<Phrase[]>([]);
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [sessionUnlocked, setSessionUnlocked] = useState(false);
  const [password, setPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [oldPassword, setOldPassword] = useState("");
  const [message, setMessage] = useState("");
  const [saveState, setSaveState] = useState<SaveState>("saved");
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; selected: string; range: TextRange } | null>(null);
  const [highlight, setHighlight] = useState<{ stanzaStart: number; stanzaEnd: number; lineStart: number; lineEnd: number } | null>(null);
  const [voiceText, setVoiceText] = useState("");
  const [analysis, setAnalysis] = useState<LineAnalysis[]>([]);
  const [draftPanel, setDraftPanel] = useState<DraftPanel | null>(null);
  const [rhymePanel, setRhymePanel] = useState<RhymePanel | null>(null);
  const [modelStatus, setModelStatus] = useState<ModelStatus>({});
  const [isRecording, setIsRecording] = useState(false);
  const [autocompleteEnabled, setAutocompleteEnabled] = useState(() => localStorage.getItem("stihia.autocomplete") !== "off");
  const [autocompleteScope, setAutocompleteScope] = useState<AutocompleteScope>(
    () => (localStorage.getItem("stihia.autocompleteScope") as AutocompleteScope | null) ?? "general"
  );
  const [completion, setCompletion] = useState<{ text: string; engine: string; cursor: number } | null>(null);
  const [editorCursor, setEditorCursor] = useState(0);
  const [editorScrollTop, setEditorScrollTop] = useState(0);
  const recognitionRef = useRef<any>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaChunksRef = useRef<Blob[]>([]);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const applyVoiceRef = useRef(false);
  const editorRef = useRef<HTMLTextAreaElement>(null);

  const locked = Boolean(selectedPoem?.is_locked && !sessionUnlocked);
  const changed = localDraft
    ? hasRealContent(title, text)
    : Boolean(selectedPoem && (title !== selectedPoem.title || text !== selectedPoem.text));
  const editorAvailable = Boolean(selectedPoem || localDraft);
  const currentLineContract = useMemo(
    () => (contextMenu ? lineRangeForOffsets(text, contextMenu.range.start, contextMenu.range.end) : { start: 1, end: 1, count: 1 }),
    [text, contextMenu]
  );
  const analysisSummary = useMemo(() => {
    const hardIssues = analysis.filter((line) => line.flags.includes("rhythm")).length;
    const softIssues = analysis.filter((line) => line.flags.includes("near_rhythm")).length;
    const schemes = Array.from(new Set(analysis.map((line) => line.rhyme_scheme).filter(Boolean)));
    return {
      hardIssues,
      softIssues,
      scheme: schemes[0] ?? "нет",
      lines: analysis.filter((line) => line.text.trim()).length
    };
  }, [analysis]);

  const visiblePoems = view === "deleted" ? deletedPoems : poems;
  const editorLines = text.split("\n");
  const editorFontSize = mode === "idle" ? Math.max(14, Math.min(24, settings.studio_font_size - 3)) : settings.studio_font_size;
  const inlineCompletion =
    completion && completion.cursor === editorCursor ? completionTextForInsert(text, editorCursor, completion.text) : "";

  useEffect(() => {
    localStorage.setItem("stihia.autocomplete", autocompleteEnabled ? "on" : "off");
  }, [autocompleteEnabled]);

  useEffect(() => {
    localStorage.setItem("stihia.autocompleteScope", autocompleteScope);
  }, [autocompleteScope]);

  useEffect(() => {
    refresh().catch((error) => setMessage(`API недоступен: ${error.message}`));
  }, []);

  useEffect(() => {
    if (!localDraft) return;
    if (hasRealContent(title, text)) {
      localStorage.setItem(LOCAL_NEW_DRAFT_KEY, JSON.stringify({ title, text }));
      return;
    }
    localStorage.removeItem(LOCAL_NEW_DRAFT_KEY);
  }, [localDraft, title, text]);

  useEffect(() => {
    const timeout = window.setTimeout(async () => {
      if (!text.trim()) {
        setAnalysis([]);
        return;
      }
      try {
        const result = await api.analyzeText(text);
        setAnalysis(result.lines);
      } catch {
        setAnalysis([]);
      }
    }, 240);
    return () => window.clearTimeout(timeout);
  }, [text]);

  useEffect(() => {
    if (locked || view === "settings" || !editorAvailable) return;
    if (!changed) {
      setSaveState("saved");
      return;
    }
    setSaveState((state) => (state === "local" ? "local" : "editing"));
    if (selectedPoem) {
      localStorage.setItem(
        draftKey(selectedPoem.id),
        JSON.stringify({ title, text, localUpdatedAt: new Date().toISOString(), serverUpdatedAt: selectedPoem.updated_at })
      );
    }
    const timeout = window.setTimeout(() => {
      persistPoem("autosave").catch(() => setSaveState("local"));
    }, 1200);
    return () => window.clearTimeout(timeout);
  }, [title, text, selectedPoem?.id, selectedPoem?.title, selectedPoem?.text, localDraft, locked, view]);

  useEffect(() => {
    if (!autocompleteEnabled || !editorAvailable || locked || view === "settings") {
      setCompletion(null);
      return;
    }
    const timeout = window.setTimeout(async () => {
      const editor = editorRef.current;
      if (!editor) return;
      const cursor = editor.selectionStart;
      const line = lineBeforeCursor(text, cursor).trim();
      if (line.length < 4 || /\n/.test(line)) {
        setCompletion(null);
        return;
      }
      try {
        const result = await api.completeLine(text, line, autocompleteScope);
        if (editorRef.current?.selectionStart !== cursor) return;
        setCompletion(result.completion ? { text: result.completion, engine: result.engine, cursor } : null);
      } catch {
        setCompletion(null);
      }
    }, 260);
    return () => window.clearTimeout(timeout);
  }, [autocompleteEnabled, autocompleteScope, locked, editorAvailable, text, view]);

  async function refresh() {
    const [active, deleted, appSettings, archive, models] = await Promise.all([
      api.listPoems(),
      api.listDeletedPoems(),
      api.getSettings().catch(() => DEFAULT_SETTINGS),
      api.listPhrases().catch(() => []),
      api.modelStatus().catch(() => ({}))
    ]);
    setPoems(active);
    setDeletedPoems(deleted);
    setSettings(appSettings);
    setPhrases(archive);
    setModelStatus(models);

    const restoredLocal = readLocalNewDraft();
    if (!selectedPoem && restoredLocal) {
      openLocalDraft(restoredLocal.title, restoredLocal.text, "Восстановлен локальный черновик.");
      return;
    }
    if (!selectedPoem && active[0]) {
      await selectPoem(active[0]);
    }
  }

  async function selectPoem(poem: Poem) {
    const draft = readDraft(poem);
    setLocalDraft(false);
    setSelectedPoem(poem);
    setTitle(draft?.title ?? poem.title);
    setText(draft?.text ?? poem.text);
    setSaveState(draft ? "local" : "saved");
    setLastSavedAt(poem.updated_at);
    setDraftPanel(null);
    setRhymePanel(null);
    setMessage(draft ? "Восстановлен локальный черновик. Автосохранение отправит его в базу." : "");
    setVersions(await api.listVersions(poem.id).catch(() => []));
    setProtectedFragments(await api.listProtectedFragments(poem.id).catch(() => []));
    setView(poem.is_deleted ? "deleted" : "active");
  }

  function openLocalDraft(nextTitle = "Новый стих", nextText = "", nextMessage = "") {
    setSelectedPoem(null);
    setLocalDraft(true);
    setTitle(nextTitle);
    setText(nextText);
    setVersions([]);
    setProtectedFragments([]);
    setDraftPanel(null);
    setRhymePanel(null);
    setLastSavedAt(null);
    setSaveState(hasRealContent(nextTitle, nextText) ? "editing" : "saved");
    setView("active");
    setMessage(nextMessage);
    window.setTimeout(() => editorRef.current?.focus(), 0);
  }

  function createPoem() {
    if (localDraft && !hasRealContent(title, text)) {
      openLocalDraft();
      return;
    }
    openLocalDraft("Новый стих", "", "Пустой стих не будет создан, пока ты не начнешь писать.");
  }

  async function persistPoem(source: "manual" | "autosave" = "manual") {
    if (locked) return;
    if (!hasRealContent(title, text)) {
      setSaveState("saved");
      if (localDraft) localStorage.removeItem(LOCAL_NEW_DRAFT_KEY);
      if (source === "manual") setMessage("Пустой стих не сохраняю.");
      return;
    }
    if (!localDraft && selectedPoem && !changed) {
      setSaveState("saved");
      if (source === "manual") setMessage("Изменений нет.");
      return;
    }
    setSaveState("saving");
    const cleanTitle = title.trim() || "Новый стих";
    const updated = localDraft || !selectedPoem
      ? await api.createPoem(cleanTitle, text)
      : await api.updatePoem(selectedPoem.id, cleanTitle, text, source);

    setLocalDraft(false);
    setSelectedPoem(updated);
    setTitle(updated.title);
    setText(updated.text);
    setPoems((items) => [updated, ...items.filter((item) => item.id !== updated.id)]);
    setVersions(await api.listVersions(updated.id).catch(() => []));
    setProtectedFragments(await api.listProtectedFragments(updated.id).catch(() => []));
    setPhrases(await api.listPhrases().catch(() => phrases));
    localStorage.removeItem(LOCAL_NEW_DRAFT_KEY);
    localStorage.removeItem(draftKey(updated.id));
    setSaveState("saved");
    setLastSavedAt(updated.updated_at);
    if (source === "manual") setMessage("Сохранено.");
  }

  async function deletePoem() {
    if (localDraft) {
      localStorage.removeItem(LOCAL_NEW_DRAFT_KEY);
      openLocalDraft();
      setLocalDraft(false);
      setMessage("Локальный черновик убран.");
      return;
    }
    if (!selectedPoem) return;
    await api.deletePoem(selectedPoem.id);
    setMessage("Стих скрыт.");
    setSelectedPoem(null);
    setTitle("Новый стих");
    setText("");
    await refresh();
  }

  async function restorePoem(poem: Poem) {
    const restored = await api.restorePoem(poem.id);
    setMessage("Стих восстановлен.");
    await refresh();
    await selectPoem(restored);
  }

  async function lockPoem() {
    if (!selectedPoem) return;
    const updated = await api.lockPoem(selectedPoem.id);
    setSelectedPoem(updated);
    setPoems((items) => items.map((item) => (item.id === updated.id ? updated : item)));
  }

  async function unlockSession() {
    const result = await api.unlockSession(password);
    setSessionUnlocked(result.session_unlocked);
    setPassword("");
  }

  async function changePassword() {
    await api.changePassword(oldPassword || null, newPassword);
    setOldPassword("");
    setNewPassword("");
    setMessage("Пароль обновлен.");
  }

  async function saveSettings() {
    const updated = await api.updateSettings(settings);
    setSettings(updated);
    setMessage("Настройки сохранены.");
  }

  async function flushOutbox() {
    const result = await api.flushTelegramOutbox();
    setMessage(`Очередь Telegram: отправлено ${result.sent}, ошибок ${result.failed}`);
  }

  async function savePhrase(selected: string, range = lineRangeForOffsets(text, 0, selected.length)) {
    if (!selectedPoem || !selected.trim()) return;
    const phrase = await api.createPhrase({
      text: selected.trim(),
      poem_id: selectedPoem.id,
      start_line: range.start,
      end_line: range.end,
      note: "сохранено вручную"
    });
    setPhrases((items) => [phrase, ...items]);
    setMessage("Фраза сохранена в архив.");
  }

  async function protectSelection(selected: string, kind: "intended" | "locked", range = currentLineContract) {
    if (!selectedPoem || !selected.trim()) return;
    const fragment = await api.createProtectedFragment(selectedPoem.id, {
      text: selected.trim(),
      start_line: range.start,
      end_line: range.end,
      kind
    });
    setProtectedFragments((items) => [fragment, ...items]);
    setMessage(kind === "intended" ? "Фрагмент отмечен как задуманный." : "ИИ не будет менять этот фрагмент.");
  }

  async function showRhymes(rawWord?: string) {
    const editor = editorRef.current;
    const input = rawWord || (editor ? wordNearCursor(text, editor.selectionStart) : "") || lastWord(text);
    const word = (lastWord(input) || input).replace(/[^\p{L}-]/gu, "");
    if (!word) return;
    setRhymePanel({ word, candidates: [], status: "loading" });
    try {
      const result = await api.findRhymes(word, text);
      setRhymePanel({ word: result.word, candidates: result.candidates, status: "ready" });
    } catch {
      setRhymePanel({ word, candidates: [], status: "error" });
    }
  }

  async function requestDraft(source: string, modeName: "recommendation" | "transformation", range: TextRange) {
    const lineRange = lineRangeForOffsets(text, range.start, range.end);
    if (!source.trim()) return;
    setDraftPanel({
      mode: modeName,
      source,
      range,
      lineRange,
      variants: [],
      status: "loading",
      message: "Генерирую варианты"
    });
    try {
      const result = await api.draft(source, modeName);
      const variants = result.variants.filter((variant) => variant.split("\n").length === lineRange.count);
      setDraftPanel({
        mode: modeName,
        source,
        range,
        lineRange,
        variants,
        status: variants.length ? "ready" : "empty",
        message: variants.length ? `${variants.length} варианта, строк: ${lineRange.count}` : "Качественного варианта нет"
      });
    } catch (error) {
      setDraftPanel({
        mode: modeName,
        source,
        range,
        lineRange,
        variants: [],
        status: "error",
        message: error instanceof Error ? error.message : "Ошибка генерации"
      });
    }
  }

  function applyDraftVariant(variant: string) {
    if (!draftPanel) return;
    const { start, end } = draftPanel.range;
    const next = `${text.slice(0, start)}${variant}${text.slice(end)}`;
    setText(next);
    setDraftPanel(null);
    setCompletion(null);
    window.setTimeout(() => {
      editorRef.current?.focus();
      editorRef.current?.setSelectionRange(start, start + variant.length);
    }, 0);
  }

  async function openPhrase(phrase: Phrase) {
    const poem = await api.getPoem(phrase.source.poem_id);
    await selectPoem(poem);
    setView("active");
    window.setTimeout(() => revealPhraseSource(poem.text, phrase.source.start_line, phrase.source.end_line), 40);
  }

  function revealPhraseSource(poemText: string, startLine: number, endLine: number) {
    const editor = editorRef.current;
    if (!editor) return;
    const lineCount = poemText.split("\n").length;
    const stanzaStart = Math.max(1, startLine - ((startLine - 1) % 4));
    const stanzaEnd = Math.min(lineCount, stanzaStart + 3);
    const lineHeight = editorFontSize * 1.58;

    editor.focus();
    editor.scrollTo({
      top: Math.max(0, (stanzaStart - 1) * lineHeight - editor.clientHeight * 0.24),
      behavior: "smooth"
    });

    const selectLines = (from: number, to: number) => {
      const start = offsetForLine(poemText, from);
      const end = offsetForLine(poemText, to + 1);
      editor.setSelectionRange(start, end);
    };

    setHighlight({ stanzaStart, stanzaEnd, lineStart: startLine, lineEnd: endLine });
    selectLines(stanzaStart, stanzaEnd);
    window.setTimeout(() => selectLines(startLine, endLine), 900);
    window.setTimeout(() => setHighlight(null), 2600);
  }

  function exportMarkdown() {
    if (!selectedPoem) return;
    window.location.href = api.exportMarkdownUrl(selectedPoem.id);
  }

  function acceptCompletion() {
    if (!completion || !editorRef.current) return;
    const cursor = editorRef.current.selectionStart;
    const addition = completionTextForInsert(text, cursor, completion.text);
    if (!addition) return;
    setText((value) => `${value.slice(0, cursor)}${addition}${value.slice(cursor)}`);
    setCompletion(null);
    window.setTimeout(() => {
      const nextPosition = cursor + addition.length;
      editorRef.current?.focus();
      editorRef.current?.setSelectionRange(nextPosition, nextPosition);
      setEditorCursor(nextPosition);
    }, 0);
  }

  function syncEditorCursor(editor = editorRef.current) {
    if (!editor) return;
    setEditorCursor(editor.selectionStart);
    setEditorScrollTop(editor.scrollTop);
  }

  function selectEditorLine(lineNumber: number) {
    if (!editorRef.current) return;
    const start = offsetForLine(text, lineNumber);
    const end = offsetForLine(text, lineNumber + 1);
    const lineHeight = editorFontSize * 1.58;
    editorRef.current.focus();
    editorRef.current.scrollTo({
      top: Math.max(0, (lineNumber - 1) * lineHeight - editorRef.current.clientHeight * 0.36),
      behavior: "smooth"
    });
    editorRef.current.setSelectionRange(start, end);
    setEditorCursor(end);
    setHighlight({ stanzaStart: lineNumber, stanzaEnd: lineNumber, lineStart: lineNumber, lineEnd: lineNumber });
    window.setTimeout(() => setHighlight(null), 1400);
  }

  function openContextMenu(event: React.MouseEvent<HTMLTextAreaElement>) {
    event.preventDefault();
    const rawRange = expandCollapsedSelectionToLine(text, event.currentTarget.selectionStart, event.currentTarget.selectionEnd);
    const selected = text.slice(rawRange.start, rawRange.end);
    event.currentTarget.setSelectionRange(rawRange.start, rawRange.end);
    setContextMenu({ x: event.clientX, y: event.clientY, selected, range: rawRange });
  }

  async function startVoice() {
    if (settings.speech_recognizer !== "browser") {
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
        setVoiceText("Запись через MediaRecorder недоступна в этом браузере.");
        return;
      }
      setVoiceText("Слушаю. После остановки отправлю аудио выбранному движку.");
      setIsRecording(true);
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const recorderOptions = MediaRecorder.isTypeSupported("audio/webm") ? { mimeType: "audio/webm" } : undefined;
        const recorder = new MediaRecorder(stream, recorderOptions);
        mediaStreamRef.current = stream;
        mediaChunksRef.current = [];
        recorder.ondataavailable = (event) => {
          if (event.data.size > 0) mediaChunksRef.current.push(event.data);
        };
        recorder.onstop = async () => {
          stream.getTracks().forEach((track) => track.stop());
          mediaStreamRef.current = null;
          setIsRecording(false);
          if (!applyVoiceRef.current) {
            setVoiceText("");
            return;
          }
          try {
            setVoiceText("Распознаю аудио...");
            const blob = new Blob(mediaChunksRef.current, { type: "audio/webm" });
            const result = await api.transcribeAudio(blob, settings.speech_recognizer);
            if (result.warning) {
              setVoiceText(result.warning);
              return;
            }
            setVoiceText(result.text);
            insertVoiceText(result.text);
          } catch (error) {
            setVoiceText(error instanceof Error ? error.message : "Не удалось распознать аудио.");
          }
        };
        mediaRecorderRef.current = recorder;
        recorder.start();
      } catch (error) {
        setIsRecording(false);
        setVoiceText(error instanceof Error ? error.message : "Микрофон недоступен.");
      }
      return;
    }

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setVoiceText("Браузерное распознавание недоступно.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "ru-RU";
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.onresult = (event: any) => {
      const transcript = Array.from(event.results)
        .map((result: any) => result[0].transcript)
        .join("\n");
      setVoiceText(transcript);
    };
    recognition.onend = () => setIsRecording(false);
    recognition.start();
    recognitionRef.current = recognition;
    setIsRecording(true);
  }

  function insertVoiceText(value: string) {
    if (!value.trim()) return;
    const editor = editorRef.current;
    const cursor = editor?.selectionStart ?? text.length;
    const prefix = text && !text.slice(0, cursor).endsWith("\n") ? "\n" : "";
    const insert = `${prefix}${value.trim()}`;
    setText((current) => `${current.slice(0, cursor)}${insert}${current.slice(cursor)}`);
    window.setTimeout(() => {
      const position = cursor + insert.length;
      editorRef.current?.focus();
      editorRef.current?.setSelectionRange(position, position);
    }, 0);
  }

  function stopVoice(apply: boolean) {
    applyVoiceRef.current = apply;
    if (settings.speech_recognizer !== "browser") {
      if (mediaRecorderRef.current?.state === "recording") {
        mediaRecorderRef.current.stop();
      } else {
        mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
        setIsRecording(false);
      }
      return;
    }
    recognitionRef.current?.stop?.();
    setIsRecording(false);
    if (apply && voiceText.trim()) {
      insertVoiceText(voiceText);
      setVoiceText("");
    }
  }

  return (
    <main
      className={mode === "idle" ? "shell idle" : "shell"}
      style={{
        background: mode === "idle" ? "#000000" : settings.studio_background,
        color: mode === "idle" ? "#f7f7f4" : settings.studio_text
      }}
      onClick={() => setContextMenu(null)}
    >
      <header className="topbar">
        <button className="brand" onClick={() => setView("active")} title="Стихия">
          <Sparkles size={18} />
          <strong>Стихия</strong>
        </button>
        <nav className="mode-switch" aria-label="Режим редактора">
          <button className={mode === "studio" ? "active" : ""} onClick={() => setMode("studio")} title="Студия">Студия</button>
          <button className={mode === "idle" ? "active" : ""} onClick={() => setMode("idle")} title="IDLE как редактор кода">
            <Keyboard size={15} />
            IDLE
          </button>
        </nav>
        <div className="actions">
          <button title="Новый стих" onClick={createPoem}><FilePlus2 size={18} /></button>
          <button title="Сохранить" onClick={() => persistPoem("manual")} disabled={!changed && !localDraft}><Save size={18} /></button>
          <button title="Поиск рифмы" onClick={() => showRhymes()}><Search size={18} /></button>
          <button title="Экспорт в Markdown" onClick={exportMarkdown} disabled={!selectedPoem}><Download size={18} /></button>
          <button title="Настройки" onClick={() => setView("settings")}><Settings size={18} /></button>
        </div>
      </header>

      <aside className="library">
        <div className="library-tabs">
          <button className={view === "active" ? "active" : ""} onClick={() => setView("active")} title="Стихи">Стихи</button>
          <button className={view === "archive" ? "active" : ""} onClick={() => setView("archive")} title="Архив фраз"><Archive size={15} /></button>
          <button className={view === "deleted" ? "active" : ""} onClick={() => setView("deleted")} title="Удаленные"><Trash2 size={15} /></button>
        </div>

        {view !== "archive" && view !== "settings" && (
          <>
            <div className="label">{view === "deleted" ? "Скрытые" : "Стихи"}</div>
            {localDraft && (
              <button className="poem selected local" onClick={() => openLocalDraft(title, text)}>
                <span>Локальный черновик</span>
                <small>создастся после первого текста</small>
              </button>
            )}
            {visiblePoems.map((poem) => (
              <button
                key={poem.id}
                className={`poem ${poem.is_locked ? "locked" : ""} ${selectedPoem?.id === poem.id ? "selected" : ""}`}
                onClick={() => selectPoem(poem)}
              >
                <span>{poem.is_locked ? (sessionUnlocked ? <LockOpen size={14} /> : <Lock size={14} />) : null}{poem.title}</span>
                <small>создан {formatDate(poem.created_at)} · изменен {formatDate(poem.updated_at)}</small>
              </button>
            ))}
          </>
        )}

        {view === "archive" && (
          <>
            <div className="label">Уникальные фразы</div>
            {phrases.map((phrase) => (
              <button key={phrase.id} className="phrase" onClick={() => openPhrase(phrase)}>
                <span>{phrase.text}</span>
                <small>{phrase.note ?? "образ"} · строка {phrase.source.start_line}</small>
              </button>
            ))}
          </>
        )}
      </aside>

      <section className="editor">
        {view === "settings" ? (
          <SettingsView
            settings={settings}
            setSettings={setSettings}
            oldPassword={oldPassword}
            setOldPassword={setOldPassword}
            newPassword={newPassword}
            setNewPassword={setNewPassword}
            saveSettings={saveSettings}
            changePassword={changePassword}
            modelStatus={modelStatus}
            flushOutbox={flushOutbox}
            autocompleteEnabled={autocompleteEnabled}
            setAutocompleteEnabled={setAutocompleteEnabled}
            autocompleteScope={autocompleteScope}
            setAutocompleteScope={setAutocompleteScope}
          />
        ) : editorAvailable ? (
          locked ? (
            <div className="locked-screen">
              <Lock size={28} />
              <h1>{selectedPoem?.title}</h1>
              <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Пароль" />
              <button className="primary" onClick={unlockSession}>Разблокировать</button>
            </div>
          ) : (
            <>
              <div className="editor-head">
                <input
                  className="title"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  spellCheck={false}
                />
                <span className={`save-state ${saveState}`}>{saveStateLabel(saveState, lastSavedAt, localDraft)}</span>
              </div>
              <div className="meter-strip" aria-label="Сводка разбора">
                <span>{analysisSummary.lines} строк</span>
                <span>схема {analysisSummary.scheme}</span>
                <span className={analysisSummary.hardIssues ? "bad" : ""}>
                  {analysisSummary.hardIssues ? `ритм ${analysisSummary.hardIssues}` : "ритм держится"}
                </span>
                {analysisSummary.softIssues > 0 && <span className="soft">спорно {analysisSummary.softIssues}</span>}
                {completion && <span className="hint">Tab примет подсказку</span>}
              </div>
              <div
                className={`poem-editor-wrap ${highlight ? "highlighted" : ""} ${mode === "idle" ? "code-editor" : ""}`}
                style={{ fontSize: editorFontSize }}
              >
                <div className="line-underlay" style={{ transform: `translateY(${-editorScrollTop}px)` }} aria-hidden="true">
                  {editorLines.map((line, index) => {
                    const lineNumber = index + 1;
                    const item = analysis[index];
                    const stanzaActive = !!highlight && lineNumber >= highlight.stanzaStart && lineNumber <= highlight.stanzaEnd;
                    const lineActive = !!highlight && lineNumber >= highlight.lineStart && lineNumber <= highlight.lineEnd;
                    return (
                      <span
                        key={`${lineNumber}-${line.length}`}
                        className={`line-underlay-row ${lineTone(item)} ${stanzaActive ? "stanza-active" : ""} ${lineActive ? "active" : ""}`}
                      />
                    );
                  })}
                </div>
                <div className="line-gutter" style={{ transform: `translateY(${-editorScrollTop}px)` }} aria-hidden="true">
                  {editorLines.map((_, index) => <span key={index}>{index + 1}</span>)}
                </div>
                <div className="line-metrics" style={{ transform: `translateY(${-editorScrollTop}px)` }} aria-hidden="true">
                  {editorLines.map((_, index) => {
                    const item = analysis[index];
                    return (
                      <span key={index} className={lineTone(item)}>
                        {item ? `${item.syllables}${item.rhythm_expected ? `/${item.rhythm_expected}` : ""} ${lineIssueLabel(item)}` : ""}
                      </span>
                    );
                  })}
                </div>
                <pre className="autocomplete-ghost" style={{ transform: `translateY(${-editorScrollTop}px)` }} aria-hidden="true">
                  <span className="ghost-base">{text.slice(0, editorCursor)}</span>
                  <span className="ghost-suggestion">{inlineCompletion}</span>
                </pre>
                <textarea
                  ref={editorRef}
                  className="poem-text"
                  value={text}
                  onChange={(event) => {
                    setText(event.target.value);
                    setCompletion(null);
                    syncEditorCursor(event.currentTarget);
                  }}
                  onSelect={(event) => syncEditorCursor(event.currentTarget)}
                  onClick={(event) => syncEditorCursor(event.currentTarget)}
                  onKeyUp={(event) => syncEditorCursor(event.currentTarget)}
                  onScroll={(event) => setEditorScrollTop(event.currentTarget.scrollTop)}
                  onKeyDown={(event) => {
                    if (event.key === "Tab" && completion) {
                      event.preventDefault();
                      acceptCompletion();
                    }
                  }}
                  onContextMenu={openContextMenu}
                  spellCheck={false}
                  placeholder="Пиши стих здесь..."
                />
              </div>
              <div className="voice-dock">
                <button className={isRecording ? "voice-button recording" : "voice-button"} onClick={isRecording ? () => stopVoice(true) : startVoice} title="Голосовой ввод">
                  <Mic size={17} />
                  <span>{isRecording ? "Добавить" : "Голос"}</span>
                </button>
                {isRecording && <button className="icon-text danger" onClick={() => stopVoice(false)}><X size={15} /> Отмена</button>}
                <small>{settings.speech_recognizer}</small>
              </div>
              {voiceText && <pre className="live-transcript">{voiceText}</pre>}
            </>
          )
        ) : (
          <div className="empty">Выбери стих или создай новый.</div>
        )}
      </section>

      <aside className="inspector">
        <InspectorTools
          selectedPoem={selectedPoem}
          localDraft={localDraft}
          view={view}
          lockPoem={lockPoem}
          deletePoem={deletePoem}
          restorePoem={restorePoem}
          showRhymes={showRhymes}
          requestDraft={() => requestDraft(text, "transformation", { start: 0, end: text.length })}
        />
        {draftPanel && (
          <DraftPanelView
            panel={draftPanel}
            onApply={applyDraftVariant}
            onClose={() => setDraftPanel(null)}
            onRegenerate={() => requestDraft(draftPanel.source, draftPanel.mode, draftPanel.range)}
          />
        )}
        {rhymePanel && (
          <RhymePanelView
            panel={rhymePanel}
            onClose={() => setRhymePanel(null)}
            onInsert={(candidate) => {
              const editor = editorRef.current;
              const cursor = editor?.selectionStart ?? text.length;
              setText((current) => `${current.slice(0, cursor)}${candidate}${current.slice(cursor)}`);
            }}
          />
        )}
        <div className="label spaced">Версии</div>
        <div className="versions">
          {versions.map((version) => (
            <button key={version.id} onClick={() => { setTitle(version.title); setText(version.text); }}>
              <History size={14} />
              <span>{formatDate(version.created_at)} · {version.source}</span>
            </button>
          ))}
        </div>
        {protectedFragments.length > 0 && (
          <>
            <div className="label spaced">Не трогать</div>
            <div className="protected-list">
              {protectedFragments.slice(0, 6).map((fragment) => (
                <button key={fragment.id} onClick={() => revealPhraseSource(text, fragment.start_line, fragment.end_line)}>
                  <span>{fragment.kind === "intended" ? "задумано" : "запрет"}</span>
                  <small>{fragment.text}</small>
                </button>
              ))}
            </div>
          </>
        )}
        {message && <div className="status">{message}</div>}
      </aside>

      {contextMenu && (
        <menu className="context-menu" style={{ left: contextMenu.x, top: contextMenu.y }}>
          <small>Строк: {currentLineContract.count}</small>
          <button onClick={() => protectSelection(contextMenu.selected, "intended")}>Отметить</button>
          <button onClick={() => requestDraft(contextMenu.selected, "recommendation", contextMenu.range)}>Рекомендация ИИ</button>
          <button onClick={() => requestDraft(contextMenu.selected, "transformation", contextMenu.range)}>ИИ трансформация</button>
          <button onClick={() => showRhymes(contextMenu.selected)}>Найти рифму</button>
          <button onClick={() => savePhrase(contextMenu.selected, currentLineContract)}>В архив</button>
          <button onClick={() => protectSelection(contextMenu.selected, "locked")}>Запретить ИИ менять</button>
        </menu>
      )}
    </main>
  );
}

function InspectorTools({
  selectedPoem,
  localDraft,
  view,
  lockPoem,
  deletePoem,
  restorePoem,
  showRhymes,
  requestDraft
}: {
  selectedPoem: Poem | null;
  localDraft: boolean;
  view: View;
  lockPoem: () => void;
  deletePoem: () => void;
  restorePoem: (poem: Poem) => void;
  showRhymes: () => void;
  requestDraft: () => void;
}) {
  return (
    <div className="tool-grid">
      <button title="Запаролить" onClick={lockPoem} disabled={!selectedPoem}><Lock size={17} /></button>
      <button title={localDraft ? "Убрать черновик" : "Скрыть"} onClick={deletePoem} disabled={!selectedPoem && !localDraft}><Trash2 size={17} /></button>
      {view === "deleted" && selectedPoem && <button title="Восстановить" onClick={() => restorePoem(selectedPoem)}><RotateCcw size={17} /></button>}
      <button title="Поиск рифмы" onClick={showRhymes}><Search size={17} /></button>
      <button title="ИИ трансформация" onClick={requestDraft}><Wand2 size={17} /></button>
    </div>
  );
}

function DraftPanelView({
  panel,
  onApply,
  onClose,
  onRegenerate
}: {
  panel: DraftPanel;
  onApply: (variant: string) => void;
  onClose: () => void;
  onRegenerate: () => void;
}) {
  return (
    <section className="ai-panel">
      <div className="panel-head">
        <div>
          <strong>{panel.mode === "recommendation" ? "Рекомендации" : "Трансформация"}</strong>
          <small>{panel.message}</small>
        </div>
        <div className="panel-actions">
          <button title="Реген" onClick={onRegenerate}><RefreshCw size={15} /></button>
          <button title="Закрыть" onClick={onClose}><X size={15} /></button>
        </div>
      </div>
      {panel.status === "loading" && <div className="panel-note">ИИ думает...</div>}
      {panel.status === "empty" && <div className="panel-note">Вариант не принят фильтром качества.</div>}
      {panel.status === "error" && <div className="panel-note error">{panel.message}</div>}
      <div className="variant-list">
        {panel.variants.map((variant, index) => (
          <article key={`${variant}-${index}`} className="variant-card">
            <pre>{variant}</pre>
            <button onClick={() => onApply(variant)}><Check size={15} /> Принять</button>
          </article>
        ))}
      </div>
    </section>
  );
}

function RhymePanelView({
  panel,
  onClose,
  onInsert
}: {
  panel: RhymePanel;
  onClose: () => void;
  onInsert: (candidate: string) => void;
}) {
  return (
    <section className="ai-panel">
      <div className="panel-head">
        <div>
          <strong>Рифмы</strong>
          <small>{panel.word}</small>
        </div>
        <button title="Закрыть" onClick={onClose}><X size={15} /></button>
      </div>
      {panel.status === "loading" && <div className="panel-note">Подбираю...</div>}
      {panel.status === "error" && <div className="panel-note error">Не удалось получить рифмы.</div>}
      <div className="rhyme-list">
        {panel.candidates.map((candidate) => (
          <button key={candidate} onClick={() => onInsert(candidate)}>{candidate}</button>
        ))}
      </div>
    </section>
  );
}

function SettingsView({
  settings,
  setSettings,
  oldPassword,
  setOldPassword,
  newPassword,
  setNewPassword,
  saveSettings,
  changePassword,
  modelStatus,
  flushOutbox,
  autocompleteEnabled,
  setAutocompleteEnabled,
  autocompleteScope,
  setAutocompleteScope
}: {
  settings: AppSettings;
  setSettings: React.Dispatch<React.SetStateAction<AppSettings>>;
  oldPassword: string;
  setOldPassword: (value: string) => void;
  newPassword: string;
  setNewPassword: (value: string) => void;
  saveSettings: () => void;
  changePassword: () => void;
  modelStatus: ModelStatus;
  flushOutbox: () => void;
  autocompleteEnabled: boolean;
  setAutocompleteEnabled: (value: boolean) => void;
  autocompleteScope: AutocompleteScope;
  setAutocompleteScope: (value: AutocompleteScope) => void;
}) {
  function setRecognizer(value: string) {
    setSettings({ ...settings, speech_recognizer: value as SpeechRecognizer });
  }

  return (
    <div className="settings-view">
      <h1>Настройки</h1>
      <section>
        <h2>Вид Studio</h2>
        <div className="settings-grid">
          <label>
            Фон
            <span className="color-row">
              <input type="color" value={settings.studio_background} onChange={(event) => setSettings({ ...settings, studio_background: event.target.value })} />
              <input value={settings.studio_background} onChange={(event) => setSettings({ ...settings, studio_background: event.target.value })} />
            </span>
          </label>
          <label>
            Текст
            <span className="color-row">
              <input type="color" value={settings.studio_text} onChange={(event) => setSettings({ ...settings, studio_text: event.target.value })} />
              <input value={settings.studio_text} onChange={(event) => setSettings({ ...settings, studio_text: event.target.value })} />
            </span>
          </label>
        </div>
        <label>
          Размер текста: {settings.studio_font_size}px
          <input type="range" min="16" max="34" value={settings.studio_font_size} onChange={(event) => setSettings({ ...settings, studio_font_size: Number(event.target.value) })} />
        </label>
        <p className="preview" style={{ fontSize: settings.studio_font_size }}>Предпросмотр строки в редакторе</p>
        <button className="primary" onClick={saveSettings}>Сохранить настройки</button>
      </section>
      <section>
        <h2>Автокомплит</h2>
        <label className="checkbox-line">
          <input type="checkbox" checked={autocompleteEnabled} onChange={(event) => setAutocompleteEnabled(event.target.checked)} />
          Включить подсказки строки
        </label>
        <select value={autocompleteScope} onChange={(event) => setAutocompleteScope(event.target.value as AutocompleteScope)}>
          <option value="general">Лучший вариант</option>
          <option value="personal">По моему стилю</option>
        </select>
      </section>
      <section>
        <h2>Распознавание голоса</h2>
        <select value={settings.speech_recognizer} onChange={(event) => setRecognizer(event.target.value)}>
          <option value="local_whisper">Локальная Whisper-модель</option>
          <option value="qwen_asr">Qwen ASR 1.7B</option>
          <option value="browser">Браузерный алгоритм</option>
          <option value="silero_vad_only">Только Silero VAD</option>
        </select>
      </section>
      <section>
        <h2>Модели</h2>
        <div className="model-list">
          {Object.entries(modelStatus).map(([name, status]) => (
            <div key={name}>
              <span>{name}</span>
              <strong>{status.exists ? "найдена" : "нет"}</strong>
              <small>{formatBytes(status.size_bytes)} · {status.path}</small>
            </div>
          ))}
        </div>
      </section>
      <section>
        <h2>Telegram</h2>
        <button onClick={flushOutbox}>Отправить очередь сейчас</button>
      </section>
      <section>
        <h2>Пароль профиля</h2>
        <input type="password" placeholder="Старый пароль" value={oldPassword} onChange={(event) => setOldPassword(event.target.value)} />
        <input type="password" placeholder="Новый пароль" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
        <button onClick={changePassword}>Сменить пароль</button>
      </section>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
