export type SpeechRecognizer = "local_whisper" | "qwen_asr" | "browser" | "silero_vad_only";

export type Poem = {
  id: string;
  title: string;
  text: string;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
  is_locked: boolean;
  telegram_message_id: number | null;
};

export type PoemVersion = {
  id: string;
  poem_id: string;
  title: string;
  text: string;
  created_at: string;
  source: string;
};

export type ProtectedFragment = {
  id: string;
  poem_id: string;
  text: string;
  start_line: number;
  end_line: number;
  kind: "intended" | "locked";
  created_at: string;
};

export type Phrase = {
  id: string;
  text: string;
  note: string | null;
  created_at: string;
  source: {
    poem_id: string;
    start_line: number;
    end_line: number;
  };
};

export type AppSettings = {
  studio_background: string;
  studio_text: string;
  studio_font_size: number;
  speech_recognizer: SpeechRecognizer;
};

export type LineAnalysis = {
  number: number;
  text: string;
  syllables: number;
  last_word: string | null;
  rhyme_tail: string | null;
  rhyme_group: string | null;
  rhyme_scheme: string;
  rhythm_expected: number;
  rhythm_delta: number;
  stanza_index: number;
  line_in_stanza: number;
  flags: string[];
};

export type ModelStatus = Record<string, { path: string; exists: boolean; size_bytes: number }>;

export type SpeechTranscription = {
  text: string;
  engine: string;
  warning: string | null;
};

export type CompletionResponse = {
  completion: string;
  line_count: number;
  engine: string;
};
