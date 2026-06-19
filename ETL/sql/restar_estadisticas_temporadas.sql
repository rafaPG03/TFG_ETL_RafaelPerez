-- DROP FUNCTION public.restar_estadisticas_temporada();

CREATE OR REPLACE FUNCTION public.restar_estadisticas_temporada()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_temporada integer;
    v_partidos_restantes integer;
BEGIN
    -- 1. Identificar la temporada del partido que se está borrando (usamos OLD)
    SELECT temporada INTO v_temporada 
    FROM public.dim_partidos 
    WHERE id_partido = OLD.id_partido;

    -- 2. Restar los valores cuantitativos
    UPDATE public.h_jugador_temporada
    SET 
        partidos = partidos - 1,
        minutos = minutos - OLD.minutos,
        titular = titular - (CASE WHEN OLD.sustituto = FALSE THEN 1 ELSE 0 END),
        goles = goles - OLD.goles,
        asistencias = asistencias - OLD.asistencias,
        tiros_totales = tiros_totales - OLD.tiros_totales,
        tiros_a_puerta = tiros_a_puerta - OLD.tiros_a_puerta,
        pases_totales = pases_totales - OLD.pases_totales,
        pases_clave = pases_clave - OLD.pases_clave,
        entradas = entradas - OLD.entradas,
        bloqueos = bloqueos - OLD.bloqueos,
        intercepciones = intercepciones - OLD.intercepciones,
        duelos_totales = duelos_totales - OLD.duelos_totales,
        duelos_ganados = duelos_ganados - OLD.duelos_ganados,
        faltas_sufridas = faltas_sufridas - OLD.faltas_recibidas,
        faltas_cometidas = faltas_cometidas - OLD.faltas_cometidas,
        regates_intentados = regates_intentados - OLD.regates_intentados,
        regates_exito = regates_exito - OLD.regates,
        regateado = regateado - OLD.regateado,
        amarillas = amarillas - OLD.amarilla,
        rojas = rojas - OLD.roja,
        penaltis_marcados = penaltis_marcados - OLD.penaltis_marcados,
        goles_concedidos = goles_concedidos - OLD.goles_concedidos,
        paradas = paradas - OLD.paradas,
        penaltis_parados = penaltis_parados - OLD.penaltis_parados
    WHERE id_jugador = OLD.id_jugador 
      AND id_equipo = OLD.id_equipo 
      AND temporada = v_temporada;

    -- 3. RECALCULAR NOTA MEDIA (El campo calculado independiente)
    -- Lo hacemos después de restar para que tome el promedio de lo que queda en la tabla
    UPDATE public.h_jugador_temporada
    SET nota_media = (
        SELECT COALESCE(AVG(h.nota), 0) -- Si no quedan partidos, la nota es 0
        FROM public.h_jugador_partido h
        JOIN public.dim_partidos p ON h.id_partido = p.id_partido
        WHERE h.id_jugador = OLD.id_jugador 
          AND h.id_equipo = OLD.id_equipo 
          AND p.temporada = v_temporada
    )
    WHERE id_jugador = OLD.id_jugador 
      AND id_equipo = OLD.id_equipo 
      AND temporada = v_temporada
    RETURNING partidos INTO v_partidos_restantes;

    -- 4. LIMPIEZA: Si el jugador ya no tiene partidos en esa temporada, borramos la fila
    IF v_partidos_restantes <= 0 THEN
        DELETE FROM public.h_jugador_temporada 
        WHERE id_jugador = OLD.id_jugador 
          AND id_equipo = OLD.id_equipo 
          AND temporada = v_temporada;
    END IF;

    RETURN OLD;
END;
$function$
;

DROP TRIGGER IF EXISTS trg_restar_temporada ON public.h_jugador_partido;

CREATE TRIGGER trg_restar_temporada
AFTER DELETE ON public.h_jugador_partido
FOR EACH ROW
EXECUTE FUNCTION restar_estadisticas_temporada();