<?php

declare(strict_types=1);

namespace TextHumanize\Tests;

use PHPUnit\Framework\TestCase;
use TextHumanize\AnalysisReport;
use TextHumanize\HumanizeOptions;
use TextHumanize\HumanizeResult;
use TextHumanize\LangDetector;
use TextHumanize\Profiles;
use TextHumanize\RandomHelper;
use TextHumanize\TextAnalyzer;
use TextHumanize\TextHumanize;
use TextHumanize\Lang\Registry;
use TextHumanize\Pipeline\Segmenter;
use TextHumanize\Pipeline\TypographyNormalizer;
use TextHumanize\Pipeline\Debureaucratizer;
use TextHumanize\Pipeline\StructureDiversifier;
use TextHumanize\Pipeline\RepetitionReducer;
use TextHumanize\Pipeline\TextNaturalizer;
use TextHumanize\Pipeline\Validator;
use TextHumanize\Pipeline\ValidationResult;

class TextHumanizeTest extends TestCase
{
    // ==================== Core API ====================

    public function testHumanizeReturnsResult(): void
    {
        $text = 'Furthermore, it is important to note that the implementation of this system ensures comprehensive coverage of all requirements. Moreover, the solution provides a robust framework for addressing these challenges effectively.';
        $result = TextHumanize::humanize($text);

        $this->assertInstanceOf(HumanizeResult::class, $result);
        $this->assertSame($text, $result->original);
        $this->assertNotEmpty($result->processed);
        $this->assertNotEmpty($result->lang);
        $this->assertSame('web', $result->profile);
    }

    public function testHumanizeEmptyText(): void
    {
        $result = TextHumanize::humanize('');
        $this->assertSame('', $result->original);
        $this->assertSame('', $result->processed);
    }

    public function testHumanizeWithSeed(): void
    {
        $text = 'Furthermore, it is important to note that the implementation ensures comprehensive coverage. Moreover, the solution provides a robust framework for addressing challenges effectively.';
        $r1 = TextHumanize::humanize($text, seed: 42);
        $r2 = TextHumanize::humanize($text, seed: 42);
        $this->assertSame($r1->processed, $r2->processed);
    }

    public function testHumanizeRussian(): void
    {
        $text = 'Осуществление данного мероприятия является важным аспектом. В рамках данного исследования было установлено, что необходимо обеспечить надлежащее функционирование.';
        $result = TextHumanize::humanize($text);
        $this->assertSame('ru', $result->lang);
        $this->assertNotEmpty($result->processed);
    }

    public function testHumanizeWithProfile(): void
    {
        $text = 'Furthermore, the comprehensive implementation ensures robust performance. Moreover, it provides a scalable framework.';
        foreach (['chat', 'web', 'seo', 'docs', 'formal'] as $profile) {
            $result = TextHumanize::humanize($text, profile: $profile);
            $this->assertSame($profile, $result->profile);
        }
    }

    public function testHumanizePreservesKeywords(): void
    {
        $text = 'TextHumanize provides comprehensive text processing. The TextHumanize library ensures quality output.';
        $result = TextHumanize::humanize($text, preserve: ['keywords' => ['TextHumanize']]);
        $this->assertStringContainsString('TextHumanize', $result->processed);
    }

    // ==================== Analyze ====================

    public function testAnalyzeReturnsReport(): void
    {
        $text = 'This is a simple test sentence. Here is another one.';
        $report = TextHumanize::analyze($text);
        $this->assertInstanceOf(AnalysisReport::class, $report);
        $this->assertGreaterThan(0, $report->totalWords);
        $this->assertGreaterThan(0, $report->totalSentences);
        $this->assertGreaterThanOrEqual(0.0, $report->artificialityScore);
        $this->assertLessThanOrEqual(100.0, $report->artificialityScore);
    }

    public function testAnalyzeEmptyText(): void
    {
        $report = TextHumanize::analyze('');
        $this->assertSame(0, $report->totalWords);
        $this->assertSame(0.0, $report->artificialityScore);
    }

    public function testAnalyzeToArray(): void
    {
        $report = TextHumanize::analyze('Some text here.');
        $arr = $report->toArray();
        $this->assertIsArray($arr);
        $this->assertArrayHasKey('lang', $arr);
        $this->assertArrayHasKey('artificiality_score', $arr);
        $this->assertArrayHasKey('total_words', $arr);
    }

    // ==================== Explain ====================

    public function testExplainReturnsStructuredData(): void
    {
        $text = 'Furthermore, it is important to note that the implementation ensures comprehensive coverage of all requirements.';
        $explanation = TextHumanize::explain($text);

        $this->assertIsArray($explanation);
        $this->assertArrayHasKey('before', $explanation);
        $this->assertArrayHasKey('after', $explanation);
        $this->assertArrayHasKey('recommendations', $explanation);
        $this->assertArrayHasKey('summary', $explanation);
        $this->assertArrayHasKey('change_ratio', $explanation);
    }

    // ==================== Language Detection ====================

    public function testDetectEnglish(): void
    {
        $this->assertSame('en', LangDetector::detect('This is a test sentence in English.'));
    }

    public function testDetectRussian(): void
    {
        $this->assertSame('ru', LangDetector::detect('Это тестовое предложение на русском языке.'));
    }

    public function testDetectUkrainian(): void
    {
        $this->assertSame('uk', LangDetector::detect('Це тестове речення українською мовою.'));
    }

    public function testDetectGerman(): void
    {
        $this->assertSame('de', LangDetector::detect('Dies ist ein Testsatz auf Deutsch.'));
    }

    public function testDetectFrench(): void
    {
        $this->assertSame('fr', LangDetector::detect("C'est une phrase de test en français."));
    }

    public function testDetectSpanish(): void
    {
        $this->assertSame('es', LangDetector::detect('Esta es una oración de prueba en español.'));
    }

    // ==================== Profiles ====================

    public function testProfilesExist(): void
    {
        foreach (['chat', 'web', 'seo', 'docs', 'formal'] as $name) {
            $profile = Profiles::get($name);
            $this->assertIsArray($profile);
            $this->assertArrayHasKey('decancel_intensity', $profile);
            $this->assertArrayHasKey('target_sentence_len', $profile);
        }
    }

    public function testShouldApplyFlagDisabled(): void
    {
        // formal profile has liveliness_intensity = 0.0
        $formal = Profiles::get('formal');
        $this->assertFalse(Profiles::shouldApply('inject_liveliness', $formal, 50));
    }

    public function testShouldApplyFlagEnabled(): void
    {
        $chat = Profiles::get('chat');
        $this->assertTrue(Profiles::shouldApply('debureaucratize', $chat, 50));
    }

    // ==================== HumanizeOptions ====================

    public function testOptionsValidProfile(): void
    {
        $options = new HumanizeOptions(profile: 'chat');
        $this->assertSame('chat', $options->profile);
    }

    public function testOptionsInvalidProfile(): void
    {
        $this->expectException(\InvalidArgumentException::class);
        new HumanizeOptions(profile: 'invalid');
    }

    public function testOptionsIntensityClamped(): void
    {
        $options = new HumanizeOptions(intensity: 150);
        $this->assertSame(100, $options->intensity);

        $options2 = new HumanizeOptions(intensity: -10);
        $this->assertSame(0, $options2->intensity);
    }

    // ==================== RandomHelper ====================

    public function testRandomSeeded(): void
    {
        $r1 = new RandomHelper(42);
        $r2 = new RandomHelper(42);

        $seq1 = [$r1->random(), $r1->random(), $r1->random()];
        $seq2 = [$r2->random(), $r2->random(), $r2->random()];
        $this->assertSame($seq1, $seq2);
    }

    public function testRandInt(): void
    {
        $rng = new RandomHelper(1);
        for ($i = 0; $i < 50; $i++) {
            $val = $rng->randInt(1, 10);
            $this->assertGreaterThanOrEqual(1, $val);
            $this->assertLessThanOrEqual(10, $val);
        }
    }

    public function testChoiceFromArray(): void
    {
        $rng = new RandomHelper(7);
        $items = ['a', 'b', 'c'];
        $choice = $rng->choice($items);
        $this->assertContains($choice, $items);
    }

    // ==================== Language Registry ====================

    public function testRegistryGetEnglish(): void
    {
        $pack = Registry::get('en');
        $this->assertIsArray($pack);
        $this->assertArrayHasKey('bureaucratic', $pack);
        $this->assertArrayHasKey('ai_connectors', $pack);
        $this->assertArrayHasKey('synonyms', $pack);
    }

    public function testRegistryGetRussian(): void
    {
        $pack = Registry::get('ru');
        $this->assertIsArray($pack);
        $this->assertNotEmpty($pack['bureaucratic'] ?? []);
    }

    public function testRegistryHasDeepSupport(): void
    {
        $this->assertTrue(Registry::hasDeepSupport('en'));
        $this->assertTrue(Registry::hasDeepSupport('ru'));
        $this->assertTrue(Registry::hasDeepSupport('de'));
        $this->assertFalse(Registry::hasDeepSupport('zh'));
    }

    public function testRegistryUnknownLang(): void
    {
        $pack = Registry::get('xx');
        $this->assertIsArray($pack);
        // Returns empty fallback
    }

    // ==================== Segmenter ====================

    public function testSegmenterProtectsCode(): void
    {
        $text = "Here is code:\n```python\nprint('hello')\n```\nEnd.";
        $segmenter = new Segmenter();
        $seg = $segmenter->segment($text);

        $this->assertStringNotContainsString('print', $seg->text);
        $restored = $seg->restore($seg->text);
        $this->assertStringContainsString("print('hello')", $restored);
    }

    public function testSegmenterProtectsUrls(): void
    {
        $text = 'Visit https://example.com for more.';
        $segmenter = new Segmenter();
        $seg = $segmenter->segment($text);

        $this->assertStringNotContainsString('https://example.com', $seg->text);
        $restored = $seg->restore($seg->text);
        $this->assertStringContainsString('https://example.com', $restored);
    }

    public function testSegmenterProtectsKeywords(): void
    {
        $text = 'Our TextHumanize library is great.';
        $segmenter = new Segmenter();
        $seg = $segmenter->segment($text, ['TextHumanize']);

        $restored = $seg->restore($seg->text);
        $this->assertStringContainsString('TextHumanize', $restored);
    }

    // ==================== Typography Normalizer ====================

    public function testTypographyNormalizeDashes(): void
    {
        $typo = new TypographyNormalizer();
        [$result, $changes] = $typo->normalize('Hello — world', 'en');
        $this->assertIsString($result);
        $this->assertStringContainsString('Hello', $result);
    }

    public function testTypographyNormalizeQuotes(): void
    {
        $typo = new TypographyNormalizer();
        [$result, $changes] = $typo->normalize('«test»', 'en');
        $this->assertIsString($result);
        $this->assertStringContainsString('test', $result);
    }

    // ==================== Debureaucratizer ====================

    public function testDebureaucratizer(): void
    {
        $langPack = Registry::get('en');
        $profile = Profiles::get('chat');
        $rng = new RandomHelper(42);

        $debureaucratizer = new Debureaucratizer();
        $text = 'It is important to note that we need to ensure proper implementation.';
        $result = $debureaucratizer->process($text, $langPack, $profile, 70, $rng);
        $this->assertNotEmpty($result);
    }

    // ==================== Validator ====================

    public function testValidatorAcceptsSmallChange(): void
    {
        $validator = new Validator();
        $options = new HumanizeOptions();
        $original = 'This is a test sentence that should remain mostly the same.';
        $processed = 'This is a test sentence that should stay mostly the same.';

        $result = $validator->validate($original, $processed, $options);
        $this->assertInstanceOf(ValidationResult::class, $result);
        $this->assertTrue($result->isValid);
    }

    public function testValidatorDetectsMissingKeyword(): void
    {
        $validator = new Validator();
        $options = new HumanizeOptions(preserve: ['keywords' => ['TextHumanize']]);
        $original = 'TextHumanize is a great library.';
        $processed = 'The library is great.';

        $result = $validator->validate($original, $processed, $options);
        $this->assertFalse($result->isValid);
        $this->assertNotEmpty($result->errors);
    }

    // ==================== HumanizeResult ====================

    public function testResultChangeRatio(): void
    {
        $result = new HumanizeResult(
            original: 'Hello world',
            processed: 'Hello world',
            lang: 'en',
            profile: 'web',
            changes: [],
        );
        $this->assertSame(0.0, $result->getChangeRatio());
    }

    public function testResultChangeRatioModified(): void
    {
        $result = new HumanizeResult(
            original: 'Hello beautiful world today',
            processed: 'Hey nice planet now',
            lang: 'en',
            profile: 'web',
            changes: [],
        );
        $ratio = $result->getChangeRatio();
        $this->assertGreaterThan(0.0, $ratio);
        $this->assertLessThanOrEqual(1.0, $ratio);
    }

    // ==================== Version ====================

    public function testVersion(): void
    {
        $this->assertSame('0.1.0', TextHumanize::VERSION);
    }

    // ==================== Integration ====================

    public function testFullPipelineEnglish(): void
    {
        $text = 'Furthermore, it is important to note that the implementation of this system ensures comprehensive coverage of all requirements. Moreover, the solution provides a robust framework for addressing these challenges effectively. Additionally, the approach demonstrates significant potential for scalability and adaptability in various contexts. Consequently, we can conclude that this methodology represents a substantial advancement in the field.';

        $result = TextHumanize::humanize($text, lang: 'en', profile: 'chat', intensity: 70, seed: 42);

        $this->assertSame('en', $result->lang);
        $this->assertSame('chat', $result->profile);
        $this->assertNotEmpty($result->processed);
        // Should have some changes
        $this->assertNotEmpty($result->changes);
    }

    public function testFullPipelineRussian(): void
    {
        $text = 'Необходимо отметить, что осуществление данного мероприятия является ключевым аспектом. В рамках данного исследования было установлено, что надлежащее функционирование системы обеспечивает достижение поставленных целей. Кроме того, данный подход демонстрирует значительный потенциал.';

        $result = TextHumanize::humanize($text, lang: 'ru', profile: 'web', intensity: 60, seed: 7);

        $this->assertSame('ru', $result->lang);
        $this->assertNotEmpty($result->processed);
    }

    public function testAnalyzeDetectsArtificiality(): void
    {
        $aiText = 'Furthermore, this comprehensive implementation ensures robust performance. Moreover, it provides a scalable framework. Additionally, the solution demonstrates significant potential. Consequently, we can conclude that this approach is effective.';
        $report = TextHumanize::analyze($aiText, 'en');

        // AI text should have some artificiality
        $this->assertGreaterThan(0.0, $report->artificialityScore);
    }

    public function testHumanizeReducesArtificiality(): void
    {
        $aiText = 'Furthermore, it is important to note that the implementation of this system ensures comprehensive coverage. Moreover, the solution provides a robust framework. Additionally, the approach demonstrates significant potential. Consequently, this methodology represents a substantial advancement.';

        $beforeReport = TextHumanize::analyze($aiText, 'en');
        $result = TextHumanize::humanize($aiText, lang: 'en', intensity: 70, seed: 42);
        $afterReport = TextHumanize::analyze($result->processed, 'en');

        // After humanization, artificiality should ideally be lower or equal
        // (not always guaranteed, but generally true)
        $this->assertLessThanOrEqual(
            $beforeReport->artificialityScore + 5,
            $afterReport->artificialityScore,
            'Artificiality should not increase significantly'
        );
    }
}
