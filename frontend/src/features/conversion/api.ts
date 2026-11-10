import type { Capabilities, Conversion } from './types';
import { outputFilename } from './fileUtils';

const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

export async function getCapabilities(signal: AbortSignal): Promise<Capabilities> {
  const response = await fetch(`${baseUrl}/api/formats`, { signal });
  if (!response.ok) throw new Error('The converter is unavailable right now. Please try again.');
  return response.json();
}

interface ConvertOptions {
  file: File;
  conversion: Conversion;
  timeoutSeconds: number;
  signal: AbortSignal;
  onUpload: (progress: number) => void;
  onProcessing: () => void;
}

export function convertFile(options: ConvertOptions): Promise<{ blob: Blob; filename: string }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const abort = () => xhr.abort();
    xhr.open('POST', `${baseUrl}/api/convert`);
    xhr.responseType = 'blob';
    // Extra time covers upload and response transfer beyond the backend's conversion limit.
    xhr.timeout = (options.timeoutSeconds + 180) * 1000;
    options.signal.addEventListener('abort', abort, { once: true });
    xhr.onloadend = () => options.signal.removeEventListener('abort', abort);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) options.onUpload(Math.round((event.loaded / event.total) * 100));
    };
    xhr.upload.onload = options.onProcessing;
    xhr.onload = async () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve({
          blob: xhr.response,
          filename: outputFilename(options.file.name, options.conversion),
        });
        return;
      }
      let message = 'Conversion failed. Please try again with another file.';
      try {
        const error = JSON.parse(await (xhr.response as Blob).text());
        message = error.error?.message || message;
      } catch {
        if (xhr.status === 413) message = 'The upload is too large. Please choose a smaller file.';
        if (xhr.status === 502 || xhr.status === 503)
          message = 'The converter is unavailable right now. Please try again.';
      }
      reject(new Error(message));
    };
    xhr.onerror = () =>
      reject(new Error('Could not reach the converter. Check your connection and try again.'));
    xhr.ontimeout = () =>
      reject(new Error('This request took too long. Please try a smaller file.'));
    xhr.onabort = () => reject(new DOMException('Request cancelled', 'AbortError'));
    if (options.signal.aborted) {
      reject(new DOMException('Request cancelled', 'AbortError'));
      return;
    }
    const body = new FormData();
    body.append('file', options.file);
    body.append('target', options.conversion.target);
    xhr.send(body);
  });
}
