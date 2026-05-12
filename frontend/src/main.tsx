import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Archive,
  Download,
  FilePlus2,
  History,
  Lock,
  LockOpen,
  Mic,
  RotateCcw,
  Save,
  Search,
  Settings,
  Trash2,
  Wand2
} from "lucide-react";
import { api } from "./api";
import type { AppSettings, LineAnalysis, ModelStatus, Phrase, Poem, PoemVersion, SpeechRecognizer } from "./types";
import "./styles.css";

type View = "active" | "deleted" | "archive" | "settings";
type Mode = "studio" | "idle";
type AutocompleteScope = "personal" | "general";

const DEFAULT_SETTINGS: AppSettings = {
  studio_background: "#050505",
  studio_text: "#f7f7f4",
  studio_font_size: 22,
  speech_recognizer: "local_whisper"
};

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

function lineRangeForSelection(text: string, selectedText: string) {
  const index = selectedText ? text.indexOf(selectedText) : -1;
  if (index < 0) {
    return { start: 1, end: 1, count: 1 };
  }
  const before = text.slice(0, index);
  const start = before.split("\n").length;
  const count = Math.max(1, selectedText.split("\n").length);
  return { start, end: start + count - 1, count };
}

function lineBeforeCursor(value: string, cursor: number) {
  const before = value.slice(0, cursor);
  return before.slice(before.lastIndexOf("\n") + 1);
}

function offsetForLine(text: string, line: number) {
  if (line <= 1) {
    return 0;
  }
  let offset = 0;
  for (let current = 1; current < line; current += 1) {
    const nextBreak = text.indexOf("\n", offset);
    if (nextBreak < 0) {
      return text.length;
    }
    offset = nextBreak + 1;
  }
  return offset;
}

function App() {
  const [view, setView] = useState<View>("active");
  const [mode, setMode] = useState<Mode>("studio");
  const [poems, setPoems] = useState<Poem[]>([]);
  const [deletedPoems, setDeletedPoems] = useState<Poem[]>([]);
  const [selectedPoem, setSelectedPoem] = useState<Poem | null>(null);
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [versions, setVersions] = useState<PoemVersion[]>([]);
  const [phrases, setPhrases] = useState<Phrase[]>([]);
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [sessionUnlocked, setSessionUnlocked] = useState(false);
  const [password, setPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [oldPassword, setOldPassword] = useState("");
  const [message, setMessage] = useState("");
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; selected: string } | null>(null);
  const [highlight, setHighlight] = useState<{ stanzaStart: number; stanzaEnd: number; lineStart: number; lineEnd: number } | null>(null);
  const [voiceText, setVoiceText] = useState("");
  const [analysis, setAnalysis] = useState<LineAnalysis[]>([]);
  const [toolResult, setToolResult] = useState<string[]>([]);
  const [modelStatus, setModelStatus] = useState<ModelStatus>({});
  const [isRecording, setIsRecording] = useState(false);
  const [autocompleteEnabled, setAutocompleteEnabled] = useState(() => localStorage.getItem("stihia.autocomplete") !== "off");
  const [autocompleteScope, setAutocompleteScope] = useState<AutocompleteScope>(
    () => (localStorage.getItem("stihia.autocompleteScope") as AutocompleteScope | null) ?? "general"
  );
  const [completion, setCompletion] = useState<{ text: string; engine: string } | null>(null);
  const recognitionRef = useRef<any>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaChunksRef = useRef<Blob[]>([]);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const applyVoiceRef = useRef(false);
  const editorRef = useRef<HTMLTextAreaElement>(null);

  const locked = selectedPoem?.is_locked && !sessionUnlocked;
  const currentLineContract = useMemo(() => lineRangeForSelection(text, contextMenu?.selected ?? ""), [text, contextMenu]);

  useEffect(() => {
    localStorage.setItem("stihia.autocomplete", autocompleteEnabled ? "on" : "off");
  }, [autocompleteEnabled]);

  useEffect(() => {
    localStorage.setItem("stihia.autocompleteScope", autocompleteScope);
  }, [autocompleteScope]);

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

    if (!selectedPoem && active[0]) {
      selectPoem(active[0]);
    }
  }

  async function selectPoem(poem: Poem) {
    setSelectedPoem(poem);
    setTitle(poem.title);
    setText(poem.text);
    setVersions(await api.listVersions(poem.id).catch(() => []));
    setAnalysis((await api.analyzeText(poem.text).catch(() => ({ lines: [] }))).lines);
    setView(poem.is_deleted ? "deleted" : "active");
  }

  async function createPoem() {
    const poem = await api.createPoem("Новый стих", "");
    setPoems((items) => [poem, ...items]);
    await selectPoem(poem);
  }

  async function savePoem(source = "Сохранено") {
    if (!selectedPoem || locked) return;
    const updated = await api.updatePoem(selectedPoem.id, title, text);
    setSelectedPoem(updated);
    setPoems((items) => [updated, ...items.filter((item) => item.id !== updated.id)]);
    setVersions(await api.listVersions(updated.id));
    setAnalysis((await api.analyzeText(updated.text)).lines);
    setMessage(source);
  }

  async function deletePoem() {
    if (!selectedPoem) return;
    await api.deletePoem(selectedPoem.id);
    setMessage("Стих скрыт");
    setSelectedPoem(null);
    setTitle("");
    setText("");
    await refresh();
  }

  async function restorePoem(poem: Poem) {
    const restored = await api.restorePoem(poem.id);
    setMessage("Стих восстановлен");
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
    setMessage("Пароль обновлен");
  }

  async function saveSettings() {
    const updated = await api.updateSettings(settings);
    setSettings(updated);
    setMessage("Настройки сохранены");
  }

  async function flushOutbox() {
    const result = await api.flushTelegramOutbox();
    setMessage(`Очередь Telegram: отправлено ${result.sent}, ошибок ${result.failed}`);
  }

  async function savePhrase(selected: string) {
    if (!selectedPoem || !selected.trim()) return;
    const range = lineRangeForSelection(text, selected);
    const phrase = await api.createPhrase({
      text: selected.trim(),
      poem_id: selectedPoem.id,
      start_line: range.start,
      end_line: range.end,
      note: "сохранено вручную"
    });
    setPhrases((items) => [phrase, ...items]);
    setMessage("Фраза сохранена в архив");
  }

  async function showRhymes(selected: string) {
    const word = (selected.trim().split(/\s+/).pop() || "").replace(/[^\p{L}-]/gu, "");
    if (!word) return;
    const result = await api.findRhymes(word, text);
    setToolResult(result.candidates);
    setMessage(`Рифмы к слову: ${result.word}`);
  }

  async function showDraft(selected: string, modeName: string) {
    if (!selected.trim()) return;
    const result = await api.draft(selected, modeName);
    setToolResult(result.variants);
    setMessage(`Варианты: ${result.line_count} строк, форма сохранена`);
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
    const lineHeight = settings.studio_font_size * 1.58;

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
    window.setTimeout(() => selectLines(startLine, endLine), 950);
    window.setTimeout(() => setHighlight(null), 2800);
  }

  function exportMarkdown() {
    if (!selectedPoem) return;
    window.location.href = api.exportMarkdownUrl(selectedPoem.id);
  }

  function acceptCompletion() {
    if (!completion || !editorRef.current) return;
    const cursor = editorRef.current.selectionStart;
    const spacer = completion.text.startsWith(" ") ? "" : " ";
    const addition = `${spacer}${completion.text}`;
    setText((value) => `${value.slice(0, cursor)}${addition}${value.slice(cursor)}`);
    setCompletion(null);
    window.setTimeout(() => {
      const nextPosition = cursor + addition.length;
      editorRef.current?.focus();
      editorRef.current?.setSelectionRange(nextPosition, nextPosition);
    }, 0);
  }

  function openContextMenu(event: React.MouseEvent<HTMLTextAreaElement>) {
    event.preventDefault();
    const selected = window.getSelection()?.toString() || text.slice(event.currentTarget.selectionStart, event.currentTarget.selectionEnd);
    setContextMenu({ x: event.clientX, y: event.clientY, selected });
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
          if (event.data.size > 0) {
            mediaChunksRef.current.push(event.data);
          }
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
            if (result.text.trim()) {
              setText((value) => `${value}${value ? "\n" : ""}${result.text.trim()}`);
            }
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
      setText((value) => `${value}${value ? "\n" : ""}${voiceText.trim()}`);
      setVoiceText("");
    }
  }

  useEffect(() => {
    refresh().catch((error) => setMessage(`API недоступен: ${error.message}`));
  }, []);

  useEffect(() => {
    if (!autocompleteEnabled || !selectedPoem || locked || view === "settings") {
      setCompletion(null);
      return;
    }
    const timeout = window.setTimeout(async () => {
      const editor = editorRef.current;
      if (!editor) return;
      const line = lineBeforeCursor(text, editor.selectionStart).trim();
      if (line.length < 4) {
        setCompletion(null);
        return;
      }
      try {
        const result = await api.completeLine(text, line, autocompleteScope);
        setCompletion(result.completion ? { text: result.completion, engine: result.engine } : null);
      } catch {
        setCompletion(null);
      }
    }, 420);
    return () => window.clearTimeout(timeout);
  }, [autocompleteEnabled, autocompleteScope, locked, selectedPoem, text, view]);

  const visiblePoems = view === "deleted" ? deletedPoems : poems;

  return (
    <main
      className={mode === "idle" ? "shell idle" : "shell"}
      style={{ background: settings.studio_background, color: settings.studio_text }}
      onClick={() => setContextMenu(null)}
    >
      <header className="topbar">
        <strong>Стихия</strong>
        <nav>
          <button className={mode === "studio" ? "active" : ""} onClick={() => setMode("studio")}>Студия</button>
          <button className={mode === "idle" ? "active" : ""} onClick={() => setMode("idle")}>IDLE</button>
        </nav>
        <div className="actions">
          <button title="Новый стих" onClick={createPoem}><FilePlus2 size={18} /></button>
          <button title="Сохранить" onClick={() => savePoem()}><Save size={18} /></button>
          <button title="Экспорт в Markdown" onClick={exportMarkdown}><Download size={18} /></button>
          <button title="Настройки" onClick={() => setView("settings")}><Settings size={18} /></button>
        </div>
      </header>

      <aside className="library">
        <div className="library-tabs">
          <button className={view === "active" ? "active" : ""} onClick={() => setView("active")}>Стихи</button>
          <button className={view === "archive" ? "active" : ""} onClick={() => setView("archive")}><Archive size={15} /> Архив</button>
          <button className={view === "deleted" ? "active" : ""} onClick={() => setView("deleted")}><Trash2 size={15} /> Удаленные</button>
        </div>

        {view !== "archive" && view !== "settings" && (
          <>
            <div className="label">{view === "deleted" ? "Скрытые стихи" : "По последнему изменению"}</div>
            {visiblePoems.map((poem) => (
              <button
                key={poem.id}
                className={`poem ${poem.is_locked ? "locked" : ""} ${selectedPoem?.id === poem.id ? "selected" : ""}`}
                onClick={() => selectPoem(poem)}
              >
                <span>{poem.is_locked ? (sessionUnlocked ? <LockOpen size={14} /> : <Lock size={14} />) : null}{poem.title}</span>
                <small>создан: {formatDate(poem.created_at)} · изменен: {formatDate(poem.updated_at)}</small>
              </button>
            ))}
          </>
        )}

        {view === "archive" && (
          <>
            <div className="label">Лучшие фразы</div>
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
        ) : selectedPoem ? (
          locked ? (
            <div className="locked-screen">
              <Lock size={28} />
              <h1>{selectedPoem.title}</h1>
              <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Пароль" />
              <button className="primary" onClick={unlockSession}>Разблокировать сессию</button>
            </div>
          ) : (
            <>
              <input className="title" value={title} onChange={(event) => setTitle(event.target.value)} />
              <textarea
                ref={editorRef}
                className={highlight ? "poem-text highlighted" : "poem-text"}
                style={{ fontSize: settings.studio_font_size }}
                value={text}
                onChange={(event) => {
                  setText(event.target.value);
                  setCompletion(null);
                }}
                onKeyDown={(event) => {
                  if (event.key === "Tab" && completion) {
                    event.preventDefault();
                    acceptCompletion();
                  }
                }}
                onContextMenu={openContextMenu}
                spellCheck={false}
              />
              {completion && (
                <button className="autocomplete-strip" onClick={acceptCompletion}>
                  <span>{completion.text}</span>
                  <small>Tab · {completion.engine}</small>
                </button>
              )}
              <div className="voice-inline">
                <Mic size={16} />
                <span>{isRecording ? "Запись идет" : "Голосовой ввод в редакторе"} · {settings.speech_recognizer}</span>
                {isRecording ? (
                  <>
                    <button onClick={() => stopVoice(true)}>Добавить</button>
                    <button onClick={() => stopVoice(false)}>Отмена</button>
                  </>
                ) : (
                  <button onClick={startVoice}>Начать</button>
                )}
              </div>
              {voiceText && <pre className="live-transcript">{voiceText}</pre>}
            </>
          )
        ) : (
          <div className="empty">Выбери стих или создай новый.</div>
        )}
      </section>

      <aside className="inspector">
        <div className="label">Действия</div>
        <button onClick={() => selectedPoem && lockPoem()}><Lock size={16} /> Запаролить стих</button>
        <button onClick={deletePoem}><Trash2 size={16} /> Скрыть</button>
        {view === "deleted" && selectedPoem && <button onClick={() => restorePoem(selectedPoem)}><RotateCcw size={16} /> Восстановить</button>}
        <button onClick={() => showRhymes(text.split(/\s+/).at(-1) ?? "")}><Search size={16} /> Поиск рифмы</button>
        <button onClick={() => showDraft(text, "transformation")}><Wand2 size={16} /> ИИ трансформация</button>

        <div className="label spaced">Версии</div>
        <div className="versions">
          {versions.map((version) => (
            <button key={version.id} onClick={() => { setTitle(version.title); setText(version.text); }}>
              <History size={14} />
              <span>{formatDate(version.created_at)} · {version.source}</span>
            </button>
          ))}
        </div>
        <div className="label spaced">Разбор</div>
        <div className="analysis-list">
          {analysis.slice(0, 8).map((line) => (
            <div key={line.number}>
              <span>{line.number}</span>
              <strong>{line.syllables}</strong>
              <small>{line.last_word ?? "нет слова"}</small>
            </div>
          ))}
        </div>
        {toolResult.length > 0 && (
          <>
            <div className="label spaced">Варианты</div>
            <div className="tool-result">
              {toolResult.map((item) => (
                <button key={item} onClick={() => item.includes("\n") && setText(item)}>{item}</button>
              ))}
            </div>
          </>
        )}
        {message && <div className="status">{message}</div>}
      </aside>

      {contextMenu && (
        <menu className="context-menu" style={{ left: contextMenu.x, top: contextMenu.y }}>
          <small>Выделено строк: {currentLineContract.count}</small>
          <button onClick={() => setMessage("Фрагмент отмечен как задуманный")}>Отметить как задумано</button>
          <button onClick={() => showDraft(contextMenu.selected, "recommendation")}>Рекомендация ИИ</button>
          <button onClick={() => showDraft(contextMenu.selected, "transformation")}>ИИ трансформация</button>
          <button onClick={() => showRhymes(contextMenu.selected)}>Найти рифму</button>
          <button onClick={() => savePhrase(contextMenu.selected)}>Сохранить как образ</button>
          <button onClick={() => setMessage("ИИ больше не будет трогать этот фрагмент")}>Запретить ИИ менять</button>
        </menu>
      )}
    </main>
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
  setSettings: (settings: AppSettings) => void;
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
        <h2>Вид редактора</h2>
        <label>Фон Studio<input value={settings.studio_background} onChange={(event) => setSettings({ ...settings, studio_background: event.target.value })} /></label>
        <label>Текст Studio<input value={settings.studio_text} onChange={(event) => setSettings({ ...settings, studio_text: event.target.value })} /></label>
        <label>Размер текста<input type="range" min="16" max="34" value={settings.studio_font_size} onChange={(event) => setSettings({ ...settings, studio_font_size: Number(event.target.value) })} /></label>
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
