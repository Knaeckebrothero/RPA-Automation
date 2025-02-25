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
    'Nordsee Bank', 99072002, 'Musterstraße 47', '26122 Oldenburg', 'Friedrich Bergmann',
    '6420607913', '2588330154', 'f.bergmann@nordseebank.de',
    2606, 0, 0, 0,
    4537, 10, 0, 22, 218,
    60, 0, 0, 0, 0,
    0, 53.77
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
                'Nordlicht Finanz AG', 98178386, 'Hafenstraße 101', '22391 Hamburg', 'Klaus-Peter Hoffmann',
                '3315425256', '3739328819', 'kontakt@nordlichtfinanz.de',
                3295, 0, 0, 0,
                6681, 2, 0, 23, 1941,
                35, 0, 0, 0, 0,
                0, 37.95
   UNION ALL SELECT
                'Volksbank Himmelstadt', 96010248, 'Mühlweg 12', '97332 Himmelstadt', 'Dr. Anna Müller',
                '8809692907', '2748838286', 'info@volksbank-himmelstadt.de',
                3862, 0, 0, 0,
                9808, 28, 0, 47, 825,
                96, 0, 0, 0, 0,
                0, 35.75
  UNION ALL SELECT
                'Bayerische Finanzbank AG', 91837196, 'Ludwigstraße 15', '80539 München', 'Dr. Anna Müller',
                '5792701363', '9930624992', 'kontakt@bayerischefinanzbank.de',
                7003, 0, 0, 0,
                1467, 6, 0, 27, 539,
                74, 0, 0, 0, 0,
                0, 331.42
  UNION ALL SELECT
                'Bergmann Finanz AG', 85094332, 'Hauptstraße 47', '80331 München', 'Dr. Karl-Heinz Sommer',
                '9730628282', '2437435391', 'info@bergmann-finanz.de',
                1570, 0, 0, 0,
                6476, 11, 0, 13, 446,
                40, 0, 0, 0, 0,
                0, 22.47
  UNION ALL SELECT
                'Bankhaus Müller & Partner', 79211456, 'Königsallee 34', '40212 Düsseldorf', 'Dr. Hans-Jürgen Becker',
                '6515085211', '5079790228', 'kontakt@bankhaus-mueller.de',
                1089, 0, 0, 0,
                7918, 22, 0, 50, 767,
                98, 0, 0, 0, 0,
                0, 12.30
  UNION ALL SELECT
                'NordBank AG', 72292864, 'Königsstraße 24', '20095 Hamburg', 'Friedrich Müller',
                '8213487504', '6919984842', 'kontakt@nordbank.de',
                3698, 0, 0, 0,
                2129, 2, 0, 5, 1284,
                75, 0, 0, 0, 0,
                0, 105.81
  UNION ALL SELECT
                'Bavaria Volksbank', 62147948, 'Münchner Straße 45', '80333 München', 'Herr Thomas Müller',
                '6648472502', '6455939744', 'kontakt@bavariavolksbank.de',
                4444, 0, 0, 0,
                7760, 21, 0, 26, 447,
                79, 0, 0, 0, 0,
                0, 53.33
  UNION ALL SELECT
                'Nordsee Bank AG', 18111573, 'Fischmarkt 7', '20148 Hamburg', 'Dr. Hans-Otto Fischer',
                '7462869227', '2434539738', 'kontakt@nordseebank.de',
                3878, 0, 0, 0,
                2427, 22, 0, 18, 501,
                43, 0, 0, 0, 0,
                0, 128.79
  UNION ALL SELECT
                'Wiesenhof Bank AG', 12516299, 'Am Birkenwald 17', '70435 Stuttgart', 'Friedrich Müller',
                '8636629316', '3670943465', 'friedrich.mueller@wiesenhofbank.de',
                9155, 0, 0, 0,
                9769, 3, 0, 39, 1690,
                77, 0, 0, 0, 0,
                0, 79.07
  UNION ALL SELECT
                'Never Submit Bank', 3654848, 'We dont report to you way', '70435 NeverSendHausen', 'Schick Nix',
                '8636629316', '3670943465', 'never.submit@noreply.dev',
                9155, 0, 0, 0,
                9769, 3, 0, 39, 1690,
                77, 0, 0, 0, 0,
                0, 79.07
              ) AS bulk_data
WHERE EXISTS (SELECT 1 FROM client WHERE bafin_id = 99072002);

COMMIT;
