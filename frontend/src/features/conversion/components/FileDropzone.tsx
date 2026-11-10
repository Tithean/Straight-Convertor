import { useRef, useState } from 'react';
import { FileText, Upload, X } from 'lucide-react';
import { formatSize } from '../fileUtils';

interface Props {
  file: File | null;
  disabled: boolean;
  maxSize: number;
  onSelect: (files: File[]) => void;
  onRemove: () => void;
}

export default function FileDropzone({ file, disabled, maxSize, onSelect, onRemove }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const dragDepth = useRef(0);
  const [dragging, setDragging] = useState(false);

  if (file)
    return (
      <div className="selected-file">
        <span className="file-symbol">
          <FileText size={24} aria-hidden="true" />
        </span>
        <div className="file-details">
          <strong title={file.name}>{file.name}</strong>
          <span>{formatSize(file.size)} · Ready to convert</span>
        </div>
        <button
          type="button"
          className="icon-button"
          aria-label="Remove selected file"
          disabled={disabled}
          onClick={onRemove}
        >
          <X size={19} />
        </button>
      </div>
    );

  return (
    <div
      className={`dropzone ${dragging ? 'is-dragging' : ''} ${disabled ? 'is-disabled' : ''}`}
      onDragOver={(event) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = disabled ? 'none' : 'copy';
      }}
      onDragEnter={(event) => {
        event.preventDefault();
        dragDepth.current++;
        if (!disabled) setDragging(true);
      }}
      onDragLeave={(event) => {
        event.preventDefault();
        dragDepth.current--;
        if (dragDepth.current <= 0) setDragging(false);
      }}
      onDrop={(event) => {
        event.preventDefault();
        dragDepth.current = 0;
        setDragging(false);
        if (!disabled) onSelect(Array.from(event.dataTransfer.files));
      }}
    >
      <span className="upload-symbol">
        <Upload size={25} strokeWidth={1.6} aria-hidden="true" />
      </span>
      <strong>Drop your file here</strong>
      <span className="dropzone-or">or select one from your device</span>
      <button
        type="button"
        className="button button-secondary browse-button"
        disabled={disabled}
        onClick={() => input.current?.click()}
      >
        Choose file
      </button>
      <input
        ref={input}
        type="file"
        className="visually-hidden"
        tabIndex={-1}
        aria-label="Choose a file to convert"
        accept=".docx,.pptx,.pdf"
        disabled={disabled}
        onChange={(event) => {
          if (event.target.files) onSelect(Array.from(event.target.files));
          event.target.value = '';
        }}
      />
      <span className="file-hint">
        DOCX, PPTX, PDF <span aria-hidden="true">·</span> Up to {Math.round(maxSize / 1024 / 1024)}{' '}
        MB
      </span>
    </div>
  );
}
