<?php

declare(strict_types=1);

namespace TextHumanize;

/**
 * Result of a paraphrase operation.
 */
class ParaphraseResult
{
    /**
     * @param list<string> $changes  Descriptions of applied transformations.
     * @param float        $confidence 0..1 confidence in correctness.
     */
    public function __construct(
        public readonly string $original,
        public readonly string $paraphrased,
        public readonly array $changes,
        public readonly float $confidence,
    ) {}
}

/**
 * Syntactic paraphraser (no ML).
 *
 * Transforms sentences while preserving meaning:
 * - Clause reordering
 * - Active ↔ Passive (EN)
 * - Sentence splitting / merging
 * - Nominalization ↔ Verbalization
 * - Adverb fronting
 */
class Paraphraser
{
    // ═══════════════════════════════════════════════════════════════
    //  Passive voice pattern (EN)
    // ═══════════════════════════════════════════════════════════════

    /**
     * "The book was written by John" → passive-by pattern.
     */
    private const EN_PASSIVE_BY_PATTERN =
        '/^(The\s+)?(.+?)\s+(was|were|is|are|has been|have been|had been)\s+'
        . '(\w+ed)\s+by\s+(.+?)([.!?]?)$/iu';

    // ═══════════════════════════════════════════════════════════════
    //  Clause-swap patterns per language
    // ═══════════════════════════════════════════════════════════════

    /**
     * Each entry: [regex, capture-group layout].
     *
     * Layout types:
     *   'std3' — groups: 1=conjunction, 2=subordinate, 3=main
     *   'if4'  — groups: 1=conjunction, 2=subordinate, 3=(optional "то"/"то "), 4=main
     *
     * @var array<string, list<array{string, string, string}>>
     */
    private const CLAUSE_SWAP = [
        'en' => [
            ['/^(Although|Though|Even though|While|Whereas)\s+(.+?),\s+(.+)$/iu', 'std3', ''],
            ['/^(Because|Since|As)\s+(.+?),\s+(.+)$/iu',                         'std3', ''],
            ['/^(If)\s+(.+?),\s+(.+)$/iu',                                       'std3', 'if'],
            ['/^(When|Whenever)\s+(.+?),\s+(.+)$/iu',                            'std3', ''],
        ],
        'ru' => [
            ['/^(Хотя|Несмотря на то что|Несмотря на то, что)\s+(.+?),\s+(.+)$/iu', 'std3', ''],
            ['/^(Потому что|Поскольку|Так как)\s+(.+?),\s+(.+)$/iu',                'std3', ''],
            ['/^(Если)\s+(.+?),\s+(то\s+)?(.+)$/iu',                               'if4',  'если'],
            ['/^(Когда)\s+(.+?),\s+(.+)$/iu',                                      'std3', ''],
        ],
        'uk' => [
            ['/^(Хоча|Незважаючи на те що)\s+(.+?),\s+(.+)$/iu', 'std3', ''],
            ['/^(Тому що|Оскільки)\s+(.+?),\s+(.+)$/iu',         'std3', ''],
            ['/^(Якщо)\s+(.+?),\s+(то\s+)?(.+)$/iu',             'if4',  'якщо'],
        ],
    ];

    // ═══════════════════════════════════════════════════════════════
    //  Nominalization / Verbalization maps
    // ═══════════════════════════════════════════════════════════════

    /** @var array<string, array<string, string>> verb → noun */
    private const NOMINALIZATION_MAP = [
        'en' => [
            'decide' => 'decision', 'conclude' => 'conclusion',
            'develop' => 'development', 'improve' => 'improvement',
            'analyze' => 'analysis', 'investigate' => 'investigation',
            'implement' => 'implementation', 'evaluate' => 'evaluation',
            'consider' => 'consideration', 'recommend' => 'recommendation',
            'observe' => 'observation', 'explain' => 'explanation',
            'describe' => 'description', 'suggest' => 'suggestion',
            'discuss' => 'discussion', 'produce' => 'production',
            'reduce' => 'reduction', 'introduce' => 'introduction',
            'transform' => 'transformation', 'create' => 'creation',
            'demonstrate' => 'demonstration', 'participate' => 'participation',
        ],
        'ru' => [
            'решать' => 'решение', 'развивать' => 'развитие',
            'анализировать' => 'анализ', 'улучшать' => 'улучшение',
            'исследовать' => 'исследование', 'внедрять' => 'внедрение',
            'оценивать' => 'оценка', 'рекомендовать' => 'рекомендация',
            'обсуждать' => 'обсуждение', 'производить' => 'производство',
            'сокращать' => 'сокращение', 'создавать' => 'создание',
            'описывать' => 'описание', 'объяснять' => 'объяснение',
            'предлагать' => 'предложение', 'участвовать' => 'участие',
        ],
    ];

    // ═══════════════════════════════════════════════════════════════
    //  Sentence-split conjunctions & merge connectors
    // ═══════════════════════════════════════════════════════════════

    /** @var array<string, list<string>> */
    private const SPLIT_CONJUNCTIONS = [
        'en' => [', and ', ', but ', ', so ', ', yet ', '; however, ', '; moreover, ',
                 '; therefore, ', '; furthermore, '],
        'ru' => [', и ', ', но ', ', а ', ', поэтому ', '; однако ', '; кроме того, ',
                 '; следовательно, '],
        'uk' => [', і ', ', але ', ', а ', ', тому ', '; однак ', '; крім того, '],
    ];

    /** @var array<string, list<string>> */
    private const MERGE_CONNECTORS = [
        'en' => ['moreover', 'furthermore', 'in addition', 'also', 'besides'],
        'ru' => ['кроме того', 'помимо этого', 'также', 'к тому же', 'и вдобавок'],
        'uk' => ['крім того', 'також', 'до того ж', 'на додаток'],
    ];

    // ---------------------------------------------------------------

    private string $lang;
    private RandomHelper $rng;
    private float $intensity;

    /** @var list<array{string, string, string}> */
    private array $clausePatterns;
    /** @var list<string> */
    private array $splitConj;
    /** @var list<string> */
    private array $mergeConn;
    /** @var array<string, string> */
    private array $nomMap;
    /** @var array<string, string> noun → verb (reversed) */
    private array $verbMap;

    /**
     * @param string   $lang      Language code (en, ru, uk, …).
     * @param int|null $seed      RNG seed for reproducibility.
     * @param float    $intensity 0..1, fraction of sentences to transform.
     */
    public function __construct(
        string $lang = 'en',
        ?int $seed = null,
        float $intensity = 0.5,
    ) {
        $this->lang = $lang;
        $this->rng = new RandomHelper($seed);
        $this->intensity = $intensity;

        $this->clausePatterns = self::CLAUSE_SWAP[$lang] ?? [];
        $this->splitConj = self::SPLIT_CONJUNCTIONS[$lang] ?? [];
        $this->mergeConn = self::MERGE_CONNECTORS[$lang] ?? [];
        $this->nomMap = self::NOMINALIZATION_MAP[$lang] ?? [];
        $this->verbMap = array_flip($this->nomMap);
    }

    // ===============================================================
    //  Public API
    // ===============================================================

    /**
     * Paraphrase a full text.
     */
    public function paraphrase(string $text): ParaphraseResult
    {
        $sentences = $this->splitSentences($text);
        $changes = [];
        $resultSentences = [];
        $totalConfidence = 0.0;
        $nChanged = 0;

        foreach ($sentences as $i => $sent) {
            if ($this->rng->random() > $this->intensity) {
                $resultSentences[] = $sent;
                continue;
            }

            [$transformed, $changeType, $conf] = $this->tryTransform($sent, $i, $sentences);

            if ($transformed !== $sent) {
                $resultSentences[] = $transformed;
                $changes[] = $changeType;
                $totalConfidence += $conf;
                $nChanged++;
            } else {
                $resultSentences[] = $sent;
            }
        }

        $resultText = implode(' ', $resultSentences);
        $avgConf = $nChanged > 0 ? $totalConfidence / $nChanged : 1.0;

        return new ParaphraseResult(
            original: $text,
            paraphrased: $resultText,
            changes: $changes,
            confidence: $avgConf,
        );
    }

    /**
     * Paraphrase a single sentence.
     *
     * @return array{string, string} [paraphrased sentence, change type]
     */
    public function paraphraseSentence(string $sentence): array
    {
        [$result, $changeType] = $this->tryTransform($sentence, 0, [$sentence]);
        return [$result, $changeType];
    }

    /**
     * Convenience static method (mirrors the Python paraphrase_text() function).
     */
    public static function paraphraseText(
        string $text,
        string $lang = 'en',
        float $intensity = 0.5,
        ?int $seed = null,
    ): string {
        $p = new self(lang: $lang, seed: $seed, intensity: $intensity);
        return $p->paraphrase($text)->paraphrased;
    }

    // ===============================================================
    //  Transformation dispatcher
    // ===============================================================

    /**
     * Try to transform a sentence. Returns first successful transformation.
     *
     * @param list<string> $allSents
     * @return array{string, string, float} [result, change_description, confidence]
     */
    private function tryTransform(string $sent, int $idx, array $allSents): array
    {
        /** @var list<callable(string): array{string, string, float}> */
        $transformations = [
            fn(string $s): array => $this->tryClauseSwap($s),
            fn(string $s): array => $this->tryPassiveToActive($s),
            fn(string $s): array => $this->trySentenceSplit($s),
            fn(string $s): array => $this->tryFronting($s),
            fn(string $s): array => $this->tryNominalizationSwap($s),
        ];

        $this->rng->shuffle($transformations);

        foreach ($transformations as $fn) {
            [$result, $desc, $conf] = $fn($sent);
            if ($result !== $sent) {
                return [$result, $desc, $conf];
            }
        }

        return [$sent, 'no_change', 1.0];
    }

    // ===============================================================
    //  Individual transformations
    // ===============================================================

    /**
     * Clause reordering: "Although X, Y" → "Y, although X".
     *
     * @return array{string, string, float}
     */
    private function tryClauseSwap(string $sent): array
    {
        $stripped = rtrim($sent, '.!?');
        $punct = ($sent !== '' && str_contains('.!?', mb_substr($sent, -1))) ? mb_substr($sent, -1) : '.';

        foreach ($this->clausePatterns as [$pattern, $layout, $extra]) {
            if (!preg_match($pattern, $stripped, $m)) {
                continue;
            }

            try {
                if ($layout === 'if4') {
                    // groups: 1=conjunction, 2=subordinate, 3=optional "то ", 4=main
                    $conj = $extra !== '' ? $extra : mb_strtolower($m[1]);
                    $main = $m[4];
                    $sub = $m[2];
                    $newSent = $main . ', ' . $conj . ' ' . $sub . $punct;
                } else {
                    // std3: groups 1=conjunction, 2=subordinate, 3=main
                    $conj = mb_strtolower($m[1]);
                    $main = $m[3];
                    $sub = $m[2];
                    $newSent = $main . ', ' . $conj . ' ' . $sub . $punct;
                }

                // Capitalize first letter
                $newSent = mb_strtoupper(mb_substr($newSent, 0, 1)) . mb_substr($newSent, 1);
                return [$newSent, 'clause_reorder', 0.9];
            } catch (\Throwable) {
                continue;
            }
        }

        return [$sent, '', 0.0];
    }

    /**
     * Passive → Active (English only).
     *
     * "The book was written by John" → "John wrote the book."
     *
     * @return array{string, string, float}
     */
    private function tryPassiveToActive(string $sent): array
    {
        if ($this->lang !== 'en') {
            return [$sent, '', 0.0];
        }

        if (!preg_match(self::EN_PASSIVE_BY_PATTERN, trim($sent), $m)) {
            return [$sent, '', 0.0];
        }

        $obj = trim($m[2]);
        $verbPast = $m[4];
        $subj = trim($m[5]);
        $punct = $m[6] !== '' ? $m[6] : '.';

        $active = $subj . ' ' . $verbPast . ' the ' . mb_strtolower($obj) . $punct;
        $active = mb_strtoupper(mb_substr($active, 0, 1)) . mb_substr($active, 1);

        return [$active, 'passive_to_active', 0.7];
    }

    /**
     * Split a long sentence into two at a conjunction.
     *
     * @return array{string, string, float}
     */
    private function trySentenceSplit(string $sent): array
    {
        if (count(explode(' ', $sent)) < 12) {
            return [$sent, '', 0.0];
        }

        $lowerSent = mb_strtolower($sent);

        foreach ($this->splitConj as $conj) {
            $pos = mb_strpos($lowerSent, $conj);
            if ($pos === false) {
                continue;
            }

            $part1 = trim(mb_substr($sent, 0, $pos));
            $part2 = trim(mb_substr($sent, $pos + mb_strlen($conj)));

            if (count(explode(' ', $part1)) < 4 || count(explode(' ', $part2)) < 4) {
                continue;
            }

            // Ensure part1 ends with punctuation
            if ($part1 !== '' && !str_contains('.!?', mb_substr($part1, -1))) {
                $part1 .= '.';
            }
            // Capitalize part2
            if ($part2 !== '') {
                $part2 = mb_strtoupper(mb_substr($part2, 0, 1)) . mb_substr($part2, 1);
            }

            return [$part1 . ' ' . $part2, 'sentence_split', 0.75];
        }

        return [$sent, '', 0.0];
    }

    /**
     * Adverb fronting: move a trailing adverb to the front.
     *
     * "She completed the task quickly" → "Quickly, she completed the task"
     *
     * @return array{string, string, float}
     */
    private function tryFronting(string $sent): array
    {
        $stripped = rtrim($sent, '.!?');
        $punct = ($sent !== '' && str_contains('.!?', mb_substr($sent, -1))) ? mb_substr($sent, -1) : '.';
        $words = preg_split('/\s+/u', $stripped, -1, PREG_SPLIT_NO_EMPTY);

        if ($words === false || count($words) < 5) {
            return [$sent, '', 0.0];
        }

        // EN: move trailing -ly adverb to front
        if ($this->lang === 'en') {
            $lastWord = mb_strtolower(end($words));
            if (mb_strlen($lastWord) > 4 && str_ends_with($lastWord, 'ly')) {
                $front = mb_strtoupper(mb_substr($lastWord, 0, 1)) . mb_substr($lastWord, 1);
                array_pop($words);
                $rest = implode(' ', $words);
                $rest = mb_strtolower(mb_substr($rest, 0, 1)) . mb_substr($rest, 1);
                return [$front . ', ' . $rest . $punct, 'adverb_fronting', 0.8];
            }
        }

        // RU: move trailing adverb (ending in -но, -ки, -ло) to front
        if ($this->lang === 'ru') {
            $last = mb_strtolower(end($words));
            if (str_ends_with($last, 'но') || str_ends_with($last, 'ки') || str_ends_with($last, 'ло')) {
                $front = mb_strtoupper(mb_substr($last, 0, 1)) . mb_substr($last, 1);
                array_pop($words);
                $rest = implode(' ', $words);
                $rest = mb_strtolower(mb_substr($rest, 0, 1)) . mb_substr($rest, 1);
                return [$front . ' ' . $rest . $punct, 'adverb_fronting', 0.7];
            }
        }

        return [$sent, '', 0.0];
    }

    /**
     * Swap a verb for its nominalized form, or vice versa.
     *
     * @return array{string, string, float}
     */
    private function tryNominalizationSwap(string $sent): array
    {
        $words = preg_split('/\s+/u', $sent, -1, PREG_SPLIT_NO_EMPTY);

        if ($words === false || count($words) < 4) {
            return [$sent, '', 0.0];
        }

        foreach ($words as $i => $word) {
            $wLower = mb_strtolower(rtrim($word, '.,;:!?'));
            $punctSuffix = mb_substr($word, mb_strlen($wLower));

            // verb → noun
            if (isset($this->nomMap[$wLower])) {
                $noun = $this->nomMap[$wLower];
                if (ctype_upper(mb_substr($word, 0, 1))) {
                    $noun = mb_strtoupper(mb_substr($noun, 0, 1)) . mb_substr($noun, 1);
                }
                $words[$i] = $noun . $punctSuffix;
                return [implode(' ', $words), 'nominalization', 0.6];
            }

            // noun → verb
            if (isset($this->verbMap[$wLower])) {
                $verb = $this->verbMap[$wLower];
                if (ctype_upper(mb_substr($word, 0, 1))) {
                    $verb = mb_strtoupper(mb_substr($verb, 0, 1)) . mb_substr($verb, 1);
                }
                $words[$i] = $verb . $punctSuffix;
                return [implode(' ', $words), 'verbalization', 0.6];
            }
        }

        return [$sent, '', 0.0];
    }

    // ===============================================================
    //  Sentence splitting helper
    // ===============================================================

    /**
     * Basic sentence splitting (delegates to SentenceSplitter when available).
     *
     * @return list<string>
     */
    private function splitSentences(string $text): array
    {
        $splitter = new SentenceSplitter($this->lang);
        return $splitter->split($text);
    }
}
