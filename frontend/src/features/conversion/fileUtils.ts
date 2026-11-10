import type { Capabilities, Conversion } from './types';

export function extension(filename: string): string {
  return filename.split('.').pop()?.toLowerCase() ?? '';
}

export function formatSize(bytes: number): string {
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function validateSelection(file: File, capabilities: Capabilities): string | null {
  if (file.size === 0) return 'This file is empty. Please choose another file.';
  if (file.size > capabilities.max_upload_bytes)
    return `Your file is too large. The limit is ${formatSize(capabilities.max_upload_bytes)}.`;
  if (!capabilities.conversions.some((item) => item.source === extension(file.name)))
    return 'Please choose a Word (.docx), PowerPoint (.pptx), or PDF (.pdf) file.';
  return null;
}

export function outputFilename(filename: string, conversion: Conversion): string {
  const stem = filename.replace(/\.[^.]+$/, '').replace(/[\\/\r\n]/g, '_');
  return `${stem || 'converted'}.${conversion.target}`;
}
