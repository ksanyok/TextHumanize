<?php

declare(strict_types=1);

namespace TextHumanize\Tests;

use PHPUnit\Framework\TestCase;
use TextHumanize\WatermarkDetector;
use TextHumanize\WatermarkReport;

class WatermarkDetectorTest extends TestCase
{
    // ==================== WatermarkReport ====================

    public function testReportDefaults(): void
    {
        $report = new WatermarkReport();
        $this->assertFalse($report->hasWatermarks);
        $this->assertIsArray($report->watermarkTypes);
        $this->assertIsArray($report->details);
        $this->assertSame('', $report->cleanedText);
        $this->assertSame(0, $report->charactersRemoved);
        $this->assertIsArray($report->homoglyphsFound);
        $this->assertSame(0, $report->zeroWidthCount);
        $this->assertSame(0.0, $report->confidence);
    }

    // ==================== WatermarkDetector Instance ====================

    public function testDetectCleanText(): void
    {
        $detector = new WatermarkDetector('en');
        $text = 'This is a perfectly normal text without any watermarks or hidden characters.';
        $report = $detector->detect($text);

        $this->assertInstanceOf(WatermarkReport::class, $report);
        $this->assertFalse($report->hasWatermarks);
        $this->assertSame(0, $report->zeroWidthCount);
    }

    public function testDetectZeroWidthChars(): void
    {
        $detector = new WatermarkDetector('en');
        // Insert zero-width space (U+200B) and zero-width non-joiner (U+200C)
        $text = "This is a test\u{200B} with zero\u{200C}-width chars.";
        $report = $detector->detect($text);

        $this->assertInstanceOf(WatermarkReport::class, $report);
        $this->assertTrue($report->hasWatermarks);
        $this->assertGreaterThan(0, $report->zeroWidthCount);
    }

    public function testDetectHomoglyphs(): void
    {
        $detector = new WatermarkDetector('en');
        // Replace 'a' with Cyrillic 'а' (U+0430) — a homoglyph
        $text = "This is \u{0430} test with homoglyph characters mixed in.";
        $report = $detector->detect($text);

        $this->assertInstanceOf(WatermarkReport::class, $report);
    }

    public function testDetectEmptyText(): void
    {
        $detector = new WatermarkDetector('en');
        $report = $detector->detect('');
        $this->assertInstanceOf(WatermarkReport::class, $report);
    }

    // ==================== Clean ====================

    public function testCleanRemovesZeroWidth(): void
    {
        $detector = new WatermarkDetector('en');
        $text = "Hello\u{200B} world\u{200C} test\u{200D}!";
        $cleaned = $detector->clean($text);

        $this->assertIsString($cleaned);
        $this->assertStringNotContainsString("\u{200B}", $cleaned);
        $this->assertStringNotContainsString("\u{200C}", $cleaned);
    }

    public function testCleanPlainTextUnchanged(): void
    {
        $detector = new WatermarkDetector('en');
        $text = 'This is perfectly clean text with no watermarks.';
        $cleaned = $detector->clean($text);
        $this->assertSame($text, $cleaned);
    }

    public function testCleanEmptyText(): void
    {
        $detector = new WatermarkDetector('en');
        $cleaned = $detector->clean('');
        $this->assertSame('', $cleaned);
    }

    // ==================== Static Methods ====================

    public function testDetectWatermarksStatic(): void
    {
        $text = "Test\u{200B} text with hidden chars.";
        $report = WatermarkDetector::detectWatermarks($text, 'en');
        $this->assertInstanceOf(WatermarkReport::class, $report);
    }

    public function testCleanWatermarksStatic(): void
    {
        $text = "Clean\u{200B} this up.";
        $cleaned = WatermarkDetector::cleanWatermarks($text, 'en');
        $this->assertIsString($cleaned);
        $this->assertStringNotContainsString("\u{200B}", $cleaned);
    }

    public function testDetectWatermarksStaticCleanText(): void
    {
        $text = 'Normal text without any watermarks at all.';
        $report = WatermarkDetector::detectWatermarks($text, 'en');
        $this->assertFalse($report->hasWatermarks);
    }

    // ==================== Report Fields ====================

    public function testReportCharactersRemoved(): void
    {
        $detector = new WatermarkDetector('en');
        $text = "AB\u{200B}CD\u{200B}EF";
        $report = $detector->detect($text);

        if ($report->hasWatermarks) {
            $this->assertGreaterThan(0, $report->charactersRemoved);
            $this->assertNotEmpty($report->cleanedText);
        }
    }

    public function testReportConfidenceRange(): void
    {
        $detector = new WatermarkDetector('en');
        $text = "Watermarked\u{200B}\u{200C}\u{200D}\u{FEFF} text.";
        $report = $detector->detect($text);

        $this->assertGreaterThanOrEqual(0.0, $report->confidence);
        $this->assertLessThanOrEqual(1.0, $report->confidence);
    }

    // ==================== Multi-language ====================

    public function testDetectRussianText(): void
    {
        $detector = new WatermarkDetector('ru');
        $text = "Тестовый\u{200B} текст с водяными знаками.";
        $report = $detector->detect($text);
        $this->assertInstanceOf(WatermarkReport::class, $report);
    }

    public function testCleanRussianText(): void
    {
        $detector = new WatermarkDetector('ru');
        $text = "Чистый\u{200B} текст.";
        $cleaned = $detector->clean($text);
        $this->assertStringNotContainsString("\u{200B}", $cleaned);
    }
}
