-- cleanup_materials.sql
-- Purpose: canonicalise and de-duplicate supplementary cementitious materials (SCMs)
--          while preserving referential integrity for all child tables that
--          reference public.material(material_id).
--
-- Author: AI-generated; review before running in staging / prod.
-- Idempotent: safe to re-run – existing merges are skipped, canonical rows are
--             updated but not duplicated. All work occurs inside a single
--             transaction and deferred constraints ensure FK safety.
--
-- How to run (example):
--   psql "service=cdb" -v ON_ERROR_STOP=1 -f cleanup_materials.sql
---------------------------------------------------------------------

BEGIN;
SET client_min_messages TO WARNING;
LOCK TABLE public.material IN SHARE ROW EXCLUSIVE MODE;
SET CONSTRAINTS ALL DEFERRED;

-----------------------------
-- 0.  Utility objects
-----------------------------
-- Book-keeping table (create once if missing).
CREATE TABLE IF NOT EXISTS public.material_merge_log (
    material_id_old  INTEGER NOT NULL,
    material_id_new  INTEGER NOT NULL,
    run_ts           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT mml_pkey PRIMARY KEY(material_id_old, material_id_new)
);

-- Procedure to merge one material into another (generic – discovers FK users).
CREATE OR REPLACE PROCEDURE public.merge_material(old_mat_id INT, new_mat_id INT)
LANGUAGE plpgsql AS $$
DECLARE
    rec  RECORD;
    colname TEXT;
    upd_sql TEXT;
BEGIN
    IF old_mat_id = new_mat_id THEN
        RETURN; -- nothing to do
    END IF;

    -- Loop through every FK that points to material.material_id
    FOR rec IN
        SELECT conrelid::regclass                             AS target_table,
               (SELECT attname FROM pg_attribute
                 WHERE attrelid = conrelid
                   AND attnum   = conkey[1])                 AS target_column
        FROM   pg_constraint
        WHERE  confrelid = 'public.material'::regclass
          AND  contype   = 'f'
    LOOP
        colname := rec.target_column;
        RAISE NOTICE 'Updating %.% (old=%, new=%)', rec.target_table, colname, old_mat_id, new_mat_id;
        upd_sql := format('UPDATE %I SET %I = $1 WHERE %I = $2',
                          rec.target_table, colname, colname);
        EXECUTE upd_sql USING new_mat_id, old_mat_id;
    END LOOP;

    -- Record merge
    INSERT INTO public.material_merge_log(material_id_old, material_id_new)
    VALUES(old_mat_id, new_mat_id)
    ON CONFLICT DO NOTHING;

    -- Finally delete the redundant row
    DELETE FROM public.material WHERE material_id = old_mat_id;
END;
$$;

-- 0a. Fail-fast if any composite FKs exist
DO $$
DECLARE
    bad_fk INT;
BEGIN
    SELECT COUNT(*)
      INTO bad_fk
      FROM pg_constraint
     WHERE confrelid = 'public.material'::regclass
       AND contype   = 'f'
       AND array_length(conkey,1) > 1;
    IF bad_fk > 0 THEN
        RAISE EXCEPTION 'Aborting: % composite FK(s) reference public.material(material_id)', bad_fk;
    END IF;
END$$;

-----------------------------
-- 1. Canonical SCM list
-----------------------------
CREATE TEMP TABLE _canonical_scm (
    subtype_code        TEXT PRIMARY KEY,
    specific_name       TEXT
);

INSERT INTO _canonical_scm(subtype_code, specific_name) VALUES
    ('ggbfs',              'GGBS (Ground-granulated BF Slag)'),
    ('fly_ash_bituminous', 'Fly Ash – Bituminous Coal (Class F)'),
    ('fly_ash_lignite',    'Fly Ash – Lignite/Brown Coal (Class F)'),
    ('silica_fume',        'Silica Fume'),
    ('limestone_powder',   'Limestone Powder (Filler)'),
    ('natural_pozzolan',   'Natural Pozzolan'),
    ('calcined_clay',      'Calcined Clay (Metakaolin)'),
    ('rha',                'Rice Husk Ash');

-----------------------------
-- 2. Audit BEFORE (captured into temp table)
-----------------------------
CREATE TEMP TABLE _audit_before AS
SELECT m.material_id,
       m.class_code,
       COALESCE(LOWER(m.subtype_code), '(null)') AS subtype_code_norm,
       COALESCE(LOWER(m.specific_name), '(null)') AS specific_name_norm
FROM   public.material m;

-----------------------------
-- 3. Main merge loop
-----------------------------
DO $$
DECLARE
    canon      RECORD;
    cand       RECORD;
    canonical_id INTEGER;
BEGIN
    -- Iterate every desired canonical SCM subtype
    FOR canon IN SELECT * FROM _canonical_scm LOOP
        -- (a) choose / create canonical row
        SELECT material_id
          INTO canonical_id
        FROM public.material
        WHERE class_code = 'SCM'
          AND LOWER(subtype_code) = canon.subtype_code
        ORDER BY material_id
        LIMIT 1;

        IF canonical_id IS NULL THEN
            INSERT INTO public.material(class_code, subtype_code, specific_name)
            VALUES('SCM', canon.subtype_code, canon.specific_name)
            RETURNING material_id INTO canonical_id;
        ELSE
            -- normalise the chosen row
            UPDATE public.material
               SET class_code   = 'SCM',
                   subtype_code = canon.subtype_code,
                   specific_name= canon.specific_name
             WHERE material_id  = canonical_id;
        END IF;

        -- (b) merge duplicates (case/spacing variants)
        FOR cand IN
            SELECT material_id
            FROM   public.material
            WHERE  material_id <> canonical_id
              AND  class_code   = 'SCM'
              AND (LOWER(subtype_code) = canon.subtype_code
                   OR LOWER(specific_name) = LOWER(canon.specific_name))
        LOOP
            CALL public.merge_material(cand.material_id, canonical_id);
        END LOOP;
    END LOOP;
END$$;

-----------------------------
-- 4. Mis-classified rows (e.g. CEM types living under SCM)
-----------------------------
-- Example rule: any subtype beginning with 'cem' is cement.
UPDATE public.material
   SET class_code   = 'CEMENT'
 WHERE class_code IN ('SCM','CEMENT')
   AND LOWER(subtype_code) LIKE 'cem%';

-----------------------------
COMMIT;

-----------------------------
-- 5b. Export audits (run after commit)
-----------------------------
\copy (SELECT 'before' AS phase, * FROM _audit_before) TO 'materials_audit_before.csv' CSV HEADER
\copy (SELECT 'after' AS phase, m.material_id, m.class_code, COALESCE(LOWER(m.subtype_code), '(null)'), COALESCE(LOWER(m.specific_name), '(null)') FROM public.material m) TO 'materials_audit_after.csv' CSV HEADER

\echo 'Material cleanup complete.'
