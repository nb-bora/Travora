-- Rôles de développement et d'intégration continue. Les mots de passe ci-dessous
-- ne servent QUE hors production : en production, les rôles sont créés avec des
-- secrets propres à l'environnement.
--
-- travora_owner : possède les tables, exécute les migrations.
-- travora_app   : rôle d'exécution. Ne possède rien, ne contourne pas la RLS.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'travora_owner') THEN
        CREATE ROLE travora_owner LOGIN PASSWORD 'travora_owner'
            NOSUPERUSER NOBYPASSRLS NOCREATEROLE;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'travora_app') THEN
        CREATE ROLE travora_app LOGIN PASSWORD 'travora_app'
            NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
    END IF;
END
$$;

GRANT CONNECT ON DATABASE travora TO travora_owner, travora_app;
ALTER SCHEMA public OWNER TO travora_owner;
GRANT USAGE ON SCHEMA public TO travora_app;
