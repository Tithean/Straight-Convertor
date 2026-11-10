import { useCallback, useEffect, useRef, useState } from 'react';
import { convertFile } from './api';
import type { Conversion, ConversionState } from './types';

export function useConversion() {
  const [state, setState] = useState<ConversionState>({ phase: 'idle' });
  const request = useRef<AbortController | null>(null);
  const downloadUrl = useRef<string | null>(null);

  const reset = useCallback(() => {
    request.current?.abort();
    request.current = null;
    if (downloadUrl.current) URL.revokeObjectURL(downloadUrl.current);
    downloadUrl.current = null;
    setState({ phase: 'idle' });
  }, []);

  useEffect(
    () => () => {
      request.current?.abort();
      if (downloadUrl.current) URL.revokeObjectURL(downloadUrl.current);
    },
    [],
  );

  async function start(file: File, conversion: Conversion, timeoutSeconds: number) {
    reset();
    const controller = new AbortController();
    request.current = controller;
    setState({ phase: 'uploading', progress: 0 });
    try {
      const result = await convertFile({
        file,
        conversion,
        timeoutSeconds,
        signal: controller.signal,
        onUpload: (progress) => {
          if (request.current === controller) setState({ phase: 'uploading', progress });
        },
        onProcessing: () => {
          if (request.current === controller) setState({ phase: 'converting' });
        },
      });
      // Ignore completions from a request abandoned by navigation or a reset.
      if (request.current !== controller) return;
      const url = URL.createObjectURL(result.blob);
      downloadUrl.current = url;
      setState({ phase: 'ready', url, filename: result.filename, size: result.blob.size });
    } catch (error) {
      if (request.current !== controller || controller.signal.aborted) return;
      setState({
        phase: 'error',
        message: error instanceof Error ? error.message : 'Conversion failed. Please try again.',
      });
    }
  }

  return { state, start, reset };
}
