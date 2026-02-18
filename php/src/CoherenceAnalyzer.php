<?php

declare(strict_types=1);

namespace TextHumanize;

/**
 * CoherenceReport — paragraph-level text coherence metrics.
 */
class CoherenceReport
{
    public function __construct(
        public float $overall = 0.0,                    // 0..1, higher = more coherent
        public int $paragraphCount = 0,
        public float $avgParagraphLength = 0.0,
        public float $paragraphLengthCv = 0.0,          // coefficient of variation
        public float $lexicalCohesion = 0.0,            // 0..1, lexical chains
        public float $transitionScore = 0.0,            // 0..1, transition quality
        public float $topicConsistency = 0.0,           // 0..1, topic consistency
        public float $sentenceOpeningDiversity = 0.0,   // 0..1
        /** @var list<string> */
        public array $issues = [],
    ) {
    }

    /**
     * Convert report to associative array.
     *
     * @return array<string, mixed>
     */
    public function toArray(): array
    {
        return [
            'overall' => $this->overall,
            'paragraph_count' => $this->paragraphCount,
            'avg_paragraph_length' => $this->avgParagraphLength,
            'paragraph_length_cv' => $this->paragraphLengthCv,
            'lexical_cohesion' => $this->lexicalCohesion,
            'transition_score' => $this->transitionScore,
            'topic_consistency' => $this->topicConsistency,
            'sentence_opening_diversity' => $this->sentenceOpeningDiversity,
            'issues' => $this->issues,
        ];
    }
}

/**
 * CoherenceAnalyzer — analyzes text coherence at paragraph level.
 *
 * Metrics: topic sentences, paragraph lengths, transition smoothness,
 * lexical chains, sentence-opening diversity.
 */
class CoherenceAnalyzer
{
    /** Transition words/phrases per language and category. */
    private const TRANSITIONS = [
        'en' => [
            'additive' => ['moreover', 'furthermore', 'additionally', 'also', 'besides',
                           'in addition', 'as well', 'not only', 'what is more'],
            'adversative' => ['however', 'nevertheless', 'nonetheless', 'on the other hand',
                              'in contrast', 'although', 'despite', 'yet', 'but', 'still',
                              'whereas', 'while', 'on the contrary'],
            'causal' => ['therefore', 'consequently', 'as a result', 'because', 'since',
                         'thus', 'hence', 'accordingly', 'due to', 'owing to', 'for this reason'],
            'sequential' => ['first', 'second', 'third', 'finally', 'then', 'next',
                             'subsequently', 'meanwhile', 'afterward', 'lastly', 'initially'],
            'exemplification' => ['for example', 'for instance', 'such as', 'namely',
                                  'specifically', 'in particular', 'to illustrate'],
            'summary' => ['in conclusion', 'to summarize', 'in summary', 'overall',
                          'in short', 'to sum up', 'ultimately', 'in essence'],
        ],
        'ru' => [
            'additive' => ['кроме того', 'помимо этого', 'также', 'более того',
                           'дополнительно', 'вдобавок', 'к тому же', 'наряду с'],
            'adversative' => ['однако', 'тем не менее', 'несмотря на', 'впрочем',
                              'с другой стороны', 'вместе с тем', 'при этом', 'напротив',
                              'хотя', 'всё же', 'зато'],
            'causal' => ['поэтому', 'следовательно', 'таким образом', 'потому что',
                         'вследствие', 'в результате', 'благодаря', 'из-за', 'ввиду'],
            'sequential' => ['во-первых', 'во-вторых', 'в-третьих', 'далее', 'затем',
                             'после этого', 'наконец', 'в заключение', 'сначала'],
            'exemplification' => ['например', 'в частности', 'а именно', 'так',
                                  'к примеру', 'в качестве примера'],
            'summary' => ['в итоге', 'подводя итог', 'в заключение', 'резюмируя',
                          'в целом', 'в общем', 'таким образом'],
        ],
        'uk' => [
            'additive' => ['крім того', 'окрім цього', 'також', 'більше того',
                           'додатково', 'до того ж', 'на додаток'],
            'adversative' => ['однак', 'проте', 'тим не менш', 'незважаючи на',
                              'з іншого боку', 'водночас', 'натомість', 'хоча'],
            'causal' => ['тому', 'отже', 'таким чином', 'тому що', 'адже',
                         'внаслідок', 'завдяки', 'через'],
            'sequential' => ['по-перше', 'по-друге', 'по-третє', 'далі', 'потім',
                             'після цього', 'нарешті', 'спочатку'],
            'exemplification' => ['наприклад', 'зокрема', 'а саме', 'як-от'],
            'summary' => ['підсумовуючи', 'загалом', 'на завершення', 'у підсумку'],
        ],
    ];

    private string $lang;

    /** @var array<string, list<string>> */
    private array $transitions;

    /** @var list<string> All transition phrases sorted by length desc (greedy matching). */
    private array $allTransitions;

    public function __construct(string $lang = 'ru')
    {
        $this->lang = $lang;
        $this->transitions = self::TRANSITIONS[$lang] ?? self::TRANSITIONS['en'] ?? [];

        $this->allTransitions = [];
        foreach ($this->transitions as $words) {
            foreach ($words as $w) {
                $this->allTransitions[] = $w;
            }
        }
        // Sort by length descending for greedy matching
        usort($this->allTransitions, static fn(string $a, string $b): int => mb_strlen($b) <=> mb_strlen($a));
    }

    /**
     * Analyze text coherence.
     */
    public function analyze(string $text): CoherenceReport
    {
        $report = new CoherenceReport();

        $paragraphs = $this->splitParagraphs($text);
        $report->paragraphCount = count($paragraphs);

        if (count($paragraphs) < 2) {
            $report->overall = 0.8; // single-paragraph text — cannot assess
            return $report;
        }

        // 1. Paragraph lengths
        $lengths = array_map(
            static fn(string $p): int => count(preg_split('/\s+/', $p, -1, PREG_SPLIT_NO_EMPTY)),
            $paragraphs,
        );

        $report->avgParagraphLength = count($lengths) > 0
            ? array_sum($lengths) / count($lengths)
            : 0.0;

        if ($report->avgParagraphLength > 0) {
            $sumSq = 0.0;
            foreach ($lengths as $l) {
                $sumSq += ($l - $report->avgParagraphLength) ** 2;
            }
            $std = sqrt($sumSq / count($lengths));
            $report->paragraphLengthCv = $std / $report->avgParagraphLength;
        } else {
            $report->paragraphLengthCv = 0.0;
        }

        // 2. Lexical cohesion (overlap between adjacent paragraphs)
        $report->lexicalCohesion = $this->lexicalCohesion($paragraphs);

        // 3. Transition words
        $report->transitionScore = $this->transitionQuality($paragraphs);

        // 4. Topic consistency
        $report->topicConsistency = $this->topicConsistency($paragraphs);

        // 5. Sentence-opening diversity
        $report->sentenceOpeningDiversity = $this->openingDiversity($text);

        // Issues
        if ($report->paragraphLengthCv < 0.15) {
            $report->issues[] = 'paragraph_uniform_length';
        }
        if ($report->paragraphLengthCv > 1.5) {
            $report->issues[] = 'paragraph_lengths_very_uneven';
        }
        if ($report->lexicalCohesion < 0.1) {
            $report->issues[] = 'low_lexical_cohesion';
        }
        if ($report->transitionScore < 0.15) {
            $report->issues[] = 'few_transitions';
        }
        if ($report->sentenceOpeningDiversity < 0.3) {
            $report->issues[] = 'repetitive_sentence_openings';
        }
        foreach ($lengths as $l) {
            if ($l > 200) {
                $report->issues[] = 'very_long_paragraphs';
                break;
            }
        }
        foreach ($lengths as $l) {
            if ($l < 10) {
                $report->issues[] = 'very_short_paragraphs';
                break;
            }
        }

        // Overall score
        $report->overall = $this->computeOverall($report);

        return $report;
    }

    /**
     * Suggest concrete coherence improvements.
     *
     * @return list<string>
     */
    public function suggestImprovements(string $text, ?CoherenceReport $report = null): array
    {
        if ($report === null) {
            $report = $this->analyze($text);
        }

        $suggestions = [];

        if (in_array('paragraph_uniform_length', $report->issues, true)) {
            $suggestions[] = sprintf(
                'Paragraph lengths are too uniform (CV=%.2f). '
                . 'Vary paragraph sizes for more natural reading rhythm.',
                $report->paragraphLengthCv,
            );
        }

        if (in_array('few_transitions', $report->issues, true)) {
            $cats = array_keys($this->transitions);
            $examples = [];
            foreach (array_slice($cats, 0, 3) as $cat) {
                $words = $this->transitions[$cat] ?? [];
                if ($words !== []) {
                    $examples[] = $cat . ': ' . implode(', ', array_slice($words, 0, 3));
                }
            }
            $suggestions[] = 'Text lacks transition words. Consider adding: ' . implode('; ', $examples);
        }

        if (in_array('low_lexical_cohesion', $report->issues, true)) {
            $suggestions[] = 'Low lexical cohesion between paragraphs. '
                . 'Reuse key terms or use pronouns to connect ideas.';
        }

        if (in_array('repetitive_sentence_openings', $report->issues, true)) {
            $suggestions[] = 'Many sentences start the same way. '
                . 'Vary openings: use adverbs, subordinate clauses, inversions.';
        }

        if (in_array('very_long_paragraphs', $report->issues, true)) {
            $suggestions[] = 'Some paragraphs exceed 200 words. '
                . 'Break them into smaller chunks for readability.';
        }

        return $suggestions;
    }

    /**
     * Convenience static method: analyze coherence and return an associative array.
     *
     * @return array<string, mixed>
     */
    public static function analyzeCoherence(string $text, string $lang = 'en'): array
    {
        $analyzer = new self($lang);
        $report = $analyzer->analyze($text);

        return [
            'overall' => $report->overall,
            'lexical_cohesion' => $report->lexicalCohesion,
            'transition_score' => $report->transitionScore,
            'topic_consistency' => $report->topicConsistency,
            'sentence_opening_diversity' => $report->sentenceOpeningDiversity,
            'paragraph_count' => $report->paragraphCount,
            'avg_paragraph_length' => $report->avgParagraphLength,
            'issues' => $report->issues,
        ];
    }

    // ─────────────────────────────────────────────────────────────
    //  Private helpers
    // ─────────────────────────────────────────────────────────────

    /**
     * Split text into paragraphs (on double newlines or indented lines).
     *
     * @return list<string>
     */
    private function splitParagraphs(string $text): array
    {
        $parts = preg_split('/\n\s*\n/', trim($text));
        $paragraphs = [];
        foreach ($parts as $p) {
            $p = trim($p);
            if ($p !== '') {
                $paragraphs[] = $p;
            }
        }
        return $paragraphs;
    }

    /**
     * Extract content words (skip short stop-words by length threshold).
     *
     * @return array<string, true>
     */
    private function extractContentWords(string $text, int $minLen = 4): array
    {
        preg_match_all('/\b\w+\b/u', mb_strtolower($text), $matches);
        $set = [];
        foreach ($matches[0] as $w) {
            if (mb_strlen($w) >= $minLen) {
                $set[$w] = true;
            }
        }
        return $set;
    }

    /**
     * Average lexical overlap (Jaccard index) between adjacent paragraphs.
     */
    private function lexicalCohesion(array $paragraphs): float
    {
        if (count($paragraphs) < 2) {
            return 1.0;
        }

        $overlaps = [];
        for ($i = 0, $n = count($paragraphs) - 1; $i < $n; $i++) {
            $wordsA = $this->extractContentWords($paragraphs[$i]);
            $wordsB = $this->extractContentWords($paragraphs[$i + 1]);

            if ($wordsA === [] || $wordsB === []) {
                $overlaps[] = 0.0;
                continue;
            }

            $intersection = array_intersect_key($wordsA, $wordsB);
            $union = $wordsA + $wordsB; // keys merge (union)
            $overlaps[] = count($intersection) / count($union);
        }

        return $overlaps !== [] ? array_sum($overlaps) / count($overlaps) : 0.0;
    }

    /**
     * Evaluate transition quality between paragraphs.
     */
    private function transitionQuality(array $paragraphs): float
    {
        if (count($paragraphs) < 2) {
            return 1.0;
        }

        $transitionCount = 0;
        /** @var array<string, true> */
        $categoriesUsed = [];

        // Starting from second paragraph
        for ($i = 1, $n = count($paragraphs); $i < $n; $i++) {
            $paraLower = mb_strtolower($paragraphs[$i]);
            $start = mb_substr($paraLower, 0, min(100, mb_strlen($paraLower)));

            foreach ($this->transitions as $cat => $words) {
                $found = false;
                foreach ($words as $word) {
                    if (mb_strpos($start, $word) !== false) {
                        $transitionCount++;
                        $categoriesUsed[$cat] = true;
                        $found = true;
                        break;
                    }
                }
                if ($found) {
                    break;
                }
            }
        }

        $presence = min($transitionCount / max(count($paragraphs) - 1, 1), 1.0);
        $diversity = count($categoriesUsed) / max(count($this->transitions), 1);

        return 0.6 * $presence + 0.4 * $diversity;
    }

    /**
     * Topic consistency: how smoothly topics change between paragraphs.
     */
    private function topicConsistency(array $paragraphs): float
    {
        if (count($paragraphs) < 3) {
            return 0.8;
        }

        // Build frequency profile (counter) for each paragraph
        $profiles = [];
        foreach ($paragraphs as $para) {
            preg_match_all('/\b\w+\b/u', mb_strtolower($para), $matches);
            $counter = [];
            foreach ($matches[0] as $w) {
                if (mb_strlen($w) >= 4) {
                    $counter[$w] = ($counter[$w] ?? 0) + 1;
                }
            }
            $profiles[] = $counter;
        }

        // Compare neighbour and skip-1 similarities
        $neighborSims = [];
        for ($i = 0, $n = count($profiles) - 1; $i < $n; $i++) {
            $neighborSims[] = self::cosineSimilarity($profiles[$i], $profiles[$i + 1]);
        }

        $skipSims = [];
        for ($i = 0, $n = count($profiles) - 2; $i < $n; $i++) {
            $skipSims[] = self::cosineSimilarity($profiles[$i], $profiles[$i + 2]);
        }

        $avgNeighbor = $neighborSims !== [] ? array_sum($neighborSims) / count($neighborSims) : 0.0;
        $avgSkip = $skipSims !== [] ? array_sum($skipSims) / count($skipSims) : 0.0;

        return min($avgNeighbor * 0.7 + $avgSkip * 0.3 + 0.2, 1.0);
    }

    /**
     * Cosine similarity of two word-frequency arrays.
     *
     * @param array<string, int> $a
     * @param array<string, int> $b
     */
    private static function cosineSimilarity(array $a, array $b): float
    {
        if ($a === [] || $b === []) {
            return 0.0;
        }

        $common = array_intersect_key($a, $b);
        $dotProduct = 0.0;
        foreach ($common as $k => $_) {
            $dotProduct += $a[$k] * $b[$k];
        }

        $magA = 0.0;
        foreach ($a as $v) {
            $magA += $v ** 2;
        }
        $magA = sqrt($magA);

        $magB = 0.0;
        foreach ($b as $v) {
            $magB += $v ** 2;
        }
        $magB = sqrt($magB);

        if ($magA == 0.0 || $magB == 0.0) {
            return 0.0;
        }

        return $dotProduct / ($magA * $magB);
    }

    /**
     * Sentence-opening diversity (Type-Token Ratio of first words).
     */
    private function openingDiversity(string $text): float
    {
        $splitter = new SentenceSplitter($this->lang);
        $sentences = $splitter->split(trim($text));

        if (count($sentences) < 3) {
            return 0.8;
        }

        $firstWords = [];
        foreach ($sentences as $s) {
            $s = trim($s);
            if ($s !== '') {
                $words = preg_split('/\s+/', $s, -1, PREG_SPLIT_NO_EMPTY);
                if ($words !== []) {
                    $firstWords[] = mb_strtolower($words[0]);
                }
            }
        }

        if (count($firstWords) < 3) {
            return 0.8;
        }

        $unique = count(array_unique($firstWords));
        $total = count($firstWords);

        return $unique / $total;
    }

    /**
     * Compute the overall coherence score.
     */
    private function computeOverall(CoherenceReport $report): float
    {
        $scores = [
            $report->lexicalCohesion * 0.25,
            $report->transitionScore * 0.25,
            $report->topicConsistency * 0.25,
            $report->sentenceOpeningDiversity * 0.15,
        ];

        // Penalty for too uniform / too uneven paragraphs
        $cv = $report->paragraphLengthCv;
        if ($cv >= 0.2 && $cv <= 0.8) {
            $paraScore = 1.0;
        } elseif ($cv < 0.2) {
            $paraScore = 0.5 + $cv * 2.5;
        } else {
            $paraScore = max(0.0, 1.0 - ($cv - 0.8) * 0.5);
        }

        $scores[] = $paraScore * 0.10;

        return min(max(array_sum($scores), 0.0), 1.0);
    }
}
