import { useEffect, useState } from 'react';
import {
  ArrowDown,
  ArrowLeftRight,
  ArrowRight,
  Check,
  FileText,
  Info,
  Layers,
  LockKeyhole,
  Presentation,
  RefreshCw,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import { getCapabilities } from '../features/conversion/api';
import FileDropzone from '../features/conversion/components/FileDropzone';
import FormatSelect from '../features/conversion/components/FormatSelect';
import ConversionStatus from '../features/conversion/components/ConversionStatus';
import { extension, validateSelection } from '../features/conversion/fileUtils';
import type { Capabilities, Conversion } from '../features/conversion/types';
import { useConversion } from '../features/conversion/useConversion';

export default function App() {
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [loadingError, setLoadingError] = useState('');
  const [reload, setReload] = useState(0);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState('');
  const { state, start, reset } = useConversion();
  const busy = state.phase === 'uploading' || state.phase === 'converting';
  const selected = capabilities?.conversions[selectedIndex];

  useEffect(() => {
    const controller = new AbortController();
    setLoadingError('');
    getCapabilities(controller.signal)
      .then(setCapabilities)
      .catch((error: unknown) => {
        if (!controller.signal.aborted)
          setLoadingError(
            error instanceof Error
              ? error.message
              : 'Could not connect to the converter. Please try again.',
          );
      });
    return () => controller.abort();
  }, [reload]);

  function clearFile() {
    reset();
    setFile(null);
    setFileError('');
  }

  function selectFiles(files: File[]) {
    if (!capabilities || busy) return;
    if (files.length !== 1) {
      setFileError('Please choose one file at a time.');
      return;
    }
    const candidate = files[0];
    const error = validateSelection(candidate, capabilities);
    if (error) {
      setFileError(error);
      return;
    }
    reset();
    setFileError('');
    setFile(candidate);
    setSelectedIndex(
      capabilities.conversions.findIndex((item) => item.source === extension(candidate.name)),
    );
  }

  function selectConversion(index: number) {
    if (busy) return;
    const conversion = capabilities?.conversions[index];
    reset();
    if (file && conversion?.source !== extension(file.name)) setFile(null);
    setFileError('');
    setSelectedIndex(index);
  }

  function converterIcon(conversion: Conversion, size = 21) {
    return conversion.source === 'pptx' ? (
      <Presentation size={size} />
    ) : conversion.source === 'pdf' ? (
      <Layers size={size} />
    ) : (
      <FileText size={size} />
    );
  }

  return (
    <>
      <header className="site-header">
        <div className="header-inner">
          <a className="brand" href="#" aria-label="Straight home">
            <span className="brand-mark">
              <ArrowLeftRight size={21} strokeWidth={2.2} />
            </span>
            straight<span className="brand-period">.</span>
          </a>
          <a className="header-link" href="#how-it-works">
            How it works <ArrowRight size={15} aria-hidden="true" />
          </a>
        </div>
      </header>
      <main>
        <section className="hero" aria-labelledby="page-title">
          <div className="eyebrow">
            <span />
            LESS FRICTION. MORE DONE.
          </div>
          <h1>
            New format.
            <br className="mobile-break" /> Same great work.
          </h1>
          <p>
            Your documents, in the format you need.
            <br />
            Simple conversions. No account. No extra steps.
          </p>
        </section>
        <div className="workspace">
          <aside className="conversion-sidebar" aria-label="Conversion types">
            <div className="section-eyebrow">CHOOSE A CONVERSION</div>
            <div className="conversion-options">
              {capabilities?.conversions.map((conversion, index) => (
                <button
                  key={`${conversion.source}-${conversion.target}`}
                  className={`conversion-option ${selectedIndex === index ? 'is-selected' : ''}`}
                  aria-pressed={selectedIndex === index}
                  disabled={busy}
                  onClick={() => selectConversion(index)}
                >
                  <span className={`option-icon ${conversion.source}`}>
                    {converterIcon(conversion)}
                  </span>
                  <span>
                    <strong>{conversion.label}</strong>
                    <small>
                      {conversion.source.toUpperCase()} <ArrowRight size={11} aria-hidden="true" />{' '}
                      {conversion.target.toUpperCase()}
                    </small>
                  </span>
                  {selectedIndex === index && (
                    <span className="selection-check">
                      <Check size={13} />
                    </span>
                  )}
                </button>
              ))}
              {!capabilities && (
                <div className="sidebar-placeholder">
                  Your conversion tools
                  <br />
                  will appear here.
                </div>
              )}
            </div>
            <div className="sidebar-note">
              <ShieldCheck size={19} aria-hidden="true" />
              <p>
                A little privacy, by default.
                <br />
                <span>Files are processed temporarily and removed after delivery.</span>
              </p>
            </div>
          </aside>

          <section className="converter-card" aria-labelledby="converter-title" aria-busy={busy}>
            <div className="card-heading">
              <div>
                <div className="section-eyebrow">THE SIMPLE FILE CONVERTER</div>
                <h2 id="converter-title">{selected?.label ?? 'Let’s get your file ready.'}</h2>
                <p>{selected?.description ?? 'Connecting to your conversion tools…'}</p>
              </div>
              <span className="step-badge">{state.phase === 'ready' ? 'DONE' : '01 — 03'}</span>
            </div>
            {loadingError ? (
              <div className="connection-error">
                <Info size={24} />
                <h3>Couldn’t reach the converter</h3>
                <p>{loadingError}</p>
                <button
                  className="button button-secondary"
                  onClick={() => setReload((value) => value + 1)}
                >
                  <RefreshCw size={16} />
                  Try again
                </button>
              </div>
            ) : !capabilities || !selected ? (
              <div className="loading-panel" role="status">
                <RefreshCw size={22} className="spinner" />
                Loading conversion tools…
              </div>
            ) : state.phase === 'ready' ? (
              <ConversionStatus state={state} onReset={clearFile} />
            ) : (
              <>
                <FileDropzone
                  file={file}
                  disabled={busy}
                  maxSize={capabilities.max_upload_bytes}
                  onSelect={selectFiles}
                  onRemove={clearFile}
                />
                {fileError && (
                  <p className="inline-error" role="alert">
                    {fileError}
                  </p>
                )}
                <FormatSelect
                  source={file ? extension(file.name) : undefined}
                  selected={selected}
                  conversions={capabilities.conversions}
                  disabled={busy}
                  onChange={(target) => {
                    const index = capabilities.conversions.findIndex(
                      (item) => item.source === selected.source && item.target === target,
                    );
                    if (index >= 0) selectConversion(index);
                  }}
                />
                <div className="conversion-note">
                  <Info size={16} aria-hidden="true" />
                  <p>
                    {selected.note}
                    {selected.source === 'pdf' && ` Up to ${capabilities.max_pdf_pages} pages.`}
                  </p>
                </div>
                {!selected.available && (
                  <div className="unavailable-note" role="status">
                    This conversion is temporarily unavailable. PDF to PowerPoint is still
                    available.
                  </div>
                )}
                <ConversionStatus state={state} onReset={clearFile} />
                <button
                  className="button button-primary convert-button"
                  disabled={!file || busy || !selected.available}
                  onClick={() => {
                    if (file) void start(file, selected, capabilities.timeout_seconds);
                  }}
                >
                  {busy ? (
                    <>
                      <RefreshCw size={18} className="spinner" />
                      Working on your file…
                    </>
                  ) : (
                    <>
                      {state.phase === 'error'
                        ? 'Try conversion again'
                        : `Convert to ${selected.target.toUpperCase()}`}
                      <ArrowRight size={18} />
                    </>
                  )}
                </button>
                <div className="card-footer">
                  <LockKeyhole size={13} aria-hidden="true" />
                  <span>No sign-up. No stored file history.</span>
                </div>
              </>
            )}
          </section>
        </div>
        <section className="how-it-works" id="how-it-works" aria-labelledby="how-title">
          <div className="how-heading">
            <h2 id="how-title">Three steps. That’s it.</h2>
            <p>From the file you have to the file you need.</p>
          </div>
          <div className="steps">
            <div className="step">
              <span className="step-number">01</span>
              <div>
                <h3>Choose your file</h3>
                <p>Drop a document or browse your device.</p>
              </div>
            </div>
            <ArrowRight className="step-arrow" size={18} aria-hidden="true" />
            <div className="step">
              <span className="step-number">02</span>
              <div>
                <h3>Make the switch</h3>
                <p>Choose your format and let us handle it.</p>
              </div>
            </div>
            <ArrowRight className="step-arrow" size={18} aria-hidden="true" />
            <div className="step">
              <span className="step-number">03</span>
              <div>
                <h3>Take it with you</h3>
                <p>Download your file. Get back to your day.</p>
              </div>
            </div>
          </div>
        </section>
        <div className="trust-line">
          <span>
            <ShieldCheck size={16} />
            Temporary processing
          </span>
          <span>
            <Zap size={16} />
            No account needed
          </span>
          <span>
            <ArrowDown size={16} />
            Direct downloads
          </span>
        </div>
      </main>
      <footer className="site-footer">
        <span>
          straight<span className="brand-period">.</span>{' '}
          <span className="footer-tagline">A simpler way to convert.</span>
        </span>
        <span>Made for your everyday files.</span>
      </footer>
    </>
  );
}
