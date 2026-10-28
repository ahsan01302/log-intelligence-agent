import { validateFile } from '../../core/upload-store';

describe('validateFile (mirrors backend upload rules)', () => {
  const ok = (name: string, size = 10) => validateFile({ name, size }, 20);

  it('accepts .log and .txt files with safe names', () => {
    expect(ok('app.log')).toBeNull();
    expect(ok('Server_2026-01-01.TXT')).toBeNull();
  });

  it('rejects other file types', () => {
    expect(ok('report.pdf')).toMatch(/\.log and \.txt/);
    expect(ok('noextension')).toMatch(/\.log and \.txt/);
  });

  it('rejects names the backend would refuse', () => {
    expect(ok('my app.log')).toMatch(/Rename/);
    expect(ok('.hidden.log')).toMatch(/Rename/);
  });

  it('rejects empty and oversized files', () => {
    expect(ok('a.log', 0)).toMatch(/empty/);
    expect(ok('a.log', 20 * 1024 * 1024 + 1)).toMatch(/larger than 20 MB/);
  });
});
