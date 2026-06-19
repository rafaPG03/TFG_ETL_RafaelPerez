CREATE OR REPLACE FUNCTION public.fn_recalcular_h_equipo_temporada_jornada(
    p_temporada integer,
    p_jornada integer
)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    WITH partidos_hasta_jornada AS (
        SELECT
            d.id_partido,
            d.temporada,
            t.jornada,
            d.id_local,
            d.id_visitante,
            COALESCE(d.goles_local, 0) AS goles_local,
            COALESCE(d.goles_visitante, 0) AS goles_visitante
        FROM public.dim_partidos d
        JOIN public.dim_tiempo t
          ON t.id_tiempo = d.id_tiempo
        WHERE d.temporada = p_temporada
          AND t.jornada <= p_jornada
          AND d.status = 'Completado'
    ),
    equipos_temporada AS (
        SELECT DISTINCT id_local AS id_equipo
        FROM public.dim_partidos
        WHERE temporada = p_temporada
        UNION
        SELECT DISTINCT id_visitante AS id_equipo
        FROM public.dim_partidos
        WHERE temporada = p_temporada
    ),
    filas_local AS (
        SELECT
            p.id_local AS id_equipo,
            1 AS partidos_jugados,
            CASE WHEN p.goles_local > p.goles_visitante THEN 1 ELSE 0 END AS victorias,
            CASE WHEN p.goles_local = p.goles_visitante THEN 1 ELSE 0 END AS empates,
            CASE WHEN p.goles_local < p.goles_visitante THEN 1 ELSE 0 END AS derrotas,
            p.goles_local AS gf,
            p.goles_visitante AS gc,
            1 AS partidos_jugados_local,
            CASE WHEN p.goles_local > p.goles_visitante THEN 1 ELSE 0 END AS victorias_local,
            CASE WHEN p.goles_local = p.goles_visitante THEN 1 ELSE 0 END AS empates_local,
            CASE WHEN p.goles_local < p.goles_visitante THEN 1 ELSE 0 END AS derrotas_local,
            p.goles_local AS gf_local,
            p.goles_visitante AS gc_local,
            0 AS partidos_jugados_visitante,
            0 AS victorias_visitante,
            0 AS empates_visitante,
            0 AS derrotas_visitante,
            0 AS gf_visitante,
            0 AS gc_visitante,
            CASE
                WHEN p.goles_local > p.goles_visitante THEN 3
                WHEN p.goles_local = p.goles_visitante THEN 1
                ELSE 0
            END AS puntos
        FROM partidos_hasta_jornada p
    ),
    filas_visitante AS (
        SELECT
            p.id_visitante AS id_equipo,
            1 AS partidos_jugados,
            CASE WHEN p.goles_visitante > p.goles_local THEN 1 ELSE 0 END AS victorias,
            CASE WHEN p.goles_visitante = p.goles_local THEN 1 ELSE 0 END AS empates,
            CASE WHEN p.goles_visitante < p.goles_local THEN 1 ELSE 0 END AS derrotas,
            p.goles_visitante AS gf,
            p.goles_local AS gc,
            0 AS partidos_jugados_local,
            0 AS victorias_local,
            0 AS empates_local,
            0 AS derrotas_local,
            0 AS gf_local,
            0 AS gc_local,
            1 AS partidos_jugados_visitante,
            CASE WHEN p.goles_visitante > p.goles_local THEN 1 ELSE 0 END AS victorias_visitante,
            CASE WHEN p.goles_visitante = p.goles_local THEN 1 ELSE 0 END AS empates_visitante,
            CASE WHEN p.goles_visitante < p.goles_local THEN 1 ELSE 0 END AS derrotas_visitante,
            p.goles_visitante AS gf_visitante,
            p.goles_local AS gc_visitante,
            CASE
                WHEN p.goles_visitante > p.goles_local THEN 3
                WHEN p.goles_visitante = p.goles_local THEN 1
                ELSE 0
            END AS puntos
        FROM partidos_hasta_jornada p
    ),
    acumulado AS (
        SELECT * FROM filas_local
        UNION ALL
        SELECT * FROM filas_visitante
    ),
    stats_equipo AS (
        SELECT
            e.id_equipo,
            COALESCE(SUM(a.puntos), 0) AS puntos,
            COALESCE(SUM(a.partidos_jugados), 0) AS partidos_jugados,
            COALESCE(SUM(a.victorias), 0) AS victorias,
            COALESCE(SUM(a.empates), 0) AS empates,
            COALESCE(SUM(a.derrotas), 0) AS derrotas,
            COALESCE(SUM(a.gf), 0) AS gf,
            COALESCE(SUM(a.gc), 0) AS gc,
            COALESCE(SUM(a.partidos_jugados_local), 0) AS partidos_jugados_local,
            COALESCE(SUM(a.victorias_local), 0) AS victorias_local,
            COALESCE(SUM(a.empates_local), 0) AS empates_local,
            COALESCE(SUM(a.derrotas_local), 0) AS derrotas_local,
            COALESCE(SUM(a.gf_local), 0) AS gf_local,
            COALESCE(SUM(a.gc_local), 0) AS gc_local,
            COALESCE(SUM(a.partidos_jugados_visitante), 0) AS partidos_jugados_visitante,
            COALESCE(SUM(a.victorias_visitante), 0) AS victorias_visitante,
            COALESCE(SUM(a.empates_visitante), 0) AS empates_visitante,
            COALESCE(SUM(a.derrotas_visitante), 0) AS derrotas_visitante,
            COALESCE(SUM(a.gf_visitante), 0) AS gf_visitante,
            COALESCE(SUM(a.gc_visitante), 0) AS gc_visitante
        FROM equipos_temporada e
        LEFT JOIN acumulado a
          ON a.id_equipo = e.id_equipo
        GROUP BY e.id_equipo
    ),
    resultados_equipo AS (
        SELECT
            p.id_local AS id_equipo,
            p.jornada,
            p.id_partido,
            CASE
                WHEN p.goles_local > p.goles_visitante THEN 'W'
                WHEN p.goles_local = p.goles_visitante THEN 'D'
                ELSE 'L'
            END AS resultado
        FROM partidos_hasta_jornada p
        UNION ALL
        SELECT
            p.id_visitante AS id_equipo,
            p.jornada,
            p.id_partido,
            CASE
                WHEN p.goles_visitante > p.goles_local THEN 'W'
                WHEN p.goles_visitante = p.goles_local THEN 'D'
                ELSE 'L'
            END AS resultado
        FROM partidos_hasta_jornada p
    ),
    forma_top5 AS (
        SELECT
            r.id_equipo,
            STRING_AGG(r.resultado, '' ORDER BY r.jornada DESC, r.id_partido DESC) AS forma
        FROM (
            SELECT
                re.*,
                ROW_NUMBER() OVER (
                    PARTITION BY re.id_equipo
                    ORDER BY re.jornada DESC, re.id_partido DESC
                ) AS rn
            FROM resultados_equipo re
        ) r
        WHERE r.rn <= 5
        GROUP BY r.id_equipo
    ),
    clasificacion AS (
        SELECT
            s.id_equipo,
            p_temporada AS temporada,
            p_jornada AS jornada,
            ROW_NUMBER() OVER (
                ORDER BY s.puntos DESC, (s.gf - s.gc) DESC, s.gf DESC, s.id_equipo ASC
            ) AS posicion,
            de.nombre_equipo,
            s.puntos,
            (s.gf - s.gc) AS dg,
            COALESCE(f.forma, '') AS forma,
            s.partidos_jugados,
            s.victorias,
            s.empates,
            s.derrotas,
            s.gf,
            s.gc,
            s.partidos_jugados_local,
            s.victorias_local,
            s.empates_local,
            s.derrotas_local,
            s.gf_local,
            s.gc_local,
            s.partidos_jugados_visitante,
            s.victorias_visitante,
            s.empates_visitante,
            s.derrotas_visitante,
            s.gf_visitante,
            s.gc_visitante
        FROM stats_equipo s
        LEFT JOIN forma_top5 f
          ON f.id_equipo = s.id_equipo
        LEFT JOIN public.dim_equipo de
          ON de.id_equipo = s.id_equipo
    )
    INSERT INTO public.h_equipo_temporada (
        id_equipo,
        temporada,
        jornada,
        posicion,
        nombre_equipo,
        puntos,
        dg,
        forma,
        partidos_jugados,
        victorias,
        empates,
        derrotas,
        gf,
        gc,
        partidos_jugados_local,
        victorias_local,
        empates_local,
        derrotas_local,
        gf_local,
        gc_local,
        partidos_jugados_visitante,
        victorias_visitante,
        empates_visitante,
        derrotas_visitante,
        gf_visitante,
        gc_visitante
    )
    SELECT
        c.id_equipo,
        c.temporada,
        c.jornada,
        c.posicion,
        c.nombre_equipo,
        c.puntos,
        c.dg,
        c.forma,
        c.partidos_jugados,
        c.victorias,
        c.empates,
        c.derrotas,
        c.gf,
        c.gc,
        c.partidos_jugados_local,
        c.victorias_local,
        c.empates_local,
        c.derrotas_local,
        c.gf_local,
        c.gc_local,
        c.partidos_jugados_visitante,
        c.victorias_visitante,
        c.empates_visitante,
        c.derrotas_visitante,
        c.gf_visitante,
        c.gc_visitante
    FROM clasificacion c
    ON CONFLICT (id_equipo, temporada, jornada)
    DO UPDATE SET
        posicion = EXCLUDED.posicion,
        nombre_equipo = EXCLUDED.nombre_equipo,
        puntos = EXCLUDED.puntos,
        dg = EXCLUDED.dg,
        forma = EXCLUDED.forma,
        partidos_jugados = EXCLUDED.partidos_jugados,
        victorias = EXCLUDED.victorias,
        empates = EXCLUDED.empates,
        derrotas = EXCLUDED.derrotas,
        gf = EXCLUDED.gf,
        gc = EXCLUDED.gc,
        partidos_jugados_local = EXCLUDED.partidos_jugados_local,
        victorias_local = EXCLUDED.victorias_local,
        empates_local = EXCLUDED.empates_local,
        derrotas_local = EXCLUDED.derrotas_local,
        gf_local = EXCLUDED.gf_local,
        gc_local = EXCLUDED.gc_local,
        partidos_jugados_visitante = EXCLUDED.partidos_jugados_visitante,
        victorias_visitante = EXCLUDED.victorias_visitante,
        empates_visitante = EXCLUDED.empates_visitante,
        derrotas_visitante = EXCLUDED.derrotas_visitante,
        gf_visitante = EXCLUDED.gf_visitante,
        gc_visitante = EXCLUDED.gc_visitante;
END;
$$;


CREATE OR REPLACE FUNCTION public.fn_trigger_recalcular_h_equipo_temporada()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_temporada integer;
    v_jornada integer;
    v_j integer;
BEGIN
    IF NEW.id_tiempo IS NULL OR NEW.temporada IS NULL THEN
        RETURN NEW;
    END IF;

    IF NEW.status <> 'Completado' THEN
        RETURN NEW;
    END IF;

    IF TG_OP = 'UPDATE'
       AND OLD.status = NEW.status
       AND COALESCE(OLD.goles_local, -9999) = COALESCE(NEW.goles_local, -9999)
       AND COALESCE(OLD.goles_visitante, -9999) = COALESCE(NEW.goles_visitante, -9999)
       AND COALESCE(OLD.ganador, '') = COALESCE(NEW.ganador, '') THEN
        RETURN NEW;
    END IF;

    v_temporada := NEW.temporada;

    SELECT t.jornada
      INTO v_jornada
      FROM public.dim_tiempo t
     WHERE t.id_tiempo = NEW.id_tiempo;

    IF v_jornada IS NULL THEN
        RETURN NEW;
    END IF;

    FOR v_j IN
        SELECT DISTINCT t2.jornada
        FROM public.dim_partidos d2
        JOIN public.dim_tiempo t2
          ON t2.id_tiempo = d2.id_tiempo
        WHERE d2.temporada = v_temporada
          AND t2.jornada >= v_jornada
        ORDER BY t2.jornada
    LOOP
        PERFORM public.fn_recalcular_h_equipo_temporada_jornada(v_temporada, v_j);
    END LOOP;

    RETURN NEW;
END;
$$;


DROP TRIGGER IF EXISTS trg_recalcular_h_equipo_temporada ON public.dim_partidos;

CREATE TRIGGER trg_recalcular_h_equipo_temporada
AFTER UPDATE OF status, goles_local, goles_visitante, ganador
ON public.dim_partidos
FOR EACH ROW
EXECUTE FUNCTION public.fn_trigger_recalcular_h_equipo_temporada();
