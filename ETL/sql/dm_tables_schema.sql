-- Esquema de las tablas de Data Mining de LaLiga (PostgreSQL).
--
-- Requisitos en la base de datos destino:
--   public.dim_equipo   (PK: id_equipo)
--   public.dim_jugador  (PK: id_jugador)
--   public.dim_partidos (PK: id_partido)
--
-- Este script crea solamente la estructura; no copia los datos.
-- Esta pensado para ejecutarse una sola vez sobre una BD que aun no tenga
-- las tablas dm_*.

BEGIN;

CREATE SCHEMA IF NOT EXISTS public;

DO $preflight$
BEGIN
    IF to_regclass('public.dim_equipo') IS NULL THEN
        RAISE EXCEPTION
            'Falta la tabla requerida public.dim_equipo en la base de datos destino';
    END IF;

    IF to_regclass('public.dim_jugador') IS NULL THEN
        RAISE EXCEPTION
            'Falta la tabla requerida public.dim_jugador en la base de datos destino';
    END IF;

    IF to_regclass('public.dim_partidos') IS NULL THEN
        RAISE EXCEPTION
            'Falta la tabla requerida public.dim_partidos en la base de datos destino';
    END IF;
END
$preflight$;

CREATE TABLE public.dm_estado_forma_jugadores (
    id_jugador       integer                NOT NULL,
    nombre_jugador   character varying(150),
    id_equipo        integer,
    estado           character varying(50),
    score_temporada  numeric(6,2),
    score_reciente   numeric(6,2),
    evolucion        numeric(6,2),

    CONSTRAINT dm_estado_forma_jugadores_pkey
        PRIMARY KEY (id_jugador),
    CONSTRAINT fk_dm_estado_forma_jugadores_jugador
        FOREIGN KEY (id_jugador)
        REFERENCES public.dim_jugador (id_jugador),
    CONSTRAINT fk_dm_estado_forma_jugadores_equipo
        FOREIGN KEY (id_equipo)
        REFERENCES public.dim_equipo (id_equipo)
);

CREATE TABLE public.dm_forma_equipos (
    temporada        integer                NOT NULL,
    id_equipo        integer                NOT NULL,
    nombre_equipo    character varying(150),
    puntuacion_forma numeric(5,2),
    estado           character varying(50),
    tendencia        numeric(5,2),
    variabilidad     numeric(5,2),

    CONSTRAINT dm_forma_equipos_pkey
        PRIMARY KEY (temporada, id_equipo),
    CONSTRAINT fk_dm_forma_equipos_equipo
        FOREIGN KEY (id_equipo)
        REFERENCES public.dim_equipo (id_equipo)
);

CREATE TABLE public.dm_golesesperados_partidos (
    id_partido                bigint                 NOT NULL,
    id_local                  integer                NOT NULL,
    nombre_local              character varying(100),
    id_visitante              integer                NOT NULL,
    nombre_visitante          character varying(100),
    goles_local_esperados     numeric(5,2),
    goles_visitante_esperados numeric(5,2),
    diferencia_goles_esperada numeric(5,2),
    resultado_estimado        character varying(30),
    marcador_estimado         character varying(10),

    CONSTRAINT dm_golesesperados_partidos_pkey
        PRIMARY KEY (id_partido),
    CONSTRAINT fk_dm_golesesperados_partido
        FOREIGN KEY (id_partido)
        REFERENCES public.dim_partidos (id_partido),
    CONSTRAINT fk_dm_golesesperados_local
        FOREIGN KEY (id_local)
        REFERENCES public.dim_equipo (id_equipo),
    CONSTRAINT fk_dm_golesesperados_visitante
        FOREIGN KEY (id_visitante)
        REFERENCES public.dim_equipo (id_equipo)
);

CREATE TABLE public.dm_jugadores_ratings (
    id_jugador          integer          NOT NULL,
    temporada           integer          NOT NULL,
    nombre              text,
    ataque              double precision,
    creacion            double precision,
    defensa             double precision,
    porteros            double precision,
    duelos              double precision,
    regates             double precision,
    percentil_ataque    double precision,
    percentil_creacion  double precision,
    percentil_defensa   double precision,
    percentil_porteros  double precision,
    percentil_duelos    double precision,
    percentil_regates   double precision,

    CONSTRAINT dm_jugadores_ratings_pkey
        PRIMARY KEY (id_jugador, temporada),
    CONSTRAINT fk_dm_jugadores_ratings_jugador
        FOREIGN KEY (id_jugador)
        REFERENCES public.dim_jugador (id_jugador)
);

CREATE TABLE public.dm_necesidades_plantilla (
    id_equipo  integer                NOT NULL,
    temporada  integer                NOT NULL,
    necesidad character varying(100) NOT NULL,
    motivo     character varying(300),

    CONSTRAINT dm_necesidades_plantilla_pkey
        PRIMARY KEY (id_equipo, temporada, necesidad),
    CONSTRAINT fk_dm_necesidades_plantilla_equipo
        FOREIGN KEY (id_equipo)
        REFERENCES public.dim_equipo (id_equipo)
);

CREATE TABLE public.dm_prediccion_partidos (
    id_partido              bigint                 NOT NULL,
    id_local                integer,
    nombre_local            character varying(100),
    id_visitante            integer,
    nombre_visitante        character varying(100),
    prob_victoria_local     numeric(5,2),
    prob_empate             numeric(5,2),
    prob_victoria_visitante numeric(5,2),
    prediccion              character varying(50),

    CONSTRAINT dm_prediccion_partidos_pkey
        PRIMARY KEY (id_partido),
    CONSTRAINT fk_dm_prediccion_partidos_partido
        FOREIGN KEY (id_partido)
        REFERENCES public.dim_partidos (id_partido),
    CONSTRAINT fk_dm_prediccion_partidos_local
        FOREIGN KEY (id_local)
        REFERENCES public.dim_equipo (id_equipo),
    CONSTRAINT fk_dm_prediccion_partidos_visitante
        FOREIGN KEY (id_visitante)
        REFERENCES public.dim_equipo (id_equipo)
);

CREATE TABLE public.dm_probables_goleadores (
    id_partido      bigint                 NOT NULL,
    id_equipo       integer                NOT NULL,
    id_jugador      bigint                 NOT NULL,
    nombre_jugador  character varying(150),
    probabilidad    numeric(5,3),

    CONSTRAINT dm_probables_goleadores_pkey
        PRIMARY KEY (id_partido, id_jugador),
    CONSTRAINT fk_dm_probables_goleadores_partido
        FOREIGN KEY (id_partido)
        REFERENCES public.dim_partidos (id_partido),
    CONSTRAINT fk_dm_probables_goleadores_equipo
        FOREIGN KEY (id_equipo)
        REFERENCES public.dim_equipo (id_equipo),
    CONSTRAINT fk_dm_probables_goleadores_jugador
        FOREIGN KEY (id_jugador)
        REFERENCES public.dim_jugador (id_jugador)
);

CREATE TABLE public.dm_recomendacion_fichajes (
    id_equipo           integer                NOT NULL,
    nombre_equipo       character varying(150),
    necesidad           character varying(100) NOT NULL,
    id_jugador          integer                NOT NULL,
    nombre_jugador      character varying(150),
    id_equipo_actual    integer,
    equipo_actual       character varying(150),
    score_recomendacion numeric(6,4),
    motivo              character varying(300),

    CONSTRAINT dm_recomendacion_fichajes_pkey
        PRIMARY KEY (id_equipo, necesidad, id_jugador),
    CONSTRAINT fk_dm_recomendacion_equipo
        FOREIGN KEY (id_equipo)
        REFERENCES public.dim_equipo (id_equipo),
    CONSTRAINT fk_dm_recomendacion_jugador
        FOREIGN KEY (id_jugador)
        REFERENCES public.dim_jugador (id_jugador),
    CONSTRAINT fk_dm_recomendacion_equipo_actual
        FOREIGN KEY (id_equipo_actual)
        REFERENCES public.dim_equipo (id_equipo)
);

CREATE TABLE public.dm_similitud_jugadores (
    id_jugador       integer                NOT NULL,
    temporada        integer                NOT NULL,
    nombre           character varying(150),
    posicion         character varying(50),
    cluster          integer,
    id_similar1      integer,
    nombre_similar1  character varying(150),
    similitud1       numeric(8,4),
    id_similar2      integer,
    nombre_similar2  character varying(150),
    similitud2       numeric(8,4),
    id_similar3      integer,
    nombre_similar3  character varying(150),
    similitud3       numeric(8,4),
    id_similar4      integer,
    nombre_similar4  character varying(150),
    similitud4       numeric(8,4),
    id_similar5      integer,
    nombre_similar5  character varying(150),
    similitud5       numeric(8,4),

    CONSTRAINT dm_similitud_jugadores_pkey
        PRIMARY KEY (id_jugador, temporada),
    CONSTRAINT fk_dm_similitud_jugadores_jugador
        FOREIGN KEY (id_jugador)
        REFERENCES public.dim_jugador (id_jugador),
    CONSTRAINT fk_dm_similitud_jugadores_similar1
        FOREIGN KEY (id_similar1)
        REFERENCES public.dim_jugador (id_jugador),
    CONSTRAINT fk_dm_similitud_jugadores_similar2
        FOREIGN KEY (id_similar2)
        REFERENCES public.dim_jugador (id_jugador),
    CONSTRAINT fk_dm_similitud_jugadores_similar3
        FOREIGN KEY (id_similar3)
        REFERENCES public.dim_jugador (id_jugador),
    CONSTRAINT fk_dm_similitud_jugadores_similar4
        FOREIGN KEY (id_similar4)
        REFERENCES public.dim_jugador (id_jugador),
    CONSTRAINT fk_dm_similitud_jugadores_similar5
        FOREIGN KEY (id_similar5)
        REFERENCES public.dim_jugador (id_jugador)
);

CREATE TABLE public.dm_simulacion_montecarlo (
    id_equipo       integer                NOT NULL,
    equipo          character varying(150),
    campeon_pct     numeric(5,2),
    champions_pct   numeric(5,2),
    europa_pct      numeric(5,2),
    media_tabla_pct numeric(5,2),
    descenso_pct    numeric(5,2),

    CONSTRAINT dm_simulacion_montecarlo_pkey
        PRIMARY KEY (id_equipo),
    CONSTRAINT fk_dm_simulacion_montecarlo_equipo
        FOREIGN KEY (id_equipo)
        REFERENCES public.dim_equipo (id_equipo)
);

-- PostgreSQL no crea automaticamente indices para las columnas que actuan
-- como claves foraneas. Estos indices aceleran joins y comprobaciones.
CREATE INDEX idx_dm_estado_forma_jugadores_equipo
    ON public.dm_estado_forma_jugadores (id_equipo);

CREATE INDEX idx_dm_forma_equipos_equipo
    ON public.dm_forma_equipos (id_equipo);

CREATE INDEX idx_dm_golesesperados_local
    ON public.dm_golesesperados_partidos (id_local);

CREATE INDEX idx_dm_golesesperados_visitante
    ON public.dm_golesesperados_partidos (id_visitante);

CREATE INDEX idx_dm_jugadores_ratings_temporada
    ON public.dm_jugadores_ratings (temporada);

CREATE INDEX idx_dm_necesidades_plantilla_temporada
    ON public.dm_necesidades_plantilla (temporada);

CREATE INDEX idx_dm_prediccion_partidos_local
    ON public.dm_prediccion_partidos (id_local);

CREATE INDEX idx_dm_prediccion_partidos_visitante
    ON public.dm_prediccion_partidos (id_visitante);

CREATE INDEX idx_dm_probables_goleadores_equipo
    ON public.dm_probables_goleadores (id_equipo);

CREATE INDEX idx_dm_probables_goleadores_jugador
    ON public.dm_probables_goleadores (id_jugador);

CREATE INDEX idx_dm_recomendacion_fichajes_jugador
    ON public.dm_recomendacion_fichajes (id_jugador);

CREATE INDEX idx_dm_recomendacion_fichajes_equipo_actual
    ON public.dm_recomendacion_fichajes (id_equipo_actual);

CREATE INDEX idx_dm_similitud_jugadores_temporada
    ON public.dm_similitud_jugadores (temporada);

CREATE INDEX idx_dm_similitud_jugadores_similar1
    ON public.dm_similitud_jugadores (id_similar1);

CREATE INDEX idx_dm_similitud_jugadores_similar2
    ON public.dm_similitud_jugadores (id_similar2);

CREATE INDEX idx_dm_similitud_jugadores_similar3
    ON public.dm_similitud_jugadores (id_similar3);

CREATE INDEX idx_dm_similitud_jugadores_similar4
    ON public.dm_similitud_jugadores (id_similar4);

CREATE INDEX idx_dm_similitud_jugadores_similar5
    ON public.dm_similitud_jugadores (id_similar5);

COMMIT;
