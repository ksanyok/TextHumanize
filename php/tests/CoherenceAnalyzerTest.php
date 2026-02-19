<?php

declare(strict_types=1);

namespace TextHumanize\Tests;

use PHPUnit\Framework\TestCase;
use TextHumanize\CoherenceAnalyzer;
use TextHumanize\CoherenceReport;

class CoherenceAnalyzerTest extends TestCase
{
    // ==================== CoherenceReport ====================

    public function testReportDefaults(): void
    {
        $report = new CoherenceReport();
        $this->assertSame(0.0, $report->overall);
        $this->assertSame(0, $report->paragraphCount);
        $this->assertSame(0.0, $report->avgParagraphLength);
        $this->assertSame(0.0, $report->paragraphLengthCv);
        $this->assertSame(0.0, $report->lexicalCohesion);
        $this->assertSame(0.0, $report->transitionScore);
        $this->assertSame(0.0, $report->topicConsistency);
        $this->assertSame(0.0, $report->sentenceOpeningDiversity);
        $this->assertIsArray($report->issues);
    }

    public function testReportToArray(): void
    {
        $report = new CoherenceReport(
            overall: 0.75,
            paragraphCount: 3,
            avgParagraphLength: 25.0,
            lexicalCohesion: 0.6,
            transitionScore: 0.8,
        );
        $arr = $report->toArray();

        $this->assertIsArray($arr);
        $this->assertArrayHasKey('overall', $arr);
        $this->assertArrayHasKey('paragraph_count', $arr);
        $this->assertArrayHasKey('lexical_cohesion', $arr);
        $this->assertArrayHasKey('transition_score', $arr);
        $this->assertSame(0.75, $arr['overall']);
        $this->assertSame(3, $arr['paragraph_count']);
    }

    public function testReportToArrayWithIssues(): void
    {
        $report = new CoherenceReport(
            overall: 0.5,
            paragraphCount: 1,
            issues: ['Low paragraph count', 'Missing transitions'],
        );
        $arr = $report->toArray();
        $this->assertArrayHasKey('issues', $arr);
        $this->assertCount(2, $arr['issues']);
    }

    // ==================== CoherenceAnalyzer Instance ====================

    public function testAnalyzeMultiParagraph(): void
    {
        $analyzer = new CoherenceAnalyzer('en');
        $text = "The first paragraph discusses the main topic of technology.\n\nThe second paragraph covers related developments. Moreover, it connects to the previous point.\n\nThe final paragraph summarizes the key findings and offers conclusions.";
        $report = $analyzer->analyze($text);

        $this->assertInstanceOf(CoherenceReport::class, $report);
        $this->assertGreaterThanOrEqual(0.0, $report->overall);
        $this->assertLessThanOrEqual(1.0, $report->overall);
        $this->assertGreaterThan(0, $report->paragraphCount);
    }

    public function testAnalyzeSingleParagraph(): void
    {
        $analyzer = new CoherenceAnalyzer('en');
        $text = 'This is a single paragraph with several sentences. It discusses one main topic. The sentences flow together nicely.';
        $report = $analyzer->analyze($text);
        $this->assertInstanceOf(CoherenceReport::class, $report);
    }

    public function testAnalyzeEmptyText(): void
    {
        $analyzer = new CoherenceAnalyzer('en');
        $report = $analyzer->analyze('');
        $this->assertInstanceOf(CoherenceReport::class, $report);
    }

    public function testAnalyzeRussian(): void
    {
        $analyzer = new CoherenceAnalyzer('ru');
        $text = "Первый абзац обсуждает основную тему.\n\nВторой абзац развивает мысль и добавляет детали.\n\nТретий абзац подводит итоги.";
        $report = $analyzer->analyze($text);
        $this->assertInstanceOf(CoherenceReport::class, $report);
    }

    // ==================== Suggest Improvements ====================

    public function testSuggestImprovements(): void
    {
        $analyzer = new CoherenceAnalyzer('en');
        $text = "This is short.\n\nAnother short one.";
        $suggestions = $analyzer->suggestImprovements($text);

        $this->assertIsArray($suggestions);
        // Should return at least some suggestions for poor text
    }

    public function testSuggestImprovementsWithReport(): void
    {
        $analyzer = new CoherenceAnalyzer('en');
        $text = "The main topic is important. Another point follows.\n\nThis paragraph is separate. It introduces a new idea.";
        $report = $analyzer->analyze($text);
        $suggestions = $analyzer->suggestImprovements($text, $report);

        $this->assertIsArray($suggestions);
        foreach ($suggestions as $suggestion) {
            $this->assertIsString($suggestion);
        }
    }

    public function testSuggestImprovementsGoodText(): void
    {
        $analyzer = new CoherenceAnalyzer('en');
        $text = "The first chapter provides a comprehensive overview of the research methodology used in this study. It explains the key variables and measurements.\n\nMoreover, the second chapter builds upon these foundations by presenting the experimental results. Furthermore, the data analysis reveals significant correlations between the variables.\n\nIn conclusion, the final chapter synthesizes these findings and discusses their implications for future research. Additionally, practical recommendations are offered.";
        $suggestions = $analyzer->suggestImprovements($text);
        $this->assertIsArray($suggestions);
    }

    // ==================== Static Method ====================

    public function testAnalyzeCoherenceStatic(): void
    {
        $text = "The first point is about quality. The second point discusses performance.\n\nAnother section covers scalability.";
        $result = CoherenceAnalyzer::analyzeCoherence($text, 'en');

        $this->assertIsArray($result);
        $this->assertArrayHasKey('overall', $result);
    }

    public function testAnalyzeCoherenceStaticRussian(): void
    {
        $text = "Первая часть о качестве. Вторая часть о производительности.\n\nДругой раздел описывает масштабируемость.";
        $result = CoherenceAnalyzer::analyzeCoherence($text, 'ru');
        $this->assertIsArray($result);
    }

    // ==================== Metrics Ranges ====================

    public function testMetricsInValidRange(): void
    {
        $analyzer = new CoherenceAnalyzer('en');
        $text = "This is the first major point about software engineering. It covers design patterns and best practices.\n\nThe second section relates to testing. Furthermore, it discusses integration testing and unit testing approaches.\n\nFinally, the third section addresses deployment strategies. Moreover, it connects back to the testing concepts mentioned earlier.";
        $report = $analyzer->analyze($text);

        $this->assertGreaterThanOrEqual(0.0, $report->lexicalCohesion);
        $this->assertLessThanOrEqual(1.0, $report->lexicalCohesion);
        $this->assertGreaterThanOrEqual(0.0, $report->transitionScore);
        $this->assertLessThanOrEqual(1.0, $report->transitionScore);
        $this->assertGreaterThanOrEqual(0.0, $report->topicConsistency);
        $this->assertLessThanOrEqual(1.0, $report->topicConsistency);
        $this->assertGreaterThanOrEqual(0.0, $report->sentenceOpeningDiversity);
        $this->assertLessThanOrEqual(1.0, $report->sentenceOpeningDiversity);
    }
}
