-- DROP FUNCTION public.actualizar_estadisticas_temporada();

CREATE OR REPLACE FUNCTION public.actualizar_estadisticas_temporada()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_temporada integer;
BEGIN
    -- 1. Obtener la temporada desde dim_partidos
    SELECT temporada INTO v_temporada 
    FROM public.dim_partidos 
    WHERE id_partido = NEW.id_partido;

    -- 2. Actualizar si ya existe el registro, o insertar si no (UPSERT)
    INSERT INTO public.h_jugador_temporada (
        id_jugador, id_equipo, temporada, posicion, partidos, minutos, 
        titular, goles, asistencias, tiros_totales, tiros_a_puerta, 
        pases_totales, pases_clave, precision_pases, entradas, bloqueos, 
        intercepciones, duelos_totales, duelos_ganados, faltas_sufridas, 
        faltas_cometidas, regates_intentados, regates_exito, regateado, 
        amarillas, rojas, penaltis_marcados, goles_concedidos, paradas, penaltis_parados
    )
    VALUES (
        NEW.id_jugador, NEW.id_equipo, v_temporada, NEW.posicion, 1, NEW.minutos,
        CASE WHEN NEW.sustituto = FALSE THEN 1 ELSE 0 END, 
        NEW.goles, NEW.asistencias, NEW.tiros_totales, NEW.tiros_a_puerta,
        NEW.pases_totales, NEW.pases_clave, NEW.precision_pases, NEW.entradas, NEW.bloqueos,
        NEW.intercepciones, NEW.duelos_totales, NEW.duelos_ganados, NEW.faltas_recibidas,
        NEW.faltas_cometidas, NEW.regates_intentados, NEW.regates, NEW.regateado,
        NEW.amarilla, NEW.roja, NEW.penaltis_marcados, NEW.goles_concedidos, NEW.paradas, NEW.penaltis_parados
    )
    ON CONFLICT (id_jugador, id_equipo, temporada) 
    DO UPDATE SET
        partidos = h_jugador_temporada.partidos + 1,
        minutos = h_jugador_temporada.minutos + EXCLUDED.minutos,
        titular = h_jugador_temporada.titular + EXCLUDED.titular,
        goles = h_jugador_temporada.goles + EXCLUDED.goles,
        asistencias = h_jugador_temporada.asistencias + EXCLUDED.asistencias,
        tiros_totales = h_jugador_temporada.tiros_totales + EXCLUDED.tiros_totales,
        tiros_a_puerta = h_jugador_temporada.tiros_a_puerta + EXCLUDED.tiros_a_puerta,
        pases_totales = h_jugador_temporada.pases_totales + EXCLUDED.pases_totales,
        pases_clave = h_jugador_temporada.pases_clave + EXCLUDED.pases_clave,
        entradas = h_jugador_temporada.entradas + EXCLUDED.entradas,
        bloqueos = h_jugador_temporada.bloqueos + EXCLUDED.bloqueos,
        intercepciones = h_jugador_temporada.intercepciones + EXCLUDED.intercepciones,
        duelos_totales = h_jugador_temporada.duelos_totales + EXCLUDED.duelos_totales,
        duelos_ganados = h_jugador_temporada.duelos_ganados + EXCLUDED.duelos_ganados,
        faltas_sufridas = h_jugador_temporada.faltas_sufridas + EXCLUDED.faltas_sufridas,
        faltas_cometidas = h_jugador_temporada.faltas_cometidas + EXCLUDED.faltas_cometidas,
        regates_intentados = h_jugador_temporada.regates_intentados + EXCLUDED.regates_intentados,
        regates_exito = h_jugador_temporada.regates_exito + EXCLUDED.regates_exito,
        regateado = h_jugador_temporada.regateado + EXCLUDED.regateado,
        amarillas = h_jugador_temporada.amarillas + EXCLUDED.amarillas,
        rojas = h_jugador_temporada.rojas + EXCLUDED.rojas,
        penaltis_marcados = h_jugador_temporada.penaltis_marcados + EXCLUDED.penaltis_marcados,
        goles_concedidos = h_jugador_temporada.goles_concedidos + EXCLUDED.goles_concedidos,
        paradas = h_jugador_temporada.paradas + EXCLUDED.paradas,
        penaltis_parados = h_jugador_temporada.penaltis_parados + EXCLUDED.penaltis_parados;

	UPDATE public.h_jugador_temporada
    SET nota_media = (
        SELECT AVG(h.nota)
        FROM public.h_jugador_partido h
        JOIN public.dim_partidos p ON h.id_partido = p.id_partido
        WHERE h.id_jugador = NEW.id_jugador 
          AND h.id_equipo = NEW.id_equipo 
          AND p.temporada = v_temporada
    )
    WHERE id_jugador = NEW.id_jugador 
      AND id_equipo = NEW.id_equipo 
      AND temporada = v_temporada;

    RETURN NEW;
END;
$function$
;

CREATE TRIGGER trg_actualizar_temporada
AFTER INSERT ON public.h_jugador_partido
FOR EACH ROW
EXECUTE FUNCTION actualizar_estadisticas_temporada();