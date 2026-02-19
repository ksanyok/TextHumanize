/**
 * Tests for the full processing stages.
 */

import { describe, it, expect } from 'vitest';
import { TypographyNormalizer } from '../src/normalizer';
import { Debureaucratizer } from '../src/debureaucratizer';
import { TextNaturalizer } from '../src/naturalizer';

describe('TypographyNormalizer', () => {
  it('should remove double spaces', () => {
    const norm = new TypographyNormalizer('web', 'en');
    const result = norm.normalize('Hello  world.  Test.');
    expect(result).not.toContain('  ');
  });

  it('should normalize dashes', () => {
    const norm = new TypographyNormalizer('web', 'en');
    const result = norm.normalize('Hello -- world.');
    expect(result).toContain('—');
  });

  it('should normalize ellipsis', () => {
    const norm = new TypographyNormalizer('web', 'en');
    const result = norm.normalize('Wait...');
    expect(result).toContain('…');
  });

  it('should track changes', () => {
    const norm = new TypographyNormalizer('web', 'en');
    norm.normalize('Hello  world...');
    expect(norm.changes.length).toBeGreaterThan(0);
  });

  it('should normalize RU quotes', () => {
    const norm = new TypographyNormalizer('web', 'ru');
    const result = norm.normalize('Он сказал "привет" ей.');
    expect(result).toContain('«');
    expect(result).toContain('»');
  });
});

describe('Debureaucratizer', () => {
  it('should replace bureaucratic EN words', () => {
    const decancel = new Debureaucratizer('en', 'web', 100, 42);
    const result = decancel.process(
      'We need to utilize advanced methodologies to facilitate the implementation.',
    );
    // At least one word should be replaced
    expect(decancel.changes.length).toBeGreaterThan(0);
  });

  it('should replace bureaucratic RU words', () => {
    const decancel = new Debureaucratizer('ru', 'web', 100, 42);
    const result = decancel.process(
      'Необходимо осуществлять данный процесс.',
    );
    expect(decancel.changes.length).toBeGreaterThan(0);
  });

  it('should respect change budget', () => {
    const decancel = new Debureaucratizer('en', 'web', 100, 42);
    // Short text — small budget
    const result = decancel.process('Utilize this.');
    // Budget = max(2, floor(2 * 0.15)) = 2
    expect(decancel.changes.length).toBeLessThanOrEqual(2);
  });

  it('should handle unknown language gracefully', () => {
    const decancel = new Debureaucratizer('ja', 'web', 60, 42);
    const text = 'テスト文です。';
    const result = decancel.process(text);
    expect(result).toBe(text); // No changes
  });
});

describe('TextNaturalizer', () => {
  it('should replace AI-characteristic words in EN', () => {
    const nat = new TextNaturalizer('en', 'web', 100, 42);
    const text = 'The comprehensive analysis demonstrates significant improvements in our robust methodology. Furthermore, the implementation leverages innovative paradigms.';
    const result = nat.process(text);
    expect(nat.changes.length).toBeGreaterThan(0);
  });

  it('should handle short text without crash', () => {
    const nat = new TextNaturalizer('en', 'web', 60, 42);
    const result = nat.process('Hello world.');
    expect(result).toBeTruthy();
  });

  it('should be deterministic with same seed', () => {
    const text = 'The comprehensive methodology facilitates significant optimization.';
    const nat1 = new TextNaturalizer('en', 'web', 80, 42);
    const result1 = nat1.process(text);
    const nat2 = new TextNaturalizer('en', 'web', 80, 42);
    const result2 = nat2.process(text);
    expect(result1).toBe(result2);
  });
});
