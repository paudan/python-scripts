--
-- PostgreSQL database dump
--

-- Dumped from database version 9.3.1
-- Dumped by pg_dump version 9.3.0
-- Started on 2015-10-02 00:38:57

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- TOC entry 11 (class 2615 OID 14810667)
-- Name: google_finance; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA google_finance;


ALTER SCHEMA google_finance OWNER TO postgres;

SET search_path = google_finance, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- TOC entry 296 (class 1259 OID 14982990)
-- Name: financial_data; Type: TABLE; Schema: google_finance; Owner: postgres; Tablespace: 
--

CREATE TABLE financial_data (
    id integer NOT NULL,
    type character varying(20) NOT NULL,
    issue_date date NOT NULL,
    ticker character varying(10) NOT NULL,
    data json,
    annual boolean
);


ALTER TABLE google_finance.financial_data OWNER TO postgres;

--
-- TOC entry 295 (class 1259 OID 14982988)
-- Name: financial_data_id_seq; Type: SEQUENCE; Schema: google_finance; Owner: postgres
--

CREATE SEQUENCE financial_data_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE google_finance.financial_data_id_seq OWNER TO postgres;

--
-- TOC entry 2386 (class 0 OID 0)
-- Dependencies: 295
-- Name: financial_data_id_seq; Type: SEQUENCE OWNED BY; Schema: google_finance; Owner: postgres
--

ALTER SEQUENCE financial_data_id_seq OWNED BY financial_data.id;


--
-- TOC entry 297 (class 1259 OID 14983021)
-- Name: parsed; Type: TABLE; Schema: google_finance; Owner: postgres; Tablespace: 
--

CREATE TABLE parsed (
    ticker character varying(10) NOT NULL,
    id integer NOT NULL,
    timest timestamp(0) without time zone DEFAULT now() NOT NULL
);


ALTER TABLE google_finance.parsed OWNER TO postgres;

--
-- TOC entry 298 (class 1259 OID 14983026)
-- Name: parsed_id_seq; Type: SEQUENCE; Schema: google_finance; Owner: postgres
--

CREATE SEQUENCE parsed_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE google_finance.parsed_id_seq OWNER TO postgres;

--
-- TOC entry 2387 (class 0 OID 0)
-- Dependencies: 298
-- Name: parsed_id_seq; Type: SEQUENCE OWNED BY; Schema: google_finance; Owner: postgres
--

ALTER SEQUENCE parsed_id_seq OWNED BY parsed.id;


--
-- TOC entry 294 (class 1259 OID 14810668)
-- Name: tickers; Type: TABLE; Schema: google_finance; Owner: postgres; Tablespace: 
--

CREATE TABLE tickers (
    ticker character varying(10) NOT NULL,
    exchange character varying(10),
    company_name character varying(100)
);


ALTER TABLE google_finance.tickers OWNER TO postgres;

--
-- TOC entry 2239 (class 2604 OID 14982993)
-- Name: id; Type: DEFAULT; Schema: google_finance; Owner: postgres
--

ALTER TABLE ONLY financial_data ALTER COLUMN id SET DEFAULT nextval('financial_data_id_seq'::regclass);


--
-- TOC entry 2240 (class 2604 OID 14983028)
-- Name: id; Type: DEFAULT; Schema: google_finance; Owner: postgres
--

ALTER TABLE ONLY parsed ALTER COLUMN id SET DEFAULT nextval('parsed_id_seq'::regclass);


--
-- TOC entry 2245 (class 2606 OID 14982998)
-- Name: financial_data_pkey; Type: CONSTRAINT; Schema: google_finance; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY financial_data
    ADD CONSTRAINT financial_data_pkey PRIMARY KEY (id);


--
-- TOC entry 2247 (class 2606 OID 14983030)
-- Name: parsed_pkey; Type: CONSTRAINT; Schema: google_finance; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY parsed
    ADD CONSTRAINT parsed_pkey PRIMARY KEY (id);


--
-- TOC entry 2243 (class 2606 OID 14810672)
-- Name: tickers_gf_pkey; Type: CONSTRAINT; Schema: google_finance; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY tickers
    ADD CONSTRAINT tickers_gf_pkey PRIMARY KEY (ticker);


--
-- TOC entry 2248 (class 2606 OID 14982999)
-- Name: financial_data_fk; Type: FK CONSTRAINT; Schema: google_finance; Owner: postgres
--

ALTER TABLE ONLY financial_data
    ADD CONSTRAINT financial_data_fk FOREIGN KEY (ticker) REFERENCES tickers(ticker) ON UPDATE CASCADE ON DELETE RESTRICT;


-- Completed on 2015-10-02 00:38:58

--
-- PostgreSQL database dump complete
--

