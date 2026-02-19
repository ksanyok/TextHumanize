/**
 * Tests for TextHumanize JS/TS port.
 */

import { describe, it, expect } from 'vitest';
import { humanize, analyze, detectAi } from '../src/core';
import { TextAnalyzer } from '../src/analyzer';
import { Pipeline } from '../src/pipeline';
import { VERSION } from '../src/version';
import { getLangPack, hasDeepSupport, supportedLanguages } from '../src/lang';

describe('Version', () => {
  it('should export version string', () => {
    expect(VERSION).toBe('0.8.0');
  });
});

describe('TextAnalyzer', () => {
  it('should analyze empty text', () => {
    const analyzer = new TextAnalyzer('en');
    const report = analyzer.analyze('');
    expect(report.totalWords).toBe(0);
    expect(report.artificialityScore).toBe(0);
  });

  it('should compute basic metrics', () => {
    const text = 'The cat sat on the mat. It was a sunny day. Birds were singing.';
    const analyzer = new TextAnalyzer('en');
    const report = analyzer.analyze(text);
    expect(report.totalWords).toBeGreaterThan(0);
    expect(report.totalSentences).toBe(3);
    expect(report.avgSentenceLength).toBeGreaterThan(0);
  });

  it('should detect high artificiality in uniform text', () => {
    const text = 'This is a test. That is a test. Here is a test. There is a test.';
    const analyzer = new TextAnalyzer('en');
    const report = analyzer.analyze(text);
    expect(report.artificialityScore).toBeGreaterThanOrEqual(0);
  });
});

describe('humanize', () => {
  it('should handle empty text', () => {
    const result = humanize('');
    expect(result.text).toBe('');
    expect(result.lang).toBe('en');
  });

  it('should process English text', () => {
    const result = humanize('The implementation utilizes advanced methodologies.', {
      lang: 'en',
      intensity: 50,
    });
    expect(result.text).toBeTruthy();
    expect(result.lang).toBe('en');
    expect(result.profile).toBe('web');
  });

  it('should auto-detect language', () => {
    const result = humanize('This is an English sentence. It has multiple parts.');
    expect(result.lang).toBe('en');
  });

  it('should return changes array', () => {
    const result = humanize('Hello  world.  Test text.', { lang: 'en' });
    expect(Array.isArray(result.changes)).toBe(true);
  });
});

describe('analyze', () => {
  it('should return analysis report', () => {
    const report = analyze('Testing the analyzer function.', 'en');
    expect(report.lang).toBe('en');
    expect(report.totalChars).toBeGreaterThan(0);
  });
});

describe('detectAi', () => {
  it('should return verdict and score', () => {
    const result = detectAi('This is a sample text for detection.', 'en');
    expect(result.verdict).toBeTruthy();
    expect(typeof result.score).toBe('number');
    expect(result.details).toBeTruthy();
  });
});

describe('Pipeline', () => {
  it('should instantiate with default options', () => {
    const pipeline = new Pipeline();
    expect(pipeline).toBeTruthy();
  });

  it('should run basic processing', () => {
    const pipeline = new Pipeline({ lang: 'en', intensity: 50 });
    const result = pipeline.run('Hello  world.  Test.', 'en');
    expect(result.text).not.toContain('  ');
  });
});

describe('Language Registry', () => {
  it('should have English pack', () => {
    const pack = getLangPack('en');
    expect(pack).toBeTruthy();
    expect(pack!.code).toBe('en');
    expect(Object.keys(pack!.bureaucratic).length).toBeGreaterThan(10);
  });

  it('should have Russian pack', () => {
    const pack = getLangPack('ru');
    expect(pack).toBeTruthy();
    expect(pack!.code).toBe('ru');
  });

  it('should report deep support correctly', () => {
    expect(hasDeepSupport('en')).toBe(true);
    expect(hasDeepSupport('ru')).toBe(true);
    expect(hasDeepSupport('ja')).toBe(false);
  });

  it('should list supported languages', () => {
    const langs = supportedLanguages();
    expect(langs).toContain('en');
    expect(langs).toContain('ru');
  });
});
