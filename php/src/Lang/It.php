<?php

declare(strict_types=1);

namespace TextHumanize\Lang;

/**
 * Italian language pack.
 */
class It
{
    public static function pack(): array
    {
        return [
            'code' => 'it',
            'name' => 'Italian',
            'trigrams' => [
                'che', 'ell', 'ion', 'ent', 'ato', 'per', 'men', 'azi',
                'con', 'one', 'zio', 'sta', 'ere', 'non', 'ess', 'pre',
                'att', 'ale', 'nte', 'ria', 'ica', 'ura', 'ire', 'gli',
                'pro', 'tra', 'ter', 'tto', 'res', 'ost', 'ono', 'uto',
                'ita', 'eri', 'ova', 'ali', 'dei', 'ati', 'ori', 'com',
            ],
            'stop_words' => self::stopWords(),
            'bureaucratic' => self::bureaucratic(),
            'bureaucratic_phrases' => self::bureaucraticPhrases(),
            'ai_connectors' => self::aiConnectors(),
            'synonyms' => self::synonyms(),
            'sentence_starters' => [],
            'colloquial_markers' => [
                'onestamente', 'in realtà', 'in fondo', 'diciamo', 'in pratica', 'tra l\'altro',
            ],
            'abbreviations' => [
                'Sig.', 'Sig.ra', 'Dott.', 'Prof.', 'ecc.', 'es.', 'vol.', 'pag.', 'ed.', 'cap.',
            ],
            'conjunctions' => ['e', 'ma', 'o', 'né', 'che', 'poi'],
            'split_conjunctions' => [
                ' e ', ' ma ', ' tuttavia ', ' mentre ', ' sebbene ', ' perché ', ' poiché ',
            ],
            'profile_targets' => [
                'chat' => ['min' => 6, 'max' => 16],
                'web' => ['min' => 8, 'max' => 22],
                'seo' => ['min' => 10, 'max' => 24],
                'docs' => ['min' => 10, 'max' => 26],
                'formal' => ['min' => 12, 'max' => 30],
            ],
        ];
    }

    private static function stopWords(): array
    {
        return [
            'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una',
            'e', 'o', 'ma', 'né', 'che', 'se', 'non', 'in',
            'di', 'del', 'della', 'dei', 'delle', 'al', 'alla',
            'con', 'per', 'da', 'su', 'tra', 'fra',
            'io', 'tu', 'lui', 'lei', 'noi', 'voi', 'loro',
            'è', 'sono', 'ha', 'hanno', 'era', 'essere', 'avere',
            'questo', 'questa', 'questi', 'queste', 'quello', 'quella',
            'mio', 'mia', 'tuo', 'tua', 'suo', 'sua', 'nostro',
            'più', 'meno', 'molto', 'bene', 'come', 'dove',
            'tutto', 'tutti', 'tutta', 'tutte', 'altro', 'altra',
            'già', 'ancora', 'anche', 'solo', 'ogni',
            'qui', 'là', 'quando', 'mentre',
            'ci', 'si', 'mi', 'ti', 'vi', 'ne',
        ];
    }

    private static function bureaucratic(): array
    {
        return [
            'implementare' => ['mettere in atto', 'realizzare', 'applicare'],
            'ottimizzare' => ['migliorare', 'perfezionare', 'affinare'],
            'finalizzare' => ['concludere', 'finire', 'completare'],
            'concretizzare' => ['realizzare', 'mettere in pratica'],
            'generare' => ['creare', 'produrre', 'dare'],
            'determinare' => ['stabilire', 'decidere', 'fissare'],
            'significativo' => ['notevole', 'importante', 'rilevante'],
            'fondamentale' => ['essenziale', 'basilare', 'centrale'],
            'primario' => ['principale', 'primo', 'essenziale'],
            'inerente' => ['proprio', 'legato', 'connesso'],
            'esaustivo' => ['completo', 'dettagliato', 'approfondito'],
            'innovativo' => ['nuovo', 'creativo', 'originale'],
            'paradigmatico' => ['esemplare', 'tipico', 'modello'],
            'preponderante' => ['principale', 'dominante', 'maggiore'],
            'onnicomprensivo' => ['completo', 'totale', 'globale'],
            'imprescindibile' => ['necessario', 'essenziale', 'irrinunciabile'],
        ];
    }

    private static function bureaucraticPhrases(): array
    {
        return [
            'è doveroso sottolineare' => ['va detto', 'bisogna dire'],
            "nell'ambito di" => ['in', 'dentro', 'durante'],
            'al fine di' => ['per', 'allo scopo di'],
            'in relazione a' => ['riguardo a', 'su', 'per'],
            'in considerazione di' => ['dato', 'visto', 'considerando'],
            'in maniera significativa' => ['molto', 'parecchio', 'nettamente'],
            'riveste un ruolo cruciale' => ['è molto importante', 'conta molto'],
            "assume un'importanza" => ['è importante', 'conta'],
            'risulta necessario' => ['bisogna', 'serve', 'occorre'],
            'per quanto concerne' => ['per quanto riguarda', 'riguardo a'],
        ];
    }

    private static function aiConnectors(): array
    {
        return [
            'Inoltre' => ['In più', 'Anche', 'Per di più', 'Poi'],
            'Tuttavia' => ['Ma', 'Però', 'Eppure', 'Ciononostante'],
            'Di conseguenza' => ['Quindi', 'Perciò', 'Così', 'Dunque'],
            'Ciononostante' => ['Ma', 'Tuttavia', 'Eppure'],
            'Per di più' => ['In più', 'Inoltre', 'Anche'],
            'In definitiva' => ['Alla fine', 'In conclusione', 'Insomma'],
            'A tal proposito' => ['A questo punto', 'In merito'],
            'È importante sottolineare' => ['Va detto', 'Bisogna dire'],
            'Vale la pena notare' => ['Da notare', 'Interessante è'],
            'In conclusione' => ['Per concludere', 'Alla fine'],
            'Pertanto' => ['Quindi', 'Perciò', 'Dunque'],
            'Altresì' => ['Anche', 'Inoltre', 'Pure'],
        ];
    }

    private static function synonyms(): array
    {
        return [
            'importante' => ['rilevante', 'significativo', 'essenziale'],
            'grande' => ['ampio', 'vasto', 'considerevole'],
            'piccolo' => ['ridotto', 'modesto', 'esiguo'],
            'veloce' => ['rapido', 'agile', 'pronto'],
            'problema' => ['difficoltà', 'sfida', 'ostacolo'],
            'soluzione' => ['risposta', "via d'uscita", 'rimedio'],
            'risultato' => ['esito', 'effetto', 'frutto'],
            'metodo' => ['approccio', 'tecnica', 'sistema'],
            'processo' => ['procedura', 'percorso', 'iter'],
            'obiettivo' => ['scopo', 'traguardo', 'meta'],
            'vantaggio' => ['beneficio', 'plus', 'punto di forza'],
            'sviluppo' => ['evoluzione', 'progresso', 'crescita'],
            'analisi' => ['studio', 'esame', 'indagine'],
            'efficace' => ['efficiente', 'produttivo', 'funzionale'],
            'complesso' => ['complicato', 'articolato', 'elaborato'],
            'moderno' => ['attuale', 'contemporaneo', 'odierno'],
            'qualità' => ['livello', 'standard', 'valore'],
        ];
    }
}
