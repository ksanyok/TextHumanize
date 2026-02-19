<?php

declare(strict_types=1);

namespace TextHumanize\Pipeline;

use TextHumanize\Profiles;
use TextHumanize\RandomHelper;

/**
 * TextNaturalizer — KEY MODULE for bypassing AI text detectors.
 * 
 */
class TextNaturalizer
{
    private string $lang;
    private array $profile;
    private int $intensity;
    private RandomHelper $rng;
    public array $changes = [];

    // AI-overused words per language → replacement lists
    private const AI_WORD_REPLACEMENTS = [
        'en' => [
            'utilize' => ['use', 'apply', 'employ'],
            'utilizes' => ['uses', 'applies'],
            'utilized' => ['used', 'applied'],
            'implement' => ['do', 'carry out', 'set up'],
            'facilitate' => ['help', 'enable', 'support'],
            'comprehensive' => ['full', 'complete', 'thorough', 'broad'],
            'significant' => ['big', 'major', 'notable', 'key'],
            'demonstrate' => ['show', 'prove', 'reveal'],
            'subsequently' => ['then', 'later', 'next'],
            'furthermore' => ['also', 'plus', 'and'],
            'consequently' => ['so', 'thus', 'as a result'],
            'nevertheless' => ['still', 'even so', 'yet'],
            'additionally' => ['also', 'plus', 'on top of that'],
            'crucial' => ['key', 'vital', 'important'],
            'pivotal' => ['key', 'central', 'important'],
            'paramount' => ['key', 'top', 'critical'],
            'leverage' => ['use', 'take advantage of'],
            'delve' => ['explore', 'dig into', 'look at'],
            'intricate' => ['complex', 'detailed', 'involved'],
            'robust' => ['strong', 'solid', 'reliable'],
            'streamline' => ['simplify', 'speed up', 'optimize'],
            'synergy' => ['teamwork', 'cooperation', 'combo'],
            'paradigm' => ['model', 'pattern', 'framework'],
            'holistic' => ['complete', 'overall', 'full'],
            'multifaceted' => ['complex', 'varied', 'diverse'],
            'nuanced' => ['subtle', 'detailed', 'fine'],
            'underscore' => ['highlight', 'stress', 'emphasize'],
            'landscape' => ['field', 'area', 'scene'],
            'endeavor' => ['effort', 'attempt', 'try'],
            'meticulous' => ['careful', 'precise', 'thorough'],
        ],
        'ru' => [
            'осуществлять' => ['делать', 'проводить', 'выполнять'],
            'функционирование' => ['работа', 'действие'],
            'обеспечивает' => ['даёт', 'создаёт', 'позволяет'],
            'непосредственно' => ['прямо', 'напрямую'],
            'соответствующий' => ['нужный', 'подходящий'],
            'значительный' => ['большой', 'заметный', 'немалый'],
            'чрезвычайно' => ['очень', 'крайне', 'невероятно'],
            'целесообразно' => ['стоит', 'лучше', 'разумно'],
            'представляет' => ['это', 'выглядит как'],
            'существенный' => ['важный', 'серьёзный', 'большой'],
        ],
    ];

    // AI-characteristic phrases per language
    private const AI_PHRASE_PATTERNS = [
        'en' => [
            'it is important to note' => ['notably', 'worth noting', 'keep in mind'],
            'it should be noted that' => ['note that', 'keep in mind'],
            'it is worth mentioning' => ['also', 'notably'],
            'plays a crucial role' => ['matters', 'is key', 'is important'],
            'in today\'s world' => ['today', 'now', 'these days'],
            'in today\'s digital age' => ['today', 'now'],
            'the fact that' => ['that'],
            'a wide range of' => ['many', 'various', 'lots of'],
            'in order to' => ['to'],
            'due to the fact that' => ['because', 'since'],
            'has the potential to' => ['can', 'could', 'might'],
            'it goes without saying' => ['clearly', 'obviously'],
            'at the end of the day' => ['ultimately', 'in the end'],
            'serve as a testament to' => ['show', 'prove'],
        ],
        'ru' => [
            'необходимо отметить' => ['стоит сказать', 'важно', 'заметим'],
            'следует отметить' => ['стоит сказать', 'заметим'],
            'представляет собой' => ['это', '— это'],
            'в настоящее время' => ['сейчас', 'теперь'],
            'в конечном итоге' => ['в итоге', 'в конце концов'],
            'играет ключевую роль' => ['важен', 'важна', 'ключевой'],
            'на сегодняшний день' => ['сейчас', 'сегодня'],
            'в первую очередь' => ['прежде всего', 'сначала'],
            'в целом и общем' => ['в целом', 'вообще'],
            'что касается' => ['насчёт', 'по поводу', 'о'],
            'тот факт что' => ['то что', 'что'],
        ],
    ];

    // Perplexity boosters per language
    private const PERPLEXITY_BOOSTERS = [
        'en' => [
            'hedges' => ['probably', 'I think', 'seems like', 'I suppose', 'maybe',
                'arguably', 'in a way', 'sort of', 'kind of', 'I\'d say'],
            'discourse_markers' => ['well', 'honestly', 'actually', 'look',
                'listen', 'right', 'sure', 'okay'],
            'parenthetical' => ['(though not always)', '(at least in theory)',
                '(or so it seems)', '(to be fair)', '(for the most part)'],
            'rhetorical_questions' => ['But why does this matter?',
                'So what does this tell us?', 'But is it really that simple?'],
            'fragments' => ['Not always.', 'Fair enough.', 'True.',
                'Makes sense.', 'Hard to say.', 'Depends.'],
        ],
        'ru' => [
            'hedges' => ['наверное', 'думаю', 'похоже', 'пожалуй', 'возможно',
                'скорее всего', 'в каком-то смысле', 'по-моему'],
            'discourse_markers' => ['ну', 'слушайте', 'вот', 'знаете',
                'понимаете', 'смотрите', 'так вот'],
            'parenthetical' => ['(хотя не всегда)', '(по крайней мере в теории)',
                '(или так кажется)', '(если честно)'],
            'rhetorical_questions' => ['Но почему это важно?',
                'И что это нам даёт?', 'Но так ли всё просто?'],
            'fragments' => ['Не всегда.', 'Трудно сказать.', 'Верно.',
                'Логично.', 'Зависит от ситуации.'],
        ],
    ];

    // English contractions
    private const CONTRACTIONS = [
        'do not' => "don't", 'does not' => "doesn't",
        'did not' => "didn't", 'is not' => "isn't",
        'are not' => "aren't", 'was not' => "wasn't",
        'were not' => "weren't", 'have not' => "haven't",
        'has not' => "hasn't", 'had not' => "hadn't",
        'will not' => "won't", 'would not' => "wouldn't",
        'could not' => "couldn't", 'should not' => "shouldn't",
        'cannot' => "can't", 'can not' => "can't",
        'must not' => "mustn't", 'shall not' => "shan't",
        'it is' => "it's", 'it has' => "it's",
        'that is' => "that's", 'there is' => "there's",
        'here is' => "here's", 'what is' => "what's",
        'who is' => "who's", 'how is' => "how's",
        'I am' => "I'm", 'I have' => "I've",
        'I will' => "I'll", 'I would' => "I'd",
        'we are' => "we're", 'we have' => "we've",
        'we will' => "we'll", 'they are' => "they're",
        'they have' => "they've", 'they will' => "they'll",
        'you are' => "you're", 'you have' => "you've",
        'you will' => "you'll", 'let us' => "let's",
    ];

    public function __construct()
    {
        // No-op: all state is injected via process()
    }

    /**
     * Process text — apply style naturalization.
     */
    public function process(string $text, string $lang, array $profile, int $intensity, RandomHelper $rng): string
    {
        $this->lang = $lang;
        $this->profile = $profile;
        $this->intensity = $intensity;
        $this->rng = $rng;
        $this->changes = [];

        $prob = $this->intensity / 100.0;

        // Phrase/word replacements — regex-based, safe on full text
        $text = $this->replaceAiPhrases($text, $prob);
        $text = $this->replaceAiWords($text, $prob);

        // Burstiness & perplexity use splitSentences + implode(' ') which
        // destroys newline structure.  Process per-line to preserve structure.
        $text = $this->perParagraph($text, 'injectBurstiness', $prob);
        $text = $this->perParagraph($text, 'boostPerplexity', $prob);

        // Contractions — regex, safe
        $text = $this->applyContractions($text, $prob);

        return $text;
    }

    /**
     * Apply a processing method to each non-empty line independently.
     *
     * Preserves paragraph / list structure.
     */
    private function perParagraph(string $text, string $method, float $prob): string
    {
        $lines = explode("\n", $text);
        $result = [];
        foreach ($lines as $line) {
            if (trim($line) === '' || str_contains($line, "\x00THZ_")) {
                $result[] = $line;
            } else {
                $result[] = $this->$method($line, $prob);
            }
        }
        return implode("\n", $result);
    }

    /**
     * Replace AI-characteristic phrases.
     */
    private function replaceAiPhrases(string $text, float $prob): string
    {
        $phrases = self::AI_PHRASE_PATTERNS[$this->lang] ?? self::AI_PHRASE_PATTERNS['en'] ?? [];

        foreach ($phrases as $phrase => $replacements) {
            if (!Profiles::coinFlip($prob, $this->rng)) {
                continue;
            }

            $pattern = '/' . preg_quote($phrase, '/') . '/ui';
            if (preg_match($pattern, $text, $match, PREG_OFFSET_CAPTURE)) {
                $replacement = $this->rng->choice($replacements);
                $replacement = self::matchCase($match[0][0], $replacement);
                $text = substr_replace($text, $replacement, $match[0][1], strlen($match[0][0]));
                $this->changes[] = [
                    'type' => 'naturalize_phrase',
                    'from' => $match[0][0],
                    'to' => $replacement,
                ];
            }
        }

        return $text;
    }

    /**
     * Replace AI-overused words.
     */
    private function replaceAiWords(string $text, float $prob): string
    {
        $words = self::AI_WORD_REPLACEMENTS[$this->lang] ?? self::AI_WORD_REPLACEMENTS['en'] ?? [];
        $wordCount = count(preg_split('/\s+/', trim($text)));
        $maxReplacements = max(5, intdiv($wordCount, 20));
        $replaced = 0;

        foreach ($words as $word => $replacements) {
            if ($replaced >= $maxReplacements) {
                break;
            }

            if (!Profiles::coinFlip($prob, $this->rng)) {
                continue;
            }

            $pattern = '/\b' . preg_quote($word, '/') . '\b/ui';
            if (preg_match($pattern, $text, $match, PREG_OFFSET_CAPTURE)) {
                // Context guard: check if replacement is safe
                if (!ContextGuard::isSafe($word, $text, (int) $match[0][1], (int) $match[0][1] + strlen($match[0][0]))) {
                    continue;
                }

                $replacement = $this->rng->choice($replacements);
                $replacement = self::matchCase($match[0][0], $replacement);
                $text = substr_replace($text, $replacement, $match[0][1], strlen($match[0][0]));
                $this->changes[] = [
                    'type' => 'naturalize_word',
                    'from' => $match[0][0],
                    'to' => $replacement,
                ];
                $replaced++;
            }
        }

        return $text;
    }

    /**
     * Inject burstiness — vary sentence lengths.
     */
    private function injectBurstiness(string $text, float $prob): string
    {
        $sentences = preg_split('/(?<=[.!?…])\s+/u', trim($text));
        if (count($sentences) < 3) {
            return $text;
        }

        $lengths = array_map(fn(string $s): int => count(preg_split('/\s+/', trim($s))), $sentences);
        $avg = array_sum($lengths) / count($lengths);

        if ($avg <= 0) {
            return $text;
        }

        $variance = 0;
        foreach ($lengths as $len) {
            $variance += ($len - $avg) ** 2;
        }
        $variance /= count($lengths);
        $cv = sqrt($variance) / $avg;

        if ($cv >= 0.6) {
            return $text; // Already bursty enough
        }

        $result = [];
        $changed = false;

        // Split long sentences
        foreach ($sentences as $sentence) {
            $wc = count(preg_split('/\s+/', trim($sentence)));
            if ($wc > 25 && Profiles::coinFlip($prob, $this->rng)) {
                $parts = $this->smartSplit($sentence);
                if ($parts !== null) {
                    $result = array_merge($result, $parts);
                    $this->changes[] = ['type' => 'naturalize_burstiness_split'];
                    $changed = true;
                    continue;
                }
            }
            $result[] = $sentence;
        }

        // Join short sentences
        $joined = [];
        $i = 0;
        while ($i < count($result)) {
            $wc = count(preg_split('/\s+/', trim($result[$i])));
            if ($wc <= 6 && $i + 1 < count($result)
                && count(preg_split('/\s+/', trim($result[$i + 1]))) <= 8
                && Profiles::coinFlip($prob * 0.5, $this->rng)
            ) {
                $first = preg_replace('/[.!?]+$/', '', trim($result[$i]));
                $second = $result[$i + 1];
                $second = mb_strtolower(mb_substr($second, 0, 1)) . mb_substr($second, 1);
                $joined[] = "$first, and $second";
                $this->changes[] = ['type' => 'naturalize_burstiness_join'];
                $changed = true;
                $i += 2;
            } else {
                $joined[] = $result[$i];
                $i++;
            }
        }

        return $changed ? implode(' ', $joined) : $text;
    }

    /**
     * Smart split — find best split point (semicolon > comma+conj > comma).
     * @return string[]|null
     */
    private function smartSplit(string $sentence): ?array
    {
        $words = preg_split('/\s+/', trim($sentence));
        $mid = intdiv(count($words), 2);
        $bestPos = null;
        $bestDist = PHP_INT_MAX;
        $bestPriority = 0;

        // Priority 1: semicolons
        if (preg_match_all('/;/u', $sentence, $matches, PREG_OFFSET_CAPTURE)) {
            foreach ($matches[0] as $m) {
                $pos = $m[1];
                $beforeWords = count(preg_split('/\s+/', trim(mb_substr($sentence, 0, $pos))));
                $afterWords = count($words) - $beforeWords;
                if ($beforeWords >= 5 && $afterWords >= 5) {
                    $dist = abs($beforeWords - $mid);
                    if ($bestPriority < 3 || $dist < $bestDist) {
                        $bestDist = $dist;
                        $bestPos = $pos;
                        $bestPriority = 3;
                    }
                }
            }
        }

        // Priority 2: commas
        if ($bestPriority < 2 && preg_match_all('/,/u', $sentence, $matches, PREG_OFFSET_CAPTURE)) {
            foreach ($matches[0] as $m) {
                $pos = $m[1];
                $beforeWords = count(preg_split('/\s+/', trim(mb_substr($sentence, 0, $pos))));
                $afterWords = count($words) - $beforeWords;
                if ($beforeWords >= 5 && $afterWords >= 5) {
                    $dist = abs($beforeWords - $mid);
                    if ($dist < $bestDist) {
                        $bestDist = $dist;
                        $bestPos = $pos;
                        $bestPriority = 2;
                    }
                }
            }
        }

        if ($bestPos === null) {
            return null;
        }

        $first = trim(mb_substr($sentence, 0, $bestPos));
        $second = trim(mb_substr($sentence, $bestPos + 1));

        if (!preg_match('/[.!?]$/', $first)) {
            $first .= '.';
        }

        if (mb_strlen($second) > 0) {
            $second = mb_strtoupper(mb_substr($second, 0, 1)) . mb_substr($second, 1);
        }

        return [$first, $second];
    }

    /**
     * Boost perplexity — insert hedging, discourse markers, etc.
     * Only for chat/web profiles.
     */
    private function boostPerplexity(string $text, float $prob): string
    {
        $profileName = '';
        foreach (Profiles::PROFILES as $name => $p) {
            if ($p === $this->profile) {
                $profileName = $name;
                break;
            }
        }

        if (!in_array($profileName, ['chat', 'web'])) {
            return $text;
        }

        $boosters = self::PERPLEXITY_BOOSTERS[$this->lang] ?? self::PERPLEXITY_BOOSTERS['en'] ?? [];
        if (empty($boosters)) {
            return $text;
        }

        $sentences = preg_split('/(?<=[.!?…])\s+/u', trim($text));
        $maxInserts = max(1, intdiv(count($sentences), 6));
        $inserts = 0;
        $changed = false;

        for ($i = 2; $i < count($sentences) && $inserts < $maxInserts; $i++) {
            // Discourse marker at start of sentence (safer than after word 1 —
            // avoids splitting multi-word constructions like "Поки що")
            if (Profiles::coinFlip($prob * 0.3, $this->rng) && !empty($boosters['discourse_markers'])) {
                $marker = $this->rng->choice($boosters['discourse_markers']);
                $capMarker = mb_strtoupper(mb_substr($marker, 0, 1)) . mb_substr($marker, 1);
                $sent = $sentences[$i];
                $lowered = mb_strtolower(mb_substr($sent, 0, 1)) . mb_substr($sent, 1);
                $sentences[$i] = $capMarker . ', ' . $lowered;
                $this->changes[] = ['type' => 'naturalize_perplexity', 'what' => 'discourse_marker'];
                $inserts++;
                $changed = true;
                continue;
            }

            // Hedge at start
            if (Profiles::coinFlip($prob * 0.25, $this->rng) && !empty($boosters['hedges'])) {
                $hedge = $this->rng->choice($boosters['hedges']);
                $sentences[$i] = ucfirst($hedge) . ', ' . mb_strtolower(mb_substr($sentences[$i], 0, 1)) . mb_substr($sentences[$i], 1);
                $this->changes[] = ['type' => 'naturalize_perplexity', 'what' => 'hedge'];
                $inserts++;
                $changed = true;
            }
        }

        return $changed ? implode(' ', $sentences) : $text;
    }

    /**
     * Apply English contractions (chat/web profiles only).
     */
    private function applyContractions(string $text, float $prob): string
    {
        if ($this->lang !== 'en') {
            return $text;
        }

        $profileName = '';
        foreach (Profiles::PROFILES as $name => $p) {
            if ($p === $this->profile) {
                $profileName = $name;
                break;
            }
        }

        if (!in_array($profileName, ['chat', 'web'])) {
            return $text;
        }

        foreach (self::CONTRACTIONS as $full => $contraction) {
            if (!Profiles::coinFlip($prob, $this->rng)) {
                continue;
            }

            $pattern = '/\b' . preg_quote($full, '/') . '\b/ui';
            if (preg_match($pattern, $text, $match, PREG_OFFSET_CAPTURE)) {
                $replacement = self::matchCase($match[0][0], $contraction);
                $text = substr_replace($text, $replacement, $match[0][1], strlen($match[0][0]));
                $this->changes[] = [
                    'type' => 'naturalize_contraction',
                    'from' => $match[0][0],
                    'to' => $replacement,
                ];
            }
        }

        return $text;
    }

    /**
     * Match case of first letter.
     */
    private static function matchCase(string $original, string $replacement): string
    {
        if (mb_strlen($original) === 0 || mb_strlen($replacement) === 0) {
            return $replacement;
        }

        $firstChar = mb_substr($original, 0, 1);
        if ($firstChar === mb_strtoupper($firstChar) && mb_strtoupper($firstChar) !== mb_strtolower($firstChar)) {
            return mb_strtoupper(mb_substr($replacement, 0, 1)) . mb_substr($replacement, 1);
        }

        return $replacement;
    }
}
