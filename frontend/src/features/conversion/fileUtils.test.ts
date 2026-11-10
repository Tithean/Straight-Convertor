import { describe, expect, it } from 'vitest';
import { extension, outputFilename, validateSelection } from './fileUtils';
import type { Capabilities } from './types';

const capabilities: Capabilities = {
  max_upload_bytes: 1000,
  max_pdf_pages: 100,
  timeout_seconds: 120,
  conversions: [
    { source: 'pdf', target: 'pptx', label: '', description: '', note: '', available: true },
  ],
};

describe('file selection', () => {
  it('accepts uppercase file extensions', () => {
    expect(extension('Quarterly.Report.PDF')).toBe('pdf');
    expect(validateSelection(new File(['test'], 'Report.PDF'), capabilities)).toBeNull();
  });
  it('rejects empty and oversized files before uploading', () => {
    expect(validateSelection(new File([], 'empty.pdf'), capabilities)).toContain('empty');
    expect(validateSelection(new File(['x'.repeat(1001)], 'large.pdf'), capabilities)).toContain(
      'too large',
    );
  });
  it('rejects unsupported formats and preserves dots in download names', () => {
    expect(validateSelection(new File(['text'], 'file.txt'), capabilities)).toContain(
      'Please choose',
    );
    expect(outputFilename('Report.final.PDF', capabilities.conversions[0])).toBe(
      'Report.final.pptx',
    );
  });
});
