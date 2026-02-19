<?php

declare(strict_types=1);

namespace TextHumanize\Pipeline;

use TextHumanize\RandomHelper;

/**
 * SemanticParaphraser — rule-based syntactic paraphrasing.
 *
 * Transforms:
 *  1. Clause reorder (subordinate clause ↔ main clause)
 *  2. Sentence split (compound → two simple)
 *  3. Sentence merge (two short → one compound)
 *  4. Adverb / temporal fronting
 *  5. Coordination → subordination
 *  6. Conditional inversion (EN: "If you need" → "Should you need")
 *
 * All transforms are rule-based, zero ML/LLM dependency.
 */
class SemanticParaphraser
{
    /** @var array{original: string, transformed: string, kind: string}[] */
    public array $changes = [];

    private string $lang;
    private float $intensity;
    private RandomHelper $rng;

    /** @var array<int, array{pattern: string, replacement: callable}> */
    private array $clausePatterns;

    /** @var string[] */
    private array $splitConjunctions;

    /** @var string[] */
    private array $mergeConnectors;

    public function __construct(string $lang, float $intensity, RandomHelper $rng)
    {
        $this->lang = $lang;
        $this->intensity = max(0.0, min(1.0, $intensity));
        $this->rng = $rng;
        $this->clausePatterns = self::getClausePatterns($lang);
        $this->splitConjunctions = self::getSplitConjunctions($lang);
        $this->mergeConnectors = self::getMergeConnectors($lang);
    }

    /**
     * Process text, paraphrasing sentences while preserving paragraph structure.
     */
    public function process(string $text): string
    {
        $this->changes = [];
        if (mb_strlen(trim($text)) < 20) {
            return $text;
        }

        $lines = explode("\n", $text);
        $result = [];
        foreach ($lines as $line) {
            // Skip lines containing segmenter placeholders
            if (str_contains($line, "\x00THZ_") || trim($line) === '') {
                $result[] = $line;
            } else {
                $result[] = $this->processParagraph($line);
            }
        }
        return implode("\n", $result);
    }

    private function processParagraph(string $para): string
    {
        // Simple sentence splitting by ". "
        $sentences = $this->splitSentences($para);
        if (count($sentences) === 0) {
            return $para;
        }

        $maxTransforms = max(1, (int)(count($sentences) * $this->intensity));
        $nTransforms = 0;
        $result = [];

        foreach ($sentences as $i => $sent) {
            if ($nTransforms >= $maxTransforms) {
                $result[] = $sent;
                continue;
            }
            if ($this->rng->random() > $this->intensity) {
                $result[] = $sent;
                continue;
            }

            [$transformed, $kind] = $this->tryTransform($sent);
            if ($transformed !== $sent) {
                $result[] = $transformed;
                $nTransforms++;
                $this->changes[] = [
                    'original' => $sent,
                    'transformed' => $transformed,
                    'kind' => $kind,
                ];
            } else {
                $result[] = $sent;
            }
        }

        // Try merge pass
        if ($nTransforms < $maxTransforms && count($result) >= 3) {
            $result = $this->tryMergePass($result);
        }

        return implode(' ', $result);
    }

    /**
     * @return array{string, string} [transformed, kind]
     */
    private function tryTransform(string $sent): array
    {
        $transforms = [
            [$this, 'tryClauseReorder'],
            [$this, 'trySentenceSplit'],
            [$this, 'tryFronting'],
            [$this, 'tryConditionalInversion'],
            [$this, 'tryCoordToSubord'],
        ];

        // Shuffle transforms
        $order = range(0, count($transforms) - 1);
        $this->rng->shuffle($order);

        foreach ($order as $idx) {
            [$transformed, $kind] = $transforms[$idx]($sent);
            if ($transformed !== $sent && mb_strlen(trim($transformed)) > 5) {
                return [$transformed, $kind];
            }
        }

        return [$sent, 'no_change'];
    }

    // ──────────── 1. Clause reorder ────────────

    /**
     * @return array{string, string}
     */
    private function tryClauseReorder(string $sent): array
    {
        $bare = rtrim($sent, '.!?');
        $punct = '.';
        if ($sent !== '' && in_array(mb_substr($sent, -1), ['.', '!', '?'], true)) {
            $punct = mb_substr($sent, -1);
        }

        foreach ($this->clausePatterns as $cp) {
            if (preg_match($cp['pattern'], $bare, $m)) {
                $new = ($cp['replacement'])($m) . $punct;
                $new = mb_strtoupper(mb_substr($new, 0, 1)) . mb_substr($new, 1);
                return [$new, 'clause_reorder'];
            }
        }
        return [$sent, ''];
    }

    // ──────────── 2. Sentence split ────────────

    /**
     * @return array{string, string}
     */
    private function trySentenceSplit(string $sent): array
    {
        if (count(explode(' ', $sent)) < 12) {
            return [$sent, ''];
        }

        $lower = mb_strtolower($sent);
        foreach ($this->splitConjunctions as $conj) {
            $pos = mb_strpos($lower, mb_strtolower($conj));
            if ($pos !== false) {
                $part1 = trim(mb_substr($sent, 0, $pos));
                $part2 = trim(mb_substr($sent, $pos + mb_strlen($conj)));

                if (count(explode(' ', $part1)) >= 4 && count(explode(' ', $part2)) >= 4) {
                    if (!in_array(mb_substr($part1, -1), ['.', '!', '?'], true)) {
                        $part1 .= '.';
                    }
                    if ($part2 !== '' && mb_strtolower(mb_substr($part2, 0, 1)) === mb_substr($part2, 0, 1)) {
                        $part2 = mb_strtoupper(mb_substr($part2, 0, 1)) . mb_substr($part2, 1);
                    }
                    return ["$part1 $part2", 'sentence_split'];
                }
            }
        }

        return [$sent, ''];
    }

    // ──────────── 3. Fronting ────────────

    /**
     * @return array{string, string}
     */
    private function tryFronting(string $sent): array
    {
        $words = explode(' ', rtrim($sent, '.!?'));
        if (count($words) < 5) {
            return [$sent, ''];
        }
        $punct = '.';
        if ($sent !== '' && in_array(mb_substr($sent, -1), ['.', '!', '?'], true)) {
            $punct = mb_substr($sent, -1);
        }

        if (in_array($this->lang, ['ru', 'uk'], true)) {
            $temporalRu = ['сегодня', 'вчера', 'завтра', 'потом', 'сначала',
                           'наконец', 'недавно', 'раньше', 'обычно', 'иногда'];
            $temporalUk = ['сьогодні', 'вчора', 'завтра', 'потім', 'спочатку',
                           'нарешті', 'нещодавно', 'раніше', 'зазвичай', 'іноді'];
            $temporal = $this->lang === 'ru' ? $temporalRu : $temporalUk;
            $lastWord = mb_strtolower(rtrim(end($words), '.,;:!?'));
            if (in_array($lastWord, $temporal, true)) {
                $front = mb_strtoupper(mb_substr($lastWord, 0, 1)) . mb_substr($lastWord, 1);
                array_pop($words);
                $rest = implode(' ', $words);
                $rest = mb_strtolower(mb_substr($rest, 0, 1)) . mb_substr($rest, 1);
                return ["$front $rest$punct", 'temporal_fronting'];
            }
        }

        return [$sent, ''];
    }

    // ──────────── 4. Conditional inversion (EN) ────────────

    /**
     * @return array{string, string}
     */
    private function tryConditionalInversion(string $sent): array
    {
        if ($this->lang !== 'en') {
            return [$sent, ''];
        }

        if (preg_match(
            '/^If\s+(?:you|we|they)\s+(need|want|have|require|decide|choose)\b(.+?),\s*(.+)$/iu',
            $sent,
            $m
        )) {
            $verb = $m[1];
            $restCond = trim($m[2]);
            $mainClause = trim($m[3]);
            $result = "Should you $verb $restCond, $mainClause";
            $result = mb_strtoupper(mb_substr($result, 0, 1)) . mb_substr($result, 1);
            return [$result, 'conditional_inversion'];
        }

        return [$sent, ''];
    }

    // ──────────── 5. Coordination → Subordination ────────────

    /**
     * @return array{string, string}
     */
    private function tryCoordToSubord(string $sent): array
    {
        $bare = rtrim($sent, '.!?');
        $punct = '.';
        if ($sent !== '' && in_array(mb_substr($sent, -1), ['.', '!', '?'], true)) {
            $punct = mb_substr($sent, -1);
        }

        if ($this->lang === 'en') {
            if (preg_match('/^(.+?),?\s+and\s+(.+)$/iu', $bare, $m)) {
                $part1 = trim($m[1]);
                $part2 = trim($m[2]);
                if (count(explode(' ', $part1)) >= 4 && count(explode(' ', $part2)) >= 4) {
                    if (mb_strtoupper(mb_substr($part2, 0, 1)) === mb_substr($part2, 0, 1)) {
                        $part2 = mb_strtolower(mb_substr($part2, 0, 1)) . mb_substr($part2, 1);
                    }
                    $connectors = [
                        "$part1; moreover, $part2",
                        "$part1. Additionally, " . mb_strtoupper(mb_substr($part2, 0, 1)) . mb_substr($part2, 1),
                    ];
                    $chosen = $this->rng->choice($connectors);
                    return ["$chosen$punct", 'coord_to_subord'];
                }
            }
        } elseif (in_array($this->lang, ['ru', 'uk'], true)) {
            $conj = $this->lang === 'ru' ? ' и ' : ' і ';
            $parts = explode($conj, $bare, 2);
            if (count($parts) === 2) {
                $p1 = trim($parts[0]);
                $p2 = trim($parts[1]);
                if (count(explode(' ', $p1)) >= 4 && count(explode(' ', $p2)) >= 4) {
                    if (mb_strtoupper(mb_substr($p2, 0, 1)) === mb_substr($p2, 0, 1)) {
                        $p2 = mb_strtolower(mb_substr($p2, 0, 1)) . mb_substr($p2, 1);
                    }
                    $connsRu = [
                        "$p1, при этом $p2",
                        "$p1. Вместе с тем " . mb_strtoupper(mb_substr($p2, 0, 1)) . mb_substr($p2, 1),
                    ];
                    $connsUk = [
                        "$p1, при цьому $p2",
                        "$p1. Водночас " . mb_strtoupper(mb_substr($p2, 0, 1)) . mb_substr($p2, 1),
                    ];
                    $conns = $this->lang === 'ru' ? $connsRu : $connsUk;
                    $chosen = $this->rng->choice($conns);
                    return ["$chosen$punct", 'coord_to_subord'];
                }
            }
        }

        return [$sent, ''];
    }

    // ──────────── Merge pass ────────────

    /**
     * @param string[] $sentences
     * @return string[]
     */
    private function tryMergePass(array $sentences): array
    {
        if (empty($this->mergeConnectors) || count($sentences) < 3) {
            return $sentences;
        }

        $result = $sentences;
        for ($i = 0; $i < count($result) - 1; $i++) {
            $s1 = $result[$i];
            $s2 = $result[$i + 1];
            if ($s1 !== '' && $s2 !== ''
                && count(explode(' ', $s1)) <= 8
                && count(explode(' ', $s2)) <= 8
                && $this->rng->random() < $this->intensity * 0.3) {

                $first = rtrim(rtrim($s1), '.!?');
                $second = trim($s2);
                if ($second !== '' && mb_strtoupper(mb_substr($second, 0, 1)) === mb_substr($second, 0, 1)) {
                    $second = mb_strtolower(mb_substr($second, 0, 1)) . mb_substr($second, 1);
                }

                $conn = $this->rng->choice($this->mergeConnectors);
                $merged = "$first, $conn $second";
                $result[$i] = $merged;
                $result[$i + 1] = '';

                $this->changes[] = [
                    'original' => "$s1 | $s2",
                    'transformed' => $merged,
                    'kind' => 'sentence_merge',
                ];
                break;
            }
        }

        return array_values(array_filter($result, fn(string $s): bool => trim($s) !== ''));
    }

    // ──────────── Helpers ────────────

    /**
     * @return string[]
     */
    private function splitSentences(string $text): array
    {
        // Simple sentence split by ". " or "! " or "? "
        $sentences = preg_split('/(?<=[.!?])\s+/', trim($text));
        return $sentences !== false ? array_filter($sentences, fn(string $s): bool => trim($s) !== '') : [$text];
    }

    /**
     * @return array<int, array{pattern: string, replacement: callable}>
     */
    private static function getClausePatterns(string $lang): array
    {
        return match ($lang) {
            'en' => [
                ['pattern' => '/^(Although|Though|Even though|While|Whereas)\s+(.+?),\s+(.+)$/iu',
                 'replacement' => fn(array $m) => trim($m[3], '.!? ') . ', ' . mb_strtolower($m[1]) . ' ' . trim($m[2])],
                ['pattern' => '/^(Because|Since|As)\s+(.+?),\s+(.+)$/iu',
                 'replacement' => fn(array $m) => trim($m[3], '.!? ') . ' ' . mb_strtolower($m[1]) . ' ' . trim($m[2])],
                ['pattern' => '/^(If)\s+(.+?),\s+(.+)$/iu',
                 'replacement' => fn(array $m) => trim($m[3], '.!? ') . ' if ' . trim($m[2])],
                ['pattern' => '/^(When|Whenever|Once)\s+(.+?),\s+(.+)$/iu',
                 'replacement' => fn(array $m) => trim($m[3], '.!? ') . ' ' . mb_strtolower($m[1]) . ' ' . trim($m[2])],
                ['pattern' => '/^(Before|After|Until)\s+(.+?),\s+(.+)$/iu',
                 'replacement' => fn(array $m) => trim($m[3], '.!? ') . ' ' . mb_strtolower($m[1]) . ' ' . trim($m[2])],
            ],
            'ru' => [
                ['pattern' => '/^(Хотя|Несмотря на то,? что)\s+(.+?),\s+(.+)$/iu',
                 'replacement' => fn(array $m) => trim($m[3], '.!? ') . ', ' . mb_strtolower($m[1]) . ' ' . trim($m[2])],
                ['pattern' => '/^(Поскольку|Так как|Потому что)\s+(.+?),\s+(.+)$/iu',
                 'replacement' => fn(array $m) => trim($m[3], '.!? ') . ', ' . mb_strtolower($m[1]) . ' ' . trim($m[2])],
                ['pattern' => '/^(Если)\s+(.+?),\s+(?:то\s+)?(.+)$/iu',
                 'replacement' => fn(array $m) => trim($m[3], '.!? ') . ', если ' . trim($m[2])],
                ['pattern' => '/^(Когда|Пока|После того как)\s+(.+?),\s+(.+)$/iu',
                 'replacement' => fn(array $m) => trim($m[3], '.!? ') . ', ' . mb_strtolower($m[1]) . ' ' . trim($m[2])],
            ],
            'uk' => [
                ['pattern' => '/^(Хоча|Незважаючи на те,? що)\s+(.+?),\s+(.+)$/iu',
                 'replacement' => fn(array $m) => trim($m[3], '.!? ') . ', ' . mb_strtolower($m[1]) . ' ' . trim($m[2])],
                ['pattern' => '/^(Оскільки|Тому що)\s+(.+?),\s+(.+)$/iu',
                 'replacement' => fn(array $m) => trim($m[3], '.!? ') . ', ' . mb_strtolower($m[1]) . ' ' . trim($m[2])],
                ['pattern' => '/^(Якщо)\s+(.+?),\s+(?:то\s+)?(.+)$/iu',
                 'replacement' => fn(array $m) => trim($m[3], '.!? ') . ', якщо ' . trim($m[2])],
                ['pattern' => '/^(Коли|Після того як|Перш ніж)\s+(.+?),\s+(.+)$/iu',
                 'replacement' => fn(array $m) => trim($m[3], '.!? ') . ', ' . mb_strtolower($m[1]) . ' ' . trim($m[2])],
            ],
            'de' => [
                ['pattern' => '/^(Obwohl|Obgleich|Obschon)\s+(.+?),\s+(.+)$/iu',
                 'replacement' => fn(array $m) => trim($m[3], '.!? ') . ', ' . mb_strtolower($m[1]) . ' ' . trim($m[2])],
                ['pattern' => '/^(Weil|Da)\s+(.+?),\s+(.+)$/iu',
                 'replacement' => fn(array $m) => trim($m[3], '.!? ') . ', ' . mb_strtolower($m[1]) . ' ' . trim($m[2])],
                ['pattern' => '/^(Wenn|Falls)\s+(.+?),\s+(.+)$/iu',
                 'replacement' => fn(array $m) => trim($m[3], '.!? ') . ', ' . mb_strtolower($m[1]) . ' ' . trim($m[2])],
            ],
            default => [],
        };
    }

    /**
     * @return string[]
     */
    private static function getSplitConjunctions(string $lang): array
    {
        return match ($lang) {
            'en' => [', and ', ', but ', ', so ', ', yet ', '; however, ', '; moreover, '],
            'ru' => [', и ', ', но ', ', а ', ', поэтому ', '; однако '],
            'uk' => [', і ', ', але ', ', а ', ', тому ', '; однак '],
            'de' => [', und ', ', aber ', ', doch ', '; jedoch '],
            default => [],
        };
    }

    /**
     * @return string[]
     */
    private static function getMergeConnectors(string $lang): array
    {
        return match ($lang) {
            'en' => ['and', 'while also', 'and at the same time', 'moreover'],
            'ru' => ['и при этом', 'причём', 'а также', 'и вместе с тем'],
            'uk' => ['і при цьому', 'причому', 'а також', 'і водночас'],
            'de' => ['und dabei', 'und zugleich', 'wobei'],
            default => [],
        };
    }
}
