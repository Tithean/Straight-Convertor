import { AlertCircle, Check, Download, LoaderCircle } from 'lucide-react';
import { formatSize } from '../fileUtils';
import type { ConversionState } from '../types';

export default function ConversionStatus({
  state,
  onReset,
}: {
  state: ConversionState;
  onReset: () => void;
}) {
  if (state.phase === 'idle') return null;
  if (state.phase === 'error')
    return (
      <div className="error-box" role="alert">
        <AlertCircle size={18} aria-hidden="true" />
        <span>{state.message}</span>
      </div>
    );
  if (state.phase === 'ready')
    return (
      <div className="success-panel" role="status">
        <span className="success-icon">
          <Check size={24} aria-hidden="true" />
        </span>
        <h3>Your file is ready.</h3>
        <p title={state.filename}>{state.filename}</p>
        <span className="result-size">{formatSize(state.size)}</span>
        <a className="button button-primary" href={state.url} download={state.filename}>
          <Download size={18} aria-hidden="true" />
          Download file
        </a>
        <button className="text-button" type="button" onClick={onReset}>
          Convert another file
        </button>
      </div>
    );
  return (
    <div className="progress-panel" role="status" aria-live="polite">
      <div className="progress-heading">
        <LoaderCircle className="spinner" size={18} aria-hidden="true" />
        <strong>
          {state.phase === 'uploading' ? 'Uploading your file…' : 'Converting your file…'}
        </strong>
        {state.phase === 'uploading' && <span>{state.progress}%</span>}
      </div>
      {state.phase === 'uploading' ? (
        <progress max={100} value={state.progress} aria-label="Upload progress" />
      ) : (
        <progress aria-label="Conversion in progress" />
      )}
      <p>
        {state.phase === 'uploading'
          ? 'Keep this page open while your file uploads.'
          : 'Larger documents can take a little longer. Your download will appear here.'}
      </p>
    </div>
  );
}
