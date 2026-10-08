# Bedienung

Alles, was man wissen muss, um damit zu arbeiten. Der Bildschirmaufbau
selbst ändert sich nicht mehr.

## Das Menü

```
╲     ╲     ╲     ╲     ╲     ╲  NEW AIR
 ╲   ╱ ╲   ╱ ╲   ╱ ╲   ╱ ╲   ╱ ╲  MEDIA GROUP
  ╲ ╱   ╲ ╱   ╲ ╱   ╲ ◆   ╲ ╱
   ╲     ╲     ◆     ╲     ╲
  ╱ ╲   ╱ ◆   ╱ ╲   ╱ ◆   ╱ ╲
 ╱   ◆ ╱   ╲ ╱   ╲ ╱   ╲ ╱   ╲ ╱
╲     ╲     ╲     ◆     ╲     ╲
 ╲   ╱ ╲   ╱ ╲   ╱ ╲   ╱ ╲   ╱ ╲

 ▶  1. Angebot erstellen         Aus Leistungen ein Angebot bauen
    2. Rechnung erstellen        Aus Leistungen abrechnen
    3. Kunden                    Kunden anlegen, ansehen, suchen
    4. Leistungen                Die Preisliste pflegen
    5. Dokumente                 Angebote und Rechnungen durchsehen
    6. Stammdaten                Firma, Bank, Logo, Brieftexte
    7. PDF neu schreiben         Ein Dokument noch einmal ausgeben
    8. Rechnungsordner öffnen    Den Ordner mit den PDF zeigen
    q. Beenden                   Das Programm verlassen
```

## Wie du dich bewegst

**↑ und ↓** verschieben die Auswahl. Das Bild bleibt ruhig, es wird nur die
markierte Zeile neu gezeichnet.

**⏎ (Enter)** bestätigt den markierten Punkt.

| Taste | Wirkung |
|---|---|
| `1` bis `9`, `q` | direkt zum Punkt |
| erster Buchstabe | passt auf den Punkt |
| `n` | neu anlegen |
| `F2` | ändern |
| `Entf` | löschen, fragt vorher nach |
| `esc` | einen Schritt zurück |
| `Strg+Q` | beenden |

Die Pfeiltasten brauchen ein Terminal, das sie kennt: **Terminal.app**,
*iTerm*, Windows Terminal oder PowerShell. In der klassischen
Eingabeaufforderung von Windows funktionieren sie teilweise nicht — dort
helfen die Zahlen oder der Anfangsbuchstabe.

Ohne Farbe geht alles auch: mit `NO_COLOR=1` wird alles schwarz geschrieben,
das Menü bleibt bedienbar.

Das Terminalfenster braucht mindestens 80 Spalten und 24 Zeilen. Ist es
kleiner, passt das Menü nicht und es sieht abgeschnitten aus.

## So arbeitest du damit

**Die Felder sind vorbelegt.** Wo sich etwas ausrechnen lässt, steht der
Vorschlag schon drin — Datum heute, Nummer als nächste freie, Fälligkeit in
zwei Wochen. Enter genügt.

**Positionen wählst du aus der Preisliste**, statt sie abzutippen. Wähle dort
eine Leistung, dann justierst du Menge und Preis.

**Vor dem Speichern kommt die Kontrolle**: alle Positionen, der Gesamtbetrag,
der Brieftext. Erst dann entsteht das Dokument und die PDF, und der Pfad wird
dir genannt.

## Nummern

Vier Stellen, führende Nullen: `0001`, `0002`, `0003`. **Angebot und
Rechnung kommen aus einem Zähler**, damit nebeneinandersteht, dass sie zum
selben Vorgang gehören. Angebot `0001` und Rechnung `0002` sind Paar und
Vorgang.

Die Nummer wird vorgeschlagen, aber sie gehört dir und deinem Steuerberater.
Die Datenbank lässt keine doppelte Nummer zu, auch nicht über die Art hinweg.

## Angebot in Rechnung

Steht die Auswahl in der Dokumentenliste auf einem **Angebot**, macht `r`
daraus eine Rechnung. Kunde, alle Positionen, Texte und Preise wandern mit,
samt der Verknüpfung zur Preisliste. Das Angebot bleibt als Beleg stehen.

Offen bleiben nur Nummer, Datum und Fälligkeit — die stehen schon in der
Kontrolle, weil sie sich von Rechnung zu Rechnung unterscheiden.

Steht die Auswahl auf keinem Angebot, fängt `r` wie bisher eine neue Rechnung
an. Die Taste meint immer dasselbe: abrechnen.

## Textbausteine

Unter `6` → `3` und `4`: je ein Text für Angebote und für Rechnungen.

Das ist ein eigener Editor mit Zeilennummern, kein einzeiliges Feld — der
Text hat Absätze, und die müssen beim Speichern unbeschädigt bleiben. Leerzeilen
trennen Absätze.

| Taste | Wirkung |
|---|---|
| `Strg+S` | speichern |
| `Strg+R` | den mitgelieferten Vorschlag zurückholen |
| `esc` | abbrechen |

Unter dem Feld stehen die Namen, die du verwenden kannst.

Doppelte Klammern ersetzt das Programm:

| Platzhalter | ergibt |
|---|---|
| `{{Kunde}}` | Soundcheck GmbH |
| `{{Kunde_Anrede}}` | Herr Mustermann |
| `{{Ansprechpartner}}` | Max Mustermann |
| `{{Nummer}}` | 2026-014 |
| `{{Datum}}` | 06.10.2026 |
| `{{Faellig}}` | 20.10.2026 |
| `{{Gueltig_bis}}` | 27.10.2026 |
| `{{Betrag}}` | 3.290,00 € |
| `{{Anzahl_Positionen}}` | 2 |
| `{{EigeneFirma}}` | New Air Media Group |
| `{{Bank}}` | Deutsche Kreditbank |
| `{{IBAN}}` | DE02 1203 0000 0000 2020 51 |

**Tippfehler bleiben sichtbar.** `{{Kuude}}` steht als `{{Kuude}}` auf der
PDF, statt still zu verschwinden. Beim Speichern sagt das Programm, welche
Namen es nicht kennt.

`{{Kunde_Anrede}}` schneidet den Vornamen ab: aus „Herr Max Mustermann" wird
„Herr Mustermann". Damit kannst du frei formulieren statt in
Höflichkeitsformeln zu verfallen.

## Rabatt

Im Schritt mit den Positionen gibt es einen eigenen Punkt **Rabatt
eintragen**. Gefragt wird nur der Betrag — das Minus setzt das Programm,
weil ein Rabatt immer abzieht. Die Bezeichnung bleibt „Rabatt" und ist
änderbar.

```
Aufnahme Ton                    2 Tag    1.700,00 €
Mischung und Mastering         10 Stunde     950,00 €
Rabatt                                        -300,00 €
                                   Gesamtbetrag  2.350,00 €
```

Auf der PDF steht der Rabatt in der Akzentfarbe, damit er als eigener Posten
erkennbar ist, ohne dass die Tabelle bunt wird. Er funktioniert auf Angebot
und Rechnung gleichermaßen, und er wandert bei der Umwandlung eines Angebots
mit.

Es gibt keinen Prozentrabatt. Dafür müsste das Programm den Betrag aus der
Zwischensumme rechnen, was bei einem Rabatt auf einen Rabatt unangenehm wird.

## Wie die PDF aussieht

- eine einzige Akzentfarbe, `#512E80`, aus dem Logo ausgelesen
- viel Weißraum, dünne Linien statt Kästen
- gesperrte Spalten: Bezeichnung links, Preise rechts
- das Logo behält Proportionen und steht auf jeder Seite
- Fußzeile mit Firmenzeile und Seitenzahl
- auf Angeboten steht keine Steuernummer, auf Rechnungen schon

Preise enthalten keine Steuerausweisung. Die App ist als Werkzeug für
Kleinunternehmer gebaut; wer umsatzsteuerpflichtig ist, trägt den Betrag
inklusive Steuer als Endpreis ein.
