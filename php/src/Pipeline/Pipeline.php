<?php

declare(strict_types=1);

namespace TextHumanize\Pipeline;

use TextHumanize\AnalysisReport;
use TextHumanize\HumanizeOptions;
use TextHumanize\HumanizeResult;
use TextHumanize\Lang\Registry;
use TextHumanize\LangDetector;
use TextHumanize\Profiles;
use TextHumanize\RandomHelper;
use TextHumanize\TextAnalyzer;

/**
 * Pipeline — the 10-stage text humanization pipeline.
 *
 * Stages:
 *  1. Segmentation (protect code, URLs, etc.)
 *  2. Typography normalization
 *  3. Debureaucratization (deep languages only)
 *  4. Structure diversification (deep languages only)
 *  5. Repetition reduction (deep languages only)
 *  6. Liveliness injection (deep languages only)
 *  7. Universal processing (all languages)
 *  8. Style naturalization (all languages)
 *  9. Validation
 * 10. Segment restoration
 */
class Pipeline
{
    /** @var array<string, callable[]> Plugins to run before a stage */
    private static array $pluginsBefore = [];

    /** @var array<string, callable[]> Plugins to run after a stage */
    private static array $pluginsAfter = [];

    private const STAGE_NAMES = [
        'segmentation', 'typography', 'debureaucratize',
        'structure', 'repetitions', 'liveliness',
        'universal', 'naturalize', 'validation', 'restore',
    ];

    /**
     * Register a custom plugin for a pipeline stage.
     *
     * @param callable $plugin  fn(string $text, string $lang, string $profile, int $intensity): string
     * @param string|null $before  Stage to insert before
     * @param string|null $after   Stage to insert after
     */
    public static function registerPlugin(
        callable $plugin,
        ?string $before = null,
        ?string $after = null,
    ): void {
        if ($before === null && $after === null) {
            throw new \InvalidArgumentException("Specify 'before' or 'after' stage name.");
        }
        $target = $before ?? $after;
        if (!in_array($target, self::STAGE_NAMES, true)) {
            throw new \InvalidArgumentException("Unknown stage: {$target}");
        }
        if ($before !== null) {
            self::$pluginsBefore[$before][] = $plugin;
        } else {
            self::$pluginsAfter[$after][] = $plugin;
        }
    }

    /**
     * Remove all registered plugins.
     */
    public static function clearPlugins(): void
    {
        self::$pluginsBefore = [];
        self::$pluginsAfter = [];
    }

    /**
     * Run plugins for a given stage.
     */
    private static function runPlugins(string $stage, string $text, string $lang, string $profile, int $intensity, bool $isBefore): string
    {
        $registry = $isBefore ? self::$pluginsBefore : self::$pluginsAfter;
        foreach ($registry[$stage] ?? [] as $plugin) {
            $text = $plugin($text, $lang, $profile, $intensity);
        }
        return $text;
    }
    /**
     * Run the full humanization pipeline.
     */
    public static function run(string $text, HumanizeOptions $options): HumanizeResult
    {
        $text = trim($text);
        if ($text === '') {
            return new HumanizeResult(
                original: '',
                processed: '',
                lang: $options->lang ?? 'en',
                profile: $options->profile,
                changes: [],
            );
        }

        // Detect language if not specified
        $lang = $options->lang ?? LangDetector::detect($text);
        $hasDeep = Registry::hasDeepSupport($lang);
        $langPack = Registry::get($lang);
        $profile = Profiles::get($options->profile);

        // Initialize seeded RNG
        $rng = new RandomHelper($options->seed);

        $changes = [];
        $processed = $text;

        // --- Stage 1: Segmentation ---
        $processed = self::runPlugins('segmentation', $processed, $lang, $options->profile, $options->intensity, true);
        $segmenter = new Segmenter();
        $segmented = $segmenter->segment(
            $processed,
            $options->preserve['keywords'] ?? [],
            $options->preserve['brands'] ?? [],
        );
        $processed = $segmented->text;
        $processed = self::runPlugins('segmentation', $processed, $lang, $options->profile, $options->intensity, false);

        // --- Stage 2: Typography normalization ---
        $processed = self::runPlugins('typography', $processed, $lang, $options->profile, $options->intensity, true);
        $typoNorm = new TypographyNormalizer();
        [$processed, $typoChanges] = $typoNorm->normalize($processed, $lang);
        if (!empty($typoChanges)) {
            $changes[] = ['stage' => 'typography', 'changes' => $typoChanges];
        }
        $processed = self::runPlugins('typography', $processed, $lang, $options->profile, $options->intensity, false);

        // --- Stages 3-6: Deep language processing ---
        if ($hasDeep) {
            // Stage 3: Debureaucratization
            $processed = self::runPlugins('debureaucratize', $processed, $lang, $options->profile, $options->intensity, true);
            if (Profiles::shouldApply('debureaucratize', $profile, $options->intensity)) {
                $debureaucratizer = new Debureaucratizer();
                $before = $processed;
                $processed = $debureaucratizer->process($processed, $langPack, $profile, $options->intensity, $rng);
                if ($processed !== $before) {
                    $changes[] = ['stage' => 'debureaucratize'];
                }
            }
            $processed = self::runPlugins('debureaucratize', $processed, $lang, $options->profile, $options->intensity, false);

            // Stage 4: Structure diversification
            $processed = self::runPlugins('structure', $processed, $lang, $options->profile, $options->intensity, true);
            if (Profiles::shouldApply('diversify_structure', $profile, $options->intensity)) {
                $diversifier = new StructureDiversifier();
                $before = $processed;
                $processed = $diversifier->process($processed, $langPack, $profile, $options->intensity, $rng);
                if ($processed !== $before) {
                    $changes[] = ['stage' => 'structure'];
                }
            }
            $processed = self::runPlugins('structure', $processed, $lang, $options->profile, $options->intensity, false);

            // Stage 5: Repetition reduction
            $processed = self::runPlugins('repetitions', $processed, $lang, $options->profile, $options->intensity, true);
            if (Profiles::shouldApply('reduce_repetitions', $profile, $options->intensity)) {
                $repetitionReducer = new RepetitionReducer();
                $before = $processed;
                $processed = $repetitionReducer->process($processed, $langPack, $profile, $options->intensity, $rng);
                if ($processed !== $before) {
                    $changes[] = ['stage' => 'repetitions'];
                }
            }
            $processed = self::runPlugins('repetitions', $processed, $lang, $options->profile, $options->intensity, false);

            // Stage 6: Liveliness injection
            $processed = self::runPlugins('liveliness', $processed, $lang, $options->profile, $options->intensity, true);
            if (Profiles::shouldApply('inject_liveliness', $profile, $options->intensity)) {
                $livelinessInjector = new LivelinessInjector();
                $before = $processed;
                $processed = $livelinessInjector->process($processed, $langPack, $profile, $options->intensity, $rng);
                if ($processed !== $before) {
                    $changes[] = ['stage' => 'liveliness'];
                }
            }
            $processed = self::runPlugins('liveliness', $processed, $lang, $options->profile, $options->intensity, false);
        }

        // --- Stage 7: Universal processing ---
        $processed = self::runPlugins('universal', $processed, $lang, $options->profile, $options->intensity, true);
        $universalProcessor = new UniversalProcessor();
        $before = $processed;
        $processed = $universalProcessor->process($processed, $profile, $options->intensity, $rng);
        if ($processed !== $before) {
            $changes[] = ['stage' => 'universal'];
        }
        $processed = self::runPlugins('universal', $processed, $lang, $options->profile, $options->intensity, false);

        // --- Stage 8: Style naturalization ---
        $processed = self::runPlugins('naturalize', $processed, $lang, $options->profile, $options->intensity, true);
        $naturalizer = new TextNaturalizer();
        $before = $processed;
        $processed = $naturalizer->process($processed, $lang, $profile, $options->intensity, $rng);
        if ($processed !== $before) {
            $changes[] = ['stage' => 'naturalize'];
        }
        $processed = self::runPlugins('naturalize', $processed, $lang, $options->profile, $options->intensity, false);

        // --- Stage 9: Validation ---
        $processed = self::runPlugins('validation', $processed, $lang, $options->profile, $options->intensity, true);
        $validator = new Validator();
        $validation = $validator->validate($text, $processed, $options);

        if ($validation->shouldRollback) {
            // Partial rollback, keep only typography and universal
            $processed = $text;
            $segmented2 = $segmenter->segment(
                $processed,
                $options->preserve['keywords'] ?? [],
                $options->preserve['brands'] ?? [],
            );
            $processed = $segmented2->text;
            [$processed, $_] = $typoNorm->normalize($processed, $lang);
            $processed = $universalProcessor->process($processed, $profile, $options->intensity, $rng);
            $processed = $segmented2->restore($processed);
            $changes = [['stage' => 'rollback', 'reason' => $validation->errors]];
        } else {
            // --- Stage 10: Restore segments ---
            $processed = self::runPlugins('restore', $processed, $lang, $options->profile, $options->intensity, true);
            $processed = $segmented->restore($processed);
            $processed = self::runPlugins('restore', $processed, $lang, $options->profile, $options->intensity, false);
        }
        $processed = self::runPlugins('validation', $processed, $lang, $options->profile, $options->intensity, false);

        if (!$validation->isValid && !$validation->shouldRollback) {
            $changes[] = ['stage' => 'validation', 'warnings' => $validation->warnings, 'errors' => $validation->errors];
        }

        // Apply constraints
        $processed = self::applyConstraints($processed, $options);

        return new HumanizeResult(
            original: $text,
            processed: $processed,
            lang: $lang,
            profile: $options->profile,
            changes: $changes,
        );
    }

    /**
     * Apply output constraints (max_length, min_length).
     */
    private static function applyConstraints(string $text, HumanizeOptions $options): string
    {
        $maxLen = $options->constraints['max_length'] ?? null;
        $minLen = $options->constraints['min_length'] ?? null;

        if ($maxLen !== null && mb_strlen($text) > $maxLen) {
            // Truncate at last sentence boundary before maxLen
            $truncated = mb_substr($text, 0, $maxLen);
            $lastDot = mb_strrpos($truncated, '.');
            if ($lastDot !== false && $lastDot > $maxLen * 0.5) {
                $text = mb_substr($truncated, 0, $lastDot + 1);
            } else {
                $text = $truncated;
            }
        }

        return $text;
    }
}
