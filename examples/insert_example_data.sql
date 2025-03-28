-- Script to insert some example data for development and testing purposes


BEGIN TRANSACTION;

-- First check if the clients table is empty
INSERT INTO client (
    institute, bafin_id, address, city, contact_person,
    phone, fax, email,
    p033, p034, p035, p036,
    ab2s1n01, ab2s1n02, ab2s1n03, ab2s1n04, ab2s1n05,
    ab2s1n06, ab2s1n07, ab2s1n08, ab2s1n09, ab2s1n10,
    ab2s1n11, ratio
)
SELECT
    'Placeholder Financial Trust', 36540021, 'Platzhalter Platz 2', '70401 Ersatzstadt', 'Petra Platzhalter',
    '8636620002', '3670940002', 'dummy@placeholderfinance.test',
    10325, 0, 0, 0,
    10980, 2, 0, 37, 1845,
    82, 0, 0, 0, 0,
    0, 79.75
WHERE NOT EXISTS (SELECT 1 FROM client LIMIT 1);

-- If the first insert went through (table was empty), insert the rest
INSERT INTO client (
    institute, bafin_id, address, city, contact_person,
    phone, fax, email,
    p033, p034, p035, p036,
    ab2s1n01, ab2s1n02, ab2s1n03, ab2s1n04, ab2s1n05,
    ab2s1n06, ab2s1n07, ab2s1n08, ab2s1n09, ab2s1n10,
    ab2s1n11, ratio
)
SELECT *
FROM (
   SELECT
                 'Missing Data Bank', 36540011, 'Datenlose Straße 1', '70400 Nichtgesendet', 'Max Fehlend',
                 '8636620001', '3670940001', 'no.data@missingdata.test',
                 8240, 0, 0, 0,
                 8894, 5, 0, 42, 1520,
                 68, 0, 0, 0, 0,
                 0, 78.30
   UNION ALL SELECT
                 'Awaiting Submission GmbH', 36540031, 'Warteschleife Weg 3', '70402 Ausstehendorf', 'Willi Wartend',
                 '8636620003', '3670940003', 'waiting@awaitingsubmission.test',
                 7890, 0, 0, 0,
                 8340, 4, 0, 35, 1420,
                 71, 0, 0, 0, 0,
                 0, 79.90
   UNION ALL SELECT
                 'No Response Credit Union', 36540041, 'Schweigsame Straße 4', '70403 Stillestadt', 'Silvia ' ||
                                                                                                    'Schweigend',
                 '8636620004', '3670940004', 'silent@noresponse.test',
                 11470, 0, 0, 0,
                 12050, 1, 0, 40, 1980,
                 90, 0, 0, 0, 0,
                 0, 81.00
   UNION ALL SELECT
                 'Data Pending Bank AG', 36540051, 'Ausstehende Allee 5', '70404 Datenpendorf', 'Dieter Datenlos',
                 '8636620005', '3670940005', 'pending@datapending.test',
                 9675, 0, 0, 0,
                 10230, 6, 0, 43, 1745,
                 85, 0, 0, 0, 0,
                 0, 79.90
   UNION ALL SELECT
                 'Yet To File Sparkasse', 36540061, 'Nichtabgabe Straße 6', '70405 Späthausen', 'Stefan Säumig',
                 '8636620006', '3670940006', 'later@yettofile.test',
                 8955, 0, 0, 0,
                 9505, 2, 0, 36, 1630,
                 73, 0, 0, 0, 0,
                 0, 79.63
   UNION ALL SELECT
                 'Reminder Needed Bank', 36540071, 'Erinnerungsweg 7', '70406 Mahnstadt', 'Erika Erinnerer',
                 '8636620007', '3670940007', 'remind@reminderbank.test',
                 10780, 0, 0, 0,
                 11350, 3, 0, 41, 1890,
                 87, 0, 0, 0, 0,
                 0, 80.62
   UNION ALL SELECT
                 'Outstanding Report Bank', 36540081, 'Unerledigte Uferstraße 8', '70407 Ausstehenhausen', 'Otto ' ||
                                                                                                           'Offen',
                 '8636620008', '3670940008', 'pending@outstandingreport.test',
                 9340, 0, 0, 0,
                 9925, 4, 0, 38, 1720,
                 79, 0, 0, 0, 0,
                 0, 79.14
   UNION ALL SELECT
                 'Non-Compliant Financial Group', 36540091, 'Nichterfüllungsstraße 9', '70408 Verweigerndorf',
                 'Norbert Noncompliant',
                 '8636620009', '3670940009', 'ignore@noncompliant.test',
                 7650, 0, 0, 0,
                 8120, 5, 0, 32, 1380,
                 65, 0, 0, 0, 0,
                 0, 79.75
   UNION ALL SELECT
                 'Overdue Submission Institute', 36540101, 'Fristversäumnis Allee 10', '70409 Überfälligstadt',
                 'Oskar Überfällig',
                 '8636620010', '3670940010', 'late@overduesubmission.test',
                 10120, 0, 0, 0,
                 10670, 2, 0, 45, 1820,
                 84, 0, 0, 0, 0,
                 0, 80.17
   UNION ALL SELECT
                 'FinanzHanseatik Bank AG', 11204103, 'Alstergasse 12', '20457 Hamburg', 'Katrin Müller',
                 '2024489995', '9258035920', 'kontakt@finanzhanseatik.de',
                 9973, 0, 0, 0,
                 1602, 29, 0, 28, 1989,
                 97, 0, 0, 0, 0,
                 0, 266.30
   UNION ALL SELECT
                 'Wiesenhof Bank AG', 12516299, 'Am Birkenwald 17', '70435 Stuttgart', 'Friedrich Müller',
                 '8636629316', '3670943465', 'friedrich.mueller@wiesenhofbank.de',
                 9155, 0, 0, 0,
                 9769, 3, 0, 39, 1690,
                 77, 0, 0, 0, 0,
                 0, 79.07
   UNION ALL SELECT
                 'FinanzWerk AG', 14075544, 'Kaiserstraße 172', '90489 Nürnberg', 'Sabine Müller',
                 '3588750380', '2486824394', 'kontakt@finanzwerk.de',
                 3923, 0, 0, 0,
                 3879, 19, 0, 19, 1242,
                 34, 0, 0, 0, 0,
                 0, 75.54
   UNION ALL SELECT
                 'Nordsee Bank AG', 18111573, 'Fischmarkt 7', '20148 Hamburg', 'Dr. Hans-Otto Fischer',
                 '7462869227', '2434539738', 'kontakt@nordseebank.de',
                 3878, 0, 0, 0,
                 2427, 22, 0, 18, 501,
                 43, 0, 0, 0, 0,
                 0, 128.79
   UNION ALL SELECT
                 'Nordlicht Finanz GmbH', 18662275, 'Börsenstraße 18', '20457 Hamburg', 'Katrin Müller',
                 '4631295411', '8495929012', 'kontakt@nordlichtfinanz.de',
                 1862, 922, 793, 733,
                 8700, 4, 397, 39, 539,
                 32, 1265, 1469, 1872, 1102,
                 162, 27.66
   UNION ALL SELECT
                 'Nordlichter Finanz AG', 23729386, 'Lindenallee 12', '20457 Hamburg', 'Claudia Bremer',
                 '3241405965', '1050745018', 'info@nordlichter-finanz.de',
                 3697, 0, 0, 0,
                 7481, 29, 0, 17, 1295,
                 86, 0, 0, 0, 0,
                 0, 41.50
   UNION ALL SELECT
                 'FinanzKontor AG', 25559315, 'Hauptstraße 42', '12345 München', 'Lukas Schneider',
                 '8714423855', '1670480492', 'kontakt@finanzkontor.de',
                 4373, 0, 0, 0,
                 8065, 15, 0, 19, 1105,
                 76, 0, 0, 0, 0,
                 0, 47.12
   UNION ALL SELECT
                 'Nordstern Finanzhaus', 25993150, 'Königsallee 12', '40212 Düsseldorf', 'Lukas Krüger',
                 '8532248148', '4559514753', 'kontakt@nordsternfinanz.de',
                 3476, 0, 0, 0,
                 8394, 6, 0, 1, 845,
                 79, 0, 0, 0, 0,
                 0, 37.28
   UNION ALL SELECT
                 'Rheinland Kapital', 26798511, 'Königsallee 35', '40212 Düsseldorf', 'Franziska Müller',
                 '4529891909', '8717577543', 'kontakt@rheinlandkapital.de',
                 3239, 0, 0, 0,
                 6676, 28, 0, 34, 889,
                 55, 0, 0, 0, 0,
                 0, 42.16
   UNION ALL SELECT
                 'Nordstern Finanzhaus', 28898949, 'Königsallee 34', '45123 Essen', 'Johannes Becker',
                 '7985466306', '1840642904', 'kontakt@nordstern-finanzhaus.de',
                 4597, 0, 0, 0,
                 4550, 28, 0, 24, 1603,
                 92, 0, 0, 0, 0,
                 0, 73.00
   UNION ALL SELECT
                 'FinanzKontor AG', 29225251, 'Am Finanzplatz 24', '60311 Frankfurt am Main', 'Johanna Müller',
                 '2688659919', '7349437670', 'kontakt@finanzkontor.de',
                 4158, 0, 0, 0,
                 4120, 10, 0, 47, 852,
                 58, 0, 0, 0, 0,
                 0, 42.06
   UNION ALL SELECT
                 'Bergfeld Finanzinstitut', 31816001, 'Hauptstraße 98', '10178 Berlin', 'Friedrich Müller',
                 '4002347858', '6961645307', 'kontakt@bergfeldfinanz.de',
                 8447, 0, 0, 0,
                 722, 21, 0, 29, 161,
                 76, 0, 0, 0, 218,
                 0, 170.34
   UNION ALL SELECT
                 'FinanzKraft Bank AG', 39518024, 'Hauptstraße 12', '10115 Berlin', 'Hans Müller',
                 '3241363961', '2061591249', 'kontakt@finanzkraft-bank.de',
                 2674, 0, 0, 0,
                 8971, 11, 0, 32, 752,
                 87, 0, 0, 0, 0,
                 0, 27.14
   UNION ALL SELECT
                 'Bavarian Trust Bank AG', 49183032, 'Ludwigstraße 22', '80333 München', 'Dr. Franziska Müller',
                 '3382192326', '3414127357', 'kontakt@bavariantrust.de',
                 5232, 881, 1778, 1073,
                 1704, 0, 1394, 23, 602,
                 97, 1737, 1754, 5157, 15,
                 1735, 93.16
   UNION ALL SELECT
                 'FinanzWelle AG', 51081097, 'Hauptstraße 123', '10115 Berlin', 'Klaus Müller',
                 '8530037609', '4490065702', 'kontakt@finanzwelle.de',
                 4911, 0, 0, 0,
                 516, 28, 0, 31, 1630,
                 77, 0, 0, 0, 0,
                 0, 215.21
   UNION ALL SELECT
                 'VolksBank Rhein-Main eG', 53837987, 'Lindenstraße 15', '60594 Frankfurt am Main', 'Herr Tobias Schmidt',
                 '6331543983', '2107827868', 'info@volksbank-rhein-main.de',
                 8286, 0, 0, 0,
                 4683, 11, 0, 40, 1143,
                 37, 0, 0, 0, 0,
                 0, 140.11
   UNION ALL SELECT
                 'Berliner Volksbank Union', 54940359, 'Friedrichstr. 123', '10117 Berlin', 'Michael Schröder',
                 '4539143500', '6236020732', 'kontakt@bvu-berlin.de',
                 8046, 520, 1316, 256,
                 8771, 14, 1486, 0, 509,
                 75, 1681, 712, 314, 1507,
                 998, 63.10
   UNION ALL SELECT
                 'Bergmann Finanzinstitut AG', 57538145, 'Königsallee 34', '40215 Düsseldorf', 'Johanna Müller',
                 '6486341359', '3751037226', 'kontakt@bergmann-finanz.de',
                 659, 934, 1339, 39,
                 7973, 14, 1456, 4, 1805,
                 74, 505, 457, 1184, 1688,
                 1146, 67.28
   UNION ALL SELECT
                 'Nordrhein Finanzhaus', 58113627, 'Friedrichstraße 123', '40210 Düsseldorf', 'Lena Müller',
                 '2714808096', '8228348194', 'kontakt@nordrheinfinanzhaus.de',
                 8369,0,0,0,
                 434,28,0,1,1667,
                 83,5834,0,0,0,
                 0, 81.94
   UNION ALL SELECT
                 'Bavaria Volksbank', 62147948, 'Münchner Straße 45', '80333 München', 'Herr Thomas Müller',
                 '6648472502', '6455939744', 'kontakt@bavariavolksbank.de',
                 4444, 0, 0, 0,
                 7760, 21, 0, 26, 447,
                 79, 0, 0, 0, 0,
                 0, 53.33
   UNION ALL SELECT
                 'FinanzHub Berlin', 62979714, 'Hauptstraße 15', '10115 Berlin', 'Julia Schneider',
                 '1662446287', '9036225232', 'kontakt@finanzhub-berlin.de',
                 7537, 0, 0, 0,
                 2291, 4, 0, 46, 915,
                 81, 0, 0, 0, 0,
                 0, 225.86
   UNION ALL SELECT
                 'AlpenBank AG', 66063189, 'Bergstraße 12', '80331 München', 'Maximilian Schneider',
                 '4713353024', '4052082526', 'kontakt@alpenbank.de',
                 4067,0,0,0,
                 3110,16,0,28,719,
                 73,0,0,0,0,
                 0, 103.07
   UNION ALL SELECT
                 'Nordsee Finanzhaus', 68622905, 'Fischerstraße 12', '28195 Bremen', 'Helena Krüger',
                 '4405715279', '1471621457', 'kontakt@nordsee-finanzhaus.de',
                 4954, 0, 0, 0,
                 6679, 21, 0, 28, 1448,
                 62, 0, 0, 0, 0,
                 0, 60.14
   UNION ALL SELECT
                 'Nordrhein Finanzhaus AG', 71653902, 'Bismarckstraße 48', '40210 Düsseldorf', 'Friedrich Klein',
                 '1611661525', '3886856999', 'kontakt@nordrhein-finanzhaus.de',
                 1949, 1536, 925, 948,
                 1855, 17, 881, 31, 892,
                 85, 222, 581, 792, 470,
                 1049, 77.93
   UNION ALL SELECT
                 'NordBank AG', 72292864, 'Königsstraße 24', '20095 Hamburg', 'Friedrich Müller',
                 '8213487504', '6919984842', 'kontakt@nordbank.de',
                 3698, 0, 0, 0,
                 2129, 2, 0, 5, 1284,
                 75, 0, 0, 0, 0,
                 0, 105.81
   UNION ALL SELECT
                 'Bergland Finanzhaus', 74525449, 'Tulpenweg 5', '10437 Berlin', 'Marina Kleinfeld',
                 '3246985850', '1327547086', 'kontakt@berglandfinanzhaus.de',
                 8588, 0, 0, 0,
                 7664, 1, 0, 35, 1035,
                 58, 0, 0, 0, 0,
                 0, 97.67
   UNION ALL SELECT
                 'Rheinische Finanzen AG', 77714260, 'Schlossallee 17', '40212 Düsseldorf', 'Ursula Schneider',
                 '9804774547', '8213580008', 'kontakt@rheinischefinanzen.de',
                 9305, 0, 0, 0,
                 5675, 5, 0, 25, 1991,
                 32, 0, 0, 0, 0,
                 0, 120.41
   UNION ALL SELECT
                 'Bankhaus Müller & Partner', 79211456, 'Königsallee 34', '40212 Düsseldorf', 'Dr. Hans-Jürgen Becker',
                 '6515085211', '5079790228', 'kontakt@bankhaus-mueller.de',
                 1089, 0, 0, 0,
                 7918, 22, 0, 50, 767,
                 98, 0, 0, 0, 0,
                 0, 12.30
   UNION ALL SELECT
                 'Bergmann Finanz AG', 85094332, 'Hauptstraße 47', '80331 München', 'Dr. Karl-Heinz Sommer',
                 '9730628282', '2437435391', 'info@bergmann-finanz.de',
                 1570, 0, 0, 0,
                 6476, 11, 0, 13, 446,
                 40, 0, 0, 0, 0,
                 0, 22.47
   UNION ALL SELECT
                 'Bavaria Finanzhaus', 85221372, 'Königsstraße 45', '80331 München', 'Robert Feldmann',
                 '4105079701', '2069512545', 'kontakt@bavariafinanzhaus.de',
                 2633, 0, 0, 0,
                 5469, 13, 0, 5, 1025,
                 37, 0, 0, 0, 0,
                 0, 40.20
   UNION ALL SELECT
                 'Bayerische Finanzbank AG', 91837196, 'Ludwigstraße 15', '80539 München', 'Dr. Anna Müller',
                 '5792701363', '9930624992', 'kontakt@bayerischefinanzbank.de',
                 7003, 0, 0, 0,
                 1467, 6, 0, 27, 539,
                 74, 0, 0, 0, 0,
                 0, 331.42
   UNION ALL SELECT
                 'Nordlicht Finance AG', 92728104, 'Alsterstraße 18', '20354 Hamburg', 'Katrin Schneider',
                 '3863207057', '9098772505', 'kontakt@nordlichtfinance.de',
                 7396, 0, 0, 0,
                 7822, 30, 0, 41, 681,
                 37, 0, 0, 0, 0,
                 0, 85.89
   UNION ALL SELECT
                 'Bergblau Finanzen AG', 93017421, 'Am Waldweg 12', '50670 Köln', 'Friedrich Müller',
                 '8770089863', '5975067443', 'kontakt@bergblaufinanzen.de',
                 8136, 0, 0, 0,
                 3746, 29, 0, 8, 1119,
                 76, 0, 0, 0, 0,
                 0, 163.44
   UNION ALL SELECT
                 'Volksbank Himmelstadt', 96010248, 'Mühlweg 12', '97332 Himmelstadt', 'Dr. Anna Müller',
                 '8809692907', '2748838286', 'info@volksbank-himmelstadt.de',
                 3862, 0, 0, 0,
                 9808, 28, 0, 47, 825,
                 96, 0, 0, 0, 0,
                 0, 35.75
   UNION ALL SELECT
                 'Rheinland Finanzhaus', 98098861, 'Hauptstraße 15', '50667 Köln', 'Lukas Braun',
                 '4167609878', '4608104312', 'kontakt@rheinland-finanzhaus.de',
                 1612, 0, 0, 0,
                 4484, 9, 0, 5, 1335,
                 42, 0, 0, 0, 0,
                 0, 27.44
   UNION ALL SELECT
                 'Nordlicht Finanz AG', 98178386, 'Hafenstraße 101', '22391 Hamburg', 'Klaus-Peter Hoffmann',
                 '3315425256', '3739328819', 'kontakt@nordlichtfinanz.de',
                 3295, 0, 0, 0,
                 6681, 2, 0, 23, 1941,
                 35, 0, 0, 0, 0,
                 0, 37.95
   UNION ALL SELECT
                 'Rheinische Finanzhaus', 98185521, 'Königsallee 45', '40215 Düsseldorf', 'Frau Stefanie Müller',
                 '2459146840', '2690544493', 'kontakt@rheinischefinanzhaus.de',
                 1764, 0, 0, 0,
                 5037, 10, 0, 4, 238,
                 71, 0, 0, 0, 0,
                 0, 32.91
   UNION ALL SELECT
                 'Nordlichter Finanzgruppe AG', 98484847, 'Am Hafen 27', '20457 Hamburg', 'Frau Dr. Katharina Meier',
                 '3536882860', '9037104306', 'kontakt@nordlichter-finanzgruppe.de',
                 1674, 84, 1878, 1109,
                 525, 9, 1304, 25, 1061,
                 50, 738, 1775, 1705, 1655,
                 937, 48.50
   UNION ALL SELECT
                 'Nordsee Bank', 99072002, 'Musterstraße 47', '26122 Oldenburg', 'Friedrich Bergmann',
                 '6420607913', '2588330154', 'f.bergmann@nordseebank.de',
                 2606, 0, 0, 0,
                 4537, 10, 0, 22, 218,
                 60, 0, 0, 0, 0,
                 0, 53.77
   UNION ALL SELECT
                 'Bergwald Finanzgruppe', 99960596, 'Lindenstraße 24', '80331 München', 'Anna Keller',
                 '5623136254', '4267658463', 'kontakt@bergwaldfinanz.de',
                 3119, 0, 0, 0,
                 738, 12, 0, 19, 588,
                 80, 0, 0, 0, 0,
                 0, 217.05
              ) AS bulk_data
WHERE EXISTS (SELECT 1 FROM client WHERE bafin_id = 36540021);

COMMIT;
