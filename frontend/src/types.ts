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
