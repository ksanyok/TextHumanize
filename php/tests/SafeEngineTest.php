<?php

declare(strict_types=1);

namespace TextHumanize\Tests;

use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\TestCase;
use TextHumanize\TextHumanize;

/**
 * Publication-safety of the 0.37 engine (same guarantees as js/tests/multilang.test.ts).
 */
class SafeEngineTest extends TestCase
{
    public static function langs(): array
    {
        return [['ru'], ['uk'], ['en'], ['pl'], ['es'], ['pt']];
    }

    private static function fixture(string $lang): string
    {
        return (string) file_get_contents(__DIR__ . "/../../benchmarks/seo_html/{$lang}.html");
    }

    private static function grab(string $re, string $html): array
    {
        return preg_match_all($re, $html, $m) ? $m[0] : [];
    }

    private static function visible(string $html): string
    {
        return (string) preg_replace('/\s+/u', ' ', strip_tags($html));
    }

    #[DataProvider('langs')]
    public function testFixtureKeepsMarkupAndChangesText(string $lang): void
    {
        $html = self::fixture($lang);
        $r = TextHumanize::humanizeHtml($html, ['lang' => $lang, 'profile' => 'seo', 'intensity' => 55]);
        $edits = array_filter($r['changes'], static fn ($c) => !in_array($c['type'], ['typography', 'adaptive_intensity'], true));
        $this->assertGreaterThanOrEqual(5, count($edits));
        $this->assertSame(self::grab('/<a\b[^>]*>[\s\S]*?<\/a>/', $html), self::grab('/<a\b[^>]*>[\s\S]*?<\/a>/', $r['html']));
        $this->assertSame(self::grab('/<\/?[a-z0-9]+/i', $html), self::grab('/<\/?[a-z0-9]+/i', $r['html']));
        $this->assertSame(self::grab('/<h[1-6][^>]*>[\s\S]*?<\/h[1-6]>/', $html), self::grab('/<h[1-6][^>]*>[\s\S]*?<\/h[1-6]>/', $r['html']));
        $this->assertSame(0, $r['stats']['reverted']);
        $this->assertLessThan($r['ai_score_before'], $r['ai_score_after']);
        $text = (string) preg_replace('/\s+([.!?])/u', '$1', self::visible($r['html']));
        $this->assertDoesNotMatchRegularExpression('/,\s*[,.;:]|\.\.(?!\.)|[.!?]\s+,|\p{L}\s{2,}\p{L}/u', $text);
        $this->assertSame([], $r['warnings']);
    }

    public function testProtectedElementsAreUntouched(): void
    {
        $html = '<p>Furthermore, it is important to note that <a href="/x">it is important to note that</a> matters. '
            . 'Moreover, <code>utilize()</code> is robust.</p><p data-humanize="off">Furthermore, it is important to note that this stays.</p>';
        $r = TextHumanize::humanizeHtml($html, ['lang' => 'en', 'intensity' => 100, 'seed' => 3]);
        $this->assertStringContainsString('<a href="/x">it is important to note that</a>', $r['html']);
        $this->assertStringContainsString('<code>utilize()</code>', $r['html']);
        $this->assertStringContainsString('<p data-humanize="off">Furthermore, it is important to note that this stays.</p>', $r['html']);
    }

    public function testContrastConnectorsAreNeverDropped(): void
    {
        $html = '<p>A ferramenta é rápida e barata para equipes pequenas. No entanto, faltam relatórios para grandes agências hoje em dia.</p>';
        for ($seed = 1; $seed <= 25; $seed++) {
            $r = TextHumanize::humanizeHtml($html, ['lang' => 'pt', 'intensity' => 100, 'seed' => $seed]);
            $this->assertMatchesRegularExpression('/\. (No entanto|Mas|Contudo|Porém|Todavia|Ainda assim|Entretanto|Mesmo assim)[\s,]/u', strip_tags($r['html']));
        }
    }

    public function testLightVerbsKeepCollocations(): void
    {
        $html = '<p>Компания должна осуществлять контроль над позициями и осуществлять мониторинг результатов каждый день без исключений.</p>';
        for ($seed = 1; $seed <= 25; $seed++) {
            $out = TextHumanize::humanizeHtml($html, ['lang' => 'ru', 'intensity' => 100, 'seed' => $seed])['html'];
            $this->assertDoesNotMatchRegularExpression('/делать (контроль|мониторинг)|контролировать над/u', $out);
        }
    }

    public function testMixedScriptWarning(): void
    {
        $r = TextHumanize::humanizeHtml('<p>Платформа объединяет предложения судовладельцев, менеджеров и манning агентств по всему миру.</p>', ['lang' => 'ru']);
        $this->assertSame([['type' => 'mixed_script', 'token' => 'манning']], $r['warnings']);
    }

    public function testPlainTextUsesSafeEngineAndLegacyStaysAvailable(): void
    {
        $text = 'Furthermore, it is important to note that high-quality backlinks significantly enhance visibility. '
            . 'Moreover, a robust strategy facilitates growth. In conclusion, it is crucial to implement a holistic approach.';
        $safe = TextHumanize::humanize($text, 'en', 'web', 80, [], [], 7);
        $this->assertNotSame($text, $safe->processed);
        $this->assertContains('safe_engine', array_column($safe->changes, 'stage'));
        $legacy = TextHumanize::humanize($text, 'en', 'web', 80, [], ['engine' => 'legacy'], 7);
        $this->assertNotContains('safe_engine', array_column($legacy->changes, 'stage'));
    }

    public function testPathologicalInputStaysFast(): void
    {
        foreach ([str_repeat(' ', 50000) . 'x', str_repeat('<a', 30000), str_repeat('<!--', 20000), str_repeat('word ', 40000)] as $input) {
            $t = microtime(true);
            TextHumanize::humanizeHtml($input, ['lang' => 'en']);
            $this->assertLessThan(3.0, microtime(true) - $t);
        }
    }
}
