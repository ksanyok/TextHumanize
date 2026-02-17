<?php

declare(strict_types=1);

namespace TextHumanize\Lang;

/**
 * Language pack registry with fallback for unknown languages.
 */
class Registry
{
    /** @var array<string, array> Cached packs */
    private static array $cache = [];

    /** Languages with full dictionary support */
    public const DEEP_LANGUAGES = ['ru', 'uk', 'en', 'de', 'fr', 'es', 'pl', 'pt', 'it'];

    /** Language pack class map */
    private const PACK_MAP = [
        'ru' => Ru::class,
        'en' => En::class,
        'uk' => Uk::class,
        'de' => De::class,
        'fr' => Fr::class,
        'es' => Es::class,
        'pl' => Pl::class,
        'pt' => Pt::class,
        'it' => It::class,
    ];

    /**
     * Get language pack. Returns empty pack for unsupported languages.
     */
    public static function get(string $lang): array
    {
        if (isset(self::$cache[$lang])) {
            return self::$cache[$lang];
        }

        if (isset(self::PACK_MAP[$lang])) {
            $pack = call_user_func([self::PACK_MAP[$lang], 'pack']);
        } else {
            $pack = self::emptyPack($lang);
        }

        self::$cache[$lang] = $pack;
        return $pack;
    }

    /**
     * Whether language has full dictionary support.
     */
    public static function hasDeepSupport(string $lang): bool
    {
        return in_array($lang, self::DEEP_LANGUAGES, true);
    }

    /**
     * Empty language pack for unknown languages.
     */
    private static function emptyPack(string $lang): array
    {
        return [
            'code' => $lang,
            'name' => $lang,
            'trigrams' => [],
            'stop_words' => [],
            'bureaucratic' => [],
            'bureaucratic_phrases' => [],
            'ai_connectors' => [],
            'synonyms' => [],
            'sentence_starters' => [],
            'colloquial_markers' => [],
            'abbreviations' => [],
            'conjunctions' => [],
            'split_conjunctions' => [],
            'profile_targets' => [
                'chat' => ['min' => 8, 'max' => 18],
                'web' => ['min' => 10, 'max' => 22],
                'seo' => ['min' => 12, 'max' => 25],
                'docs' => ['min' => 12, 'max' => 28],
                'formal' => ['min' => 15, 'max' => 30],
            ],
        ];
    }
}
