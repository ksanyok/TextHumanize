<?php

declare(strict_types=1);

namespace TextHumanize\Tests;

use PHPUnit\Framework\TestCase;
use TextHumanize\ToneAnalyzer;
use TextHumanize\ToneLevel;
use TextHumanize\ToneReport;

class ToneAnalyzerTest extends TestCase
{
    // ==================== ToneLevel Enum ====================

    public function testToneLevelValues(): void
    {
        $this->assertSame('formal', ToneLevel::FORMAL->value);
        $this->assertSame('academic', ToneLevel::ACADEMIC->value);
        $this->assertSame('professional', ToneLevel::PROFESSIONAL->value);
        $this->assertSame('neutral', ToneLevel::NEUTRAL->value);
        $this->assertSame('friendly', ToneLevel::FRIENDLY->value);
        $this->assertSame('casual', ToneLevel::CASUAL->value);
        $this->assertSame('marketing', ToneLevel::MARKETING->value);
    }

    public function testToneLevelFromString(): void
    {
        $level = ToneLevel::from('formal');
        $this->assertSame(ToneLevel::FORMAL, $level);
    }

    public function testToneLevelTryFromInvalid(): void
    {
        $level = ToneLevel::tryFrom('invalid');
        $this->assertNull($level);
    }

    // ==================== ToneReport ====================

    public function testReportDefaults(): void
    {
        $report = new ToneReport();
        $this->assertSame(ToneLevel::NEUTRAL, $report->primaryTone);
        $this->assertIsArray($report->scores);
        $this->assertSame(0.5, $report->formality);
        $this->assertSame(0.5, $report->subjectivity);
        $this->assertSame(0.0, $report->confidence);
        $this->assertIsArray($report->markers);
    }

    public function testReportToArray(): void
    {
        $report = new ToneReport(
            primaryTone: ToneLevel::FORMAL,
            scores: ['formal' => 0.8, 'casual' => 0.1],
            formality: 0.9,
            subjectivity: 0.2,
            confidence: 0.85,
            markers: ['formal' => ['furthermore', 'moreover']],
        );
        $arr = $report->toArray();

        $this->assertIsArray($arr);
        $this->assertArrayHasKey('primary_tone', $arr);
        $this->assertArrayHasKey('scores', $arr);
        $this->assertArrayHasKey('formality', $arr);
        $this->assertArrayHasKey('subjectivity', $arr);
        $this->assertArrayHasKey('confidence', $arr);
        $this->assertArrayHasKey('markers', $arr);
    }

    public function testReportToArrayPrimaryToneValue(): void
    {
        $report = new ToneReport(primaryTone: ToneLevel::CASUAL);
        $arr = $report->toArray();
        $this->assertSame('casual', $arr['primary_tone']);
    }

    // ==================== ToneAnalyzer Instance ====================

    public function testAnalyzeFormalText(): void
    {
        $analyzer = new ToneAnalyzer('en');
        $text = 'Furthermore, it is of paramount importance to acknowledge that the aforementioned implementation shall ensure compliance with all stipulated requirements. Henceforth, the utilization of this methodology shall be mandatory.';
        $report = $analyzer->analyze($text);

        $this->assertInstanceOf(ToneReport::class, $report);
        $this->assertIsFloat($report->formality);
        $this->assertGreaterThanOrEqual(0.0, $report->formality);
        $this->assertLessThanOrEqual(1.0, $report->formality);
    }

    public function testAnalyzeCasualText(): void
    {
        $analyzer = new ToneAnalyzer('en');
        $text = "Hey, so basically I think it's pretty cool stuff, you know? Like, it totally works and stuff. Awesome!";
        $report = $analyzer->analyze($text);

        $this->assertInstanceOf(ToneReport::class, $report);
    }

    public function testAnalyzeEmptyText(): void
    {
        $analyzer = new ToneAnalyzer('en');
        $report = $analyzer->analyze('');
        $this->assertInstanceOf(ToneReport::class, $report);
    }

    public function testAnalyzeRussian(): void
    {
        $analyzer = new ToneAnalyzer('ru');
        $text = 'Значительная часть проведённого анализа свидетельствует о необходимости осуществления дальнейших исследований в данной области.';
        $report = $analyzer->analyze($text);
        $this->assertInstanceOf(ToneReport::class, $report);
    }

    // ==================== Adjust Tone ====================

    public function testAdjustToCasual(): void
    {
        $analyzer = new ToneAnalyzer('en');
        $text = 'It is important to note that the implementation provides comprehensive coverage. Furthermore, the solution ensures effective performance.';
        $adjusted = $analyzer->adjust($text, ToneLevel::CASUAL, 0.7, 42);

        $this->assertIsString($adjusted);
        $this->assertNotEmpty($adjusted);
    }

    public function testAdjustToFormal(): void
    {
        $analyzer = new ToneAnalyzer('en');
        $text = "So basically this thing works pretty well I think. It's cool.";
        $adjusted = $analyzer->adjust($text, ToneLevel::FORMAL, 0.5, 42);
        $this->assertIsString($adjusted);
        $this->assertNotEmpty($adjusted);
    }

    public function testAdjustToNeutral(): void
    {
        $analyzer = new ToneAnalyzer('en');
        $text = 'Furthermore, the comprehensive methodology demonstrates significant potential for advancement.';
        $adjusted = $analyzer->adjust($text, ToneLevel::NEUTRAL, 0.5, 42);
        $this->assertIsString($adjusted);
    }

    public function testAdjustDeterministic(): void
    {
        $analyzer = new ToneAnalyzer('en');
        $text = 'It is important to note that the implementation provides comprehensive coverage.';
        $r1 = $analyzer->adjust($text, ToneLevel::CASUAL, 0.5, 42);
        $r2 = $analyzer->adjust($text, ToneLevel::CASUAL, 0.5, 42);
        $this->assertSame($r1, $r2);
    }

    public function testAdjustEmptyText(): void
    {
        $analyzer = new ToneAnalyzer('en');
        $result = $analyzer->adjust('', ToneLevel::CASUAL);
        $this->assertSame('', $result);
    }

    public function testAdjustIntensityZero(): void
    {
        $analyzer = new ToneAnalyzer('en');
        $text = 'Test sentence for intensity zero.';
        $result = $analyzer->adjust($text, ToneLevel::CASUAL, 0.0);
        $this->assertNotEmpty($result);
    }

    public function testAdjustIntensityFull(): void
    {
        $analyzer = new ToneAnalyzer('en');
        $text = 'It is important to note that the implementation provides comprehensive coverage.';
        $result = $analyzer->adjust($text, ToneLevel::CASUAL, 1.0, 42);
        $this->assertNotEmpty($result);
    }

    // ==================== Static Methods ====================

    public function testAnalyzeToneStatic(): void
    {
        $text = 'Furthermore, the implementation ensures comprehensive coverage of all requirements.';
        $report = ToneAnalyzer::analyzeTone($text, 'en');
        $this->assertInstanceOf(ToneReport::class, $report);
    }

    public function testAdjustToneStatic(): void
    {
        $text = 'Furthermore, the comprehensive solution provides robust performance.';
        $adjusted = ToneAnalyzer::adjustTone($text, 'casual', 'en', 0.5);
        $this->assertIsString($adjusted);
        $this->assertNotEmpty($adjusted);
    }

    public function testAdjustToneStaticFormal(): void
    {
        $text = "So this thing works well, you know.";
        $adjusted = ToneAnalyzer::adjustTone($text, 'formal', 'en', 0.5);
        $this->assertIsString($adjusted);
    }

    // ==================== Scores ====================

    public function testScoresContainToneLevels(): void
    {
        $analyzer = new ToneAnalyzer('en');
        $text = 'The implementation of this system ensures comprehensive coverage of all requirements. It provides a robust framework for development.';
        $report = $analyzer->analyze($text);

        if (!empty($report->scores)) {
            foreach ($report->scores as $tone => $score) {
                $this->assertIsString($tone);
                $this->assertIsNumeric($score);
                $this->assertGreaterThanOrEqual(0.0, (float) $score);
                $this->assertLessThanOrEqual(1.0, (float) $score);
            }
        }
    }

    public function testMarkersAreStringArrays(): void
    {
        $analyzer = new ToneAnalyzer('en');
        $text = 'Furthermore, the implementation ensures comprehensive coverage. Moreover, it provides robust performance. Additionally, it demonstrates scalability.';
        $report = $analyzer->analyze($text);

        foreach ($report->markers as $category => $words) {
            $this->assertIsString($category);
            $this->assertIsArray($words);
        }
    }
}
