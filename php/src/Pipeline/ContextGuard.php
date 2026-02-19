<?php

declare(strict_types=1);

namespace TextHumanize\Pipeline;

/**
 * ContextGuard — WSD-based safety check before word replacement.
 *
 * Checks whether a target word should be replaced given its surrounding
 * context. Prevents replacing words that are homonyms in a different
 * semantic field (e.g. "implement" near "class/interface" = code term).
 */
class ContextGuard
{
    private const CONTEXT_WINDOW = 80;

    /**
     * Guard patterns: word → list of blocking regex patterns.
     * If any pattern matches within ±CONTEXT_WINDOW characters, replacement is blocked.
     *
     * @var array<string, string[]>
     */
    private static array $guards = [
        'implement' => [
            '/\b(?:function|class|interface|method|module|def|void|return|abstract|override|extends|implements)\b/iu',
        ],
        'implementation' => [
            '/\b(?:function|class|interface|method|module|def|void|return|abstract|override|API|SDK|library|framework)\b/iu',
        ],
        'utilize' => [
            '/\b(?:function|class|def|API|SDK|CLI|library|framework)\b/iu',
        ],
        'leverage' => [
            '/\b(?:function|class|API|SDK|library|framework)\b/iu',
        ],
        'данный' => [
            '/\bна\s+данный\s+момент\b/iu',
        ],
        'даний' => [
            '/\bна\s+даний\s+момент\b/iu',
        ],
    ];

    /**
     * Check if replacing $word at given position in $text is safe.
     *
     * @param string $word       The target word (lowercase)
     * @param string $text       The full text
     * @param int    $matchStart Byte offset of match start
     * @param int    $matchEnd   Byte offset of match end
     * @return bool true if replacement is safe, false if blocked
     */
    public static function isSafe(string $word, string $text, int $matchStart, int $matchEnd): bool
    {
        $key = mb_strtolower($word);
        $patterns = self::$guards[$key] ?? null;
        if ($patterns === null) {
            return true; // no guard → always safe
        }

        $windowStart = max(0, $matchStart - self::CONTEXT_WINDOW);
        $windowEnd = min(strlen($text), $matchEnd + self::CONTEXT_WINDOW);
        $window = substr($text, $windowStart, $windowEnd - $windowStart);

        foreach ($patterns as $pattern) {
            if (preg_match($pattern, $window)) {
                return false;
            }
        }

        return true;
    }
}
