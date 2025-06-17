# Document Fetcher

Dies ist ein Tool zum Abrufen und Verarbeiten von Dokumenten aus E-Mails, insbesondere Bilanzen. Es nutzt OCR-Technologie, um Text aus PDFs zu extrahieren, sodass diese automatisch mit Datenbankeinträgen für Finanzprüfungen verglichen werden können.

## Inhaltsverzeichnis

- [Überblick](#überblick)
- [Funktionen](#funktionen)
- [Installation](#installation)
    - [Voraussetzungen](#voraussetzungen)
    - [Virtuelle Umgebung einrichten](#virtuelle-umgebung-einrichten)
    - [Umgebungskonfiguration](#umgebungskonfiguration)
    - [App-Initialisierung](#app-initialisierung)
    - [E-Mails erfassen](#e-mails-erfassen)
    - [Datenbank-Setup](#datenbank-setup)
- [Verwendung](#verwendung)
    - [Anwendung starten](#anwendung-starten)
    - [Web-Oberfläche verwenden](#web-oberfläche-verwenden)
    - [Verarbeitungsablauf](#verarbeitungsablauf)
- [Konfiguration](#konfiguration)
- [Docker-Bereitstellung](#docker-bereitstellung)
- [Fehlerbehebung](#fehlerbehebung)
- [Entwicklung](#entwicklung)
    - [Projektstruktur](#projektstruktur)
    - [Modulübersicht](#modulübersicht)

## Überblick

Document Fetcher automatisiert den jährlichen Prüfungsprozess, bei dem Prüfer Bilanzen verifizieren müssen. Die Anwendung verbindet sich mit E-Mail-Postfächern, ruft PDF-Dokumente ab, nutzt OCR zur Extraktion von Text und Tabellendaten und vergleicht die extrahierten Werte automatisch mit Datenbankeinträgen.

## Funktionen

- E-Mail-Postfach-Integration
- PDF-Dokumentenextraktion und -analyse
- OCR-Verarbeitung mit EasyOCR und Tesseract
- Automatisierte Datenverifizierung gegen Datenbankeinträge
- Webbasierte Benutzeroberfläche mit Streamlit
- Workflow-Management für Dokumentenverarbeitung
- Zertifikatsgenerierung für verifizierte Dokumente
- **Zugriffskontrollsystem**: Rollenbasierte (Admin, Prüfer, Inspektor) und ressourcenbasierte Berechtigungen
- **Excel-Import**: Masseninitialisierung von Prüfungssaisons aus Excel-Dateien
- **Konfigurationsverwaltung**: Dynamische Anwendungseinstellungen über Konfigurationsdateien
- **Benutzer-Kunden-Zugriffsverwaltung**: Granulare Kontrolle darüber, welche Benutzer auf welche Kunden zugreifen können
- **E-Mail-Antwortvorlagen**: Automatisierte E-Mail-Antwortgenerierung
- **Sitzungsverwaltung**: Sichere Sitzungsbehandlung mit Ablaufzeit
- **Anmeldesicherheit**: Verfolgung von Anmeldeversuchen und IP-basierte Überwachung
- **Audit-Protokollierung**: Umfassende Protokollierung aller Benutzeraktionen

## Installation

### Voraussetzungen

Stellen Sie vor der Installation sicher, dass Folgendes installiert ist:
- Python 3.11 oder höher
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (optional, für OCR-Textextraktion)
- Systembibliotheken für OpenCV und PDF-Verarbeitung

**Hinweis**: Die Anwendung verwendet PyMuPDF anstelle von Poppler für die PDF-Verarbeitung.

Zusätzlich erforderliche Python-Bibliotheken:
- **PyMuPDF**: PDF-Verarbeitung und -Manipulation
- **python-docx** und **docx2pdf**: Zertifikatsgenerierung
- **reportlab**: Erweiterte PDF-Manipulation
- **openpyxl**: Excel-Dateiunterstützung
- **PyTorch** (optional): GPU-beschleunigte OCR

#### Installation der Voraussetzungen auf verschiedenen Betriebssystemen:

**Windows:**
```bash
# Tesseract OCR über Chocolatey installieren (https://chocolatey.org/)
choco install tesseract

# Systembibliotheken für OpenCV installieren
# Diese sind normalerweise bei Python-Paketen unter Windows enthalten
```

**macOS:**
```bash
# Tesseract OCR über Homebrew installieren
brew install tesseract

# Systembibliotheken für OpenCV installieren
brew install opencv
```

**Linux (Ubuntu/Debian):**
```bash
# Tesseract OCR installieren
sudo apt-get update
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-deu  # Deutsche Sprachunterstützung

# Systembibliotheken für OpenCV und PDF-Verarbeitung installieren
sudo apt-get install libgl1-mesa-glx libglib2.0-0 libsm6 libxrender1 libxext6
```

### Virtuelle Umgebung einrichten

Es wird empfohlen, die Anwendung in einer virtuellen Umgebung zu installieren:

1. Verzeichnis auswählen:
```bash
cd rpa-document-fetcher
```

2. Virtuelle Umgebung erstellen:
```bash
# Mit venv
python -m venv venv

# Mit conda (Alternative)
conda create -n document-fetcher python=3.11
```

3. Virtuelle Umgebung aktivieren:
```bash
# Unter Windows
venv\Scripts\activate

# Unter macOS/Linux
source venv/bin/activate

# Mit conda
conda activate document-fetcher
```

4. Erforderliche Pakete installieren:
```bash
pip install -r requirements.txt

# Optional: PyTorch mit CUDA-Unterstützung für GPU-beschleunigte OCR installieren
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Umgebungskonfiguration

Erstellen Sie eine `.env`-Datei im Hauptverzeichnis mit folgenden Variablen:
```
# Protokollierungskonfiguration
LOG_LEVEL_CONSOLE=20
LOG_LEVEL_FILE=10
LOG_PATH=./.filesystem/logs/

# Dateisystempfade
FILESYSTEM_PATH=./.filesystem/
CERTIFICATE_TEMPLATE_PATH=./.filesystem/certificate_template.docx
CERTIFICATE_TOS_PATH=./.filesystem/terms_conditions.pdf

# Entwicklungsmodus-Flag
DEV_MODE=true
  
# OCR-Konfiguration
OCR_USE_GPU=false

# E-Mail-Server-Konfiguration
IMAP_HOST=ihr.mail.server.com
IMAP_PORT=993
IMAP_USER=ihr_benutzername
IMAP_PASSWORD=ihr_passwort
INBOX=ihr_postfach_name

# Für Entwicklungstests mit Mock-E-Mails
EXAMPLE_MAIL_PATH=./example_mails/
```
**Tipp:** Sie können das [Umgebungsbeispiel](./.env.example) dafür verwenden.

### App-Initialisierung

Der einfachste Weg, die Anwendung einzurichten, ist die Verwendung des bereitgestellten Initialisierungsskripts:
```bash
python app_init.py
```

Dieses Skript führt folgende Aufgaben aus:
- Erstellt die notwendige Verzeichnisstruktur
- Richtet eine Standard-Umgebungsdatei ein
- Initialisiert die Datenbank mit Beispieldaten
- Erstellt Standard-Konfigurationsdateien
- Richtet Zertifikatsvorlagen ein
- Überprüft, ob alle Komponenten bereit sind

#### Initialisierungsoptionen

Das Skript unterstützt mehrere Befehlszeilenoptionen:

```bash
# Mit Standardeinstellungen initialisieren
python app_init.py
```
```bash
# Alles zurücksetzen (Warnung: löscht vorhandene Daten)
python app_init.py --force-reset
```
```bash
# Test-E-Mails während der Initialisierung herunterladen
python app_init.py --download-emails --num-emails 20
```
```bash
# Nur die Dateisystemstruktur einrichten ohne Komponenten zu initialisieren
python app_init.py --setup-only
```
```bash
# Datenbankinitialisierung überspringen
python app_init.py --skip-db-init
```
```bash
# Alle verfügbaren Optionen anzeigen
python app_init.py --help
```

Nach erfolgreicher Initialisierung erhalten Sie Anmeldedaten und Anweisungen zum Starten der Anwendung.

### E-Mails erfassen

Dieses Projekt benötigt Zugriff auf ein E-Mail-Postfach, um Dokumente abzurufen. Für Entwicklungszwecke können Sie Beispiel-E-Mails erfassen, um offline zu arbeiten, indem Sie das bereitgestellte E-Mail-Download-Skript verwenden.

#### Verwendung des E-Mail-Downloaders

1. Stellen Sie sicher, dass Ihre `.env`-Datei mit Ihren E-Mail-Anmeldedaten konfiguriert ist:
   ```
   IMAP_HOST=ihr.mail.server.com
   IMAP_PORT=993
   IMAP_USER=ihr_benutzername
   IMAP_PASSWORD=ihr_passwort
   INBOX=ihr_postfach_name
   FILESYSTEM_PATH=./.filesystem/
   ```

2. Führen Sie das E-Mail-Download-Skript aus:
   ```bash
   # Stellen Sie sicher, dass Ihre virtuelle Umgebung aktiviert ist
   source venv/bin/activate  # oder venv\Scripts\activate unter Windows
   
   # Führen Sie das E-Mail-Download-Skript aus
   python examples/email_downloader.py
   ```

3. Standardmäßig wird das Skript:
    - Eine Verbindung zu Ihrem konfigurierten E-Mail-Server herstellen
    - Die 10 neuesten E-Mails herunterladen
    - Sie in `./example_mails/` speichern

4. Das Skript unterstützt mehrere Befehlszeilenoptionen:
   ```bash
   # 20 E-Mails statt der standardmäßigen 10 herunterladen
   python examples/email_downloader.py --num-emails 20
   
   # E-Mails in einem benutzerdefinierten Verzeichnis speichern
   python examples/email_downloader.py --output-dir ./example_mails
   
   # Verfügbare Postfächer auflisten und beenden
   python examples/email_downloader.py --list-mailboxes
   
   # Eine spezifische Suchanfrage verwenden
   python examples/email_downloader.py --search "SUBJECT pdf"
   
   # Hilfeinformationen anzeigen
   python examples/email_downloader.py --help
   ```

5. Für die Offline-Entwicklung konfigurieren Sie nach dem Herunterladen der E-Mails diese Umgebungsvariablen:
   ```
   DEV_MODE=true
   EXAMPLE_MAIL_PATH=./example_mails/
   ```

Die heruntergeladenen E-Mails werden automatisch verwendet, wenn die Anwendung im Entwicklungsmodus läuft, sodass Sie die Dokumentenverarbeitung testen können, ohne eine Verbindung zum Mail-Server herzustellen.

#### Fehlerbehebung bei der E-Mail-Erfassung

- Bei Verbindungsproblemen überprüfen Sie Ihre E-Mail-Server-Anmeldedaten
- Für Gmail-Konten müssen Sie möglicherweise ein [App-Passwort](https://support.google.com/accounts/answer/185833) erstellen
- Stellen Sie sicher, dass Ihr E-Mail-Anbieter IMAP-Zugriff erlaubt
- Überprüfen Sie, ob das Ausgabeverzeichnis existiert und beschreibbar ist

### Datenbank-Setup

Diese Anwendung verwendet SQLite für die Datenspeicherung. Die Verzeichnisstruktur für die Datenbank ist:

```
./
├── examples/
│   ├── db_init.py                  # Datenbankinitialisierungsskript
│   ├── email_downloader.py         # E-Mail-Download-Dienstprogramm
│   ├── insert_example_data.sql     # Beispieldaten zum Testen
│   └── email_templates/            # E-Mail-Antwortvorlagen
│       └── response_template.html
├── src/                            # Quellcodeverzeichnis
│   └── schema.sql                  # Datenbankschema-Definition
└── .filesystem/                    # Datenspeicherverzeichnis
    └── database.db                 # SQLite-Datenbankdatei (vom Initialisierungsskript erstellt)
```

Führen Sie das Initialisierungsskript aus, um die Datenbank zu erstellen und mit Beispieldaten zu füllen:
```bash
python examples/db_init.py
```

Das Skript wird:
1. Die Datenbankdatei erstellen, falls sie nicht existiert
2. Die erforderlichen Tabellen erstellen (einschließlich neuer Zugriffskontrolltabellen)
3. Beispieldaten einfügen, wenn die Datenbank leer ist
4. Indizes und Trigger für die Leistung einrichten

Das Skript unterstützt mehrere Befehlszeilenargumente zur Anpassung des Datenbankinitialisierungsprozesses:
```bash
python examples/db_init.py --help
```

Um die Datenbank zurückzusetzen und alle Daten zu entfernen:
```bash
python examples/db_init.py --force-reset
```

#### Datenbankschema

Die Datenbank enthält folgende Haupttabellen:
- **client**: Kundeninformationen und Finanzdaten
- **audit_case**: Aktive Prüfungsfälle und deren Stadien
- **document**: Dokumentenverfolgung und Verarbeitungsstatus
- **user**: Benutzerkonten und Authentifizierung
- **session_key**: Aktive Benutzersitzungen
- **user_client_access**: Benutzer-zu-Kunden-Zugriffsberechtigungen
- **login_attempts**: Sicherheitsverfolgung für Anmeldeversuche

## Verwendung

### Anwendung starten

Nach Abschluss der Installations- und Konfigurationsschritte starten Sie die Anwendung mit Streamlit:

```bash
# Stellen Sie sicher, dass Sie sich im Projektwurzelverzeichnis befinden
cd rpa-document-fetcher

# Aktivieren Sie Ihre virtuelle Umgebung, falls noch nicht aktiviert
source venv/bin/activate  # oder venv\Scripts\activate unter Windows

# Starten Sie die Anwendung
streamlit run src/main.py
```

Die Anwendung ist unter http://localhost:8501 in Ihrem Webbrowser verfügbar.

### Web-Oberfläche verwenden

1. **Anmeldung**: Verwenden Sie die auf dem Anmeldebildschirm bereitgestellten Demo-Konten:
    - Admin: `admin@example.com` / `admin123`
    - Prüfer: `auditor@example.com` / `auditor123`
    - Inspektor: `inspector@example.com` / `inspector123`

2. **Navigation**: Verwenden Sie die Seitenleiste zur Navigation zwischen verschiedenen Bereichen:
    - Startseite/Document Fetcher: Hauptschnittstelle zur Verarbeitung von E-Mails
    - Aktive Fälle: Prüfungsfälle anzeigen und verwalten
    - Einstellungen: Anwendungseinstellungen konfigurieren
    - Über: Anwendungsinformationen und Protokolle anzeigen

3. **Startseite**:
    - Eingehende E-Mails mit Anhängen anzeigen
    - Einzelne Dokumente auswählen oder alle Dokumente verarbeiten
    - Dokumenteneinreichungsverhältnis im Kreisdiagramm überwachen
    - Ausgewählte E-Mails verarbeiten, um Bilanzdaten zu extrahieren

4. **Seite Aktive Fälle**:
    - Alle aktiven Prüfungsfälle in Tabellenformat anzeigen
    - Einzelne Fälle zur Detailansicht auswählen
    - Fortschritt jedes Falls durch den Prüfungsworkflow überwachen
    - Kommentare zu Fällen für interne Dokumentation hinzufügen
    - Verarbeitete Dokumente und Zertifikate herunterladen
    - Zugriff wird basierend auf Benutzerberechtigungen gefiltert (Nicht-Admin-Benutzer sehen nur ihre zugewiesenen Fälle)

5. **Einstellungsseite** (nur Admin):
    - **Anwendungseinstellungen**: Zertifikatsvorlagen und Archiveinstellungen konfigurieren
    - **Prüfungseinstellungen**: Jährliche Prüfungsprozesse aus Excel-Dateien initialisieren
    - **Benutzerverwaltung**: Benutzerkonten erstellen und verwalten
    - **Zugriffskontrolle**: Benutzer-Kunden-Berechtigungen verwalten

6. **Über-Seite**:
    - Anwendungsinformationen anzeigen
    - Auf Anwendungsprotokolle zur Fehlerbehebung zugreifen
    - Probleme oder Fehler melden

### Benutzerrollen und Berechtigungen

Die Anwendung implementiert ein umfassendes rollenbasiertes Zugriffskontrollsystem:

#### Admin-Rolle
- Vollzugriff auf alle Funktionen und Kunden
- Kann Benutzer und Berechtigungen verwalten
- Prüfungssaisons aus Excel initialisieren
- Abgeschlossene Fälle archivieren
- Anwendungseinstellungen konfigurieren

#### Inspektor-Rolle
- Zugewiesene Fälle anzeigen und bearbeiten
- Zertifikate generieren
- Anwendungsprotokolle anzeigen
- Beschränkt auf zugewiesene Kunden

#### Prüfer-Rolle
- Zugewiesene Fälle anzeigen und bearbeiten
- Beschränkt auf zugewiesene Kunden
- Grundlegende Fallverwaltung

### Verarbeitungsablauf

Der Dokumentenverarbeitungsablauf besteht aus folgenden Hauptphasen:

1. **Dokumentenempfang (Phase 1)**:
    - Die Anwendung verbindet sich mit dem konfigurierten E-Mail-Postfach und ruft E-Mails mit PDF-Anhängen ab
    - Dokumente werden anhand ihrer BaFin-ID identifiziert und mit dem entsprechenden Kunden verknüpft
    - Wenn kein passender Kunde gefunden wird, bleibt das Dokument in Phase 1

2. **Datenverifizierung (Phase 2)**:
    - OCR extrahiert Text und Tabellendaten aus den PDF-Dokumenten
    - Das System identifiziert wichtige Finanzkennzahlen und Positionsnummern
    - Extrahierte Werte werden mit den Datenbankeinträgen verglichen
    - Eine Vergleichstabelle wird generiert, die Übereinstimmungen und Abweichungen zeigt
    - Wenn alle erforderlichen Werte übereinstimmen, geht der Fall zu Phase 3 über

3. **Zertifikatsgenerierung (Phase 3)**:
    - Nach der Verifizierung wird ein Zertifikat generiert, das die Datenübereinstimmung bestätigt
    - Das Zertifikat enthält Kundeninformationen, Validierungsdatum und Prüfungsreferenz
    - Das Zertifikat wird mit der ersten Seite des eingereichten Dokuments kombiniert
    - Das vollständige Zertifikatspaket kann von der Seite Aktive Fälle heruntergeladen werden

4. **Prozessabschluss (Phase 4)**:
    - Alle Dokumente und das Zertifikat stehen zum Download zur Verfügung
    - Der Prozess wird als abgeschlossen markiert
    - Der Fall kann von der Einstellungsseite archiviert werden

5. **Archivierung (Phase 5)**:
    - Abgeschlossene Fälle werden zur Aufbewahrung archiviert
    - Archivierte Fälle erscheinen nicht mehr in der Ansicht Aktive Fälle

#### Excel-Import für Prüfungssaison

Administratoren können Prüfungssaisons durch Hochladen von Excel-Dateien initialisieren:
- Excel-Dateien mit Kundendaten und Prüferzuweisungen hochladen
- Das System validiert die Excel-Struktur und erforderliche Spalten
- Erstellt oder aktualisiert Kundendatensätze basierend auf BaFin-IDs
- Erstellt automatisch Benutzerkonten für Prüfer/Inspektoren bei Bedarf
- Gewährt angemessene Zugriffsberechtigungen basierend auf Zuweisungen
- Generiert detaillierte Importberichte mit Erfolgs-/Fehlerzählungen

Um Dokumente zu verarbeiten:
1. Navigieren Sie zur Startseite/Document Fetcher
2. Zeigen Sie die Liste der verfügbaren E-Mails an
3. Wählen Sie E-Mails zur Verarbeitung aus oder klicken Sie auf "Alle Dokumente verarbeiten"
4. Verfolgen Sie den Fortschritt im Bereich Aktive Fälle
5. Überprüfen Sie extrahierte Daten und Vergleichsergebnisse
6. Generieren Sie Zertifikate für verifizierte Dokumente
7. Schließen Sie Fälle ab und archivieren Sie sie

## Konfiguration

Die Anwendung verwendet mehrere Konfigurationsmethoden:

1. **Umgebungsvariablen** (`.env`-Datei)
2. **Konfigurationsdatei** (`src/config.cfg`)
3. **Dynamische Einstellungen** über die Web-Oberfläche

### Konfigurationsdatei (config.cfg)

Die Anwendung erstellt automatisch eine Konfigurationsdatei mit Standardeinstellungen:

```ini
[APP_SETTINGS]
certificate_template_path = ./.filesystem/certificate_template.docx
terms_conditions_path = ./.filesystem/terms_conditions.pdf
archive_file_prefix = audit_archive
```

Diese Einstellungen können über die Einstellungsseite in der Web-Oberfläche geändert werden.

## Docker-Bereitstellung

Die Anwendung enthält eine Dockerfile für die containerisierte Bereitstellung:

```bash
# Docker-Image erstellen
docker build -f deployment/Dockerfile -t rpa-document-fetcher .

# Container ausführen
docker run -p 8501:8501 \
  -e IMAP_HOST=ihr.mail.server.com \
  -e IMAP_PORT=993 \
  -e IMAP_USER=ihr_benutzername \
  -e IMAP_PASSWORD=ihr_passwort \
  -e INBOX=ihr_postfach_name \
  -e DEV_MODE=false \
  rpa-document-fetcher
```

Das Docker-Image enthält:
- Python 3.11 Basis
- Tesseract OCR mit deutscher Sprachunterstützung
- Alle erforderlichen Systembibliotheken für OpenCV
- PyTorch mit CUDA-Unterstützung für GPU-Beschleunigung
- Automatische Datenbankinitialisierung beim Start

Für die Produktionsbereitstellung mit persistenten Daten:

```bash
# Volumes für persistente Daten erstellen
docker volume create rpa-filesystem
docker volume create rpa-logs

# Mit Volumes ausführen
docker run -p 8501:8501 \
  -v rpa-filesystem:/app/.filesystem \
  -v rpa-logs:/app/.filesystem/logs \
  -e IMAP_HOST=ihr.mail.server.com \
  -e IMAP_PORT=993 \
  -e IMAP_USER=ihr_benutzername \
  -e IMAP_PASSWORD=ihr_passwort \
  -e INBOX=ihr_postfach_name \
  -e DEV_MODE=false \
  rpa-document-fetcher
```

## Fehlerbehebung

### Häufige Probleme

**OCR funktioniert nicht korrekt**:
- Stellen Sie sicher, dass Tesseract ordnungsgemäß installiert und in Ihrem System-PATH ist
- Überprüfen Sie, ob das deutsche Sprachpaket für Tesseract installiert ist (tesseract-ocr-deu)
- Prüfen Sie, ob die PDF-Dokumente nicht mit zu niedriger Auflösung gescannt wurden
- Für GPU-Beschleunigung stellen Sie sicher, dass CUDA ordnungsgemäß installiert ist und setzen Sie `OCR_USE_GPU=true`

**E-Mail-Verbindungsprobleme**:
- Überprüfen Sie Ihre E-Mail-Server-Anmeldedaten in der .env-Datei
- Stellen Sie sicher, dass Ihr E-Mail-Server IMAP-Verbindungen erlaubt
- Bei Verwendung von Google benötigen Sie möglicherweise ein App-Passwort anstelle Ihres regulären Passworts
- Überprüfen Sie die Firewall-Einstellungen für Port 993 (IMAP SSL)

**Datenbankfehler**:
- Führen Sie `python examples/db_init.py --force-reset` aus, um die Datenbank zurückzusetzen
- Stellen Sie sicher, dass das .filesystem-Verzeichnis existiert und beschreibbar ist
- Prüfen Sie, ob die SQLite-Datenbank nicht von einem anderen Prozess gesperrt ist
- Überprüfen Sie die Dateiberechtigungen für die Datenbankdatei

**Web-Oberfläche lädt nicht**:
- Stellen Sie sicher, dass Streamlit ordnungsgemäß installiert ist: `pip install streamlit`
- Prüfen Sie, ob ein anderer Prozess Port 8501 verwendet
- Versuchen Sie es mit explizitem Host und Port: `streamlit run src/main.py --server.port=8501 --server.address=0.0.0.0`

**Zugriffskontrollprobleme**:
- Überprüfen Sie die Benutzerberechtigungen in der Datenbank
- Prüfen Sie die user_client_access-Tabelle auf ordnungsgemäße Zuweisungen
- Stellen Sie sicher, dass die Benutzerrolle korrekt gesetzt ist

### Protokollierung

Die Anwendung generiert Protokolle zur Unterstützung bei der Fehlerbehebung:
- Überprüfen Sie die Protokolldatei unter `./.filesystem/logs/application.log`
- Erhöhen Sie die Protokollausführlichkeit durch Setzen von `LOG_LEVEL_CONSOLE=10` und `LOG_LEVEL_FILE=10` in Ihrer .env-Datei
- Protokollstufen: DEBUG=10, INFO=20, WARNING=30, ERROR=40, CRITICAL=50
- Anmeldeversuche werden zur Sicherheitsüberwachung in der Datenbank verfolgt

## Entwicklung

### Projektstruktur

```
RPA-Document-Fetcher/
    |-- .devcontainer/
    |   └── devcontainer.json
    |-- deployment/
    |   └── Dockerfile
    |-- examples/
    |   |-- email_templates/
    |   |   └── response_template.html
    |   |-- db_init.py
    |   |-- email_downloader.py
    |   └── insert_example_data.sql
    |-- src/
    |   |-- cls/
    |   |   |-- __init__.py
    |   |   |-- accesscontrol.py    # Zugriffskontrollverwaltung
    |   |   |-- config.py           # Konfigurationshandler
    |   |   |-- database.py         # Datenbankschnittstelle
    |   |   |-- document.py         # Dokumentenverarbeitung
    |   |   |-- mailclient.py       # E-Mail-Client-Schnittstelle
    |   |   └── singleton.py        # Singleton-Pattern-Implementierung
    |   |-- processing/
    |   |   |-- __init__.py
    |   |   |-- detect.py           # Tabellen- und Texterkennung
    |   |   |-- files.py            # Dateioperationen
    |   |   └── ocr.py              # OCR-Textextraktion
    |   |-- ui/
    |   |   |-- __init__.py
    |   |   |-- expander_stages.py  # UI für verschiedene Phasen
    |   |   |-- navbar.py           # Navigations-Seitenleiste
    |   |   |-- pages.py            # Hauptseitendefinitionen
    |   |   └── visuals.py          # Visualisierungen und UI-Elemente
    |   |-- workflow/
    |   |   |-- __init__.py
    |   |   |-- audit.py            # Prüfungsworkflow-Logik
    |   |   |-- excel_import.py     # Excel-Import für Prüfungssaison
    |   |   └── security.py         # Authentifizierung und Sicherheit
    |   |-- config.cfg              # Konfigurationsdatei
    |   |-- custom_logger.py        # Protokollierungssetup
    |   |-- main.py                 # Anwendungseinstiegspunkt
    |   |-- mock_imaplib.py         # Mock-E-Mail-Client für Tests
    |   |-- regex_patterns.json     # Muster für Textextraktion
    |   |-- schema.sql              # Datenbankschema
    |   └── table_detection.py      # Tabellenerkennungs-Testskript
    |-- .env.example                # Beispiel-Umgebungsvariablen
    |-- app_init.py                 # Anwendungsinitialisierungsskript
    |-- README.md                   # Diese Datei
    └── requirements.txt            # Python-Abhängigkeiten
```

### Modulübersicht

- **cls/**: Kernklassen für Datenbank-, Dokument- und E-Mail-Verarbeitung
    - **accesscontrol.py**: Verwaltet sowohl rollenbasierte als auch ressourcenbasierte Berechtigungen
    - **config.py**: Konfigurationsdateiverwaltung und Einstellungspersistenz
    - **database.py**: SQLite-Datenbankverbindung und -operationen
    - **document.py**: Dokumentendarstellung und -verarbeitung
    - **mailclient.py**: E-Mail-Client zum Abrufen von Anhängen
    - **singleton.py**: Dienstprogramm zum Erstellen von Singleton-Instanzen

- **processing/**: Dokumentenverarbeitungs-Dienstprogramme
    - **detect.py**: Algorithmen zur Erkennung von Tabellen und Daten
    - **files.py**: Dateisystemoperationen für Dokumente
    - **ocr.py**: OCR-Integration mit EasyOCR/Tesseract

- **ui/**: Streamlit-Benutzeroberflächenkomponenten
    - **expander_stages.py**: UI-Elemente für Workflow-Phasen
    - **navbar.py**: Navigations-Seitenleiste
    - **pages.py**: Hauptseitendefinitionen und -layouts
    - **visuals.py**: Diagramme, Badges und visuelle Elemente

- **workflow/**: Geschäftslogik
    - **audit.py**: Kern-Prüfungsprozess-Workflow
    - **excel_import.py**: Behandelt Massenimport von Prüfungsdaten aus Excel-Dateien
    - **security.py**: Authentifizierung, Sitzungsverwaltung und Zugriffskontrolle
