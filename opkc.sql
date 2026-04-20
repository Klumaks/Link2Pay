--
-- PostgreSQL database dump
--

-- Dumped from database version 14.17 (Ubuntu 14.17-0ubuntu0.22.04.1)
-- Dumped by pg_dump version 17.4

-- Started on 2025-11-19 18:38:25

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
-- TOC entry 210 (class 1259 OID 16400)
-- Name: account; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.account (
    id integer NOT NULL,
    phone_number character varying(11) NOT NULL,
    pam character varying NOT NULL,
    bank character varying,
    account character varying(20),
    CONSTRAINT account_account_check CHECK (((account)::text ~ '^[0-9]{20}$'::text)),
    CONSTRAINT account_phone_number_check CHECK (((phone_number)::text ~ '^8[0-9]{10}$'::text))
);


ALTER TABLE public.account OWNER TO postgres;

--
-- TOC entry 209 (class 1259 OID 16399)
-- Name: account_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.account_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.account_id_seq OWNER TO postgres;

--
-- TOC entry 3340 (class 0 OID 0)
-- Dependencies: 209
-- Name: account_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.account_id_seq OWNED BY public.account.id;


--
-- TOC entry 212 (class 1259 OID 16415)
-- Name: links; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.links (
    id integer NOT NULL,
    account_recipient character varying(20) NOT NULL,
    amount integer NOT NULL,
    bank_recipient character varying NOT NULL,
    pay_message character varying(140),
    additionally character varying,
    disposable boolean NOT NULL,
    status boolean DEFAULT false NOT NULL,
    CONSTRAINT links_account_recipient_check CHECK (((account_recipient)::text ~ '^[0-9]{20}$'::text))
);


ALTER TABLE public.links OWNER TO postgres;

--
-- TOC entry 211 (class 1259 OID 16414)
-- Name: links_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.links_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.links_id_seq OWNER TO postgres;

--
-- TOC entry 3341 (class 0 OID 0)
-- Dependencies: 211
-- Name: links_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.links_id_seq OWNED BY public.links.id;


--
-- TOC entry 3176 (class 2604 OID 16403)
-- Name: account id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.account ALTER COLUMN id SET DEFAULT nextval('public.account_id_seq'::regclass);


--
-- TOC entry 3177 (class 2604 OID 16418)
-- Name: links id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.links ALTER COLUMN id SET DEFAULT nextval('public.links_id_seq'::regclass);


--
-- TOC entry 3331 (class 0 OID 16400)
-- Dependencies: 210
-- Data for Name: account; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.account (id, phone_number, pam, bank, account) FROM stdin;
1	89246403228	Никита Сергеевич К.	Банк1	12345678901234567890
2	89234567890	Александр Петрович П.	Банк2	23456789012345678901
3	89345678901	Дмитрий Васильевич В.	Банк3	34567890123456789012
4	89456789012	Анна Игоревна И.	Банк4	45678901234567890123
5	89567890123	Елена Николаевна Н.	Банк5	56789012345678901234
6	89678901234	Сергей Дмитриевич Д.	Банк6	67890123456789012345
7	89789012345	Ольга Викторовна В.	Банк7	78901234567890123456
8	89890123456	Иван Алексеевич А.	Банк8	89012345678901234567
9	89901234567	Мария Сергеевна С.	Банк9	90123456789012345678
10	89012345678	Артем Олегович О.	Банк10	01234567890123456789
11	89111223344	Татьяна Владимировна В.	Банк1	11223344556677889900
12	89222334455	Павел Андреевич А.	Банк2	22334455667788990011
13	89333445566	Юлия Михайловна М.	Банк3	33445566778899001122
14	89444556677	Андрей Кириллович К.	Банк4	44556677889932456741
15	89113334455	Антон Викторович В.	Банк1	11133344455566677788
16	89224445566	Кристина Анатольевна А.	Банк2	22244455566677788899
17	89335556677	Глеб Борисович Б.	Банк3	33355566677788899900
18	89446667788	Диана Робертовна Р.	Банк4	44466677788899900011
19	89557778899	Тимур Феликсович Ф.	Банк5	55577788899900011122
20	89668889900	Яна Артуровна А.	Банк6	66688899900011122233
21	89779990011	Арсений Геннадьевич Г.	Банк7	77799900011122233344
22	89880001122	Вероника Вадимовна В.	Банк8	88800011122233344455
23	89991112233	Руслан Тимурович Т.	Банк9	99911122233344455566
24	89002223344	Арина Максимовна М.	Банк10	00022233344455566677
25	89114445566	Вадим Эдуардович Э.	\N	\N
26	89225556677	Эльвира Денисовна Д.	\N	\N
27	89336667788	Игорь Янович Я.	\N	\N
28	89447778899	Ульяна Леонидовна Л.	\N	\N
29	89558889900	Филипп Аркадьевич А.	\N	\N
30	89266527052	- klumaks -		85190693160242729370
31	89266537052	- klumaks -		41070635069908344218
32	89221922266	Дмитрий Тулаев		26300306030507094177
33	89874158316	Викториее		34380407050553111543
34	89264140476	Дима		15374312912810071077
35	89192161325	Polya		43196391399147695175
36	89174951190	Гриша		98302171382838909171
\.


--
-- TOC entry 3333 (class 0 OID 16415)
-- Dependencies: 212
-- Data for Name: links; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.links (id, account_recipient, amount, bank_recipient, pay_message, additionally, disposable, status) FROM stdin;
1	85190693160242729370	3	bank1	\N	HF39AG4T	t	f
2	85190693160242729370	57	bank1	\N	HF39AG4T	t	f
3	85190693160242729370	557	bank1	\N	HF39AG4T	t	f
5	85190693160242729370	567	bank1	\N	HF39AG4T	t	f
6	85190693160242729370	288338	bank1	\N	HF39AG4T	t	t
4	85190693160242729370	667	bank1	\N	HF39AG4T	t	t
7	12345678901234567890	100	bank1	\N	HF39AG4T	t	t
8	34380407050553111543	55	bank1	\N	HF39AG4T	t	t
9	15374312912810071077	7494	bank1	\N	HF39AG4T	t	t
11	43196391399147695175	36	bank1	Дай денег	HF39AG4T	t	f
10	43196391399147695175	2	bank1	\N	HF39AG4T	t	t
12	43196391399147695175	100000	bank1	Дай деняг	HF39AG4T	t	f
13	85190693160242729370	3894	bank1	Дай деняг	HF39AG4T	t	t
14	15374312912810071077	6899	bank1	\N	HF39AG4T	t	t
15	85190693160242729370	6867	bank1	\N	HF39AG4T	t	t
16	85190693160242729370	479449	bank1	\N	HF39AG4T	t	t
17	15374312912810071077	6896	bank1	\N	HF39AG4T	t	t
18	85190693160242729370	389594	bank1	\N	HF39AG4T	t	t
19	85190693160242729370	999	bank1	Кек	HF39AG4T	t	f
20	15374312912810071077	6893949	bank1	\N	HF39AG4T	t	t
21	15374312912810071077	399404	bank1	\N	HF39AG4T	t	t
23	15374312912810071077	476	bank1	\N	HF39AG4T	t	t
22	85190693160242729370	384848	bank1	\N	HF39AG4T	t	t
24	15374312912810071077	57	bank1	\N	HF39AG4T	t	f
25	85190693160242729370	8394	bank1	Скебоб	HF39AG4T	t	t
27	12345678901234567890	150	bank1	За ресторан	HF39AG4T	t	t
26	12345678901234567890	150	bank1	За ресторан	HF39AG4T	t	t
28	12345678901234567890	150	bank1	За ресторан	HF39AG4T	t	f
29	12345678901234567890	150	bank1	За ресторан	HF39AG4T	t	t
30	34380407050553111543	50	bank1	\N	HF39AG4T	t	t
31	34380407050553111543	385992	bank1	\N	HF39AG4T	t	f
32	98302171382838909171	50	bank1	\N	HF39AG4T	t	f
33	85190693160242729370	3894	bank1	\N	HF39AG4T	t	f
34	34380407050553111543	50	bank1	\N	HF39AG4T	t	t
35	85190693160242729370	50	bank1	На печеньки	HF39AG4T	t	f
36	26300306030507094177	395	bank1	\N	HF39AG4T	t	f
37	43196391399147695175	38	bank1	\N	HF39AG4T	t	f
38	43196391399147695175	68	bank1	\N	HF39AG4T	t	f
39	12345678901234567890	8494	bank1	\N	HF39AG4T	t	f
40	98302171382838909171	1000	bank1	\N	HF39AG4T	t	f
41	34380407050553111543	1000	bank1	На подарок🎁	HF39AG4T	t	t
42	34380407050553111543	1000	bank1	На подарок🎁	HF39AG4T	t	t
43	34380407050553111543	1000	bank1	На подарок🎁	HF39AG4T	t	t
44	34380407050553111543	1000	bank1	На подарок🎁	HF39AG4T	t	t
45	34380407050553111543	1000	bank1	На подарок🎁	HF39AG4T	t	t
46	34380407050553111543	1000	bank1	На подарок🎁	HF39AG4T	t	t
47	12345678901234567890	5000	bank1	\N	HF39AG4T	f	f
48	12345678901234567890	699	bank1	\N	HF39AG4T	t	f
49	85190693160242729370	57	bank1	\N	HF39AG4T	t	f
50	85190693160242729370	58	bank1	\N	HF39AG4T	f	f
51	12345678901234567890	39	bank1	\N	HF39AG4T	t	t
52	85190693160242729370	100	bank1	ffff	HF39AG4T	t	f
53	85190693160242729370	100	bank1	у	HF39AG4T	t	t
55	85190693160242729370	3895	bank1	\N	HF39AG4T	t	t
54	15374312912810071077	3883	bank1	\N	HF39AG4T	t	t
56	15374312912810071077	739	bank1	\N	HF39AG4T	t	f
57	85190693160242729370	3883	bank1	\N	HF39AG4T	t	f
58	85190693160242729370	100	bank1	\N	HF39AG4T	t	f
\.


--
-- TOC entry 3342 (class 0 OID 0)
-- Dependencies: 209
-- Name: account_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.account_id_seq', 36, true);


--
-- TOC entry 3343 (class 0 OID 0)
-- Dependencies: 211
-- Name: links_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.links_id_seq', 58, true);


--
-- TOC entry 3183 (class 2606 OID 16413)
-- Name: account account_account_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.account
    ADD CONSTRAINT account_account_key UNIQUE (account);


--
-- TOC entry 3185 (class 2606 OID 16411)
-- Name: account account_phone_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.account
    ADD CONSTRAINT account_phone_number_key UNIQUE (phone_number);


--
-- TOC entry 3187 (class 2606 OID 16409)
-- Name: account account_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.account
    ADD CONSTRAINT account_pkey PRIMARY KEY (id);


--
-- TOC entry 3189 (class 2606 OID 16424)
-- Name: links links_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.links
    ADD CONSTRAINT links_pkey PRIMARY KEY (id);


--
-- TOC entry 3190 (class 2606 OID 16425)
-- Name: links links_account_recipient_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.links
    ADD CONSTRAINT links_account_recipient_fkey FOREIGN KEY (account_recipient) REFERENCES public.account(account) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 3339 (class 0 OID 0)
-- Dependencies: 4
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO PUBLIC;


-- Completed on 2025-11-19 18:38:29

--
-- PostgreSQL database dump complete
--

