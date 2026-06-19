-- =====================================================
-- MONTE CARLO
-- =====================================================

CREATE TABLE dm_simulacion_montecarlo (
    id_equipo INT NOT NULL,
    temporada INT NOT NULL,

    campeon_pct NUMERIC(5,2),
    champions_pct NUMERIC(5,2),
    europa_pct NUMERIC(5,2),
    media_tabla_pct NUMERIC(5,2),
    descenso_pct NUMERIC(5,2),

    fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id_equipo, temporada)
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

    fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

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

    prediccion VARCHAR(50),

    fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- NECESIDADES DE PLANTILLA
-- =====================================================

CREATE TABLE dm_necesidades_plantilla (
    id_equipo INT NOT NULL,
    temporada INT NOT NULL,

    necesidad VARCHAR(100),
    motivo VARCHAR(300),

    umbral_pct NUMERIC(5,2),

    fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id_equipo, temporada, necesidad)
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
    evolucion NUMERIC(6,2),

    fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    variabilidad NUMERIC(6,2),

    fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- PERFIL ESTADISTICO DE JUGADORES
-- =====================================================

CREATE TABLE dm_perfil_estadistico_jugadores (
    id_jugador INT NOT NULL,
    temporada INT NOT NULL,

    nombre VARCHAR(150),

    ataque NUMERIC(5,2),
    creacion NUMERIC(5,2),
    defensa NUMERIC(5,2),
    porteros NUMERIC(5,2),
    duelos NUMERIC(5,2),
    regates NUMERIC(5,2),

    percentil_ataque NUMERIC(5,2),
    percentil_creacion NUMERIC(5,2),
    percentil_defensa NUMERIC(5,2),
    percentil_porteros NUMERIC(5,2),
    percentil_duelos NUMERIC(5,2),
    percentil_regates NUMERIC(5,2),

    fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id_jugador, temporada)
);

-- =====================================================
-- CLUSTERING K-MEANS
-- =====================================================

CREATE TABLE dm_similitud_jugadores (
    id_jugador INT NOT NULL,
    temporada INT NOT NULL,

    nombre_jugador VARCHAR(150),

    cluster_id INT,
    perfil_cluster VARCHAR(100),

    fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id_jugador, temporada)
);

