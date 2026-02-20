<?php

declare(strict_types=1);

namespace TextHumanize;

use TextHumanize\Pipeline\Pipeline;

/**
 * TextHumanize — main facade for the text humanization library.
 *
 * Usage:
 *   $result = TextHumanize::humanize("AI-generated text here");
 *   echo $result->processed;
 *
 *   $report = TextHumanize::analyze("Text to analyze");
 *   echo $report->artificialityScore;
 *
 *   $explanation = TextHumanize::explain("Text to explain");
 *   print_r($explanation);
 */
class TextHumanize
{
    public const VERSION = '0.11.0';

    /**
     * Humanize text — the primary API method.
     *
     * @param string $text        The text to humanize
     * @param string|null $lang   Language code (auto-detect if null)
     * @param string $profile     Profile: chat, web, seo, docs, formal
     * @param int $intensity      Processing intensity 0-100
     * @param array $preserve     Keys preserved during processing
     * @param array $constraints  Output constraints
     * @param int|null $seed      Random seed for reproducibility
     */
    public static function humanize(
        string $text,
        ?string $lang = null,
        string $profile = 'web',
        int $intensity = 50,
        array $preserve = [],
        array $constraints = [],
        ?int $seed = null,
    ): HumanizeResult {
        $options = new HumanizeOptions(
            lang: $lang,
            profile: $profile,
            intensity: $intensity,
            preserve: $preserve,
            constraints: $constraints,
            seed: $seed,
        );

        return Pipeline::run($text, $options);
    }

    /**
     * Process large texts by splitting into manageable chunks.
     *
     * Splits the text at paragraph boundaries, processes each chunk
     * independently, then reassembles the result.
     *
     * @param string $text        Text to process (any length)
     * @param int $chunkSize      Target chunk size in characters (default 5000)
     * @param string|null $lang   Language code (auto-detect if null)
     * @param string $profile     Profile: chat, web, seo, docs, formal
     * @param int $intensity      Processing intensity 0-100
     * @param array $preserve     Keys preserved during processing
     * @param array $constraints  Output constraints
     * @param int|null $seed      Random seed for reproducibility
     */
    public static function humanizeChunked(
        string $text,
        int $chunkSize = 5000,
        ?string $lang = null,
        string $profile = 'web',
        int $intensity = 50,
        array $preserve = [],
        array $constraints = [],
        ?int $seed = null,
    ): HumanizeResult {
        $text = trim($text);
        if ($text === '' || mb_strlen($text) <= $chunkSize) {
            return self::humanize($text, $lang, $profile, $intensity, $preserve, $constraints, $seed);
        }

        $chunks = self::splitIntoChunks($text, $chunkSize);
        $allProcessed = [];
        $allChanges = [];
        $detectedLang = $lang;

        foreach ($chunks as $i => $chunk) {
            $chunkSeed = $seed !== null ? $seed + $i : null;
            $result = self::humanize($chunk, $detectedLang, $profile, $intensity, $preserve, $constraints, $chunkSeed);
            $allProcessed[] = $result->processed;
            $allChanges = array_merge($allChanges, $result->changes);
            if ($i === 0) {
                $detectedLang = $result->lang;
            }
        }

        return new HumanizeResult(
            original: $text,
            processed: implode("\n\n", $allProcessed),
            lang: $detectedLang ?? 'en',
            profile: $profile,
            changes: $allChanges,
        );
    }

    /**
     * Humanize multiple texts in a single call.
     *
     * Each text is processed independently. When a seed is provided,
     * the i-th text uses seed + i for reproducibility.
     *
     * @param list<string> $texts        Texts to process
     * @param string|null  $lang         Language code (auto-detect if null)
     * @param string       $profile      Profile: chat, web, seo, docs, formal
     * @param int          $intensity    Processing intensity 0-100
     * @param array        $preserve     Keys preserved during processing
     * @param array        $constraints  Output constraints
     * @param int|null     $seed         Base random seed
     * @return list<HumanizeResult>
     */
    public static function humanizeBatch(
        array $texts,
        ?string $lang = null,
        string $profile = 'web',
        int $intensity = 50,
        array $preserve = [],
        array $constraints = [],
        ?int $seed = null,
    ): array {
        $results = [];
        foreach ($texts as $i => $text) {
            $itemSeed = $seed !== null ? $seed + $i : null;
            $results[] = self::humanize(
                $text,
                lang: $lang,
                profile: $profile,
                intensity: $intensity,
                preserve: $preserve,
                constraints: $constraints,
                seed: $itemSeed,
            );
        }
        return $results;
    }

    /**
     * Register a custom plugin for the pipeline.
     *
     * @param callable $plugin  Callable: fn(string $text, string $lang, string $profile, int $intensity): string
     * @param string|null $before  Insert before this stage
     * @param string|null $after   Insert after this stage
     */
    public static function registerPlugin(
        callable $plugin,
        ?string $before = null,
        ?string $after = null,
    ): void {
        Pipeline::registerPlugin($plugin, $before, $after);
    }

    /**
     * Remove all registered plugins.
     */
    public static function clearPlugins(): void
    {
        Pipeline::clearPlugins();
    }

    /**
     * Analyze text for artificiality metrics.
     *
     * @param string $text       Text to analyze
     * @param string|null $lang  Language code (auto-detect if null)
     */
    public static function analyze(string $text, ?string $lang = null): AnalysisReport
    {
        $lang = $lang ?? LangDetector::detect($text);
        $analyzer = new TextAnalyzer($lang);
        return $analyzer->analyze($text);
    }

    /**
     * Explain what would be changed and why.
     *
     * Returns a structured array with before/after analysis
     * and specific recommendations.
     *
     * @param string $text       Text to explain
     * @param string|null $lang  Language code (auto-detect if null)
     * @param string $profile    Target profile
     * @param int $intensity     Target intensity
     * @return array{before: array, after: array, recommendations: string[], summary: string}
     */
    public static function explain(
        string $text,
        ?string $lang = null,
        string $profile = 'web',
        int $intensity = 50,
    ): array {
        $lang = $lang ?? LangDetector::detect($text);

        // Analyze before
        $analyzer = new TextAnalyzer($lang);
        $beforeReport = $analyzer->analyze($text);

        // Process
        $result = self::humanize($text, $lang, $profile, $intensity);

        // Analyze after
        $afterReport = $analyzer->analyze($result->processed);

        // Build recommendations
        $recommendations = [];

        if ($beforeReport->bureaucraticRatio > 0.05) {
            $recommendations[] = 'Text contains bureaucratic language that should be simplified';
        }
        if ($beforeReport->connectorRatio > 0.3) {
            $recommendations[] = 'Too many AI-typical connectors detected';
        }
        if ($beforeReport->repetitionScore > 0.3) {
            $recommendations[] = 'Word repetition is high — consider using more synonyms';
        }
        if ($beforeReport->burstinessScore < 0.3) {
            $recommendations[] = 'Sentence lengths are too uniform — vary sentence structure';
        }
        if ($beforeReport->artificialityScore > 50) {
            $recommendations[] = 'Text has high artificiality score — humanization recommended';
        }

        $scoreChange = $beforeReport->artificialityScore - $afterReport->artificialityScore;
        $summary = sprintf(
            'Artificiality score changed from %.1f to %.1f (%s%.1f). %d changes applied.',
            $beforeReport->artificialityScore,
            $afterReport->artificialityScore,
            $scoreChange >= 0 ? '-' : '+',
            abs($scoreChange),
            count($result->changes),
        );

        return [
            'before' => $beforeReport->toArray(),
            'after' => $afterReport->toArray(),
            'recommendations' => $recommendations,
            'changes' => $result->changes,
            'change_ratio' => $result->getChangeRatio(),
            'summary' => $summary,
        ];
    }

    /**
     * Split text into chunks at paragraph boundaries.
     *
     * @param string $text
     * @param int $chunkSize
     * @return string[]
     */
    private static function splitIntoChunks(string $text, int $chunkSize): array
    {
        $paragraphs = preg_split('/\n\s*\n/', $text);
        $chunks = [];
        $current = [];
        $currentLen = 0;

        foreach ($paragraphs as $para) {
            $para = trim($para);
            if ($para === '') {
                continue;
            }
            $paraLen = mb_strlen($para);

            if ($currentLen + $paraLen > $chunkSize && !empty($current)) {
                $chunks[] = implode("\n\n", $current);
                $current = [];
                $currentLen = 0;
            }

            $current[] = $para;
            $currentLen += $paraLen;
        }

        if (!empty($current)) {
            $chunks[] = implode("\n\n", $current);
        }

        return $chunks ?: [$text];
    }
}
