-- Este trigger actualiza explicitamente la tabla public.dim_partidos.

CREATE OR REPLACE FUNCTION public.fn_actualizar_dim_partido_desde_eventos()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_id_partido integer;
    v_local integer;
    v_visitante integer;
    v_goles_local integer := 0;
    v_goles_visitante integer := 0;
    v_ganador character varying(100) := NULL;
    v_nombre_local character varying(100);
    v_nombre_visitante character varying(100);
BEGIN
    v_id_partido := NEW.id_partido;

    SELECT d.id_local, d.id_visitante
      INTO v_local, v_visitante
      FROM public.dim_partidos d
     WHERE d.id_partido = v_id_partido;

    IF NOT FOUND THEN
        RETURN NEW;
    END IF;

    SELECT
        COALESCE(
            SUM(
                CASE
                    WHEN e.tipo = 'Gol'
                         AND (
                             (COALESCE(e.detalle, '') <> 'Gol en propia' AND e.id_equipo = v_local)
                             OR (COALESCE(e.detalle, '') = 'Gol en propia' AND e.id_equipo = v_visitante)
                         )
                    THEN 1
                    ELSE 0
                END
            ),
            0
        ) AS goles_local,
        COALESCE(
            SUM(
                CASE
                    WHEN e.tipo = 'Gol'
                         AND (
                             (COALESCE(e.detalle, '') <> 'Gol en propia' AND e.id_equipo = v_visitante)
                             OR (COALESCE(e.detalle, '') = 'Gol en propia' AND e.id_equipo = v_local)
                         )
                    THEN 1
                    ELSE 0
                END
            ),
            0
        ) AS goles_visitante
    INTO v_goles_local, v_goles_visitante
    FROM public.h_partido_eventos e
    WHERE e.id_partido = v_id_partido;

    SELECT nombre_equipo INTO v_nombre_local
    FROM public.dim_equipo
    WHERE id_equipo = v_local;

    SELECT nombre_equipo INTO v_nombre_visitante
    FROM public.dim_equipo
    WHERE id_equipo = v_visitante;

    IF v_goles_local > v_goles_visitante THEN
        v_ganador := COALESCE(v_nombre_local, v_local::text);
    ELSIF v_goles_visitante > v_goles_local THEN
        v_ganador := COALESCE(v_nombre_visitante, v_visitante::text);
    ELSE
        v_ganador := 'Empate';
    END IF;

    UPDATE public.dim_partidos
       SET goles_local = v_goles_local,
           goles_visitante = v_goles_visitante,
           ganador = v_ganador,
           status = 'Completado'
     WHERE id_partido = v_id_partido;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_actualizar_dim_partido_desde_eventos ON public.h_partido_eventos;

CREATE TRIGGER trg_actualizar_dim_partido_desde_eventos
AFTER INSERT ON public.h_partido_eventos
FOR EACH ROW
EXECUTE FUNCTION public.fn_actualizar_dim_partido_desde_eventos();
