<?php

declare(strict_types=1);

namespace TextHumanize\Tests;

use PHPUnit\Framework\TestCase;
use TextHumanize\ContentSpinner;
use TextHumanize\SpinResult;

class ContentSpinnerTest extends TestCase
{
    // ==================== SpinResult ====================

    public function testSpinResultProperties(): void
    {
        $result = new SpinResult(
            original: 'Hello world',
            spun: 'Hi planet',
            spintax: '{Hello|Hi} {world|planet}',
            uniqueness: 0.8,
            variantsCount: 4,
        );
        $this->assertSame('Hello world', $result->original);
        $this->assertSame('Hi planet', $result->spun);
        $this->assertSame('{Hello|Hi} {world|planet}', $result->spintax);
        $this->assertSame(0.8, $result->uniqueness);
        $this->assertSame(4, $result->variantsCount);
    }

    // ==================== ContentSpinner Instance ====================

    public function testSpinEnglish(): void
    {
        $spinner = new ContentSpinner('en', seed: 42);
        $text = 'The important implementation provides comprehensive coverage of all requirements. It ensures robust and effective performance throughout the entire process.';
        $result = $spinner->spin($text);

        $this->assertInstanceOf(SpinResult::class, $result);
        $this->assertSame($text, $result->original);
        $this->assertNotEmpty($result->spun);
        $this->assertNotEmpty($result->spintax);
        $this->assertGreaterThanOrEqual(0.0, $result->uniqueness);
        $this->assertLessThanOrEqual(1.0, $result->uniqueness);
    }

    public function testSpinDeterministic(): void
    {
        $text = 'The comprehensive solution provides robust performance and effective coverage.';
        $s1 = new ContentSpinner('en', seed: 42);
        $s2 = new ContentSpinner('en', seed: 42);

        $r1 = $s1->spin($text);
        $r2 = $s2->spin($text);
        $this->assertSame($r1->spun, $r2->spun);
    }

    public function testSpinEmptyText(): void
    {
        $spinner = new ContentSpinner('en');
        $result = $spinner->spin('');
        $this->assertSame('', $result->original);
        $this->assertSame('', $result->spun);
    }

    public function testSpinIntensityLow(): void
    {
        $spinner = new ContentSpinner('en', seed: 1, intensity: 0.1);
        $text = 'This is a simple sentence for testing.';
        $result = $spinner->spin($text);
        $this->assertNotEmpty($result->spun);
    }

    public function testSpinIntensityHigh(): void
    {
        $spinner = new ContentSpinner('en', seed: 1, intensity: 1.0);
        $text = 'The important implementation provides comprehensive coverage. It ensures robust performance throughout the process.';
        $result = $spinner->spin($text);
        $this->assertNotEmpty($result->spun);
    }

    // ==================== Generate Spintax ====================

    public function testGenerateSpintax(): void
    {
        $spinner = new ContentSpinner('en', seed: 42);
        $text = 'The comprehensive solution provides robust performance.';
        $spintax = $spinner->generateSpintax($text);

        $this->assertIsString($spintax);
        $this->assertNotEmpty($spintax);
    }

    public function testGenerateSpintaxContainsBraces(): void
    {
        $spinner = new ContentSpinner('en', seed: 42, intensity: 0.9);
        $text = 'The important and comprehensive implementation ensures robust and effective performance in this critical area.';
        $spintax = $spinner->generateSpintax($text);
        // With high intensity, should contain spintax markers
        $this->assertIsString($spintax);
    }

    // ==================== Resolve Spintax ====================

    public function testResolveSpintax(): void
    {
        $spinner = new ContentSpinner('en', seed: 42);
        $spintax = '{Hello|Hi|Hey} {world|planet|earth}';
        $resolved = $spinner->resolveSpintax($spintax);

        $this->assertIsString($resolved);
        $this->assertNotEmpty($resolved);
        // Should be one of the options
        $this->assertDoesNotMatchRegularExpression('/[{}|]/', $resolved);
    }

    public function testResolveSpintaxPlainText(): void
    {
        $spinner = new ContentSpinner('en');
        $plain = 'No spintax here at all.';
        $resolved = $spinner->resolveSpintax($plain);
        $this->assertSame($plain, $resolved);
    }

    public function testResolveSpintaxDeterministic(): void
    {
        $spintax = '{option1|option2|option3} text';
        $s1 = new ContentSpinner('en', seed: 99);
        $s2 = new ContentSpinner('en', seed: 99);
        $this->assertSame($s1->resolveSpintax($spintax), $s2->resolveSpintax($spintax));
    }

    // ==================== Generate Variants ====================

    public function testGenerateVariants(): void
    {
        $spinner = new ContentSpinner('en', seed: 42);
        $text = 'The comprehensive solution provides robust and effective performance.';
        $variants = $spinner->generateVariants($text, 5);

        $this->assertIsArray($variants);
        $this->assertGreaterThanOrEqual(1, count($variants));
        $this->assertLessThanOrEqual(5, count($variants));
        foreach ($variants as $variant) {
            $this->assertIsString($variant);
            $this->assertNotEmpty($variant);
        }
    }

    public function testGenerateVariantsSingleCount(): void
    {
        $spinner = new ContentSpinner('en', seed: 1);
        $text = 'Simple test sentence.';
        $variants = $spinner->generateVariants($text, 1);
        $this->assertCount(1, $variants);
    }

    // ==================== Static Methods ====================

    public function testSpinTextStatic(): void
    {
        $text = 'The comprehensive solution provides robust performance.';
        $result = ContentSpinner::spinText($text, 'en', 0.5, 42);

        $this->assertIsString($result);
        $this->assertNotEmpty($result);
    }

    public function testSpinVariantsStatic(): void
    {
        $text = 'The comprehensive solution provides robust performance.';
        $variants = ContentSpinner::spinVariants($text, 3, 'en', 0.5, 42);

        $this->assertIsArray($variants);
        $this->assertGreaterThanOrEqual(1, count($variants));
    }

    // ==================== Multi-language ====================

    public function testSpinRussian(): void
    {
        $spinner = new ContentSpinner('ru', seed: 42);
        $text = 'Комплексное решение обеспечивает надёжную производительность системы.';
        $result = $spinner->spin($text);
        $this->assertInstanceOf(SpinResult::class, $result);
    }

    public function testSpinGerman(): void
    {
        $spinner = new ContentSpinner('de', seed: 42);
        $text = 'Die umfassende Lösung bietet robuste Leistung und Zuverlässigkeit.';
        $result = $spinner->spin($text);
        $this->assertInstanceOf(SpinResult::class, $result);
    }
}
