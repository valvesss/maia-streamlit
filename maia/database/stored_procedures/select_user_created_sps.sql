SELECT proname 
FROM pg_proc 
INNER JOIN pg_namespace n ON n.oid = pg_proc.pronamespace 
WHERE n.nspname NOT IN ('pg_catalog', 'information_schema') 
AND proowner = (SELECT usesysid FROM pg_user WHERE usename = current_user);
