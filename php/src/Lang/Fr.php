<?php

declare(strict_types=1);

namespace TextHumanize\Lang;

/**
 * French language pack.
 */
class Fr
{
    public static function pack(): array
    {
        return [
            'code' => 'fr',
            'name' => 'French',
            'trigrams' => [
                'les', 'des', 'ent', 'que', 'ion', 'tio', 'est', 'ous',
                'ait', 'our', 'res', 'men', 'ant', 'par', 'eur', 'con',
                'com', 'une', 'pas', 'ete', 'dan', 'sur', 'ave', 'pou',
                'ont', 'ais', 'ell', 'aux', 'ess', 'ien', 'ire', 'eme',
                'pre', 'ons', 'ans', 'qui', 'tre',
            ],
            'stop_words' => self::stopWords(),
            'bureaucratic' => self::bureaucratic(),
            'bureaucratic_phrases' => self::bureaucraticPhrases(),
            'ai_connectors' => self::aiConnectors(),
            'synonyms' => self::synonyms(),
            'sentence_starters' => [],
            'colloquial_markers' => [
                'franchement', 'en fait', 'au fond', 'à vrai dire', 'disons', 'en gros',
            ],
            'abbreviations' => [
                'M.', 'Mme.', 'Dr.', 'Prof.', 'etc.', 'p. ex.', 'c.-à-d.', 'cf.', 'vol.', 'éd.',
            ],
            'conjunctions' => ['et', 'mais', 'ou', 'car', 'donc', 'puis'],
            'split_conjunctions' => [
                ' et ', ' mais ', ' cependant ', ' tandis que ', ' bien que ', ' car ', ' puisque ',
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
            'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du',
            'et', 'ou', 'mais', 'donc', 'or', 'ni', 'car',
            'je', 'tu', 'il', 'elle', 'on', 'nous', 'vous', 'ils', 'elles',
            'me', 'te', 'se', 'en', 'y',
            'est', 'sont', 'a', 'ont', 'fait', 'être', 'avoir',
            'ce', 'cette', 'ces', 'mon', 'ma', 'mes', 'ton', 'ta', 'tes',
            'son', 'sa', 'ses', 'notre', 'votre', 'leur', 'leurs',
            'dans', 'sur', 'sous', 'avec', 'pour', 'par', 'sans',
            'ne', 'pas', 'plus', 'que', 'qui', 'quoi', 'dont',
            'si', 'bien', 'très', 'moins', 'aussi',
            'tout', 'tous', 'toute', 'toutes', 'autre', 'autres',
            'ici', 'là', 'où', 'quand', 'comme', 'même',
        ];
    }

    private static function bureaucratic(): array
    {
        return [
            'implémenter' => ['mettre en place', 'réaliser'],
            'optimiser' => ['améliorer', 'ajuster'],
            'conceptualiser' => ['penser', 'imaginer', 'concevoir'],
            'finaliser' => ['terminer', 'finir', 'achever'],
            'prioriser' => ['privilégier', 'favoriser'],
            'préconiser' => ['recommander', 'conseiller'],
            'appréhender' => ['comprendre', 'saisir'],
            'concrétiser' => ['réaliser', 'accomplir'],
            'matérialiser' => ['réaliser', 'produire'],
            'substantiel' => ['important', 'considérable', 'notable'],
            'significatif' => ['notable', 'important', 'marquant'],
            'fondamental' => ['essentiel', 'de base', 'central'],
            'primordial' => ['essentiel', 'capital', 'vital'],
            'inhérent' => ['propre', 'naturel', 'lié'],
            'conséquent' => ['important', 'notable'],
            'adéquat' => ['adapté', 'convenable', 'approprié'],
            'préalable' => ['avant', "d'abord", 'initial'],
            'subséquent' => ['suivant', 'après', 'ultérieur'],
            'exhaustif' => ['complet', 'détaillé', 'approfondi'],
            'innovant' => ['nouveau', 'novateur', 'créatif'],
        ];
    }

    private static function bureaucraticPhrases(): array
    {
        return [
            'il convient de noter' => ['notons que', 'on remarque que'],
            'il est à souligner' => ['soulignons', 'important:'],
            'force est de constater' => ['on voit que', 'clairement'],
            'dans le cadre de' => ['dans', 'pendant', 'lors de'],
            'en vue de' => ['pour', 'afin de'],
            "à l'égard de" => ['envers', 'pour', 'concernant'],
            'eu égard à' => ['vu', 'étant donné'],
            'au regard de' => ['par rapport à', 'face à'],
            'de manière significative' => ['nettement', 'clairement', 'beaucoup'],
            'joue un rôle crucial' => ['est très important', 'compte beaucoup'],
            "revêt une importance" => ['est important', 'compte'],
        ];
    }

    private static function aiConnectors(): array
    {
        return [
            'En outre' => ['De plus', 'Aussi', 'Par ailleurs'],
            'Néanmoins' => ['Toutefois', 'Cependant', 'Mais', 'Pourtant'],
            'Par conséquent' => ['Donc', 'Du coup', 'Ainsi', 'Alors'],
            'En revanche' => ['Par contre', 'Mais', "À l'inverse"],
            'De surcroît' => ['En plus', 'De plus', 'Aussi'],
            'En définitive' => ['Au final', 'En fin de compte'],
            'Il convient de souligner' => ['Notons', 'À noter'],
            'Force est de constater' => ['On voit que', 'Clairement'],
            'Dans cette perspective' => ['Ici', 'Dans ce sens'],
            'À cet égard' => ['À ce sujet', 'Là-dessus'],
            'En somme' => ['Bref', 'En résumé', 'Au fond'],
            'Subséquemment' => ['Ensuite', 'Puis', 'Après'],
        ];
    }

    private static function synonyms(): array
    {
        return [
            'important' => ['capital', 'essentiel', 'majeur', 'notable'],
            'grand' => ['vaste', 'considérable', 'immense'],
            'petit' => ['réduit', 'modeste', 'faible'],
            'rapide' => ['vite', 'prompt', 'agile'],
            'problème' => ['difficulté', 'souci', 'obstacle', 'défi'],
            'solution' => ['réponse', 'issue', 'remède'],
            'résultat' => ['bilan', 'effet', 'aboutissement'],
            'méthode' => ['approche', 'technique', 'procédé'],
            'processus' => ['démarche', 'procédure', 'parcours'],
            'objectif' => ['but', 'visée', 'cible'],
            'avantage' => ['atout', 'plus', 'bénéfice'],
            'développement' => ['évolution', 'progression', 'essor'],
            'amélioration' => ['progrès', 'avancée', 'gain'],
            'analyse' => ['étude', 'examen', 'exploration'],
            'domaine' => ['champ', 'secteur', 'sphère'],
            'efficace' => ['performant', 'productif', 'utile'],
            'complexe' => ['compliqué', 'élaboré', 'dense'],
            'moderne' => ['actuel', 'récent', "d'aujourd'hui"],
            'pertinent' => ['adapté', 'juste', 'approprié'],
            'qualité' => ['niveau', 'valeur', 'calibre'],
        ];
    }
}
