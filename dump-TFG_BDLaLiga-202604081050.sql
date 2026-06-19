--
-- PostgreSQL database dump
--

\restrict 1KXEQ8RwP2l9oRzYfrsqhGYArY0Q6cDAmo9rfdflhMaMSVcQyXUHmdld15iePcD

-- Dumped from database version 18.1
-- Dumped by pg_dump version 18.1

-- Started on 2026-04-08 10:50:47

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 219 (class 1259 OID 40993)
-- Name: dim_equipo; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.dim_equipo (
    id_equipo integer NOT NULL,
    nombre_equipo character varying(100) NOT NULL,
    codigo character varying(10),
    pais character varying(50),
    fundado_en integer,
    logo text,
    estadio character varying(100),
    direccion character varying(255),
    ciudad character varying(100),
    capacidad integer
);


ALTER TABLE public.dim_equipo OWNER TO postgres;

--
-- TOC entry 220 (class 1259 OID 41002)
-- Name: dim_jugador; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.dim_jugador (
    id_jugador integer NOT NULL,
    nombre character varying(100),
    nombre_completo character varying(200),
    edad integer,
    fecha_nacimiento date,
    lugar_nacimiento character varying(100),
    pais_nacimiento character varying(100),
    nacionalidad character varying(100),
    altura integer,
    peso integer,
    foto text
);


ALTER TABLE public.dim_jugador OWNER TO postgres;

--
-- TOC entry 222 (class 1259 OID 41022)
-- Name: dim_partidos; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.dim_partidos (
    id_partido integer CONSTRAINT dim_partido_id_partido_not_null NOT NULL,
    id_tiempo integer,
    hora time without time zone,
    arbitro character varying(100),
    estadio character varying(100),
    temporada integer,
    id_local integer,
    id_visitante integer,
    ganador character varying(100),
    goles_local integer,
    goles_visitante integer,
    status character varying(50)
);


ALTER TABLE public.dim_partidos OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 41016)
-- Name: dim_tiempo; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.dim_tiempo (
    id_tiempo integer NOT NULL,
    anio integer,
    mes integer,
    nombre_mes character varying(20),
    dia integer,
    nombre_dia character varying(20),
    jornada integer
);


ALTER TABLE public.dim_tiempo OWNER TO postgres;

--
-- TOC entry 230 (class 1259 OID 41166)
-- Name: dim_usuario; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.dim_usuario (
    id_usuario integer NOT NULL,
    nombre_usuario character varying(50) NOT NULL,
    email character varying(255) NOT NULL,
    password_hash text NOT NULL,
    fecha_registro timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.dim_usuario OWNER TO postgres;

--
-- TOC entry 229 (class 1259 OID 41165)
-- Name: dim_usuario_id_usuario_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.dim_usuario_id_usuario_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.dim_usuario_id_usuario_seq OWNER TO postgres;

--
-- TOC entry 5130 (class 0 OID 0)
-- Dependencies: 229
-- Name: dim_usuario_id_usuario_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.dim_usuario_id_usuario_seq OWNED BY public.dim_usuario.id_usuario;


--
-- TOC entry 224 (class 1259 OID 41058)
-- Name: h_equipo_partido; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.h_equipo_partido (
    id_partido integer NOT NULL,
    id_equipo integer NOT NULL,
    tiros_a_puerta integer,
    tiros_totales integer,
    tiros_en_area integer,
    tiros_fuera_area integer,
    faltas_cometidas integer,
    corners integer,
    fueras_de_juego integer,
    posesion integer,
    tarjetas_amarillas integer,
    tarjetas_rojas integer,
    paradas integer,
    pases_totales integer,
    pases_acertados integer,
    pct_pases_acertados numeric(5,2),
    goles_esperados numeric(5,2),
    df_goles_esperados numeric(5,2)
);


ALTER TABLE public.h_equipo_partido OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 41045)
-- Name: h_equipo_temporada; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.h_equipo_temporada (
    id_equipo integer NOT NULL,
    temporada integer NOT NULL,
    jornada integer NOT NULL,
    posicion integer,
    nombre_equipo character varying(100),
    puntos integer,
    dg integer,
    forma character varying(10),
    partidos_jugados integer,
    victorias integer,
    empates integer,
    derrotas integer,
    gf integer,
    gc integer,
    partidos_jugados_local integer,
    victorias_local integer,
    empates_local integer,
    derrotas_local integer,
    gf_local integer,
    gc_local integer,
    partidos_jugados_visitante integer,
    victorias_visitante integer,
    empates_visitante integer,
    derrotas_visitante integer,
    gf_visitante integer,
    gc_visitante integer
);


ALTER TABLE public.h_equipo_temporada OWNER TO postgres;

--
-- TOC entry 225 (class 1259 OID 41075)
-- Name: h_jugador_partido; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.h_jugador_partido (
    id_partido integer NOT NULL,
    id_jugador integer NOT NULL,
    id_equipo integer,
    posicion character varying(10),
    minutos integer,
    nota numeric(4,2),
    capitan boolean,
    sustituto boolean,
    goles integer DEFAULT 0,
    penaltis_marcados integer DEFAULT 0,
    asistencias integer DEFAULT 0,
    paradas integer DEFAULT 0,
    goles_concedidos integer DEFAULT 0,
    tiros_totales integer DEFAULT 0,
    tiros_a_puerta integer DEFAULT 0,
    pases_totales integer DEFAULT 0,
    pases_clave integer DEFAULT 0,
    precision_pases integer DEFAULT 0,
    regates_intentados integer DEFAULT 0,
    regates integer DEFAULT 0,
    regateado integer DEFAULT 0,
    duelos_totales integer DEFAULT 0,
    duelos_ganados integer DEFAULT 0,
    faltas_cometidas integer DEFAULT 0,
    faltas_recibidas integer DEFAULT 0,
    entradas integer DEFAULT 0,
    bloqueos integer DEFAULT 0,
    intercepciones integer DEFAULT 0,
    amarilla integer DEFAULT 0,
    roja integer DEFAULT 0,
    penaltis_parados integer DEFAULT 0
);


ALTER TABLE public.h_jugador_partido OWNER TO postgres;

--
-- TOC entry 226 (class 1259 OID 41120)
-- Name: h_jugador_temporada; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.h_jugador_temporada (
    id_jugador integer NOT NULL,
    id_equipo integer NOT NULL,
    temporada integer NOT NULL,
    posicion character varying(50),
    partidos integer,
    minutos integer,
    titular integer,
    nota_media numeric(5,3),
    goles integer,
    asistencias integer,
    tiros_totales integer,
    tiros_a_puerta integer,
    pases_totales integer,
    pases_clave integer,
    precision_pases integer,
    entradas integer,
    bloqueos integer,
    intercepciones integer,
    duelos_totales integer,
    duelos_ganados integer,
    faltas_sufridas integer,
    faltas_cometidas integer,
    regates_intentados integer,
    regates_exito integer,
    regateado integer,
    amarillas integer,
    rojas integer,
    penaltis_marcados integer,
    goles_concedidos integer,
    paradas integer,
    penaltis_parados integer
);


ALTER TABLE public.h_jugador_temporada OWNER TO postgres;

--
-- TOC entry 228 (class 1259 OID 41139)
-- Name: h_partido_eventos; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.h_partido_eventos (
    id_evento integer NOT NULL,
    id_partido integer,
    minuto integer,
    extra integer DEFAULT 0,
    id_equipo integer,
    id_jugador integer,
    id_asistente_o_sale integer,
    tipo character varying(50),
    detalle character varying(100),
    comentarios text
);


ALTER TABLE public.h_partido_eventos OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 41138)
-- Name: h_partido_eventos_id_evento_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.h_partido_eventos_id_evento_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.h_partido_eventos_id_evento_seq OWNER TO postgres;

--
-- TOC entry 5131 (class 0 OID 0)
-- Dependencies: 227
-- Name: h_partido_eventos_id_evento_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.h_partido_eventos_id_evento_seq OWNED BY public.h_partido_eventos.id_evento;


--
-- TOC entry 232 (class 1259 OID 41185)
-- Name: h_usuario_favoritos; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.h_usuario_favoritos (
    id_favorito integer NOT NULL,
    id_usuario integer NOT NULL,
    id_equipo integer,
    id_jugador integer,
    fecha_agregado timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_favorito_not_empty CHECK (((id_equipo IS NOT NULL) OR (id_jugador IS NOT NULL)))
);


ALTER TABLE public.h_usuario_favoritos OWNER TO postgres;

--
-- TOC entry 231 (class 1259 OID 41184)
-- Name: h_usuario_favoritos_id_favorito_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.h_usuario_favoritos_id_favorito_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.h_usuario_favoritos_id_favorito_seq OWNER TO postgres;

--
-- TOC entry 5132 (class 0 OID 0)
-- Dependencies: 231
-- Name: h_usuario_favoritos_id_favorito_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.h_usuario_favoritos_id_favorito_seq OWNED BY public.h_usuario_favoritos.id_favorito;


--
-- TOC entry 4923 (class 2604 OID 41169)
-- Name: dim_usuario id_usuario; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dim_usuario ALTER COLUMN id_usuario SET DEFAULT nextval('public.dim_usuario_id_usuario_seq'::regclass);


--
-- TOC entry 4921 (class 2604 OID 41142)
-- Name: h_partido_eventos id_evento; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.h_partido_eventos ALTER COLUMN id_evento SET DEFAULT nextval('public.h_partido_eventos_id_evento_seq'::regclass);


--
-- TOC entry 4925 (class 2604 OID 41188)
-- Name: h_usuario_favoritos id_favorito; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.h_usuario_favoritos ALTER COLUMN id_favorito SET DEFAULT nextval('public.h_usuario_favoritos_id_favorito_seq'::regclass);


--
-- TOC entry 4929 (class 2606 OID 41001)
-- Name: dim_equipo dim_equipo_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dim_equipo
    ADD CONSTRAINT dim_equipo_pkey PRIMARY KEY (id_equipo);


--
-- TOC entry 4931 (class 2606 OID 41009)
-- Name: dim_jugador dim_jugador_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dim_jugador
    ADD CONSTRAINT dim_jugador_pkey PRIMARY KEY (id_jugador);


--
-- TOC entry 4935 (class 2606 OID 41027)
-- Name: dim_partidos dim_partido_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dim_partidos
    ADD CONSTRAINT dim_partido_pkey PRIMARY KEY (id_partido);


--
-- TOC entry 4933 (class 2606 OID 41021)
-- Name: dim_tiempo dim_tiempo_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dim_tiempo
    ADD CONSTRAINT dim_tiempo_pkey PRIMARY KEY (id_tiempo);


--
-- TOC entry 4950 (class 2606 OID 41182)
-- Name: dim_usuario dim_usuario_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dim_usuario
    ADD CONSTRAINT dim_usuario_email_key UNIQUE (email);


--
-- TOC entry 4952 (class 2606 OID 41180)
-- Name: dim_usuario dim_usuario_nombre_usuario_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dim_usuario
    ADD CONSTRAINT dim_usuario_nombre_usuario_key UNIQUE (nombre_usuario);


--
-- TOC entry 4954 (class 2606 OID 41178)
-- Name: dim_usuario dim_usuario_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dim_usuario
    ADD CONSTRAINT dim_usuario_pkey PRIMARY KEY (id_usuario);


--
-- TOC entry 4941 (class 2606 OID 41064)
-- Name: h_equipo_partido h_equipo_partido_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.h_equipo_partido
    ADD CONSTRAINT h_equipo_partido_pkey PRIMARY KEY (id_partido, id_equipo);


--
-- TOC entry 4939 (class 2606 OID 41052)
-- Name: h_equipo_temporada h_equipo_temporada_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.h_equipo_temporada
    ADD CONSTRAINT h_equipo_temporada_pkey PRIMARY KEY (id_equipo, temporada, jornada);


--
-- TOC entry 4943 (class 2606 OID 41104)
-- Name: h_jugador_partido h_jugador_partido_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.h_jugador_partido
    ADD CONSTRAINT h_jugador_partido_pkey PRIMARY KEY (id_partido, id_jugador);


--
-- TOC entry 4945 (class 2606 OID 41127)
-- Name: h_jugador_temporada h_jugador_temporada_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.h_jugador_temporada
    ADD CONSTRAINT h_jugador_temporada_pkey PRIMARY KEY (id_jugador, id_equipo, temporada);


--
-- TOC entry 4947 (class 2606 OID 41148)
-- Name: h_partido_eventos h_partido_eventos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.h_partido_eventos
    ADD CONSTRAINT h_partido_eventos_pkey PRIMARY KEY (id_evento);


--
-- TOC entry 4957 (class 2606 OID 41194)
-- Name: h_usuario_favoritos h_usuario_favoritos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.h_usuario_favoritos
    ADD CONSTRAINT h_usuario_favoritos_pkey PRIMARY KEY (id_favorito);


--
-- TOC entry 4948 (class 1259 OID 41164)
-- Name: idx_eventos_partido; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_eventos_partido ON public.h_partido_eventos USING btree (id_partido);


--
-- TOC entry 4958 (class 1259 OID 41211)
-- Name: idx_favoritos_equipo; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_favoritos_equipo ON public.h_usuario_favoritos USING btree (id_equipo) WHERE (id_equipo IS NOT NULL);


--
-- TOC entry 4959 (class 1259 OID 41212)
-- Name: idx_favoritos_jugador; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_favoritos_jugador ON public.h_usuario_favoritos USING btree (id_jugador) WHERE (id_jugador IS NOT NULL);


--
-- TOC entry 4960 (class 1259 OID 41210)
-- Name: idx_favoritos_usuario; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_favoritos_usuario ON public.h_usuario_favoritos USING btree (id_usuario);


--
-- TOC entry 4936 (class 1259 OID 41044)
-- Name: idx_partido_equipos; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_partido_equipos ON public.dim_partidos USING btree (id_local, id_visitante);


--
-- TOC entry 4937 (class 1259 OID 41043)
-- Name: idx_partido_tiempo; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_partido_tiempo ON public.dim_partidos USING btree (id_tiempo);


--
-- TOC entry 4955 (class 1259 OID 41183)
-- Name: idx_usuario_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_usuario_email ON public.dim_usuario USING btree (email);


--
-- TOC entry 4961 (class 2606 OID 41033)
-- Name: dim_partidos dim_partido_id_local_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dim_partidos
    ADD CONSTRAINT dim_partido_id_local_fkey FOREIGN KEY (id_local) REFERENCES public.dim_equipo(id_equipo);


--
-- TOC entry 4962 (class 2606 OID 41028)
-- Name: dim_partidos dim_partido_id_tiempo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dim_partidos
    ADD CONSTRAINT dim_partido_id_tiempo_fkey FOREIGN KEY (id_tiempo) REFERENCES public.dim_tiempo(id_tiempo);


--
-- TOC entry 4963 (class 2606 OID 41038)
-- Name: dim_partidos dim_partido_id_visitante_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dim_partidos
    ADD CONSTRAINT dim_partido_id_visitante_fkey FOREIGN KEY (id_visitante) REFERENCES public.dim_equipo(id_equipo);


--
-- TOC entry 4965 (class 2606 OID 41070)
-- Name: h_equipo_partido h_equipo_partido_id_equipo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.h_equipo_partido
    ADD CONSTRAINT h_equipo_partido_id_equipo_fkey FOREIGN KEY (id_equipo) REFERENCES public.dim_equipo(id_equipo);


--
-- TOC entry 4966 (class 2606 OID 41065)
-- Name: h_equipo_partido h_equipo_partido_id_partido_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.h_equipo_partido
    ADD CONSTRAINT h_equipo_partido_id_partido_fkey FOREIGN KEY (id_partido) REFERENCES public.dim_partidos(id_partido);


--
-- TOC entry 4964 (class 2606 OID 41053)
-- Name: h_equipo_temporada h_equipo_temporada_id_equipo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.h_equipo_temporada
    ADD CONSTRAINT h_equipo_temporada_id_equipo_fkey FOREIGN KEY (id_equipo) REFERENCES public.dim_equipo(id_equipo);


--
-- TOC entry 4967 (class 2606 OID 41115)
-- Name: h_jugador_partido h_jugador_partido_id_equipo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.h_jugador_partido
    ADD CONSTRAINT h_jugador_partido_id_equipo_fkey FOREIGN KEY (id_equipo) REFERENCES public.dim_equipo(id_equipo);


--
-- TOC entry 4968 (class 2606 OID 41110)
-- Name: h_jugador_partido h_jugador_partido_id_jugador_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.h_jugador_partido
    ADD CONSTRAINT h_jugador_partido_id_jugador_fkey FOREIGN KEY (id_jugador) REFERENCES public.dim_jugador(id_jugador);


--
-- TOC entry 4969 (class 2606 OID 41105)
-- Name: h_jugador_partido h_jugador_partido_id_partido_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.h_jugador_partido
    ADD CONSTRAINT h_jugador_partido_id_partido_fkey FOREIGN KEY (id_partido) REFERENCES public.dim_partidos(id_partido);


--
-- TOC entry 4970 (class 2606 OID 41133)
-- Name: h_jugador_temporada h_jugador_temporada_id_equipo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.h_jugador_temporada
    ADD CONSTRAINT h_jugador_temporada_id_equipo_fkey FOREIGN KEY (id_equipo) REFERENCES public.dim_equipo(id_equipo);


--
-- TOC entry 4971 (class 2606 OID 41128)
-- Name: h_jugador_temporada h_jugador_temporada_id_jugador_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.h_jugador_temporada
    ADD CONSTRAINT h_jugador_temporada_id_jugador_fkey FOREIGN KEY (id_jugador) REFERENCES public.dim_jugador(id_jugador);


--
-- TOC entry 4972 (class 2606 OID 41154)
-- Name: h_partido_eventos h_partido_eventos_id_equipo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.h_partido_eventos
    ADD CONSTRAINT h_partido_eventos_id_equipo_fkey FOREIGN KEY (id_equipo) REFERENCES public.dim_equipo(id_equipo);


--
-- TOC entry 4973 (class 2606 OID 41159)
-- Name: h_partido_eventos h_partido_eventos_id_jugador_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.h_partido_eventos
    ADD CONSTRAINT h_partido_eventos_id_jugador_fkey FOREIGN KEY (id_jugador) REFERENCES public.dim_jugador(id_jugador);


--
-- TOC entry 4974 (class 2606 OID 41149)
-- Name: h_partido_eventos h_partido_eventos_id_partido_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.h_partido_eventos
    ADD CONSTRAINT h_partido_eventos_id_partido_fkey FOREIGN KEY (id_partido) REFERENCES public.dim_partidos(id_partido);


--
-- TOC entry 4975 (class 2606 OID 41200)
-- Name: h_usuario_favoritos h_usuario_favoritos_id_equipo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.h_usuario_favoritos
    ADD CONSTRAINT h_usuario_favoritos_id_equipo_fkey FOREIGN KEY (id_equipo) REFERENCES public.dim_equipo(id_equipo) ON DELETE CASCADE;


--
-- TOC entry 4976 (class 2606 OID 41205)
-- Name: h_usuario_favoritos h_usuario_favoritos_id_jugador_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.h_usuario_favoritos
    ADD CONSTRAINT h_usuario_favoritos_id_jugador_fkey FOREIGN KEY (id_jugador) REFERENCES public.dim_jugador(id_jugador) ON DELETE CASCADE;


--
-- TOC entry 4977 (class 2606 OID 41195)
-- Name: h_usuario_favoritos h_usuario_favoritos_id_usuario_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.h_usuario_favoritos
    ADD CONSTRAINT h_usuario_favoritos_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.dim_usuario(id_usuario) ON DELETE CASCADE;


-- Completed on 2026-04-08 10:50:48

--
-- PostgreSQL database dump complete
--

\unrestrict 1KXEQ8RwP2l9oRzYfrsqhGYArY0Q6cDAmo9rfdflhMaMSVcQyXUHmdld15iePcD

