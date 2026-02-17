<?php

declare(strict_types=1);

namespace TextHumanize\Lang;

/**
 * German language pack.
 */
class De
{
    public static function pack(): array
    {
        return [
            'code' => 'de',
            'name' => 'German',
            'trigrams' => [
                'der', 'die', 'und', 'den', 'das', 'ein', 'sch', 'ich',
                'che', 'ine', 'ist', 'eit', 'ung', 'uch', 'ber', 'ter',
                'eni', 'ges', 'ere', 'aus', 'für', 'gen', 'cht', 'ent',
                'ver', 'ren', 'ste', 'auf', 'ach', 'bei', 'ier', 'tte',
                'lic', 'erf', 'her', 'nic', 'nde', 'and', 'mit',
            ],
            'stop_words' => self::stopWords(),
            'bureaucratic' => self::bureaucratic(),
            'bureaucratic_phrases' => self::bureaucraticPhrases(),
            'ai_connectors' => self::aiConnectors(),
            'synonyms' => self::synonyms(),
            'sentence_starters' => [],
            'colloquial_markers' => [
                'ehrlich gesagt', 'im Grunde', 'im Prinzip', 'genau genommen',
                'unter uns gesagt', 'nebenbei',
            ],
            'abbreviations' => [
                'z.B.', 'd.h.', 'u.a.', 'etc.', 'bzw.', 'ca.', 'vgl.',
                'Dr.', 'Prof.', 'Nr.', 'Str.', 'Mio.', 'Mrd.',
            ],
            'conjunctions' => ['und', 'aber', 'oder', 'denn', 'weil', 'da'],
            'split_conjunctions' => [
                ' und ', ' aber ', ' jedoch ', ' wobei ', ' während ', ' obwohl ', ' denn ',
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
            'der', 'die', 'das', 'ein', 'eine', 'und', 'oder', 'aber',
            'ist', 'sind', 'war', 'hat', 'haben', 'wird', 'werden',
            'kann', 'können', 'muss', 'müssen', 'soll', 'sollen',
            'in', 'an', 'auf', 'für', 'mit', 'von', 'zu', 'bei',
            'nach', 'über', 'unter', 'vor', 'aus', 'durch', 'um',
            'ich', 'du', 'er', 'sie', 'es', 'wir', 'ihr',
            'den', 'dem', 'des', 'einer', 'einem', 'eines',
            'nicht', 'auch', 'noch', 'schon', 'nur', 'wenn',
            'als', 'wie', 'so', 'da', 'dann', 'denn', 'weil',
            'dass', 'ob', 'man', 'sich', 'hier', 'dort',
            'sehr', 'mehr', 'viel', 'gut', 'neu', 'alle',
            'diese', 'dieser', 'dieses', 'jede', 'jeder', 'jedes',
            'sein', 'seine', 'seinem', 'seinen', 'seiner',
            'was', 'wer', 'wo', 'warum', 'welche',
        ];
    }

    private static function bureaucratic(): array
    {
        return [
            'implementieren' => ['umsetzen', 'einführen'],
            'optimieren' => ['verbessern', 'anpassen'],
            'evaluieren' => ['bewerten', 'prüfen', 'beurteilen'],
            'generieren' => ['erzeugen', 'erstellen', 'schaffen'],
            'initiieren' => ['starten', 'beginnen', 'anstoßen'],
            'adressieren' => ['angehen', 'behandeln', 'lösen'],
            'facilitieren' => ['erleichtern', 'ermöglichen'],
            'priorisieren' => ['vorziehen', 'bevorzugen'],
            'kommunizieren' => ['mitteilen', 'besprechen', 'sagen'],
            'finalisieren' => ['fertigstellen', 'abschließen'],
            'signifikant' => ['deutlich', 'merklich', 'spürbar', 'erheblich'],
            'fundamental' => ['grundlegend', 'wesentlich'],
            'essentiell' => ['wichtig', 'nötig', 'wesentlich'],
            'inhärent' => ['eigen', 'innewohnend'],
            'konsequent' => ['folgerichtig', 'durchgehend'],
            'adäquat' => ['passend', 'angemessen'],
            'primär' => ['hauptsächlich', 'vor allem'],
            'sukzessive' => ['nach und nach', 'schrittweise'],
            'marginalisieren' => ['verdrängen', 'zurückdrängen'],
            'integrieren' => ['einbinden', 'einbauen'],
            'manifestieren' => ['zeigen', 'offenbaren'],
            'etablieren' => ['einrichten', 'aufbauen', 'gründen'],
        ];
    }

    private static function bureaucraticPhrases(): array
    {
        return [
            'es ist festzustellen' => ['es zeigt sich', 'klar ist'],
            'in Anbetracht der Tatsache' => ['angesichts', 'weil'],
            'unter Berücksichtigung' => ['mit Blick auf', 'angesichts'],
            'im Rahmen von' => ['bei', 'während', 'innerhalb'],
            'zum Zwecke der' => ['für', 'um zu'],
            'in Bezug auf' => ['zu', 'bei', 'was betrifft'],
            'hinsichtlich' => ['zu', 'bei', 'was betrifft'],
            'zwecks' => ['für', 'um zu'],
            'mittels' => ['mit', 'durch'],
            'aufgrund der Tatsache' => ['weil', 'da'],
            'im Hinblick auf' => ['für', 'bezüglich'],
            'es lässt sich konstatieren' => ['man sieht', 'es zeigt sich'],
            'von großer Bedeutung' => ['wichtig', 'bedeutend'],
            'eine zentrale Rolle spielen' => ['wichtig sein', 'zentral sein'],
        ];
    }

    private static function aiConnectors(): array
    {
        return [
            'Darüber hinaus' => ['Außerdem', 'Zudem', 'Dazu', 'Weiters'],
            'Nichtsdestotrotz' => ['Trotzdem', 'Aber', 'Dennoch'],
            'Demzufolge' => ['Daher', 'Deshalb', 'Also', 'Somit'],
            'Infolgedessen' => ['Deshalb', 'Daher', 'Also'],
            'Des Weiteren' => ['Außerdem', 'Zudem', 'Dazu'],
            'Im Gegensatz dazu' => ['Anders', 'Aber', 'Dagegen'],
            'In diesem Zusammenhang' => ['Dabei', 'Hier'],
            'Zusammenfassend lässt sich sagen' => ['Kurz gesagt', 'Im Ganzen'],
            'Es ist hervorzuheben' => ['Wichtig ist', 'Bemerkenswert'],
            'Abschließend' => ['Zum Schluss', 'Am Ende'],
            'Ferner' => ['Außerdem', 'Auch', 'Zudem'],
            'Überdies' => ['Außerdem', 'Zudem', 'Dazu'],
        ];
    }

    private static function synonyms(): array
    {
        return [
            'wichtig' => ['bedeutend', 'wesentlich', 'relevant', 'zentral'],
            'groß' => ['erheblich', 'beträchtlich', 'umfangreich'],
            'klein' => ['gering', 'wenig', 'niedrig'],
            'schnell' => ['rasch', 'zügig', 'fix'],
            'langsam' => ['gemächlich', 'träge', 'bedächtig'],
            'gut' => ['positiv', 'gelungen', 'brauchbar'],
            'schlecht' => ['mangelhaft', 'unzureichend', 'schwach'],
            'Möglichkeit' => ['Option', 'Chance', 'Gelegenheit'],
            'Problem' => ['Schwierigkeit', 'Herausforderung', 'Hürde'],
            'Lösung' => ['Antwort', 'Ausweg', 'Abhilfe'],
            'Ergebnis' => ['Resultat', 'Ausgang', 'Befund'],
            'Bereich' => ['Gebiet', 'Feld', 'Sektor'],
            'Methode' => ['Verfahren', 'Ansatz', 'Vorgehen'],
            'Prozess' => ['Vorgang', 'Ablauf', 'Verfahren'],
            'Aspekt' => ['Seite', 'Punkt', 'Facette'],
            'Grund' => ['Ursache', 'Anlass', 'Motiv'],
            'Ziel' => ['Zweck', 'Absicht', 'Vorgabe'],
            'Aufgabe' => ['Auftrag', 'Pflicht', 'Job'],
            'Vorteil' => ['Nutzen', 'Plus', 'Stärke'],
            'Nachteil' => ['Minus', 'Schwäche', 'Manko'],
            'Analyse' => ['Untersuchung', 'Auswertung', 'Prüfung'],
            'Qualität' => ['Güte', 'Niveau', 'Standard'],
            'relevant' => ['wichtig', 'bedeutend', 'passend'],
            'effektiv' => ['wirksam', 'erfolgreich', 'wirkungsvoll'],
            'komplex' => ['vielschichtig', 'schwierig', 'umfangreich'],
            'modern' => ['zeitgemäß', 'aktuell', 'neu'],
        ];
    }
}
