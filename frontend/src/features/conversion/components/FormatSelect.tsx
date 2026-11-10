import { ArrowRight, ChevronDown } from 'lucide-react';
import type { Conversion, Format } from '../types';

interface Props {
  source?: string;
  selected: Conversion;
  conversions: Conversion[];
  disabled: boolean;
  onChange: (target: Format) => void;
}

export default function FormatSelect({ source, selected, conversions, disabled, onChange }: Props) {
  const options = conversions.filter((item) => item.source === (source || selected.source));
  return (
    <div className="format-row">
      <div className="format-field">
        <span className="field-label">Original format</span>
        <div className="format-value">
          <span className={`format-dot ${source || selected.source}`} />
          {(source || selected.source).toUpperCase()}
          <span className="auto-label">{source ? 'Detected' : 'Input'}</span>
        </div>
      </div>
      <ArrowRight className="format-arrow" size={19} aria-hidden="true" />
      <div className="format-field">
        <label className="field-label" htmlFor="output-format">
          Convert to
        </label>
        <div className="select-wrapper">
          <select
            id="output-format"
            value={selected.target}
            disabled={disabled}
            onChange={(event) => onChange(event.target.value as Format)}
          >
            {options.map((item) => (
              <option key={item.target} value={item.target}>
                {item.target === 'pdf' ? 'PDF document (.pdf)' : 'PowerPoint (.pptx)'}
              </option>
            ))}
          </select>
          <ChevronDown size={17} aria-hidden="true" />
        </div>
      </div>
    </div>
  );
}
