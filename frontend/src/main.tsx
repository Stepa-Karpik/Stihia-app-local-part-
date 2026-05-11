import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { Download, LockOpen, Mic, Settings } from "lucide-react";
import "./styles.css";

const poems = [
  {
    title: "Агония в пистолете",
    createdAt: "12 мая 2026",
    updatedAt: "только что",
    locked: true
  },
  {
    title: "Белый шум лестниц",
    createdAt: "11 мая 2026",
    updatedAt: "вчера",
    locked: false
  }
];

function App() {
  const [mode, setMode] = useState<"studio" | "idle">("studio");
  const [fontSize, setFontSize] = useState(22);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number } | null>(null);

  return (
    <main className="shell" onClick={() => setContextMenu(null)}>
      <header className="topbar">
        <strong>Стихия</strong>
        <nav aria-label="Режим редактора">
          <button className={mode === "studio" ? "active" : ""} onClick={() => setMode("studio")}>Студия</button>
          <button className={mode === "idle" ? "active" : ""} onClick={() => setMode("idle")}>IDLE</button>
        </nav>
        <div className="actions">
          <button title="Голосовой ввод"><Mic size={18} /></button>
          <button title="Экспорт в Markdown"><Download size={18} /></button>
          <button title="Настройки"><Settings size={18} /></button>
        </div>
      </header>

      <aside className="library">
        <div className="label">По дате изменения</div>
        {poems.map((poem) => (
          <button key={poem.title} className={poem.locked ? "poem locked" : "poem"}>
            <span>{poem.title}</span>
            <small>создан: {poem.createdAt} · изменен: {poem.updatedAt}</small>
          </button>
        ))}
        <button className="deleted">Удаленные</button>
      </aside>

      <section className={mode === "idle" ? "editor idle" : "editor"}>
        <input className="title" value="Агония в пистолете" readOnly />
        <article
          className="poem-text"
          style={{ fontSize }}
          contentEditable
          suppressContentEditableWarning
          onContextMenu={(event) => {
            event.preventDefault();
            setContextMenu({ x: event.clientX, y: event.clientY });
          }}
        >
          <p>Была агонией в смертника пистолете</p>
          <p>и его решением одуматься в миг,</p>
          <p>но город молчал, будто выдох на свете</p>
          <p>застрял между ребер и больше не стих.</p>
        </article>
        <div className="voice-inline">
          <Mic size={16} />
          <span>Голосовой ввод внутри редактора</span>
          <button>Начать</button>
        </div>
      </section>

      <aside className="inspector">
        <div className="label">Настройки текста</div>
        <label>
          Размер
          <input type="range" min="16" max="34" value={fontSize} onChange={(event) => setFontSize(Number(event.target.value))} />
        </label>
        <div className="preview" style={{ fontSize }}>Предпросмотр строки</div>
        <button className="unlock"><LockOpen size={16} /> Сессия разблокирована</button>
      </aside>

      {contextMenu && (
        <menu className="context-menu" style={{ left: contextMenu.x, top: contextMenu.y }}>
          <button>Отметить как задумано</button>
          <button>Рекомендация ИИ</button>
          <button>ИИ трансформация</button>
          <button>Найти рифму</button>
          <button>Сохранить как образ</button>
          <button>Запретить ИИ менять</button>
        </menu>
      )}
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
