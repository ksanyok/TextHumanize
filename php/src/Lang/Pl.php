<?php

declare(strict_types=1);

namespace TextHumanize\Lang;

/**
 * Polish language pack.
 */
class Pl
{
    public static function pack(): array
    {
        return [
            'code' => 'pl',
            'name' => 'Polish',
            'trigrams' => [
                'nie', 'prz', 'ych', 'nia', 'prze', 'rze', 'sta', 'owa',
                'ani', 'teg', 'jak', 'kie', 'czy', 'pod', 'icz', 'est',
                'dzi', 'osc', 'ost', 'rzy', 'sze', 'sto',
                'ale', 'jes', 'ich', 'naw', 'ier', 'raj', 'ien',
                'acz', 'pow', 'czn', 'owy', 'ter', 'ści', 'rod', 'zna',
            ],
            'stop_words' => self::stopWords(),
            'bureaucratic' => self::bureaucratic(),
            'bureaucratic_phrases' => self::bureaucraticPhrases(),
            'ai_connectors' => self::aiConnectors(),
            'synonyms' => self::synonyms(),
            'sentence_starters' => [],
            'colloquial_markers' => [
                'szczerze mówiąc', 'tak naprawdę', 'de facto', 'w gruncie rzeczy',
                'w zasadzie', 'ogólnie rzecz biorąc',
            ],
            'abbreviations' => [
                'dr', 'prof.', 'mgr', 'inż.', 'np.', 'itd.', 'itp.', 'wg',
                'zob.', 'tzw.', 'ok.', 'mln', 'mld',
            ],
            'conjunctions' => ['i', 'ale', 'lub', 'ani', 'bo', 'więc'],
            'split_conjunctions' => [
                ' i ', ' ale ', ' jednak ', ' podczas gdy ', ' chociaż ', ' ponieważ ', ' gdyż ',
            ],
            'profile_targets' => [
                'chat' => ['min' => 6, 'max' => 16],
                'web' => ['min' => 8, 'max' => 20],
                'seo' => ['min' => 10, 'max' => 24],
                'docs' => ['min' => 10, 'max' => 26],
                'formal' => ['min' => 12, 'max' => 28],
            ],
        ];
    }

    private static function stopWords(): array
    {
        return [
            'i', 'w', 'na', 'z', 'do', 'o', 'się', 'to', 'nie',
            'jest', 'że', 'ale', 'jak', 'po', 'za', 'od', 'tak',
            'ten', 'ta', 'te', 'tym', 'tego', 'tej',
            'on', 'ona', 'ono', 'my', 'wy', 'oni', 'one',
            'co', 'kto', 'gdzie', 'kiedy', 'dlaczego',
            'być', 'mieć', 'mógł', 'musi', 'może',
            'już', 'jeszcze', 'też', 'także', 'bardzo',
            'wszystko', 'każdy', 'inny', 'tylko',
            'tu', 'tam', 'teraz', 'wtedy', 'potem',
            'ich', 'jej', 'jego', 'nasz', 'wasz',
            'który', 'która', 'które', 'których',
            'przez', 'między', 'pod', 'nad', 'przed',
            'bo', 'więc', 'gdyż', 'gdy', 'aby',
        ];
    }

    private static function bureaucratic(): array
    {
        return [
            'implementować' => ['wdrożyć', 'wprowadzić', 'zastosować'],
            'optymalizować' => ['ulepszać', 'poprawiać', 'doskonalić'],
            'ewaluować' => ['oceniać', 'sprawdzać'],
            'koordynować' => ['organizować', 'zarządzać'],
            'finalizować' => ['kończyć', 'zamykać', 'dobijać'],
            'generować' => ['tworzyć', 'wytwarzać', 'produkować'],
            'determinować' => ['określać', 'wyznaczać', 'decydować'],
            'inicjować' => ['rozpoczynać', 'zaczynać', 'wszczynać'],
            'dedykować' => ['poświęcać', 'przeznaczać'],
            'znacząco' => ['wyraźnie', 'odczuwalnie', 'mocno'],
            'fundamentalny' => ['podstawowy', 'zasadniczy', 'kluczowy'],
            'innowacyjny' => ['nowy', 'nowatorski', 'twórczy'],
            'kompleksowy' => ['pełny', 'wszechstronny', 'całościowy'],
            'kluczowy' => ['główny', 'najważniejszy', 'centralny'],
            'zasadniczy' => ['główny', 'podstawowy', 'istotny'],
            'komplementarny' => ['uzupełniający', 'dodatkowy'],
            'adekwatny' => ['odpowiedni', 'stosowny', 'właściwy'],
            'priorytetowy' => ['najważniejszy', 'główny', 'pilny'],
        ];
    }

    private static function bureaucraticPhrases(): array
    {
        return [
            'należy podkreślić' => ['warto powiedzieć', 'zaznaczmy'],
            'w ramach' => ['w', 'podczas', 'w obrębie'],
            'w zakresie' => ['w', 'pod względem', 'co do'],
            'w odniesieniu do' => ['wobec', 'co do', 'jeśli chodzi o'],
            'na gruncie' => ['na bazie', 'w oparciu o'],
            'mając na uwadze' => ['biorąc pod uwagę', 'z uwagi na'],
            'celem' => ['żeby', 'aby', 'w celu'],
            'odgrywa kluczową rolę' => ['jest bardzo ważny', 'ma duże znaczenie'],
            'ma fundamentalne znaczenie' => ['jest bardzo ważne', 'jest kluczowe'],
            'w istotny sposób' => ['znacznie', 'dużo', 'bardzo'],
        ];
    }

    private static function aiConnectors(): array
    {
        return [
            'Ponadto' => ['Poza tym', 'Oprócz tego', 'Do tego'],
            'Niemniej jednak' => ['Ale', 'Jednak', 'Mimo to'],
            'W konsekwencji' => ['Dlatego', 'Więc', 'Zatem'],
            'Jednakże' => ['Ale', 'Jednak', 'Choć'],
            'Co więcej' => ['Poza tym', 'Do tego', 'Na dodatek'],
            'W związku z tym' => ['Dlatego', 'Stąd', 'W efekcie'],
            'Warto podkreślić' => ['Ważne jest', 'Godne uwagi'],
            'Należy zauważyć' => ['Zauważmy', 'Warto wiedzieć'],
            'Reasumując' => ['Podsumowując', 'W skrócie', 'Ogólnie'],
            'Mając powyższe na uwadze' => ['Biorąc to pod uwagę', 'W tym świetle'],
            'W kontekście' => ['Jeśli chodzi o', 'Co do'],
            'Tym samym' => ['Więc', 'Dlatego', 'Stąd'],
        ];
    }

    private static function synonyms(): array
    {
        return [
            'ważny' => ['istotny', 'znaczący', 'kluczowy'],
            'duży' => ['wielki', 'znaczny', 'spory', 'pokaźny'],
            'mały' => ['niewielki', 'skromny', 'drobny'],
            'szybki' => ['prędki', 'błyskawiczny', 'sprawny'],
            'problem' => ['trudność', 'kłopot', 'wyzwanie'],
            'rozwiązanie' => ['odpowiedź', 'wyjście', 'sposób'],
            'wynik' => ['rezultat', 'efekt', 'skutek'],
            'metoda' => ['sposób', 'technika', 'podejście'],
            'proces' => ['przebieg', 'procedura', 'tok'],
            'cel' => ['zamiar', 'plan', 'dążenie'],
            'zaleta' => ['plus', 'korzyść', 'mocna strona'],
            'obszar' => ['dziedzina', 'pole', 'sfera'],
            'rozwój' => ['postęp', 'ewolucja', 'wzrost'],
            'analiza' => ['badanie', 'przegląd', 'ocena'],
            'skuteczny' => ['efektywny', 'wydajny', 'sprawny'],
            'złożony' => ['skomplikowany', 'wielowarstwowy'],
            'nowoczesny' => ['współczesny', 'aktualny', 'dzisiejszy'],
            'jakość' => ['poziom', 'standard', 'klasa'],
        ];
    }
}
