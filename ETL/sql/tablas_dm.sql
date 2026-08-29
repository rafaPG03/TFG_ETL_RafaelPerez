-- =====================================================
-- MONTE CARLO
-- =====================================================

CREATE TABLE dm_simulacion_montecarlo (
    id_equipo INT NOT NULL,
    equipo VARCHAR(150),

    campeon_pct NUMERIC(5,2),
    champions_pct NUMERIC(5,2),
    europa_pct NUMERIC(5,2),
    media_tabla_pct NUMERIC(5,2),
    descenso_pct NUMERIC(5,2),

    PRIMARY KEY (id_equipo)
);

-- =====================================================
-- PROBABLES GOLEADORES
-- =====================================================

CREATE TABLE dm_probables_goleadores (
    id_partido BIGINT NOT NULL,
    id_equipo INT NOT NULL,
    id_jugador INT NOT NULL,

    nombre_jugador VARCHAR(150),
    probabilidad NUMERIC(5,3),

    PRIMARY KEY (id_partido, id_jugador)
);

-- =====================================================
-- PREDICCION DE PARTIDOS (RANDOM FOREST)
-- =====================================================

CREATE TABLE dm_prediccion_partidos (
    id_partido BIGINT PRIMARY KEY,

    fecha DATE,

    id_local INT,
    nombre_local VARCHAR(100),

    id_visitante INT,
    nombre_visitante VARCHAR(100),

    prob_victoria_local NUMERIC(5,2),
    prob_empate NUMERIC(5,2),
    prob_victoria_visitante NUMERIC(5,2),
    prediccion VARCHAR(50)
);

-- =====================================================
-- NECESIDADES DE PLANTILLA
-- =====================================================

CREATE TABLE dm_necesidades_plantilla (
    id_equipo INT NOT NULL,
    temporada INT NOT NULL,

    necesidad VARCHAR(100),
    motivo VARCHAR(300),

    PRIMARY KEY (id_equipo, necesidad)
);

-- =====================================================
-- ESTADO DE FORMA DE JUGADORES
-- =====================================================

CREATE TABLE dm_estado_forma_jugadores (
    id_jugador INT PRIMARY KEY,

    nombre_jugador VARCHAR(150),
    id_equipo INT,

    estado VARCHAR(50),

    score_temporada NUMERIC(6,2),
    score_reciente NUMERIC(6,2),
    evolucion NUMERIC(6,2)
);

-- =====================================================
-- ESTADO DE FORMA DE EQUIPOS
-- =====================================================

CREATE TABLE dm_estado_forma_equipos (
    id_equipo INT PRIMARY KEY,

    nombre_equipo VARCHAR(150),

    puntuacion_forma NUMERIC(5,2),
    estado VARCHAR(50),

    tendencia NUMERIC(6,2),
    variabilidad NUMERIC(6,2)
);

-- =====================================================
-- CLUSTERING K-MEANS
-- =====================================================

CREATE TABLE dm_similitud_jugadores (
    id_jugador INT NOT NULL,
    temporada INT NOT NULL,

    nombre VARCHAR(150),
    posicion VARCHAR(50),
    cluster INT,

    id_similar1 INT,
    nombre_similar1 VARCHAR(150),
    similitud1 NUMERIC(8,4),

    id_similar2 INT,
    nombre_similar2 VARCHAR(150),
    similitud2 NUMERIC(8,4),

    id_similar3 INT,
    nombre_similar3 VARCHAR(150),
    similitud3 NUMERIC(8,4),

    id_similar4 INT,
    nombre_similar4 VARCHAR(150),
    similitud4 NUMERIC(8,4),

    id_similar5 INT,
    nombre_similar5 VARCHAR(150),
    similitud5 NUMERIC(8,4),

    PRIMARY KEY (id_jugador, temporada)
);

-- =====================================================
-- RECOMENDACION DE FICHAJES
-- =====================================================

CREATE TABLE dm_recomendacion_fichajes (
    id_equipo INT NOT NULL,
    nombre_equipo VARCHAR(150),

    necesidad VARCHAR(100) NOT NULL,

    id_jugador INT NOT NULL,
    nombre_jugador VARCHAR(150),

    id_equipo_actual INT,
    equipo_actual VARCHAR(150),

    score_recomendacion NUMERIC(8,4),
    motivo VARCHAR(300),

    PRIMARY KEY (id_equipo, necesidad, id_jugador)
);

