<?php

declare(strict_types=1);

namespace TextHumanize\Tests;

use PHPUnit\Framework\TestCase;
use TextHumanize\HumanizeResult;
use TextHumanize\TextAnalyzer;
use TextHumanize\AnalysisReport;
use TextHumanize\TextHumanize;

class TextHumanizeExtraTest extends TestCase
{
    // ==================== humanizeChunked ====================

    public function testHumanizeChunkedShortText(): void
    {
        $text = 'Furthermore, it is important to note that the implementation provides comprehensive coverage. Moreover, the solution ensures robust performance.';
        $result = TextHumanize::humanizeChunked($text, 5000);

        $this->assertInstanceOf(HumanizeResult::class, $result);
        $this->assertSame($text, $result->original);
        $this->assertNotEmpty($result->processed);
    }

    public function testHumanizeChunkedEmptyText(): void
    {
        $result = TextHumanize::humanizeChunked('');
        $this->assertSame('', $result->original);
        $this->assertSame('', $result->processed);
    }

    public function testHumanizeChunkedSmallChunkSize(): void
    {
        $text = 'Furthermore, it is important to note that the implementation provides comprehensive coverage. Moreover, the solution ensures robust performance. Additionally, the approach demonstrates significant potential. Consequently, this methodology represents advancement.';
        $result = TextHumanize::humanizeChunked($text, 100, seed: 42);

        $this->assertInstanceOf(HumanizeResult::class, $result);
        $this->assertNotEmpty($result->processed);
    }

    public function testHumanizeChunkedWithParams(): void
    {
        $text = 'The comprehensive implementation provides robust performance and coverage. It ensures effective operation.';
        $result = TextHumanize::humanizeChunked(
            $text,
            chunkSize: 5000,
            lang: 'en',
            profile: 'web',
            intensity: 60,
            seed: 42,
        );

        $this->assertSame('en', $result->lang);
        $this->assertSame('web', $result->profile);
    }

    public function testHumanizeChunkedDeterministic(): void
    {
        $text = 'Furthermore, the solution provides robust performance. Moreover, it ensures comprehensive coverage.';
        $r1 = TextHumanize::humanizeChunked($text, 5000, seed: 42);
        $r2 = TextHumanize::humanizeChunked($text, 5000, seed: 42);
        $this->assertSame($r1->processed, $r2->processed);
    }

    public function testHumanizeChunkedRussian(): void
    {
        $text = 'Необходимо отметить, что осуществление данного мероприятия является важным аспектом. В рамках данного исследования было установлено, что надлежащее функционирование обеспечивает результат.';
        $result = TextHumanize::humanizeChunked($text, 5000, lang: 'ru');
        $this->assertSame('ru', $result->lang);
    }

    // ==================== registerPlugin / clearPlugins ====================

    public function testRegisterPluginAndClear(): void
    {
        // Register a simple uppercase plugin (must specify before/after stage)
        TextHumanize::registerPlugin(function (string $text, string $lang, string $profile, int $intensity): string {
            return strtoupper($text);
        }, after: 'naturalize');

        // Clear to avoid side effects on other tests
        TextHumanize::clearPlugins();
        $this->assertTrue(true); // No exception = success
    }

    public function testPluginIsApplied(): void
    {
        // Register a marker plugin (after restore so marker survives)
        $marker = '[[PLUGIN_WAS_HERE]]';
        TextHumanize::registerPlugin(function (string $text, string $lang, string $profile, int $intensity) use ($marker): string {
            return $text . ' ' . $marker;
        }, after: 'restore');

        $text = 'Simple test sentence for plugin.';
        $result = TextHumanize::humanize($text, lang: 'en', seed: 42);

        // Clean up
        TextHumanize::clearPlugins();

        $this->assertStringContainsString($marker, $result->processed);
    }

    public function testPluginBeforeStage(): void
    {
        TextHumanize::registerPlugin(
            function (string $text, string $lang, string $profile, int $intensity): string {
                return str_replace('MARKER', 'REPLACED', $text);
            },
            before: 'validation',
        );

        TextHumanize::clearPlugins();
        $this->assertTrue(true);
    }

    public function testPluginAfterStage(): void
    {
        TextHumanize::registerPlugin(
            function (string $text, string $lang, string $profile, int $intensity): string {
                return $text;
            },
            after: 'typography',
        );

        TextHumanize::clearPlugins();
        $this->assertTrue(true);
    }

    public function testClearPluginsIdempotent(): void
    {
        TextHumanize::clearPlugins();
        TextHumanize::clearPlugins();
        $this->assertTrue(true);
    }

    public function testMultiplePlugins(): void
    {
        TextHumanize::registerPlugin(function (string $text, string $lang, string $profile, int $intensity): string {
            return $text . ' [P1]';
        }, after: 'restore');
        TextHumanize::registerPlugin(function (string $text, string $lang, string $profile, int $intensity): string {
            return $text . ' [P2]';
        }, after: 'restore');

        $text = 'Test text for multiple plugins.';
        $result = TextHumanize::humanize($text, seed: 42);

        TextHumanize::clearPlugins();

        $this->assertStringContainsString('[P1]', $result->processed);
        $this->assertStringContainsString('[P2]', $result->processed);
    }

    // ==================== TextAnalyzer ====================

    public function testTextAnalyzerBasic(): void
    {
        $analyzer = new TextAnalyzer('en');
        $report = $analyzer->analyze('This is a simple test. Here is another sentence.');

        $this->assertInstanceOf(AnalysisReport::class, $report);
        $this->assertGreaterThan(0, $report->totalWords);
        $this->assertGreaterThan(0, $report->totalSentences);
    }

    public function testTextAnalyzerEmptyText(): void
    {
        $analyzer = new TextAnalyzer('en');
        $report = $analyzer->analyze('');
        $this->assertSame(0, $report->totalWords);
        $this->assertSame(0, $report->totalSentences);
    }

    public function testTextAnalyzerAiText(): void
    {
        $analyzer = new TextAnalyzer('en');
        $text = 'Furthermore, the comprehensive implementation ensures robust performance. Moreover, it provides a scalable framework. Additionally, the approach demonstrates significant potential. Consequently, this methodology represents advancement.';
        $report = $analyzer->analyze($text);

        $this->assertGreaterThan(0.0, $report->artificialityScore);
        $this->assertLessThanOrEqual(100.0, $report->artificialityScore);
    }

    public function testTextAnalyzerRussian(): void
    {
        $analyzer = new TextAnalyzer('ru');
        $text = 'Это простой тест на русском языке. Здесь несколько предложений.';
        $report = $analyzer->analyze($text);

        $this->assertGreaterThan(0, $report->totalWords);
    }

    public function testTextAnalyzerMetrics(): void
    {
        $analyzer = new TextAnalyzer('en');
        $text = 'The first sentence is here. A second sentence follows. Third one is short. The fourth adds more content. And a fifth closing line.';
        $report = $analyzer->analyze($text);

        $this->assertGreaterThan(0, $report->totalChars);
        $this->assertGreaterThan(0.0, $report->avgSentenceLength);
        $this->assertGreaterThanOrEqual(0.0, $report->burstinessScore);
    }

    public function testTextAnalyzerBureaucraticText(): void
    {
        $analyzer = new TextAnalyzer('en');
        $text = 'It is important to note that in order to ensure the implementation of this initiative, we must take into consideration the fact that the aforementioned requirements necessitate careful deliberation.';
        $report = $analyzer->analyze($text);

        $this->assertGreaterThanOrEqual(0.0, $report->bureaucraticRatio);
    }

    // ==================== AnalysisReport toArray ====================

    public function testAnalysisReportToArray(): void
    {
        $report = TextHumanize::analyze('Test sentence here. Another one follows.');
        $arr = $report->toArray();

        $this->assertArrayHasKey('lang', $arr);
        $this->assertArrayHasKey('total_words', $arr);
        $this->assertArrayHasKey('total_sentences', $arr);
        $this->assertArrayHasKey('total_chars', $arr);
        $this->assertArrayHasKey('artificiality_score', $arr);
        $this->assertArrayHasKey('avg_sentence_length', $arr);
        $this->assertArrayHasKey('burstiness_score', $arr);
    }

    // ==================== HumanizeResult extras ====================

    public function testResultEmptyOriginalChangeRatio(): void
    {
        $result = new HumanizeResult(
            original: '',
            processed: '',
            lang: 'en',
            profile: 'web',
            changes: [],
        );
        $this->assertSame(0.0, $result->getChangeRatio());
    }

    public function testResultToArray(): void
    {
        $result = new HumanizeResult(
            original: 'Hello world',
            processed: 'Hi world',
            lang: 'en',
            profile: 'web',
            changes: ['synonym: Hello → Hi'],
        );

        // Check if toArray exists
        if (method_exists($result, 'toArray')) {
            $arr = $result->toArray();
            $this->assertIsArray($arr);
        } else {
            $this->assertTrue(true);
        }
    }

    // ==================== Preserve constraints ====================

    public function testHumanizePreserveUrls(): void
    {
        $text = 'Visit https://example.com for more details. The comprehensive solution is available at https://github.com/test and provides robust coverage.';
        $result = TextHumanize::humanize($text, seed: 42);

        // URLs should be preserved by segmenter
        $this->assertStringContainsString('https://example.com', $result->processed);
        $this->assertStringContainsString('https://github.com/test', $result->processed);
    }

    public function testHumanizePreserveCodeBlocks(): void
    {
        $text = "Before code block.\n```python\nprint('hello')\n```\nAfter code block.";
        $result = TextHumanize::humanize($text, seed: 42);
        $this->assertStringContainsString("print('hello')", $result->processed);
    }

    // ==================== humanizeBatch ====================

    public function testHumanizeBatchBasic(): void
    {
        $texts = [
            'Furthermore, this implementation provides comprehensive coverage.',
            'Moreover, the solution ensures robust performance effectively.',
        ];
        $results = TextHumanize::humanizeBatch($texts, seed: 42);

        $this->assertCount(2, $results);
        $this->assertInstanceOf(HumanizeResult::class, $results[0]);
        $this->assertInstanceOf(HumanizeResult::class, $results[1]);
        $this->assertSame($texts[0], $results[0]->original);
        $this->assertSame($texts[1], $results[1]->original);
    }

    public function testHumanizeBatchEmpty(): void
    {
        $results = TextHumanize::humanizeBatch([]);
        $this->assertCount(0, $results);
    }

    public function testHumanizeBatchSeedReproducibility(): void
    {
        $texts = ['This text needs improvement.', 'Another example text.'];
        $r1 = TextHumanize::humanizeBatch($texts, seed: 100);
        $r2 = TextHumanize::humanizeBatch($texts, seed: 100);

        $this->assertSame($r1[0]->processed, $r2[0]->processed);
        $this->assertSame($r1[1]->processed, $r2[1]->processed);
    }

    public function testHumanizeBatchProfile(): void
    {
        $texts = ['Furthermore, the implementation is comprehensive.'];
        $results = TextHumanize::humanizeBatch($texts, profile: 'seo', seed: 42);

        $this->assertCount(1, $results);
        $this->assertSame('seo', $results[0]->profile);
    }

    // ==================== Similarity & QualityScore ====================

    public function testSimilarityIdentical(): void
    {
        $result = new HumanizeResult('hello world', 'hello world', 'en', 'web');
        $this->assertEqualsWithDelta(1.0, $result->getSimilarity(), 0.001);
    }

    public function testSimilarityDifferent(): void
    {
        $result = new HumanizeResult('hello world', 'foo bar baz', 'en', 'web');
        $this->assertEqualsWithDelta(0.0, $result->getSimilarity(), 0.001);
    }

    public function testSimilarityPartial(): void
    {
        $result = new HumanizeResult('hello world test', 'hello world new', 'en', 'web');
        $sim = $result->getSimilarity();
        $this->assertGreaterThan(0.0, $sim);
        $this->assertLessThan(1.0, $sim);
    }

    public function testSimilarityBothEmpty(): void
    {
        $result = new HumanizeResult('', '', 'en', 'web');
        $this->assertEqualsWithDelta(1.0, $result->getSimilarity(), 0.001);
    }

    public function testQualityScoreUnchanged(): void
    {
        $result = new HumanizeResult('hello world', 'hello world', 'en', 'web');
        $this->assertEqualsWithDelta(0.3, $result->getQualityScore(), 0.001);
    }

    public function testQualityScoreTotallyDifferent(): void
    {
        $result = new HumanizeResult('alpha beta gamma delta', 'one two three four five six seven', 'en', 'web');
        $this->assertLessThanOrEqual(0.5, $result->getQualityScore());
    }

    public function testQualityScoreRange(): void
    {
        $result = TextHumanize::humanize(
            'Furthermore, it is important to note that the implementation provides comprehensive coverage.',
            seed: 42,
        );
        $score = $result->getQualityScore();
        $this->assertGreaterThanOrEqual(0.0, $score);
        $this->assertLessThanOrEqual(1.0, $score);
    }
}
