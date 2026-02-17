<?php

declare(strict_types=1);

namespace TextHumanize\Lang;

/**
 * Spanish language pack.
 */
class Es
{
    public static function pack(): array
    {
        return [
            'code' => 'es',
            'name' => 'Spanish',
            'trigrams' => [
                'que', 'ión', 'ent', 'ado', 'los', 'las', 'nte', 'ció',
                'con', 'est', 'por', 'una', 'men', 'par', 'cia',
                'mos', 'ido', 'ero', 'tro', 'aci', 'dad', 'pro', 'res',
                'ien', 'ter', 'com', 'nos', 'sta', 'ore',
                'ble', 'era', 'ues', 'tra', 'ica', 'odo', 'ura',
            ],
            'stop_words' => self::stopWords(),
            'bureaucratic' => self::bureaucratic(),
            'bureaucratic_phrases' => self::bureaucraticPhrases(),
            'ai_connectors' => self::aiConnectors(),
            'synonyms' => self::synonyms(),
            'sentence_starters' => [],
            'colloquial_markers' => [
                'la verdad', 'o sea', 'digamos', 'eso sí', 'vamos', 'bueno',
            ],
            'abbreviations' => [
                'Sr.', 'Sra.', 'Dr.', 'Prof.', 'etc.', 'p. ej.', 'vol.', 'núm.', 'pág.', 'ed.',
            ],
            'conjunctions' => ['y', 'pero', 'o', 'ni', 'que', 'pues'],
            'split_conjunctions' => [
                ' y ', ' pero ', ' sin embargo ', ' mientras ', ' aunque ', ' porque ', ' ya que ',
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
            'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
            'y', 'o', 'pero', 'ni', 'que', 'si', 'no', 'en',
            'de', 'del', 'al', 'con', 'por', 'para', 'sin',
            'yo', 'tú', 'él', 'ella', 'nosotros', 'ellos', 'ellas',
            'es', 'son', 'está', 'están', 'ha', 'han', 'fue', 'ser',
            'este', 'esta', 'estos', 'estas', 'ese', 'esa',
            'mi', 'tu', 'su', 'nuestro', 'vuestro',
            'más', 'menos', 'muy', 'tan', 'como', 'donde',
            'sobre', 'entre', 'hasta', 'desde', 'hacia',
            'todo', 'todos', 'toda', 'todas', 'otro', 'otros',
            'se', 'le', 'lo', 'me', 'te', 'nos',
            'ya', 'aún', 'también', 'solo', 'cada',
            'aquí', 'ahí', 'allí', 'cuando', 'mientras',
        ];
    }

    private static function bureaucratic(): array
    {
        return [
            'implementar' => ['poner en marcha', 'aplicar', 'llevar a cabo'],
            'optimizar' => ['mejorar', 'ajustar', 'perfeccionar'],
            'conceptualizar' => ['pensar', 'idear', 'concebir'],
            'priorizar' => ['dar prioridad', 'poner primero'],
            'potenciar' => ['fortalecer', 'mejorar', 'impulsar'],
            'viabilizar' => ['hacer posible', 'permitir'],
            'coadyuvar' => ['ayudar', 'contribuir', 'apoyar'],
            'concatenar' => ['enlazar', 'unir', 'conectar'],
            'significativo' => ['notable', 'importante', 'destacado'],
            'fundamental' => ['esencial', 'básico', 'central'],
            'primordial' => ['esencial', 'principal', 'vital'],
            'inherente' => ['propio', 'natural', 'intrínseco'],
            'subsiguiente' => ['siguiente', 'posterior'],
            'exhaustivo' => ['completo', 'detallado', 'amplio'],
            'innovador' => ['nuevo', 'novedoso', 'creativo'],
            'paradigmático' => ['ejemplar', 'modelo', 'típico'],
            'exponencial' => ['rápido', 'acelerado', 'veloz'],
            'multidimensional' => ['variado', 'complejo', 'amplio'],
        ];
    }

    private static function bureaucraticPhrases(): array
    {
        return [
            'es menester señalar' => ['cabe decir', 'vale notar'],
            'en el marco de' => ['dentro de', 'en', 'durante'],
            'con el objetivo de' => ['para', 'con el fin de'],
            'a los efectos de' => ['para', 'con motivo de'],
            'en virtud de' => ['por', 'gracias a', 'debido a'],
            'en lo que respecta a' => ['en cuanto a', 'sobre', 'respecto a'],
            'de manera significativa' => ['mucho', 'claramente', 'bastante'],
            'desempeña un papel crucial' => ['es muy importante', 'es clave'],
            'reviste especial importancia' => ['es importante', 'importa mucho'],
            'resulta imprescindible' => ['es necesario', 'hace falta'],
        ];
    }

    private static function aiConnectors(): array
    {
        return [
            'Además' => ['También', 'Aparte', 'Igualmente', 'Encima'],
            'Sin embargo' => ['Pero', 'No obstante', 'Aun así'],
            'Por consiguiente' => ['Por eso', 'Así que', 'Entonces'],
            'No obstante' => ['Pero', 'Sin embargo', 'Aun así'],
            'En consecuencia' => ['Por eso', 'Entonces', 'Así que'],
            'Asimismo' => ['También', 'Igualmente', 'De igual modo'],
            'Por otra parte' => ['Por otro lado', 'Además', 'También'],
            'En definitiva' => ['Al final', 'En resumen', 'Total'],
            'Cabe destacar' => ['Es notable', 'Vale la pena notar'],
            'Es preciso señalar' => ['Hay que decir', 'Cabe notar'],
            'A modo de conclusión' => ['Para terminar', 'En resumen'],
            'En este sentido' => ['Así', 'En esa línea', 'Al respecto'],
        ];
    }

    private static function synonyms(): array
    {
        return [
            'importante' => ['relevante', 'clave', 'notable', 'esencial'],
            'grande' => ['amplio', 'extenso', 'considerable'],
            'pequeño' => ['reducido', 'modesto', 'escaso'],
            'rápido' => ['veloz', 'ágil', 'pronto'],
            'problema' => ['dificultad', 'reto', 'obstáculo', 'desafío'],
            'solución' => ['respuesta', 'salida', 'remedio'],
            'resultado' => ['efecto', 'consecuencia', 'fruto'],
            'método' => ['enfoque', 'sistema', 'técnica'],
            'proceso' => ['procedimiento', 'trámite', 'curso'],
            'objetivo' => ['meta', 'propósito', 'fin'],
            'ventaja' => ['beneficio', 'provecho', 'punto fuerte'],
            'área' => ['campo', 'zona', 'sector', 'esfera'],
            'desarrollo' => ['avance', 'evolución', 'progreso'],
            'análisis' => ['estudio', 'examen', 'revisión'],
            'eficaz' => ['efectivo', 'productivo', 'útil'],
            'complejo' => ['complicado', 'elaborado', 'difícil'],
            'moderno' => ['actual', 'contemporáneo', 'reciente'],
            'calidad' => ['nivel', 'estándar', 'valor'],
        ];
    }
}
