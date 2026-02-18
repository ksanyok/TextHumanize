<?php

declare(strict_types=1);

namespace TextHumanize;

/**
 * Content Spinner — rewriting and remixing text.
 *
 * Generates unique text versions:
 * - Spintax format {variant1|variant2|variant3}
 * - Multi-level spinning (word/phrase/sentence/paragraph)
 * - Uniqueness control
 */
class SpinResult
{
    public function __construct(
        public readonly string $original,
        public readonly string $spun,
        public readonly string $spintax,
        public readonly float $uniqueness,
        public readonly int $variantsCount,
    ) {}
}

class ContentSpinner
{
    private RandomHelper $rng;
    private float $intensity;
    private string $lang;
    /** @var array<string, list<string>> */
    private array $synonyms;

    /**
     * Synonym dictionaries for spinning (EN and RU).
     *
     * @var array<string, array<string, list<string>>>
     */
    private const SPIN_SYNONYMS = [
        'en' => [
            // Verbs
            'use' => ['utilize', 'employ', 'apply', 'leverage', 'make use of'],
            'make' => ['create', 'produce', 'generate', 'build', 'construct'],
            'get' => ['obtain', 'acquire', 'receive', 'gain', 'secure'],
            'show' => ['demonstrate', 'display', 'reveal', 'illustrate', 'present'],
            'help' => ['assist', 'support', 'aid', 'facilitate', 'enable'],
            'need' => ['require', 'necessitate', 'demand', 'call for'],
            'think' => ['believe', 'consider', 'regard', 'suppose', 'reckon'],
            'give' => ['provide', 'offer', 'supply', 'deliver', 'present'],
            'find' => ['discover', 'locate', 'identify', 'uncover', 'detect'],
            'know' => ['understand', 'recognize', 'realize', 'comprehend'],
            'want' => ['desire', 'wish', 'seek', 'aim for'],
            'try' => ['attempt', 'endeavor', 'strive', 'seek to'],
            'start' => ['begin', 'commence', 'initiate', 'launch'],
            'end' => ['finish', 'conclude', 'complete', 'terminate'],
            'change' => ['modify', 'alter', 'adjust', 'transform'],
            'improve' => ['enhance', 'upgrade', 'boost', 'optimize'],
            'reduce' => ['decrease', 'diminish', 'lower', 'minimize'],
            'increase' => ['raise', 'elevate', 'boost', 'amplify'],
            'include' => ['encompass', 'incorporate', 'comprise', 'contain'],
            'develop' => ['create', 'build', 'design', 'establish'],
            // Adjectives
            'important' => ['crucial', 'vital', 'essential', 'significant', 'critical'],
            'good' => ['excellent', 'outstanding', 'great', 'superior', 'fine'],
            'bad' => ['poor', 'inferior', 'substandard', 'inadequate'],
            'big' => ['large', 'substantial', 'considerable', 'significant'],
            'small' => ['tiny', 'minor', 'slight', 'modest', 'compact'],
            'new' => ['novel', 'recent', 'fresh', 'modern', 'latest'],
            'old' => ['previous', 'former', 'traditional', 'established'],
            'fast' => ['rapid', 'quick', 'swift', 'speedy', 'prompt'],
            'easy' => ['simple', 'straightforward', 'effortless', 'uncomplicated'],
            'hard' => ['difficult', 'challenging', 'complex', 'demanding'],
            'clear' => ['obvious', 'evident', 'apparent', 'transparent'],
            'different' => ['various', 'diverse', 'distinct', 'alternative'],
            // Adverbs
            'also' => ['additionally', 'furthermore', 'moreover', 'besides'],
            'however' => ['nevertheless', 'nonetheless', 'yet', 'still'],
            'therefore' => ['consequently', 'thus', 'hence', 'accordingly'],
            'often' => ['frequently', 'regularly', 'commonly', 'repeatedly'],
            'usually' => ['typically', 'generally', 'normally', 'commonly'],
            'quickly' => ['rapidly', 'swiftly', 'promptly', 'speedily'],
            'very' => ['extremely', 'highly', 'remarkably', 'exceptionally'],
            // Connectors
            'because' => ['since', 'as', 'due to the fact that', 'given that'],
            'but' => ['however', 'yet', 'nevertheless', 'on the other hand'],
            'and' => ['as well as', 'along with', 'in addition to', 'plus'],
        ],
        'ru' => [
            // Глаголы
            'использовать' => ['применять', 'задействовать', 'употреблять'],
            'делать' => ['выполнять', 'осуществлять', 'производить', 'совершать'],
            'получать' => ['обретать', 'приобретать', 'добывать'],
            'показывать' => ['демонстрировать', 'отображать', 'иллюстрировать'],
            'помогать' => ['содействовать', 'способствовать', 'поддерживать'],
            'начинать' => ['приступать', 'стартовать', 'инициировать'],
            'заканчивать' => ['завершать', 'оканчивать', 'финализировать'],
            'менять' => ['изменять', 'модифицировать', 'трансформировать'],
            'улучшать' => ['совершенствовать', 'оптимизировать', 'повышать'],
            'увеличивать' => ['повышать', 'наращивать', 'усиливать'],
            'уменьшать' => ['сокращать', 'снижать', 'минимизировать'],
            'создавать' => ['формировать', 'разрабатывать', 'конструировать'],
            'думать' => ['полагать', 'считать', 'рассуждать'],
            // Прилагательные
            'важный' => ['существенный', 'значимый', 'ключевой', 'принципиальный'],
            'хороший' => ['отличный', 'прекрасный', 'качественный', 'достойный'],
            'плохой' => ['скверный', 'некачественный', 'неудачный'],
            'большой' => ['крупный', 'масштабный', 'значительный', 'солидный'],
            'маленький' => ['небольшой', 'компактный', 'незначительный'],
            'новый' => ['современный', 'свежий', 'актуальный', 'недавний'],
            'быстрый' => ['стремительный', 'оперативный', 'скоростной'],
            'разный' => ['различный', 'разнообразный', 'многообразный'],
            // Наречия
            'также' => ['кроме того', 'помимо этого', 'вдобавок'],
            'однако' => ['тем не менее', 'впрочем', 'вместе с тем'],
            'поэтому' => ['следовательно', 'таким образом', 'вследствие этого'],
            'часто' => ['нередко', 'зачастую', 'регулярно'],
            'обычно' => ['как правило', 'зачастую', 'в большинстве случаев'],
            'очень' => ['чрезвычайно', 'крайне', 'весьма', 'исключительно'],
        ],
    ];

    /**
     * @param string   $lang      Language code (en, ru, etc.).
     * @param int|null $seed      RNG seed for reproducibility.
     * @param float    $intensity 0..1, fraction of words to replace.
     */
    public function __construct(
        string $lang = 'en',
        ?int $seed = null,
        float $intensity = 0.5,
    ) {
        $this->lang = $lang;
        $this->rng = new RandomHelper($seed);
        $this->intensity = $intensity;
        $this->synonyms = self::SPIN_SYNONYMS[$lang] ?? [];
    }

    /**
     * Spin text — create a unique version.
     */
    public function spin(string $text): SpinResult
    {
        $spintax = $this->buildSpintax($text);
        $spun = $this->resolveSpintaxInternal($spintax);
        $uniqueness = self::calculateUniqueness($text, $spun);
        $variants = self::countVariants($spintax);

        return new SpinResult(
            original: $text,
            spun: $spun,
            spintax: $spintax,
            uniqueness: $uniqueness,
            variantsCount: $variants,
        );
    }

    /**
     * Generate spintax format from plain text.
     */
    public function generateSpintax(string $text): string
    {
        return $this->buildSpintax($text);
    }

    /**
     * Resolve spintax into one random variant.
     *
     * @param string $spintax Text in {option1|option2|...} format.
     */
    public function resolveSpintax(string $spintax): string
    {
        return $this->resolveSpintaxInternal($spintax);
    }

    /**
     * Generate several unique text variants.
     *
     * @param string $text  Source text.
     * @param int    $count Number of variants to produce.
     * @return list<string>
     */
    public function generateVariants(string $text, int $count = 5): array
    {
        $spintax = $this->buildSpintax($text);
        $variants = [];
        $seen = [];

        $maxAttempts = $count * 3;
        for ($i = 0; $i < $maxAttempts; $i++) {
            if (count($variants) >= $count) {
                break;
            }
            $variant = $this->resolveSpintaxInternal($spintax);
            if (!in_array($variant, $seen, true)) {
                $seen[] = $variant;
                $variants[] = $variant;
            }
        }

        return $variants;
    }

    // ─── Convenience static methods ──────────────────────────

    /**
     * Spin text — create a unique version (convenience wrapper).
     */
    public static function spinText(
        string $text,
        string $lang = 'en',
        float $intensity = 0.5,
        ?int $seed = null,
    ): string {
        $spinner = new self(lang: $lang, seed: $seed, intensity: $intensity);
        return $spinner->spin($text)->spun;
    }

    /**
     * Generate several unique text variants (convenience wrapper).
     *
     * @return list<string>
     */
    public static function spinVariants(
        string $text,
        int $count = 5,
        string $lang = 'en',
        float $intensity = 0.5,
        ?int $seed = null,
    ): array {
        $spinner = new self(lang: $lang, seed: $seed, intensity: $intensity);
        return $spinner->generateVariants($text, $count);
    }

    // ─── Private ─────────────────────────────────────────────

    /**
     * Build spintax from plain text.
     */
    private function buildSpintax(string $text): string
    {
        $words = preg_split('/\s+/', $text, -1, PREG_SPLIT_NO_EMPTY);
        if ($words === false || $words === []) {
            return $text;
        }

        $result = [];

        foreach ($words as $word) {
            // Strip punctuation to get the clean word
            $clean = preg_replace('/^[.,;:!?\'"()\[\]{}]+|[.,;:!?\'"()\[\]{}]+$/', '', $word);
            if ($clean === null || $clean === '') {
                $result[] = $word;
                continue;
            }

            $pos = mb_strpos($word, $clean);
            $prefix = $pos !== false ? mb_substr($word, 0, $pos) : '';
            $suffix = $pos !== false ? mb_substr($word, $pos + mb_strlen($clean)) : '';

            // Look up synonyms
            $lower = mb_strtolower($clean);
            $syns = $this->synonyms[$lower] ?? [];

            if ($syns === [] || $this->rng->random() > $this->intensity) {
                $result[] = $word;
                continue;
            }

            // Build spintax variants
            $variants = [$clean];
            $used = array_slice($syns, 0, 4); // max 4 synonyms
            foreach ($used as $syn) {
                // Match synonym form (simple passthrough — no morphology module in PHP yet)
                $matched = $this->findSynonymForm($clean, $syn);
                // Preserve casing
                if (mb_strtoupper(mb_substr($clean, 0, 1)) === mb_substr($clean, 0, 1)
                    && mb_strtolower(mb_substr($clean, 0, 1)) !== mb_substr($clean, 0, 1)
                ) {
                    $matched = mb_strtoupper(mb_substr($matched, 0, 1)) . mb_substr($matched, 1);
                }
                if (mb_strtoupper($clean) === $clean && mb_strlen($clean) > 1) {
                    $matched = mb_strtoupper($matched);
                }
                $variants[] = $matched;
            }

            // De-duplicate while preserving order
            $unique = [];
            foreach ($variants as $v) {
                if (!in_array($v, $unique, true)) {
                    $unique[] = $v;
                }
            }

            if (count($unique) > 1) {
                $spintaxWord = '{' . implode('|', $unique) . '}';
                $result[] = $prefix . $spintaxWord . $suffix;
            } else {
                $result[] = $word;
            }
        }

        return implode(' ', $result);
    }

    /**
     * Resolve spintax by randomly choosing from each {option|...} group.
     */
    private function resolveSpintaxInternal(string $spintax): string
    {
        $rng = $this->rng;
        $result = $spintax;
        $maxDepth = 5;

        for ($d = 0; $d < $maxDepth; $d++) {
            $newResult = preg_replace_callback(
                '/\{([^{}]+)\}/',
                function (array $m) use ($rng): string {
                    $options = explode('|', $m[1]);
                    return (string) $rng->choice($options);
                },
                $result,
            );

            if ($newResult === null || $newResult === $result) {
                break;
            }
            $result = $newResult;
        }

        return $result;
    }

    /**
     * Calculate uniqueness (1 − similarity) between original and spun text.
     */
    private static function calculateUniqueness(string $original, string $spun): float
    {
        $origWords = preg_split('/\s+/', mb_strtolower($original), -1, PREG_SPLIT_NO_EMPTY) ?: [];
        $spunWords = preg_split('/\s+/', mb_strtolower($spun), -1, PREG_SPLIT_NO_EMPTY) ?: [];

        if ($origWords === []) {
            return 1.0;
        }

        $matches = 0;
        $minLen = min(count($origWords), count($spunWords));
        for ($i = 0; $i < $minLen; $i++) {
            if ($origWords[$i] === $spunWords[$i]) {
                $matches++;
            }
        }

        $maxLen = max(count($origWords), count($spunWords));
        return 1.0 - $matches / $maxLen;
    }

    /**
     * Count the number of possible variants from a spintax string.
     */
    private static function countVariants(string $spintax): int
    {
        if (preg_match_all('/\{([^{}]+)\}/', $spintax, $groups) === 0) {
            return 1;
        }

        $count = 1;
        foreach ($groups[1] as $group) {
            $options = explode('|', $group);
            $count *= count($options);
            if ($count > 1_000_000) {
                return 1_000_000; // Cap
            }
        }

        return $count;
    }

    /**
     * Find the appropriate synonym form matching the original word.
     *
     * Stub: returns the synonym as-is. Replace with a full morphology
     * engine when one is available in the PHP port.
     */
    private function findSynonymForm(string $originalWord, string $synonymLemma): string
    {
        // No morphology module ported to PHP yet — return lemma unchanged.
        return $synonymLemma;
    }
}
