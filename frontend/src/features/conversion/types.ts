export type Format = 'docx' | 'pptx' | 'pdf';

export interface Conversion {
  source: Format;
  target: Format;
  label: string;
  description: string;
  note: string;
  available: boolean;
}

export interface Capabilities {
  max_upload_bytes: number;
  max_pdf_pages: number;
  timeout_seconds: number;
  conversions: Conversion[];
}

export type ConversionState =
  | { phase: 'idle' }
  | { phase: 'uploading'; progress: number }
  | { phase: 'converting' }
  | { phase: 'ready'; url: string; filename: string; size: number }
  | { phase: 'error'; message: string };
