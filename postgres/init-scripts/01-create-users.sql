-- Für Schreibzugriff
-- Benutzer und Basis-Berechtigungen 
CREATE USER default_user WITH PASSWORD 'changeme987654321';
-- Zugriffsrechte auf Datenbankebene
GRANT CONNECT ON DATABASE db TO ilek_user;
GRANT CREATE ON DATABASE db TO ilek_user;
-- Schema-Berechtigungen
GRANT USAGE ON SCHEMA public TO ilek_user;
GRANT CREATE ON SCHEMA public TO ilek_user;
-- Tabellenberechtigungen für bestehende und zukünftige Tabellen
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ilek_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ilek_user;
-- Wichtig: Berechtigungen auch für zukünftig erstellte Tabellen setzen
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT ALL PRIVILEGES ON TABLES TO ilek_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT ALL PRIVILEGES ON SEQUENCES TO ilek_user;

-- Für Readonly-User
-- User erstellen
CREATE USER readonly_user WITH PASSWORD 'changeme123456789';
-- Basis-Zugriff auf Datenbank
GRANT CONNECT ON DATABASE db TO readonly_user;
-- Schema-Berechtigung
GRANT USAGE ON SCHEMA public TO readonly_user;
-- Leserechte auf alle existierenden Tabellen im public Schema
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
-- Rechte auf Sequences
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO readonly_user;
-- Leserechte auf zukünftige Tabellen
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    FOR ROLE ilek_user 
    GRANT SELECT ON TABLES TO readonly_user;