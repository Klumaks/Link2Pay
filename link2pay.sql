--
-- PostgreSQL database dump
--

-- Dumped from database version 14.17 (Ubuntu 14.17-0ubuntu0.22.04.1)
-- Dumped by pg_dump version 17.4

-- Started on 2025-11-19 19:19:10

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

--
-- TOC entry 4 (class 2615 OID 2200)
-- Name: public; Type: SCHEMA; Schema: -; Owner: postgres
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 213 (class 1259 OID 16483)
-- Name: date; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.date (
    id_date integer NOT NULL,
    id_transaction integer NOT NULL,
    amount integer NOT NULL,
    link_type "char" NOT NULL,
    message character varying
);


ALTER TABLE public.date OWNER TO postgres;

--
-- TOC entry 212 (class 1259 OID 16478)
-- Name: transaction; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.transaction (
    id_transaction integer NOT NULL,
    id_first_user bigint NOT NULL,
    id_second_user bigint,
    type "char" NOT NULL,
    link character varying,
    id_date integer NOT NULL
);


ALTER TABLE public.transaction OWNER TO postgres;

--
-- TOC entry 211 (class 1259 OID 16470)
-- Name: transfer; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.transfer (
    id integer NOT NULL,
    recipient character varying NOT NULL,
    payers character varying,
    ammount character varying,
    details character varying,
    id_link character varying
);


ALTER TABLE public.transfer OWNER TO postgres;

--
-- TOC entry 210 (class 1259 OID 16469)
-- Name: transfer_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.transfer_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.transfer_id_seq OWNER TO postgres;

--
-- TOC entry 3348 (class 0 OID 0)
-- Dependencies: 210
-- Name: transfer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.transfer_id_seq OWNED BY public.transfer.id;


--
-- TOC entry 214 (class 1259 OID 16503)
-- Name: users_id_user_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_user_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_user_seq OWNER TO postgres;

--
-- TOC entry 209 (class 1259 OID 16464)
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id_user integer DEFAULT nextval('public.users_id_user_seq'::regclass) NOT NULL,
    chat_id bigint NOT NULL,
    username character varying NOT NULL,
    name character varying NOT NULL,
    phone character varying(15) NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- TOC entry 3185 (class 2604 OID 16502)
-- Name: transfer id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transfer ALTER COLUMN id SET DEFAULT nextval('public.transfer_id_seq'::regclass);


--
-- TOC entry 3340 (class 0 OID 16483)
-- Dependencies: 213
-- Data for Name: date; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.date (id_date, id_transaction, amount, link_type, message) FROM stdin;
\.


--
-- TOC entry 3339 (class 0 OID 16478)
-- Dependencies: 212
-- Data for Name: transaction; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.transaction (id_transaction, id_first_user, id_second_user, type, link, id_date) FROM stdin;
\.


--
-- TOC entry 3338 (class 0 OID 16470)
-- Dependencies: 211
-- Data for Name: transfer; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.transfer (id, recipient, payers, ammount, details, id_link) FROM stdin;
2	Klumaks	username	3		1
3	Klumaks	cufiieirkc	57		2
4	Klumaks	fudjcj	557		3
5	Klumaks	hxucjv	667		4
6	Klumaks	jfcici	567		5
7	Klumaks	jdckjfnr	288338		6
8	FinCrazy	klumax	100		7
9	vvvikos_babosss	Klumaks	55		8
10	Dimasklu	Klumaks	7494		9
11	poltos77	Klumaks	2		10
12	poltos77	Klumaks	36	Дай денег	11
13	poltos77	Klumaks	100000	Дай деняг	12
14	Klumaks	poltos77	3894	Дай деняг	13
15	Dimasklu	Klumaks	6899		14
16	Klumaks	Dimasklu	6867		15
17	Klumaks	Dimasklu	479449		16
18	Dimasklu	Klumaks	6896		17
19	Klumaks	Dimasklu	389594		18
20	Klumaks	whereisgregoor	999	Кек	19
21	Dimasklu	Klumaks	6893949		20
22	Dimasklu	Klumaks	399404		21
23	Klumaks	Dimasklu	384848		22
24	Dimasklu	Klumaks	476		23
25	Dimasklu	Klumaks	57		24
26	Klumaks	Dimasklu	8394	Скебоб	25
27	FinCrazy	Klumaks	150	За ресторан	26
28	FinCrazy	FinCrazy	150	За ресторан	27
29	FinCrazy	Klumaks	150	За ресторан	28
30	FinCrazy	Klumaks	150	За ресторан	29
31	vvvikos_babosss	Klumaks	50		30
32	vvvikos_babosss	Dimasklu	385992		31
33	whereisgregoor	vvvikos_babosss	50		32
34	Klumaks	whereisgregoor	3894		33
35	vvvikos_babosss	whereisgregoor	50		34
36	Klumaks	whereisgregoor	50	На печеньки	35
37	dmt_tulaev	Dimasklu	395		36
38	poltos77	Dimasklu	38		37
39	poltos77	Dimasklu	68		38
40	FinCrazy	Dimasklu	8494		39
41	whereisgregoor	poltos77	1000		40
42	vvvikos_babosss	whereisgregoor	1000	На подарок🎁	41
43	vvvikos_babosss	whereisgregoor	1000	На подарок🎁	42
44	vvvikos_babosss	whereisgregoor	1000	На подарок🎁	43
45	vvvikos_babosss	whereisgregoor	1000	На подарок🎁	44
46	vvvikos_babosss	whereisgregoor	1000	На подарок🎁	45
47	vvvikos_babosss	whereisgregoor	1000	На подарок🎁	46
48	FinCrazy	Klumaks, FinCrazy	5000		47
49	FinCrazy	Klumaks	699		48
50	Klumaks	FinCrazy	57		49
51	Klumaks	FinCrazy, Klumaks	58		50
52	FinCrazy	Klumaks	39		51
53	Klumaks	FinCrazy	100	ffff	52
54	Klumaks	FinCrazy	100	у	53
55	Dimasklu	Klumaks	3883		54
56	Klumaks	Dimasklu	3895		55
57	Dimasklu	Klumaks	739		56
58	Klumaks	Dimasklu	3883		57
59	Klumaks	FinCrazy	100		58
60	Dimasklu	Klumaks	474		59
61	Dimasklu	Klumaks	7384		60
\.


--
-- TOC entry 3336 (class 0 OID 16464)
-- Dependencies: 209
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id_user, chat_id, username, name, phone) FROM stdin;
6	508726885	dmt_tulaev	Дмитрий Тулаев	89221922266
9	1079520287	poltos77	Polya	89192161325
5	1068578892	FinCrazy	Никита Колесников	89246403228
8	7650815980	Dimasklu	Дима	89264140476
7	725856476	vvvikos_babosss	Викториее	89874158316
13	857497613	whereisgregoor	Гриша	89174951190
11	1189006256	Klumaks	- klumaks -	89266527052
\.


--
-- TOC entry 3349 (class 0 OID 0)
-- Dependencies: 210
-- Name: transfer_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.transfer_id_seq', 61, true);


--
-- TOC entry 3350 (class 0 OID 0)
-- Dependencies: 214
-- Name: users_id_user_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_user_seq', 24, true);


--
-- TOC entry 3195 (class 2606 OID 16493)
-- Name: date date_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.date
    ADD CONSTRAINT date_pkey PRIMARY KEY (id_date);


--
-- TOC entry 3193 (class 2606 OID 16491)
-- Name: transaction transaction_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transaction
    ADD CONSTRAINT transaction_pkey PRIMARY KEY (id_transaction);


--
-- TOC entry 3191 (class 2606 OID 16477)
-- Name: transfer transfer_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transfer
    ADD CONSTRAINT transfer_pkey PRIMARY KEY (id);


--
-- TOC entry 3187 (class 2606 OID 16506)
-- Name: users users_chat_id_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_chat_id_unique UNIQUE (chat_id);


--
-- TOC entry 3189 (class 2606 OID 16489)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id_user);


--
-- TOC entry 3196 (class 2606 OID 16520)
-- Name: transaction связь с пользователем 1; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transaction
    ADD CONSTRAINT "связь с пользователем 1" FOREIGN KEY (id_first_user) REFERENCES public.users(id_user);


--
-- TOC entry 3347 (class 0 OID 0)
-- Dependencies: 4
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO PUBLIC;


-- Completed on 2025-11-19 19:19:15

--
-- PostgreSQL database dump complete
--

