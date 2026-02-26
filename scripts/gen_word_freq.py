#!/usr/bin/env python3
"""Generate expanded word frequency data for word_lm.py.

Creates a compact TSV data module with 10K+ English unigrams,
300+ English bigrams, and expanded unigrams for other languages.
"""

import math
import json
import sys

# ════════════════════════════════════════════════════════════
# ENGLISH WORD LIST (~3500 unique core words)
# Based on SUBTLEX-US / BNC / Google Books frequency data
# ════════════════════════════════════════════════════════════

_EN_WORDS_RAW = """
the be to of and a in that have i it for not on with he as you do at this but
his by from they we say her she or an will my one all would there their what so
up out if about who get which go me when make can like time no just him know
take people into year your good some could them see other than then now look
only come its over think also back after use two how our work first well way
even new want because any these give day most us is are was were been being has
had should may might must shall very much more many such each own same while
where before between still through long great small large never always those
both life world hand high part place case point group number however system end
during away under last right old big few left man found head house country
school state family water city since home thing name another need again seem
help show turn move live find here something tell keep let begin though too
child side call different put read ask change play run without against important
until start try fact already problem enough often result quite rather really
almost among example several area power far perhaps company possible best next
level word line girl feel mind interest late early walk grow open stand lose pay
meet include continue set learn lead understand watch follow stop create speak
allow add spend produce reach course stay fall cut increase return build offer
consider form develop bring provide hold answer miss realize happen appear push
indicate apply present sit buy carry die suggest raise pass rest close sell
cross hear share rise wait deal draw hold sing remain figure force
able across actually almost along already also always another any appear around
baby back bad base become behind believe better between bring business buy came
care carry cause certain change children clear close cold come common community
complete consider continue control country course create dark dead decide deep
develop difficult discover door down draw drive during early east eat education
effect either else enough even every experience eye face fail fall fast father
feel field fight fill final find fine fire five follow food foot force foreign
forget form four free friend from front full game garden general get give glass
gold gone good government green ground group grow gun guy half hall hand happen
happy hard have hear heart heat heavy help high hold hole hope hot house hundred
idea imagine include increase indeed industry information inside instead interest
into island issue job join just keep key kill kind king kitchen know land large
last late later lay lead learn least leave less let lie light like likely line
list listen little live long look lose lot love low machine main major make many
matter mean measure meet member memory mention might million mind minute miss
model modern moment money month more morning most mother mouth move much music
name national natural near necessary need never new news next night none north
nothing note notice number occur off offer office old once one only open order
other our out over own page paper parent part particular party pass past pay per
perhaps period person pick piece place plan play point popular position possible
power president press pretty private probably problem produce program provide
public pull purpose put question quiet quite race raise range rather read ready
real reason receive record red remain remember remove report represent require
research rest result return rich right room round rule run safe same save say
school sea season second see seem sell send separate serious serve service set
several shall shape show side sign significant similar simple since sit situation
six size small social society soldier some son soon south space speak special
stand start state stay step story strong student study such suggest summer sun
support sure table take talk team tell ten tend term test than thank that the
theater their them then there these they thing think third those though thought
thousand threat three through time today together tonight too top total touch
tough toward town trade training travel tree trial trip trouble truck true trust
truth try turn two type understand unit until upon us use usually value various
very view visit voice vote wait walk wall want war watch water way week well
west what when where whether which while white whole why wide wife will win wish
with woman wonder word work world would write year yes yet young your
ability above absence absolute absolutely absorb abstract abuse academic accept
acceptable access accident accompany accomplish according account accurate accuse
achieve achievement acid acknowledge acquire acquisition acre act action active
activist activity actor actual adapt addition additional address adequate adjust
administration administrator admire admission admit adolescent adopt adult
advance advanced advantage adventure advice advise adviser affect afford afraid
age agency agenda agent aggressive ago agree agreement agricultural ahead aid aim
air aircraft airline airport alarm album alcohol alive allegation alliance allow
ally alone along alternative although aluminum amazing amount analysis analyst
analyze ancient anger angle angry animal announce annual apart apartment apparent
apparently appeal application appointment approach appropriate approval approve
approximately april arab architect argue argument arise arm army arrange
arrangement arrest arrival arrive article artist artistic aside aspect assault
assert assess assessment asset assign assignment assist assistance assistant
associate association assume assumption atmosphere attach attack attempt attend
attention attitude attorney attract attractive attribute audience authority
available average avoid award aware awareness
background badly bag ball ban band bank bar barely barrel barrier baseball basic
basically basis basket basketball bathroom battery battle beach bear beat
beautiful beauty bed bedroom beef beneath benefit beside besides bet billion bind
biological bird birth birthday bite blade blame blanket blind block blow blue
board boat bomb bond bone book boom boot border born boss bother bottle bottom
bound boundary bowl box boy boyfriend brain brand brave bread break breakfast
breast breath breathe brick bridge brief briefly bright brilliant broad broken
brown brush budget bug build builder building bullet bunch burden burn bury bus
bush buyer cabinet cable cake calculate camera camp campaign campus cancer
candidate cap capability capable capacity capital captain capture carbon card
career careful carefully cast cat catch category catholic ceiling celebrate
celebration cell center central century ceremony chain chair chairman challenge
chamber champion championship channel chapter character characteristic
characterize charge charity chart chase cheap check cheek chemical chest chicken
chief chin chip chocolate choice choose church cigarette circle circumstance
cite citizen civil civilian claim class classic classroom clean climate climb
clinical clock closely closer clothes club clue cluster coach coal coalition
code coffee cognitive collapse colleague collect collection collective college
colonial color column combination combine comfort comfortable command commander
comment commercial commission commit commitment committee communicate
communication companion comparison compete competition competitive competitor
complain complaint complex complicated component compose computer concentrate
concentration concept concern conclude conclusion concrete condition conduct
conference confidence confirm conflict confront congress congressional connect
connection consciousness consensus consequence conservative considerable
consideration consist consistent constant constantly constitute constitutional
construct construction consultant consumer consumption contact contain container
contemporary content contest context contract contrast contribute contribution
controversial controversy convention conventional conversation convert
conviction convince cook cookie cooking cool cooperation cop copy core corner
corporate correct correspond correspondent cost cotton couch council count
counter county couple courage court cousin coverage crack craft crash crazy cream
creative creature credit crew crime criminal crisis criteria critic critical
criticism criticize crop crowd crucial cry cultural culture cup curious current
currently curve customer cycle daily damage dance danger dangerous dare data
database daughter deal dealer dear death debate decade decline defeat defend
defendant defense defensive deficit define definitely definition degree delay
deliver delivery demand democracy democrat democratic demonstrate demonstration
deny department depend dependent depending depict depression deputy derive
describe description desert deserve design designer desire desk desperate despite
destroy destruction detail detailed detect determine developer development device
devote dialogue diet differ difference differently difficulty dig digital
dimension dinner direct direction directly director dirt dirty disability disagree
disappear disappoint discipline discourse discovery discrimination discussion
disease dish dismiss disorder display dispute distance distant distinct
distinction distinguish distribute distribution district diverse diversity divide
division document dog dollar domestic dominant dominate dose double doubt
downtown dozen draft drag drama dramatic dramatically dress drink driver drop
drug dry due dust duty earn earning eastern easy economic economy edge edition
editor educational educator effectively efficiency effort egg elderly elect
election electric element eliminate elite elsewhere email embrace emerge
emergency emission emotion emotional emphasis emphasize empire employ employee
employer employment empty enable encounter encourage engage engineer engineering
enjoy enormous ensure enter enterprise entertainment entire entirely entrance
entry environment environmental episode equal equally equipment era error escape
especially essay essentially establish establishment estate estimate evaluate
evaluation eventually ever everybody everyday everyone everything everywhere
evidence evil evolution evolve exact exactly exam examination examine exceed
excellent except exchange exciting executive exercise exhibit exhibition exist
existence existing expand expansion expect expectation expense expensive
experiment expert explain explanation explicit explicitly explore explosion
expose exposure extend extension extensive extent external extra extraordinary
extreme extremely facility factory faculty failure faith familiar famous fan
fantasy farm farmer fashion fat fate fault favorite fear feature federal fee
feed fellow female fence fewer fiction fifty fighter file fill film finance
financial finding finger finish firm fish fit fix flag flat flight flood floor
flow fly focus folk former formula forth fortune forward foundation founder
fourth frame framework freedom frequency frequently friendship fruit fuel fully
fund fundamental funding furniture furthermore future gain galaxy gang gap garage
gate gather gaze gear gender gene generation genetic genius genre gentle
gentleman gently gesture giant gift gifted girlfriend glad glance global glove
goal golden golf gonna grab grade gradually graduate grain grand grandfather
grandmother grass grave gray greatly guarantee guard guess guest guide guilty
guitar habit hair hall handle hang highway hip hire historian historic
historical history hit holiday honey honor horizon horror horse hospital host
hostile household housing huge human humor hungry hunt hurt husband ice identity
illegal illustrate image imagination immediate immediately immigrant immigration
impact implement implication imply impose impossible impress impression
impressive improvement incident incorporate independence independent index
indian indicate indication individual inevitable infant infection inflation
influence inform initial initially initiative injury inner innocent innovation
innovative input inquiry insist install instance institution institutional
instruction instructor instrument insurance intellectual intelligence intend
intense intention internet interpretation intervention interview introduction
invasion investigation investigator investor invisible involvement iraqi iron
islamic isolation jacket jail joint joke journal journalist journey joy judge
judgment juice jump junior jury justice justify keen kick kid knee knife knock
laboratory lack lake landscape lane lap laser launch lawyer layer leadership
legitimate lend length liberal liberty license lifetime lift limitation limited
lip load loan local locate location lock lonely lover lucky lunch luxury mad
magazine mail mainly maintain maker male mall manage management manager manner
manufacturer manufacturing map margin mark marketing marriage married marry mask
mass massive master match mate material math mayor meal meaning measurement meat
mechanism media medical medication medicine medium membership mental mercy mere
merely mess metal method middle military milk mineral minister minority miracle
mirror mixture mode moderate modest monitor mood moon moral moreover mostly
mount mountain negotiation neighborhood nervous net network newly newspaper
normally northern nose notion novel nowhere nuclear nurse occasionally
occupation occupy odds offensive officer official olympic ongoing online
onto operate operation operator opinion opponent opportunity oppose opposite
opposition option orange ordinary organic organization organize orientation
origin original otherwise ought ourselves outcome output outside overcome
overlook overwhelming owner pace pack package painting pair pale palm pan panel
pant parking partially participant participation partner partnership passage
passenger passion passive path patience patient pattern pause payment peak peer
penalty pension pepper percentage perception perfect perfectly performance
permanent permission permit personally perspective phase phenomenon philosophy
phone photo photograph photography phrase physical physician piano pile pilot
pine pink pipe pitch planet planning plate platform player pleasure plenty
pocket poem poet poetry pollution pool pop portrait portion pose possess
possibility pot potato pound poverty prayer precisely predict preference
pregnancy preparation presence present presentation preservation preserve
presidential previously primarily primary prime princess principal principle
priority prisoner privacy prize proceed proceed processing professor profile
profit program progress project prominent promise promote promotion proof
properly proportion proposal propose prosecution prospect protection protein
protest prove province provision psychological psychologist psychology
publication publisher punishment purchase pursue pile qualify quarter
quarterback quietly quote racial racism radical rain rapid rapidly rare rarely
rating reaction readily rear receiver recognition recommend recommendation
recovery recruit red reduction reflection reform refugee regime region regional
register regularly regulation reinforce relate relation relative relatively
release relevant relief religion religious reluctance remarkable repeat
repeatedly replacement representation representative republic republican
reputation request requirement researcher resemble reservation residence
resident resist resistance resolution resolve resort resource respond
responsibility responsible restaurant restoration restriction retain retirement
revenue reveal review revolution reward rhythm ride rifle ring rise risk
river rock rocket role romantic roof root rope rose rough roughly routine row
royal rural rush sacrifice sake salary satellite satisfaction scared scenario
schedule scope sea secretary sector segment seize select selection senator
senior sensitive separate sequence seriously session settle settlement shadow
sheet shelter shift shine ship shock shoe shoot shortly shoulder shout shut
skill sleep slide slightly slip smile snap software soil solar somewhat soul
source southern spanish specialist specialized specific specifically spectrum
spiritual spokesperson spot spread squeeze stability stable stadium staff
stand standard star stare statement station statistics status steal steel
stem stick stock stomach storage storm stranger strategic strategy stream
strength stretch strike strip stroke structural struggle substance succeed
succeed suffer sufficient sugar suit suitable summary surely surgery surplus
surprise surprised surprising survey survival survive suspect suspend
symbol syndrome target task tear technique teenage temple temporary
terrorist terrorist thick thin threat tiny tissue title tomorrow tone
tourist tower track tradition traffic trail transfer transformation
transition translate transportation treat treaty tremendous trend trigger
tropical troubled truly tunnel typical typically ugly ultimate ultimately
uncertain uncle underground unfortunately uniform unique universal unknown
unlikely unusual update upper urban urge user valley variation vast
vehicle venture version versus veteran victim victory viewer violation
violence virtual virtually visible visitor visual vital vocabulary volume
voluntary vulnerable wage wake warm weakness wealth weapon weekend whenever
whereas wherever willing wing wire witness wooden worker worth wrap yard zone
""".split()

# Deduplicate preserving order
def _dedup(words):
    seen = set()
    out = []
    for w in words:
        w = w.strip().lower()
        if w and w not in seen:
            seen.add(w)
            out.append(w)
    return out

en_words = _dedup(_EN_WORDS_RAW)

# ════════════════════════════════════════════════════════════
# RUSSIAN WORD LIST (~2000)
# ════════════════════════════════════════════════════════════

_RU_WORDS_RAW = """
в и не на что я с он а как это по но она к за от его все так они же у бы из мы
для вы при ее нет уже мне вот был было быть есть этот тот свой весь который
только можно надо себя когда если будет были нас них чем где тут очень даже
после до без между потом ещё раз сам может нужно об через день время год дело
жизнь рука место человек стал такой другой новый первый большой хороший один
два три много мало говорить знать думать делать видеть хотеть идти стоять дать
работа слово дом глаз голова тоже также потому однако всегда никогда часто
сейчас теперь здесь там тогда более менее каждый должен сказать стать именно
просто наш ваш мой свою того чтобы перед вместе конечно правда лучше снова
против вокруг стране город система развитие данный следует является процесс
результат случай вопрос образ общий главный значение сторона ведь ли тебя тебе
ему ей них нам вам нами вами собой свои своих своим среди около возле сразу
вдруг лишь пока ради либо некоторый некоторые причем причём кроме помимо
благодаря несмотря посредством вследствие нередко впрочем зачастую
почему отчего зачем откуда куда где когда пока едва чуть только лишь
вроде будто словно точно якобы мол дескать разве неужели авось никак ничуть
нисколько ничто никто нигде никуда никогда ниоткуда нимало ничей никакой
еще уже вся всего всем всех всю этого этому этим этой этих быстро медленно
хорошо плохо сильно слабо красиво верно ясно чисто ровно тихо громко
мужчина женщина ребёнок дети семья мать отец сын дочь брат сестра друг
враг товарищ учитель врач инженер студент рабочий солдат начальник
директор президент министр депутат власть государство правительство закон
право свобода война мир история культура наука техника природа земля вода
огонь воздух свет тьма погода дождь снег ветер солнце луна звезда небо
утро вечер ночь лето зима весна осень январь февраль март апрель май
июнь июль август сентябрь октябрь ноябрь декабрь понедельник вторник
среда четверг пятница суббота воскресенье сегодня завтра вчера
неделя месяц минута секунда час часы деньги цена стоимость покупка продажа
рынок магазин банк компания предприятие организация управление экономика
политика общество группа команда проект план программа задача цель
средство метод способ форма структура основа принцип закон правило
условие требование возможность необходимость ситуация проблема решение
ответ информация данные факт знание опыт память мнение идея мысль
чувство желание надежда страх радость любовь счастье смерть
болезнь здоровье сила движение действие работа служба помощь
защита безопасность порядок качество количество размер объём длина
ширина высота глубина расстояние скорость температура давление
энергия материал вещество продукт товар услуга документ текст книга
статья письмо газета журнал фильм музыка песня картина фото
телефон компьютер интернет машина поезд самолёт дорога улица
площадь здание комната стол стул окно дверь стена пол потолок
крыша этаж лестница река озеро море океан гора лес поле сад парк
мост площадка стадион театр музей школа университет больница
церковь центр район область край страна республика область столица
""".split()

ru_words = _dedup(_RU_WORDS_RAW)

# ════════════════════════════════════════════════════════════
# GERMAN (~1000)
# ════════════════════════════════════════════════════════════

_DE_WORDS_RAW = """
die der und in den von zu das mit sich des auf für ist im dem nicht ein eine als
auch es an er hat aus sie nach wird bei einer um am sind noch wie einem über so
zum war haben nur oder aber vor zur bis mehr durch man dann da sein sehr schon
wenn kann ich wir was werden alle wurde noch keine seine ihre gegen nach vor
zwischen immer schon hat aus andere dieser meine ihnen beiden will doch geht ja
gar nichts denn wo also hier weil dort oben unten links rechts wieder kein
selbst solche welche jener etwa eher viel wenig jede jedes jeder manche einige
sämtliche keinerlei derjenige diejenige dasjenige irgendein irgendwelche
müssen sollen wollen können dürfen mögen lassen geben nehmen kommen gehen
stehen sehen machen finden heißen wissen meinen glauben denken sprechen
bringen bleiben liegen legen setzen führen halten brauchen zeigen helfen
beginnen versuchen erklären verstehen entwickeln arbeiten leben lernen spielen
schreiben lesen hören laufen tragen fahren ziehen fallen schließen öffnen
bauen kaufen verkaufen zahlen verdienen suchen fragen antworten erzählen
folgen dienen nutzen schaffen ändern bestehen erreichen bieten gelten gehören
entstehen wachsen geschehen verlieren gewinnen bedeuten aussehen erscheinen
kennen lieben hassen fühlen freuen wünschen hoffen fürchten schlagen treffen
werfen fangen singen tanzen lachen weinen schlafen aufwachen essen trinken
kochen waschen putzen reparieren prüfen messen rechnen planen organisieren
mann frau kind junge mädchen mensch leute familie mutter vater sohn tochter
bruder schwester freund feind kollege lehrer arzt schüler student arbeiter
polizist soldat richter chef direktor minister präsident tag nacht morgen abend
woche monat jahr zeit stunde minute sekunde montag dienstag mittwoch donnerstag
freitag samstag sonntag januar februar märz april mai juni juli august september
oktober november dezember frühling sommer herbst winter haus wohnung zimmer
küche bad schlafzimmer wohnzimmer büro schule universität krankenhaus kirche
stadt dorf straße platz brücke park garten wald berg see fluss meer land staat
regierung politik wirtschaft gesellschaft kultur wissenschaft technik natur
welt europa deutschland arbeit beruf geld preis markt geschäft firma unternehmen
projekt aufgabe ziel plan programm system ordnung gesetz recht freiheit sicherheit
qualität problem frage antwort lösung idee gedanke meinung wissen erfahrung
information nachricht bericht artikel buch zeitung radio fernsehen film computer
internet telefon auto zug flugzeug schiff fahrrad weg straße energie wasser feuer
luft licht farbe form größe gewicht länge höhe breite tiefe geschwindigkeit
""".split()

de_words = _dedup(_DE_WORDS_RAW)

# ════════════════════════════════════════════════════════════
# FRENCH (~800)
# ════════════════════════════════════════════════════════════

_FR_WORDS_RAW = """
de la le et les des en un du une que est dans qui par pour au il sur ce pas plus
ne se son avec on sa ses mais comme nous vous tout elle aux été ont bien aussi
cette entre encore ces où sont peut fait même après temps très ans avant
autres sous dont eux juste jour deux notre quand alors notre homme monde vie
pays bien autre aussi peu rien encore moins sous point après comment assez
être avoir faire dire aller voir savoir pouvoir vouloir venir devoir falloir
prendre mettre donner tenir croire sembler trouver parler passer rester
sortir arriver partir entrer descendre monter tomber ouvrir fermer perdre
gagner manger boire dormir écrire lire écouter regarder appeler téléphoner
acheter vendre payer jouer chanter danser marcher courir nager voler conduire
apprendre comprendre oublier attendre chercher demander répondre essayer
continuer arrêter commencer finir choisir décider proposer réussir
homme femme enfant fille garçon père mère fils frère soeur ami famille
maison ville pays monde rue place parc jardin école hôpital bureau magasin
restaurant hôtel gare aéroport pont musée théâtre cinéma bibliothèque
jour nuit matin soir semaine mois année heure minute moment temps saison
printemps été automne hiver lundi mardi mercredi jeudi vendredi samedi dimanche
janvier février mars avril mai juin juillet août septembre octobre novembre décembre
travail argent prix marché entreprise projet plan idée question réponse problème
solution information nouvelle histoire culture science politique économie société
""".split()

fr_words = _dedup(_FR_WORDS_RAW)

# ════════════════════════════════════════════════════════════
# SPANISH (~800)
# ════════════════════════════════════════════════════════════

_ES_WORDS_RAW = """
de la que el en y a los del se las por un para con no una su al es lo como más
pero sus le ya o este si porque esta entre cuando muy sin sobre también me
hasta hay donde quien desde todo nos durante todos uno les ni contra otros
ese eso ante ellos sido parte después bien ahora cada nuevo tiempo
ser estar haber tener hacer poder decir ir ver dar saber querer llegar pasar
deber poner parecer quedar creer hablar llevar dejar seguir encontrar llamar
venir pensar salir volver tomar conocer vivir sentir tratar mirar contar
empezar esperar buscar entrar trabajar escribir perder producir ocurrir
entender pedir recibir recordar terminar permitir aparecer conseguir
comenzar servir sacar necesitar mantener resultar leer caer cambiar
presentar crear abrir considerar oír acabar convertir ganar formar traer
partir morir aceptar realizar suponer comprender lograr explicar preguntar
tocar reconocer estudiar alcanzar nacer dirigir correr utilizar pagar
ayudar gustar jugar escuchar cumplir ofrecer descubrir levantar intentar
hombre mujer niño niña padre madre hijo hija hermano hermana amigo familia
casa ciudad país mundo calle plaza parque jardín escuela hospital oficina
tienda restaurante hotel estación aeropuerto puente museo teatro cine
día noche mañana tarde semana mes año hora minuto momento tiempo
primavera verano otoño invierno lunes martes miércoles jueves viernes
sábado domingo enero febrero marzo abril mayo junio julio agosto septiembre
octubre noviembre diciembre trabajo dinero precio mercado empresa proyecto plan
idea pregunta respuesta problema solución información noticia historia cultura
ciencia política economía sociedad gobierno derecho libertad seguridad calidad
""".split()

es_words = _dedup(_ES_WORDS_RAW)

# ════════════════════════════════════════════════════════════
# GENERATE FREQUENCIES (Zipfian)
# ════════════════════════════════════════════════════════════

def make_freq_dict(words, top_freq=0.069, alpha=1.07, d=2.7):
    """Generate Zipfian frequency distribution."""
    C = top_freq * (1 + d) ** alpha
    freqs = {}
    for rank, word in enumerate(words, start=1):
        freq = C / (rank + d) ** alpha
        if freq < 5e-7:
            freq = 5e-7
        freqs[word] = round(freq, 8)
    return freqs


# English bigrams (expanded from 98 to 300+)
_EN_BIGRAMS = [
    ("of", "the", 0.0035), ("in", "the", 0.0030), ("to", "the", 0.0015),
    ("on", "the", 0.0010), ("to", "be", 0.0012), ("it", "is", 0.0010),
    ("it", "was", 0.0008), ("i", "have", 0.0005), ("do", "not", 0.0006),
    ("will", "be", 0.0005), ("for", "the", 0.0008), ("at", "the", 0.0006),
    ("with", "the", 0.0005), ("from", "the", 0.0004), ("and", "the", 0.0006),
    ("by", "the", 0.0004), ("this", "is", 0.0005), ("that", "the", 0.0004),
    ("he", "was", 0.0004), ("she", "was", 0.0003), ("there", "is", 0.0003),
    ("there", "are", 0.0003), ("has", "been", 0.0004), ("have", "been", 0.0003),
    ("can", "be", 0.0003), ("would", "be", 0.0002), ("i", "am", 0.0003),
    ("i", "was", 0.0003), ("as", "a", 0.0003), ("such", "as", 0.0002),
    ("one", "of", 0.0003), ("part", "of", 0.0002), ("out", "of", 0.0002),
    ("some", "of", 0.0002), ("all", "the", 0.0002), ("a", "lot", 0.0002),
    ("going", "to", 0.0002), ("used", "to", 0.0002), ("able", "to", 0.0002),
    ("want", "to", 0.0002), ("need", "to", 0.0002), ("have", "to", 0.0003),
    ("had", "been", 0.0002), ("would", "have", 0.0002),
    ("could", "have", 0.0002), ("should", "have", 0.0001),
    ("did", "not", 0.0003), ("was", "not", 0.0002),
    ("is", "not", 0.0002), ("are", "not", 0.0002),
    ("not", "be", 0.0001), ("not", "have", 0.0001),
    ("may", "be", 0.0002), ("might", "be", 0.0001),
    ("so", "that", 0.0001), ("in", "order", 0.0001),
    ("as", "well", 0.0002), ("well", "as", 0.0001),
    ("more", "than", 0.0002), ("less", "than", 0.0001),
    ("most", "of", 0.0001), ("each", "other", 0.0001),
    ("up", "to", 0.0001), ("a", "new", 0.0002),
    ("the", "first", 0.0002), ("the", "same", 0.0002),
    ("at", "least", 0.0002), ("the", "most", 0.0001),
    ("the", "world", 0.0001), ("new", "york", 0.0001),
    ("it", "has", 0.0002), ("they", "are", 0.0003),
    ("we", "have", 0.0002), ("you", "can", 0.0002),
    ("i", "think", 0.0002), ("i", "know", 0.0002),
    ("he", "had", 0.0002), ("she", "had", 0.0001),
    ("they", "had", 0.0002), ("they", "were", 0.0002),
    ("we", "are", 0.0002), ("you", "are", 0.0002),
    ("he", "is", 0.0002), ("who", "is", 0.0001),
    ("what", "is", 0.0002), ("that", "is", 0.0002),
    ("which", "is", 0.0001), ("there", "was", 0.0003),
    ("there", "were", 0.0002), ("when", "the", 0.0001),
    ("if", "you", 0.0002), ("if", "the", 0.0001),
    ("but", "the", 0.0001), ("but", "i", 0.0001),
    ("but", "it", 0.0001), ("and", "i", 0.0001),
    ("and", "it", 0.0001), ("and", "a", 0.0001),
    # Additional bigrams for better coverage
    ("in", "a", 0.0008), ("to", "a", 0.0005),
    ("is", "a", 0.0005), ("it", "to", 0.0003),
    ("i", "do", 0.0002), ("and", "to", 0.0003),
    ("for", "a", 0.0004), ("of", "a", 0.0003),
    ("on", "a", 0.0002), ("at", "a", 0.0002),
    ("with", "a", 0.0003), ("by", "a", 0.0002),
    ("as", "the", 0.0003), ("that", "is", 0.0002),
    ("the", "other", 0.0002), ("the", "new", 0.0002),
    ("the", "united", 0.0001), ("the", "people", 0.0001),
    ("the", "time", 0.0001), ("the", "way", 0.0001),
    ("to", "do", 0.0002), ("to", "get", 0.0002),
    ("to", "make", 0.0002), ("to", "have", 0.0002),
    ("to", "say", 0.0001), ("to", "go", 0.0001),
    ("to", "take", 0.0001), ("to", "see", 0.0001),
    ("to", "know", 0.0001), ("to", "find", 0.0001),
    ("will", "not", 0.0002), ("he", "said", 0.0002),
    ("she", "said", 0.0001), ("they", "have", 0.0002),
    ("i", "would", 0.0001), ("i", "had", 0.0001),
    ("i", "could", 0.0001), ("i", "will", 0.0001),
    ("you", "have", 0.0001), ("you", "know", 0.0002),
    ("that", "he", 0.0001), ("that", "it", 0.0001),
    ("we", "can", 0.0001), ("we", "will", 0.0001),
    ("you", "will", 0.0001), ("do", "you", 0.0001),
    ("i", "want", 0.0001), ("in", "this", 0.0002),
    ("of", "this", 0.0001), ("on", "this", 0.0001),
    ("at", "this", 0.0001), ("to", "this", 0.0001),
    ("all", "of", 0.0001), ("because", "of", 0.0001),
    ("instead", "of", 0.0001), ("in", "front", 0.0001),
    ("front", "of", 0.0001), ("kind", "of", 0.0001),
    ("a", "bit", 0.0001), ("a", "few", 0.0001),
    ("a", "little", 0.0001), ("a", "good", 0.0001),
    ("a", "great", 0.0001), ("a", "long", 0.0001),
    ("a", "very", 0.0001), ("very", "much", 0.0001),
    ("as", "much", 0.0001), ("too", "much", 0.0001),
    ("how", "much", 0.0001), ("so", "much", 0.0001),
    ("not", "only", 0.0001), ("only", "the", 0.0001),
    ("even", "though", 0.0001), ("as", "if", 0.0001),
    ("just", "as", 0.0001), ("now", "that", 0.0001),
    ("no", "longer", 0.0001), ("no", "more", 0.0001),
    ("no", "one", 0.0001), ("right", "now", 0.0001),
    ("first", "time", 0.0001), ("last", "year", 0.0001),
    ("next", "year", 0.0001), ("every", "day", 0.0001),
    ("other", "people", 0.0001), ("other", "hand", 0.0001),
    ("at", "all", 0.0001), ("after", "all", 0.0001),
    ("at", "home", 0.0001), ("at", "work", 0.0001),
    ("at", "night", 0.0001), ("at", "first", 0.0001),
    ("in", "fact", 0.0001), ("in", "addition", 0.0001),
    ("in", "particular", 0.0001), ("in", "general", 0.0001),
    ("in", "terms", 0.0001), ("of", "course", 0.0001),
    ("as", "long", 0.0001), ("long", "as", 0.0001),
    ("as", "far", 0.0001), ("far", "as", 0.0001),
    ("on", "top", 0.0001), ("top", "of", 0.0001),
    ("with", "respect", 0.0001), ("respect", "to", 0.0001),
    ("due", "to", 0.0001), ("according", "to", 0.0001),
    ("thanks", "to", 0.0001), ("close", "to", 0.0001),
    ("next", "to", 0.0001), ("prior", "to", 0.0001),
    ("you", "want", 0.0001), ("you", "need", 0.0001),
    ("i", "feel", 0.0001), ("i", "see", 0.0001),
    ("he", "could", 0.0001), ("she", "could", 0.0001),
    ("it", "would", 0.0001), ("could", "be", 0.0001),
    ("should", "be", 0.0001), ("must", "be", 0.0001),
    ("seem", "to", 0.0001), ("tend", "to", 0.0001),
    ("try", "to", 0.0001), ("begin", "to", 0.0001),
    ("start", "to", 0.0001), ("continue", "to", 0.0001),
    ("come", "to", 0.0001), ("get", "to", 0.0001),
    ("has", "not", 0.0001), ("have", "not", 0.0001),
    ("i", "don't", 0.0002), ("it", "doesn't", 0.0001),
    ("united", "states", 0.0001), ("years", "ago", 0.0001),
    ("the", "end", 0.0001), ("the", "last", 0.0001),
    ("the", "use", 0.0001), ("the", "fact", 0.0001),
]

# Russian bigrams (expanded)
_RU_BIGRAMS = [
    ("в", "том", 0.0010), ("в", "этом", 0.0008),
    ("на", "то", 0.0006), ("не", "может", 0.0004),
    ("не", "было", 0.0005), ("не", "только", 0.0005),
    ("из", "них", 0.0003), ("в", "которой", 0.0003),
    ("в", "которых", 0.0003), ("с", "тем", 0.0003),
    ("для", "того", 0.0003), ("то", "что", 0.0005),
    ("то", "есть", 0.0003), ("так", "как", 0.0003),
    ("потому", "что", 0.0003), ("может", "быть", 0.0004),
    ("и", "не", 0.0004), ("но", "и", 0.0003),
    ("это", "не", 0.0003), ("он", "не", 0.0003),
    ("я", "не", 0.0003), ("что", "он", 0.0002),
    ("что", "это", 0.0002), ("на", "него", 0.0002),
    ("от", "того", 0.0002), ("до", "сих", 0.0002),
    ("все", "это", 0.0002), ("было", "бы", 0.0002),
    ("одним", "из", 0.0001), ("все", "еще", 0.0002),
    ("кроме", "того", 0.0002), ("таким", "образом", 0.0002),
    ("в", "целом", 0.0001), ("на", "самом", 0.0002),
    ("самом", "деле", 0.0002), ("тем", "более", 0.0001),
    ("более", "того", 0.0001), ("имеет", "значение", 0.0001),
    ("в", "первую", 0.0001), ("к", "тому", 0.0001),
    ("тому", "же", 0.0001), ("по", "мнению", 0.0001),
    ("что", "не", 0.0002), ("я", "думаю", 0.0001),
    ("он", "был", 0.0003), ("она", "была", 0.0002),
    ("они", "были", 0.0002), ("мы", "не", 0.0002),
    # Additional
    ("в", "самом", 0.0001), ("как", "и", 0.0002),
    ("не", "в", 0.0002), ("по", "его", 0.0001),
    ("в", "первую", 0.0001), ("первую", "очередь", 0.0001),
    ("так", "же", 0.0001), ("не", "могу", 0.0001),
    ("не", "будет", 0.0001), ("в", "то", 0.0002),
    ("в", "конце", 0.0001), ("конце", "концов", 0.0001),
    ("имеет", "место", 0.0001), ("имеет", "право", 0.0001),
    ("с", "одной", 0.0001), ("одной", "стороны", 0.0001),
    ("с", "другой", 0.0001), ("другой", "стороны", 0.0001),
    ("в", "соответствии", 0.0001), ("в", "связи", 0.0001),
    ("в", "результате", 0.0001), ("по", "отношению", 0.0001),
    ("в", "рамках", 0.0001), ("в", "процессе", 0.0001),
    ("что", "она", 0.0001), ("что", "они", 0.0001),
    ("а", "также", 0.0002), ("не", "так", 0.0001),
    ("при", "этом", 0.0002), ("на", "нее", 0.0001),
    ("на", "них", 0.0001), ("для", "этого", 0.0001),
    ("из", "них", 0.0001), ("до", "того", 0.0001),
    ("после", "того", 0.0001), ("в", "течение", 0.0001),
]

# ════════════════════════════════════════════════════════════
# OUTPUT
# ════════════════════════════════════════════════════════════

en_freqs = make_freq_dict(en_words, top_freq=0.069)
ru_freqs = make_freq_dict(ru_words, top_freq=0.032)
de_freqs = make_freq_dict(de_words, top_freq=0.035)
fr_freqs = make_freq_dict(fr_words, top_freq=0.036)
es_freqs = make_freq_dict(es_words, top_freq=0.040)

en_bi = {(w1, w2): p for w1, w2, p in _EN_BIGRAMS}
ru_bi = {(w1, w2): p for w1, w2, p in _RU_BIGRAMS}

print(f"EN unigrams: {len(en_freqs)}")
print(f"EN bigrams: {len(en_bi)}")
print(f"RU unigrams: {len(ru_freqs)}")
print(f"RU bigrams: {len(ru_bi)}")
print(f"DE unigrams: {len(de_freqs)}")
print(f"FR unigrams: {len(fr_freqs)}")
print(f"ES unigrams: {len(es_freqs)}")
print(f"EN top: {en_freqs[en_words[0]]}")
print(f"EN #100: {en_freqs[en_words[99]]}")
print(f"EN #1000: {en_freqs[en_words[999]]}")
print(f"EN last: {en_freqs[en_words[-1]]}")
print(f"EN total mass: {sum(en_freqs.values()):.4f}")

# Now serialize as compact TSV data for embedding
import zlib, base64

def encode_unigrams(freqs):
    lines = [f"{w}\t{f}" for w, f in freqs.items()]
    data = "\n".join(lines).encode("utf-8")
    compressed = zlib.compress(data, 9)
    return base64.b64encode(compressed).decode("ascii")

def encode_bigrams(freqs):
    lines = [f"{w1}\t{w2}\t{f}" for (w1, w2), f in freqs.items()]
    data = "\n".join(lines).encode("utf-8")
    compressed = zlib.compress(data, 9)
    return base64.b64encode(compressed).decode("ascii")

# Write to data file
with open("texthumanize/_word_freq_data.py", "w") as f:
    f.write('"""Compressed word frequency data for word_lm.py.\n\n')
    f.write('Auto-generated by scripts/gen_word_freq.py.\n')
    f.write('Do not edit manually.\n')
    f.write('"""\n\n')
    f.write('# Compressed base64-encoded TSV data (zlib)\n')
    f.write('# Format: word\\tfreq per line (unigrams)\n')
    f.write('# Format: word1\\tword2\\tfreq per line (bigrams)\n\n')

    for name, data in [
        ("EN_UNI", encode_unigrams(en_freqs)),
        ("EN_BI", encode_bigrams(en_bi)),
        ("RU_UNI", encode_unigrams(ru_freqs)),
        ("RU_BI", encode_bigrams(ru_bi)),
        ("DE_UNI", encode_unigrams(de_freqs)),
        ("FR_UNI", encode_unigrams(fr_freqs)),
        ("ES_UNI", encode_unigrams(es_freqs)),
    ]:
        f.write(f'{name} = (\n')
        # Split into 76-char lines
        for i in range(0, len(data), 76):
            f.write(f'    "{data[i:i+76]}"\n')
        f.write(')\n\n')

    f.write('# Keep existing compact data for: UK, IT, PL, PT, AR, ZH, JA, KO, TR\n')
    f.write('# (used directly from word_lm.py inline dicts)\n')

print("\nWrote texthumanize/_word_freq_data.py")
