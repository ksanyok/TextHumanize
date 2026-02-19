<?php

declare(strict_types=1);

namespace TextHumanize\Tests;

use PHPUnit\Framework\TestCase;
use TextHumanize\Paraphraser;
use TextHumanize\ParaphraseResult;

class ParaphraserTest extends TestCase
{
    // ==================== ParaphraseResult ====================

    public function testResultProperties(): void
    {
        $result = new ParaphraseResult(
            original: 'Hello world',
            paraphrased: 'Hi planet',
            changes: ['synonym replacement'],
            confidence: 0.8,
        );
        $this->assertSame('Hello world', $result->original);
        $this->assertSame('Hi planet', $result->paraphrased);
        $this->assertCount(1, $result->changes);
        $this->assertSame(0.8, $result->confidence);
    }

    // ==================== Paraphraser Instance ====================

    public function testParaphraseEnglish(): void
    {
        $paraphraser = new Paraphraser('en', seed: 42);
        $text = 'The comprehensive implementation provides robust coverage of all requirements. Furthermore, it ensures effective performance throughout the system.';
        $result = $paraphraser->paraphrase($text);

        $this->assertInstanceOf(ParaphraseResult::class, $result);
        $this->assertSame($text, $result->original);
        $this->assertNotEmpty($result->paraphrased);
        $this->assertIsArray($result->changes);
        $this->assertGreaterThanOrEqual(0.0, $result->confidence);
        $this->assertLessThanOrEqual(1.0, $result->confidence);
    }

    public function testParaphraseDeterministic(): void
    {
        $text = 'The comprehensive solution provides robust performance and effective coverage.';
        $p1 = new Paraphraser('en', seed: 42);
        $p2 = new Paraphraser('en', seed: 42);

        $r1 = $p1->paraphrase($text);
        $r2 = $p2->paraphrase($text);
        $this->assertSame($r1->paraphrased, $r2->paraphrased);
    }

    public function testParaphraseEmptyText(): void
    {
        $paraphraser = new Paraphraser('en');
        $result = $paraphraser->paraphrase('');
        $this->assertSame('', $result->original);
        $this->assertSame('', $result->paraphrased);
    }

    public function testParaphraseShortText(): void
    {
        $paraphraser = new Paraphraser('en', seed: 42);
        $result = $paraphraser->paraphrase('Hello.');
        $this->assertInstanceOf(ParaphraseResult::class, $result);
    }

    public function testParaphraseWithHighIntensity(): void
    {
        $paraphraser = new Paraphraser('en', seed: 42, intensity: 1.0);
        $text = 'The important solution provides comprehensive and robust coverage.';
        $result = $paraphraser->paraphrase($text);
        $this->assertNotEmpty($result->paraphrased);
    }

    public function testParaphraseWithLowIntensity(): void
    {
        $paraphraser = new Paraphraser('en', seed: 42, intensity: 0.1);
        $text = 'The solution provides comprehensive coverage.';
        $result = $paraphraser->paraphrase($text);
        $this->assertNotEmpty($result->paraphrased);
    }

    // ==================== Paraphrase Sentence ====================

    public function testParaphraseSentence(): void
    {
        $paraphraser = new Paraphraser('en', seed: 42);
        $sentence = 'The comprehensive solution provides robust performance.';
        [$paraphrased, $changeType] = $paraphraser->paraphraseSentence($sentence);

        $this->assertIsString($paraphrased);
        $this->assertIsString($changeType);
        $this->assertNotEmpty($paraphrased);
    }

    public function testParaphraseSentenceShort(): void
    {
        $paraphraser = new Paraphraser('en', seed: 42);
        [$paraphrased, $changeType] = $paraphraser->paraphraseSentence('Hello.');
        $this->assertIsString($paraphrased);
        $this->assertIsString($changeType);
    }

    // ==================== Static Method ====================

    public function testParaphraseTextStatic(): void
    {
        $text = 'The comprehensive solution provides robust performance. It ensures effective coverage.';
        $result = Paraphraser::paraphraseText($text, 'en', 0.5, 42);

        $this->assertIsString($result);
        $this->assertNotEmpty($result);
    }

    // ==================== Multi-language ====================

    public function testParaphraseRussian(): void
    {
        $paraphraser = new Paraphraser('ru', seed: 42);
        $text = 'Комплексное решение обеспечивает надёжную производительность системы.';
        $result = $paraphraser->paraphrase($text);
        $this->assertInstanceOf(ParaphraseResult::class, $result);
    }

    public function testParaphraseGerman(): void
    {
        $paraphraser = new Paraphraser('de', seed: 42);
        $text = 'Die umfassende Lösung bietet robuste Leistung und Zuverlässigkeit.';
        $result = $paraphraser->paraphrase($text);
        $this->assertInstanceOf(ParaphraseResult::class, $result);
    }

    // ==================== Changes Tracking ====================

    public function testChangesAreDescriptive(): void
    {
        $paraphraser = new Paraphraser('en', seed: 42, intensity: 0.8);
        $text = 'The important implementation provides comprehensive coverage of all requirements effectively.';
        $result = $paraphraser->paraphrase($text);

        foreach ($result->changes as $change) {
            $this->assertIsString($change);
        }
    }
}
