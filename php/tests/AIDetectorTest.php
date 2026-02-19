<?php

declare(strict_types=1);

namespace TextHumanize\Tests;

use PHPUnit\Framework\TestCase;
use TextHumanize\AIDetector;
use TextHumanize\DetectionResult;

class AIDetectorTest extends TestCase
{
    // ==================== DetectionResult ====================

    public function testDetectionResultDefaults(): void
    {
        $result = new DetectionResult();
        $this->assertSame(0.0, $result->aiProbability);
        $this->assertSame(0.0, $result->confidence);
        $this->assertSame('unknown', $result->verdict);
        $this->assertIsArray($result->details);
        $this->assertIsArray($result->explanations);
    }

    public function testHumanProbability(): void
    {
        $result = new DetectionResult();
        $result->aiProbability = 0.7;
        $this->assertEqualsWithDelta(0.3, $result->humanProbability(), 0.001);
    }

    public function testHumanProbabilityZero(): void
    {
        $result = new DetectionResult();
        $result->aiProbability = 0.0;
        $this->assertEqualsWithDelta(1.0, $result->humanProbability(), 0.001);
    }

    public function testHumanProbabilityFull(): void
    {
        $result = new DetectionResult();
        $result->aiProbability = 1.0;
        $this->assertEqualsWithDelta(0.0, $result->humanProbability(), 0.001);
    }

    public function testSummaryContainsVerdict(): void
    {
        $result = new DetectionResult();
        $result->verdict = 'likely_ai';
        $result->aiProbability = 0.85;
        $result->confidence = 0.9;
        $summary = $result->summary();
        $this->assertIsString($summary);
        $this->assertStringContainsString('likely_ai', $summary);
    }

    public function testSummaryContainsScores(): void
    {
        $result = new DetectionResult();
        $result->entropyScore = 0.5;
        $result->burstinessScore = 0.3;
        $result->vocabularyScore = 0.6;
        $summary = $result->summary();
        $this->assertIsString($summary);
        $this->assertNotEmpty($summary);
    }

    // ==================== AIDetector Instance ====================

    public function testDetectEnglishAiText(): void
    {
        $detector = new AIDetector('en');
        $text = 'Furthermore, it is important to note that the implementation of this system ensures comprehensive coverage of all requirements. Moreover, the solution provides a robust framework for addressing these challenges effectively. Additionally, the approach demonstrates significant potential for scalability.';
        $result = $detector->detect($text);

        $this->assertInstanceOf(DetectionResult::class, $result);
        $this->assertGreaterThanOrEqual(0.0, $result->aiProbability);
        $this->assertLessThanOrEqual(1.0, $result->aiProbability);
        $this->assertGreaterThanOrEqual(0.0, $result->confidence);
    }

    public function testDetectEmptyText(): void
    {
        $detector = new AIDetector('en');
        $result = $detector->detect('');
        $this->assertInstanceOf(DetectionResult::class, $result);
    }

    public function testDetectShortText(): void
    {
        $detector = new AIDetector('en');
        $result = $detector->detect('Hello world.');
        $this->assertInstanceOf(DetectionResult::class, $result);
    }

    public function testDetectHumanText(): void
    {
        $detector = new AIDetector('en');
        $text = "So yesterday I went to the store, right? And you won't believe what happened — the cashier totally forgot to scan like half my stuff. I didn't even notice till I got home lol.";
        $result = $detector->detect($text);
        $this->assertInstanceOf(DetectionResult::class, $result);
        // Human text should generally have lower AI probability
        $this->assertLessThanOrEqual(1.0, $result->aiProbability);
    }

    public function testDetectWithAutoLang(): void
    {
        $detector = new AIDetector('auto');
        $text = 'This is a test sentence in English for detection purposes. It should work properly.';
        $result = $detector->detect($text);
        $this->assertInstanceOf(DetectionResult::class, $result);
    }

    public function testDetectRussianText(): void
    {
        $detector = new AIDetector('ru');
        $text = 'Необходимо отметить, что осуществление данного мероприятия является ключевым аспектом. В рамках данного исследования было установлено, что надлежащее функционирование системы обеспечивает достижение поставленных целей.';
        $result = $detector->detect($text);
        $this->assertInstanceOf(DetectionResult::class, $result);
    }

    // ==================== Static Methods ====================

    public function testDetectAiStatic(): void
    {
        $text = 'Furthermore, this comprehensive implementation ensures robust performance. Moreover, it provides a scalable framework for development.';
        $result = AIDetector::detectAi($text, 'en');
        $this->assertInstanceOf(DetectionResult::class, $result);
    }

    public function testDetectAiStaticAutoLang(): void
    {
        $text = 'This is a simple test for detection.';
        $result = AIDetector::detectAi($text);
        $this->assertInstanceOf(DetectionResult::class, $result);
    }

    public function testDetectAiBatch(): void
    {
        $texts = [
            'Furthermore, the comprehensive solution provides robust performance.',
            'So yeah, I just went ahead and did that thing we talked about.',
            'Необходимо обеспечить надлежащее функционирование.',
        ];
        $results = AIDetector::detectAiBatch($texts, 'auto');

        $this->assertCount(3, $results);
        foreach ($results as $result) {
            $this->assertInstanceOf(DetectionResult::class, $result);
        }
    }

    public function testDetectAiBatchEmpty(): void
    {
        $results = AIDetector::detectAiBatch([]);
        $this->assertIsArray($results);
        $this->assertCount(0, $results);
    }

    // ==================== Score Properties ====================

    public function testAllScoreProperties(): void
    {
        $detector = new AIDetector('en');
        $text = 'Furthermore, it is important to note that the implementation ensures comprehensive coverage. Moreover, the solution provides a robust framework. Additionally, the approach demonstrates potential. Consequently, this represents advancement.';
        $result = $detector->detect($text);

        // All scores should be floats in [0, 1]
        $scores = [
            $result->entropyScore,
            $result->burstinessScore,
            $result->vocabularyScore,
            $result->zipfScore,
            $result->stylometryScore,
            $result->patternScore,
            $result->punctuationScore,
            $result->coherenceScore,
            $result->grammarScore,
            $result->openingScore,
            $result->readabilityScore,
            $result->rhythmScore,
        ];
        foreach ($scores as $score) {
            $this->assertIsFloat($score);
            $this->assertGreaterThanOrEqual(0.0, $score);
            $this->assertLessThanOrEqual(1.0, $score);
        }
    }

    public function testVerdictValues(): void
    {
        $detector = new AIDetector('en');

        // AI-like text
        $aiText = 'Furthermore, it is important to note that the implementation of this system ensures comprehensive coverage of all requirements. Moreover, the solution provides a robust framework for addressing these challenges effectively. Additionally, the approach demonstrates significant potential for scalability and adaptability. Consequently, we can conclude that this methodology represents a substantial advancement.';
        $result = $detector->detect($aiText);

        $validVerdicts = ['ai', 'likely_ai', 'possibly_ai', 'human', 'likely_human', 'possibly_human', 'unknown', 'uncertain'];
        $this->assertContains($result->verdict, $validVerdicts);
    }
}
