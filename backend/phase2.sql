--
-- PostgreSQL database dump
--

-- Dumped from database version 16.9 (Ubuntu 16.9-1.pgdg22.04+1)
-- Dumped by pg_dump version 16.9 (Ubuntu 16.9-1.pgdg22.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: django_admin_log; Type: TABLE DATA; Schema: public; Owner: postgres
--

SET SESSION AUTHORIZATION DEFAULT;

ALTER TABLE public.django_admin_log DISABLE TRIGGER ALL;



ALTER TABLE public.django_admin_log ENABLE TRIGGER ALL;

--
-- Data for Name: django_session; Type: TABLE DATA; Schema: public; Owner: postgres
--

ALTER TABLE public.django_session DISABLE TRIGGER ALL;

INSERT INTO public.django_session VALUES ('isg5zcfidqgjctv06zk8l6140ptimk9m', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1nd8oo:8mdSEGpsCinsr3UbNkRASuXpscPpHAs0nVB5zXHnsq0', '2022-04-23 10:59:50.462246+00');
INSERT INTO public.django_session VALUES ('4scsykgfml5vay98vucyav041e31esye', '.eJxVjEsOwjAMBe-SNYrc1HYoS_acIbKbhBZQIvWzQtydVuoCtjPz3tsEWZchrHOawhjNxZA5_TKV_pnKLuJDyr3avpZlGtXuiT3sbG81ptf1aP8OBpmHbd15AIIo2BGxOsfKGZk8nRMmRmoVW2hYAbR3G8-CnrOAy9wANNl8vqq3NnU:1nYRhN:O6LVwa4_lJ72k24V15VaOaOQcQsDD9_rF5UUGyUcAiY', '2022-04-10 12:08:45.311502+00');
INSERT INTO public.django_session VALUES ('ahmr8ez4ikyzfwixelog1li77r93vtuq', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1niFgO:ht5XT-bMLFukVBB3Dgn8vk0eZ6CDqX24iZ2mOi5n2AI', '2022-05-07 13:20:16.372607+00');
INSERT INTO public.django_session VALUES ('509zerqsj40rjtlvt5o3578ds1h3fiij', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1nnQ2g:PxNncLHAsu4Z-rfBrh4rXszNiwwIuQ7mckntdrfTMhQ', '2022-05-21 19:24:38.737794+00');
INSERT INTO public.django_session VALUES ('kzyg9vk16q1spgmkvy24nrwz0figlg8w', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1oHkrC:ouA64ZpsRbN3sPC1rewsTd6CS-O9pc4W_9eLsYLRO5Q', '2022-08-13 11:42:10.930747+00');
INSERT INTO public.django_session VALUES ('fm3ceghwtf87glu8tapaghsas4q2o8xl', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1oNrWI:a7AnozD1m-MatUaTKaZ2WR4-Ltp5X7J8stMPqFeEVdI', '2022-08-30 08:01:50.460292+00');
INSERT INTO public.django_session VALUES ('xiavoyc11cs9r9me0ochsrgepcf9sfgf', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1oUZlK:tyW0RjR-CfqglFjuQg-M-araEPgznqHocrV59F54Vp4', '2022-09-17 20:29:06.2508+00');
INSERT INTO public.django_session VALUES ('unyya9oq8aj7ohm7pd78yop5kxm1axct', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1ocjB5:FDVGNIKUKQLtzZqG4_a_SR5Zuau2U7yxWi8VGd7BM-A', '2022-10-10 08:09:23.365464+00');
INSERT INTO public.django_session VALUES ('kp9k0o897plgxk0ag61p2jtm7wibuna5', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1okpi1:RfFmd52KvTVseoeIoaVRGtrPg6J2X_3MyMqL2Fs6z0I', '2022-11-01 16:44:53.330063+00');
INSERT INTO public.django_session VALUES ('36ov2iqoaryanjypg8ouap1qdtv0qrio', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1os15b:tFsBE3kgd8WWjG2jAk4GQgO9reYzxYFyv3LPU2Q47l8', '2022-11-21 12:18:55.722286+00');
INSERT INTO public.django_session VALUES ('hkzia668zegerq1dzazrkvjjcj0hilgk', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1p27wg:fKjRKVUYSEoXhEgkY0hPg1in20YmMJiGfOmvhnL6gOk', '2022-12-19 09:39:30.369183+00');
INSERT INTO public.django_session VALUES ('q52ruzk0rti0e1bv138mladvxlo11yhu', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1p7P0p:TXQ5gOiMqRFI_2ol94E_BXhLwWLOYQ7uPlZee3A4sIo', '2023-01-02 22:53:35.343519+00');
INSERT INTO public.django_session VALUES ('0g8g7bi2tbn96lwimsqsevhqxro9mhfn', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1pDkmc:-NklzKgiqPfynjP6KLrDayZfpiNrERMWOEdTWObPYfk', '2023-01-20 11:21:10.181753+00');
INSERT INTO public.django_session VALUES ('qwb1588pl00s0ve1q7k0qorq08kwalbf', '.eJxVjDsOwyAQBe9CHSFAfFOmzxkQu4uDkwgkY1dW7h4suUjamXlvZzFta4lbz0uciV2ZZZdfBglfuR6Cnqk-GsdW12UGfiT8tJ3fG-X37Wz_DkrqZawnrU2WKqCHJBWQJVSASEYZmYW3wYpBHZpgUQqSFkjoyWen9WhcYJ8v8N030w:1pEwGH:wrFXXFPFiAYSAYegCPhYzpzEJG6T-yEaHnrXaoFFiF0', '2023-01-23 17:48:41.43541+00');
INSERT INTO public.django_session VALUES ('pwhy9zy28fprfoba10id8nrd40djbqle', '.eJxVjDsOwyAQBe9CHSFAfFOmzxkQu4uDkwgkY1dW7h4suUjamXlvZzFta4lbz0uciV2ZZZdfBglfuR6Cnqk-GsdW12UGfiT8tJ3fG-X37Wz_DkrqZawnrU2WKqCHJBWQJVSASEYZmYW3wYpBHZpgUQqSFkjoyWen9WhcYJ8v8N030w:1pPTkO:mppBeKH-9DUgibuKtNXeBwEMfj_eI7pc6zRk3fO5s9c', '2023-02-21 19:35:20.353896+00');
INSERT INTO public.django_session VALUES ('2asivfcmgpab0l66nq2hk40dcv8ql1if', '.eJxVjDsOwyAQBe9CHSFAfFOmzxkQu4uDkwgkY1dW7h4suUjamXlvZzFta4lbz0uciV2ZZZdfBglfuR6Cnqk-GsdW12UGfiT8tJ3fG-X37Wz_DkrqZawnrU2WKqCHJBWQJVSASEYZmYW3wYpBHZpgUQqSFkjoyWen9WhcYJ8v8N030w:1pW0qD:-82tzIVWLl6O6F3HEbEikbwt-lW_JpyzC2nIkbB82pM', '2023-03-11 20:08:21.866322+00');
INSERT INTO public.django_session VALUES ('bn6ub0ugqcez9rv1lcty9i39k4r21pn5', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1qFcYq:TcJXqB3wcsNBnlc5jTIz3KXNitmOHwzUiHT-T0unIro', '2023-07-15 15:30:56.691664+00');
INSERT INTO public.django_session VALUES ('5lbaxjkgcy2ua0s3f6rl4z5trv5iqiu7', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1qLUGl:5AJ3FiaETmmOGvV4lsT_C4a7onsJwKbmWe9xTYpvrLM', '2023-07-31 19:52:31.821433+00');
INSERT INTO public.django_session VALUES ('z500ydbhwwbjtmufz7rs7apvb4sabbpi', '.eJxVjDsOwyAQBe9CHSFAfFOmzxkQu4uDkwgkY1dW7h4suUjamXlvZzFta4lbz0uciV2ZZZdfBglfuR6Cnqk-GsdW12UGfiT8tJ3fG-X37Wz_DkrqZawnrU2WKqCHJBWQJVSASEYZmYW3wYpBHZpgUQqSFkjoyWen9WhcYJ8v8N030w:1qMCxk:S4IIpeShKF1JP3hANcjfQY_eprXMJ7xi8L0VzLDTFY8', '2023-08-02 19:35:52.206133+00');
INSERT INTO public.django_session VALUES ('4h4yko0dfxwbstdas542eqi6ailppubo', '.eJxVjDsOwyAQBe9CHSFAfFOmzxkQu4uDkwgkY1dW7h4suUjamXlvZzFta4lbz0uciV2ZZZdfBglfuR6Cnqk-GsdW12UGfiT8tJ3fG-X37Wz_DkrqZawnrU2WKqCHJBWQJVSASEYZmYW3wYpBHZpgUQqSFkjoyWen9WhcYJ8v8N030w:1qSdcf:Qx13XI6O17Bm9eNcPbJ9_vChRPOc3H4rzRh0ducFs9s', '2023-08-20 13:16:41.847055+00');
INSERT INTO public.django_session VALUES ('z5vm4vq7awv8a5ai93yuhvu1j5amvfvm', '.eJxVjDsOwyAQBe9CHSFAfFOmzxkQu4uDkwgkY1dW7h4suUjamXlvZzFta4lbz0uciV2ZZZdfBglfuR6Cnqk-GsdW12UGfiT8tJ3fG-X37Wz_DkrqZawnrU2WKqCHJBWQJVSASEYZmYW3wYpBHZpgUQqSFkjoyWen9WhcYJ8v8N030w:1qZz8g:3z0PHMZTL702uxo7tFD09GUTEq6JlwEfn9zlymG7yRo', '2023-09-09 19:40:06.335513+00');
INSERT INTO public.django_session VALUES ('rargmn2o5jeema5emy1w9ztprxt3fd3c', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1qcNAz:nCqwJym26lqW77mKWDyIcBMMEh1PRXqNQo6ounkD99k', '2023-09-16 09:44:21.118539+00');
INSERT INTO public.django_session VALUES ('rz2ibk41dy4hmzg2154au0y2bmqhi81o', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1qhbIQ:L6dVO_DcEAz5LtG01VeGviyeAncKNQeoUZnZJHyAClE', '2023-09-30 19:49:38.652219+00');
INSERT INTO public.django_session VALUES ('9erezmx2fzt5pjamqy2re42s2t36esgi', '.eJxVjDsOwyAQBe9CHSFAfFOmzxkQu4uDkwgkY1dW7h4suUjamXlvZzFta4lbz0uciV2ZZZdfBglfuR6Cnqk-GsdW12UGfiT8tJ3fG-X37Wz_DkrqZawnrU2WKqCHJBWQJVSASEYZmYW3wYpBHZpgUQqSFkjoyWen9WhcYJ8v8N030w:1qhubr:m0a7jPNPPGqhfF5Qy2WCR3Z-C12GQz65rGmsn29rqUw', '2023-10-01 16:26:59.979294+00');
INSERT INTO public.django_session VALUES ('ycuijkf7sftdv5jng9ubcyq8np51nac6', '.eJxVjDsOwyAQBe9CHSFAfFOmzxkQu4uDkwgkY1dW7h4suUjamXlvZzFta4lbz0uciV2ZZZdfBglfuR6Cnqk-GsdW12UGfiT8tJ3fG-X37Wz_DkrqZawnrU2WKqCHJBWQJVSASEYZmYW3wYpBHZpgUQqSFkjoyWen9WhcYJ8v8N030w:1qpSoU:3Ow9HAs8y7qAvBLN4jgeDN175luIbC4ac6yD1IRu8L0', '2023-10-22 12:23:14.431514+00');
INSERT INTO public.django_session VALUES ('2x1yql5ktd67yirjp30dwcwmse6ndvu4', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1qtpJZ:01ir2ckgVxXl13rHZYenhuo-AzI4htFCq2a_dDKYSKo', '2023-11-03 13:13:21.630298+00');
INSERT INTO public.django_session VALUES ('3empo80m3cc88ev76fsxtuz0xlvhnhlc', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1t2s7R:9B4g02BiEMhJFpQoUySCsnrxqP6dIPxYVDoAbqo0b9U', '2024-11-04 13:06:45.916778+00');
INSERT INTO public.django_session VALUES ('smuyvb3o8yvz26qgai4b9n27thopzs2m', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1r1X2T:6zqy79JsNVlKOLjFasXZxL7T2ZJSo7eKGeR1raH0wLI', '2023-11-24 19:19:33.726163+00');
INSERT INTO public.django_session VALUES ('fntx27l0tfhro3rhdj3awhpwldgmcw26', '.eJxVjDsOwyAQBe9CHSFAfFOmzxkQu4uDkwgkY1dW7h4suUjamXlvZzFta4lbz0uciV2ZZZdfBglfuR6Cnqk-GsdW12UGfiT8tJ3fG-X37Wz_DkrqZawnrU2WKqCHJBWQJVSASEYZmYW3wYpBHZpgUQqSFkjoyWen9WhcYJ8v8N030w:1t6ZIA:zVqHZxtdmeIfAr4speJaI8uMkxLgUPRhTPapZSnHsqA', '2024-11-14 17:49:06.312501+00');
INSERT INTO public.django_session VALUES ('eh01nfx9109ce9hqntgdv7fbtu48d54t', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1r7teQ:JTawYt-YTY5LdkDQos9DfEMXaMTVso8xExKPPt59xmk', '2023-12-12 08:41:02.980321+00');
INSERT INTO public.django_session VALUES ('8gqfkpd6v7a7lhsy9hs0uho2ztlf4pz2', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1rDV3n:eKLgkIPwk7Zrt0dvSKgqJeHa_M5dodCn9b5XGlZbewg', '2023-12-27 19:38:23.595452+00');
INSERT INTO public.django_session VALUES ('37z7qjp3807fece0obew6n8528wmxj56', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1rH9S1:iJIg2r1fXxedw6wh0LH9CYq_hof8RfMUO_d_M7jJwmg', '2024-01-06 21:22:29.658311+00');
INSERT INTO public.django_session VALUES ('ar9w0elyywk1fewzy0jln4exqugfa221', '.eJxVjDsOwyAQBe9CHSFAfFOmzxkQu4uDkwgkY1dW7h4suUjamXlvZzFta4lbz0uciV2ZZZdfBglfuR6Cnqk-GsdW12UGfiT8tJ3fG-X37Wz_DkrqZawnrU2WKqCHJBWQJVSASEYZmYW3wYpBHZpgUQqSFkjoyWen9WhcYJ8v8N030w:1rHTdO:aQ-wO1ToiGqanmOOAT9pftW94hZl6OC_03mo8MV8y10', '2024-01-07 18:55:34.591069+00');
INSERT INTO public.django_session VALUES ('p1i85q4fnus8dm72bhjee3qcapmxoc10', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1rTgdr:o0lg5qXTbhSn1Uz4uJCRTFkhc-eCYhzsKBBrMJhqEPw', '2024-02-10 11:14:31.154902+00');
INSERT INTO public.django_session VALUES ('3zmipr5ez2m3erhiwyopgrrxf40pprgr', '.eJxVjDsOwyAQBe9CHSFAfFOmzxkQu4uDkwgkY1dW7h4suUjamXlvZzFta4lbz0uciV2ZZZdfBglfuR6Cnqk-GsdW12UGfiT8tJ3fG-X37Wz_DkrqZawnrU2WKqCHJBWQJVSASEYZmYW3wYpBHZpgUQqSFkjoyWen9WhcYJ8v8N030w:1rTgif:Mhk9EU4DikPq9HCsSZgrkNELXX-wvG_Ev-UropduAig', '2024-02-10 11:19:29.57067+00');
INSERT INTO public.django_session VALUES ('9dqdrcpkeywdovov6wjrfkang99fk4af', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1rWKbJ:9wwAM5kL2lQiIb3rQSYLZaoaExLaXA9B4WUXXAU43Hc', '2024-02-17 18:18:49.607053+00');
INSERT INTO public.django_session VALUES ('8iw83m2fbb6hnp4jp6kh6nv54sr4k5gu', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1rZ3m9:14HQQ4EoNj3jrHpjf42IAvNghULlrQwb05MjwFqgHS4', '2024-02-25 06:57:17.730188+00');
INSERT INTO public.django_session VALUES ('g7efjb0r2fula1aem733bhwih2vsq88g', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1rbomZ:9LYYbUtk_syDk0YlY5d0RGudlx0rVTmGWAZd9wNMMwo', '2024-03-03 21:33:07.432814+00');
INSERT INTO public.django_session VALUES ('u4wi7ess0cataxtfvyyoa8pwvm4l20b4', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1rmHRD:NcUZJO3nSCACYj16pcwMDDX5yVmYFglN2foKHhB5lRs', '2024-04-01 18:10:19.417449+00');
INSERT INTO public.django_session VALUES ('h0kuv7afrwwra47mn2i1pc9dv8on1ip6', '.eJxVjDsOwyAQBe9CHSFAfFOmzxkQu4uDkwgkY1dW7h4suUjamXlvZzFta4lbz0uciV2ZZZdfBglfuR6Cnqk-GsdW12UGfiT8tJ3fG-X37Wz_DkrqZawnrU2WKqCHJBWQJVSASEYZmYW3wYpBHZpgUQqSFkjoyWen9WhcYJ8v8N030w:1rtn9n:XGgzSASrfz4rmuOvzAauOm5kqvZczqu0Q2XRGaeFmiw', '2024-04-22 11:27:23.891217+00');
INSERT INTO public.django_session VALUES ('c38cyixm04bfurtdez09v55qp88o5mxf', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1rxt3T:JUfO1fnVwuC7GjS5rpOlcCoaXS3g8-mBVJCnrXbfpls', '2024-05-03 18:33:47.554837+00');
INSERT INTO public.django_session VALUES ('30bivvj6yoc3rt9hr7j9lnksmj8aaz45', '.eJxVjDsOwyAQBe9CHSFAfFOmzxkQu4uDkwgkY1dW7h4suUjamXlvZzFta4lbz0uciV2ZZZdfBglfuR6Cnqk-GsdW12UGfiT8tJ3fG-X37Wz_DkrqZawnrU2WKqCHJBWQJVSASEYZmYW3wYpBHZpgUQqSFkjoyWen9WhcYJ8v8N030w:1s0wIu:VpK10er5yk3SEsRD6fkgDavO3TlWmqIMbODPs6QS5Kw', '2024-05-12 04:38:20.717996+00');
INSERT INTO public.django_session VALUES ('65irnmggjdh707sgld7nkjfqclovll55', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1s4HX1:ZUj8iU47o0AitoAP2ygt38Pve7cMqfrH0J0ImyoOmXE', '2024-05-21 09:54:43.079734+00');
INSERT INTO public.django_session VALUES ('2bale9yw2ljm6fgy3ocdfw5sc1o3h38b', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1sDJMi:Ruttdvia7O423YOYPXdvE8piRe7Fkb2DxsPEG-3HzJs', '2024-06-15 07:41:24.943344+00');
INSERT INTO public.django_session VALUES ('obsxbww71ocoml0abbljhhzglfonbrbe', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1sRo3K:E-5ktaNFYR3yzrVCcxBQ4h2lBMKEFVLwUTxet7hg4kw', '2024-07-25 07:17:18.928836+00');
INSERT INTO public.django_session VALUES ('f8l1xfzmoinhwvit3pgx18ft4614l1d2', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1sRo3L:swwtkJXgXs_Cr5DtO6C2RN7WFPTIjSUa81UsIufopow', '2024-07-25 07:17:19.167894+00');
INSERT INTO public.django_session VALUES ('6rlxgg3jqy0v72dh7uer8i1a5onr5chy', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1sZTqH:H5axoucQc4QoigUyUGEQPATYQzAHrnopXCOrY1zqE7M', '2024-08-15 11:19:33.355011+00');
INSERT INTO public.django_session VALUES ('ghjryw22cwyyhpqyw3umdc7qelu9ehc4', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1sgz05:7MyK_SDQ3oA0iya4TICIhA6T-EMopO79Lll3AM9c8xg', '2024-09-05 04:00:41.649704+00');
INSERT INTO public.django_session VALUES ('e6c8szzui7tm5phzi1ayvbf6xm7hb242', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1st0le:PDikb4ulmeLhqrfTB1O5UrKQzmPy2ljeJF2gnBZEapQ', '2024-10-08 08:19:30.083293+00');
INSERT INTO public.django_session VALUES ('pwzqpkx5dpv80qjxd9rlss3088uotehq', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1st0le:PDikb4ulmeLhqrfTB1O5UrKQzmPy2ljeJF2gnBZEapQ', '2024-10-08 08:19:30.327863+00');
INSERT INTO public.django_session VALUES ('giijcktofpafeiplt6hfnyp2tq4yex9z', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1stLSP:k1vmBMwbtJI-K1AmWJG9YD0GC6i-QL6yriNJNiBN5c0', '2024-10-09 06:25:01.15762+00');
INSERT INTO public.django_session VALUES ('iayqk7idn1kmk7psilrj0xpykym0e7pe', '.eJxVjDsOwyAQBe9CHSFAfFOmzxkQu4uDkwgkY1dW7h4suUjamXlvZzFta4lbz0uciV2ZZZdfBglfuR6Cnqk-GsdW12UGfiT8tJ3fG-X37Wz_DkrqZawnrU2WKqCHJBWQJVSASEYZmYW3wYpBHZpgUQqSFkjoyWen9WhcYJ8v8N030w:1t6ZIX:smW7DK1S7UG0b0a7ZnIxBz92HckQWNfFAScGRbkKl0E', '2024-11-14 17:49:29.084966+00');
INSERT INTO public.django_session VALUES ('yz394uh2aaejbsyve0gzawsmrmu4e6hx', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1tAboV:BZ4fipDNDltE6PH2SrgiiVo8FOa068ShVacM0UNLvlk', '2024-11-25 21:19:11.821608+00');
INSERT INTO public.django_session VALUES ('qzzx9yu960ebz60uftwyfy8ekmnzv0uf', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1tKj59:q9Fj9_4Xr1SEmJv3TCEpDvnOqZBWs5yoxej-YjPmN4I', '2024-12-23 19:06:11.165923+00');
INSERT INTO public.django_session VALUES ('fazam66yo7gicxsol6x45sco98jwx52l', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1tSC67:wbSziqpOAH55F8eZTsrqdOiWwV9vPqHbyzaWUubafTI', '2025-01-13 09:30:03.183539+00');
INSERT INTO public.django_session VALUES ('b4nkfofjg03f8j932ywxgweg18e56yvx', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1tepzt:OQpGVKGh5AAZ5i9ZZg_Q2MtU01VWe0WeDRXKYTkC-Pw', '2025-02-17 06:31:53.539958+00');
INSERT INTO public.django_session VALUES ('khbslcru2ah9z5twne82prae9qjsr3g9', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1tzu0x:H-_FmTFIyqE9ZaTKkGvRXQKxR0hm4_mqo-NHzGG3pbM', '2025-04-16 09:04:03.129902+00');
INSERT INTO public.django_session VALUES ('4gkv8yg4ft6tdy66q8i4e8chsn60oao2', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1tzu0x:H-_FmTFIyqE9ZaTKkGvRXQKxR0hm4_mqo-NHzGG3pbM', '2025-04-16 09:04:03.135141+00');
INSERT INTO public.django_session VALUES ('s891jkigwupaw5pvlepypemspgzo9mw3', '.eJxVjDsOwyAQBe9CHSFAfFOmzxkQu4uDkwgkY1dW7h4suUjamXlvZzFta4lbz0uciV2ZZZdfBglfuR6Cnqk-GsdW12UGfiT8tJ3fG-X37Wz_DkrqZawnrU2WKqCHJBWQJVSASEYZmYW3wYpBHZpgUQqSFkjoyWen9WhcYJ8v8N030w:1u96iD:xWSq4RFQWWvQpeMO7I8hSYwHchWYfKtg4vJq7M-LgiI', '2025-05-11 18:26:45.721313+00');
INSERT INTO public.django_session VALUES ('5rqm42ooddrrom0uy068kumguthu2cik', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1u9hkG:sjtkmFokyBM8fFGeFK_vo2gIG3QNAIKMTc8lZxvLh-0', '2025-05-13 09:59:20.819715+00');
INSERT INTO public.django_session VALUES ('ldtkjory25cu331x9e70u9zu9wddi1ej', '.eJxVjEEOwiAQRe_C2hAGOlBcuvcMZIBBqoYmpV0Z765NutDtf-_9lwi0rTVsnZcwZXEWIE6_W6T04LaDfKd2m2Wa27pMUe6KPGiX1znz83K4fweVev3WI0AZC8fiU_TsOEY0KisCRu8H8hlNBl0sQjGkrcZBGeuQmYldASveH_3VODw:1udYSd:xdEStDFoVW5cdcLIfLDFGg9BgZ5OOeCIRer7oCnE47M', '2025-08-03 18:08:31.301397+00');


ALTER TABLE public.django_session ENABLE TRIGGER ALL;

--
-- Data for Name: stations; Type: TABLE DATA; Schema: public; Owner: postgres
--

ALTER TABLE public.stations DISABLE TRIGGER ALL;



ALTER TABLE public.stations ENABLE TRIGGER ALL;

--
-- Data for Name: posts; Type: TABLE DATA; Schema: public; Owner: postgres
--

ALTER TABLE public.posts DISABLE TRIGGER ALL;



ALTER TABLE public.posts ENABLE TRIGGER ALL;

--
-- Data for Name: reviews; Type: TABLE DATA; Schema: public; Owner: postgres
--

ALTER TABLE public.reviews DISABLE TRIGGER ALL;

INSERT INTO public.reviews VALUES (217, '2025-06-18 16:17:26.498822+00', '2025-06-18 16:17:26.498822+00', 19, 5, 'super Radio muzica 24 din 24', false, 99148298);
INSERT INTO public.reviews VALUES (106, '2023-10-09 18:08:29.004995+00', '2023-10-09 18:08:29.004995+00', 7, 5, 'Laudat sa fie Domnul !🙏🏻', false, 4063886);
INSERT INTO public.reviews VALUES (107, '2023-10-11 06:01:03.169852+00', '2023-10-11 06:01:03.169852+00', 23, 5, '', false, 4123874);
INSERT INTO public.reviews VALUES (108, '2023-10-12 05:06:17.822139+00', '2023-10-12 05:06:17.822139+00', 18, 5, '', false, 4192056);
INSERT INTO public.reviews VALUES (109, '2023-10-12 19:40:10.650496+00', '2023-10-12 19:40:10.650496+00', 18, 5, '', false, 4248511);
INSERT INTO public.reviews VALUES (110, '2023-10-12 19:40:18.07134+00', '2023-10-12 19:40:18.07134+00', 18, 5, '', false, 4248517);
INSERT INTO public.reviews VALUES (111, '2023-10-12 20:34:59.459559+00', '2023-10-12 20:34:59.459559+00', 18, 5, '', false, 4250341);
INSERT INTO public.reviews VALUES (112, '2023-10-12 20:35:18.113015+00', '2023-10-12 20:35:18.113015+00', 18, 5, '', false, 4250350);
INSERT INTO public.reviews VALUES (113, '2023-10-12 20:35:24.497593+00', '2023-10-12 20:35:24.497593+00', 18, 5, '', false, 4250353);
INSERT INTO public.reviews VALUES (114, '2023-10-12 20:35:39.82923+00', '2023-10-12 20:35:39.82923+00', 18, 5, '', false, 4250360);
INSERT INTO public.reviews VALUES (115, '2023-10-13 20:17:03.169266+00', '2023-10-13 20:17:03.169266+00', 25, 5, '✌🏻', false, 4329257);
INSERT INTO public.reviews VALUES (116, '2023-10-16 18:54:52.488783+00', '2023-10-16 18:54:52.488783+00', 18, 5, '', false, 4578657);
INSERT INTO public.reviews VALUES (117, '2023-10-16 18:58:00.297254+00', '2023-10-16 18:58:00.297254+00', 18, 5, '', false, 4578794);
INSERT INTO public.reviews VALUES (118, '2023-10-17 19:33:12.136148+00', '2023-10-17 19:33:12.136148+00', 18, 5, '', false, 4697125);
INSERT INTO public.reviews VALUES (119, '2023-10-17 20:19:28.324986+00', '2023-10-17 20:19:28.324986+00', 18, 5, '', false, 4699214);
INSERT INTO public.reviews VALUES (120, '2023-10-21 05:38:13.886881+00', '2023-10-21 05:38:13.886881+00', 18, 5, '', false, 5108839);
INSERT INTO public.reviews VALUES (121, '2023-10-31 21:58:55.952313+00', '2023-10-31 21:58:55.952313+00', 18, 5, 'getrt', false, 6555232);
INSERT INTO public.reviews VALUES (122, '2023-11-01 12:38:32.250596+00', '2023-11-01 12:38:32.250596+00', 12, 5, 'Mereu aproape', false, 6669486);
INSERT INTO public.reviews VALUES (123, '2023-11-03 22:33:41.477358+00', '2023-11-03 22:33:41.477358+00', 18, 5, '', false, 7074621);
INSERT INTO public.reviews VALUES (124, '2023-11-06 19:31:22.826163+00', '2023-11-06 19:31:22.826163+00', 2, 5, '', false, 7534909);
INSERT INTO public.reviews VALUES (125, '2023-11-07 07:32:52.997662+00', '2023-11-07 07:32:52.997662+00', 40, 5, '', false, 7613867);
INSERT INTO public.reviews VALUES (126, '2023-11-15 18:38:59.819485+00', '2023-11-15 18:38:59.819485+00', 18, 5, '', false, 9252393);
INSERT INTO public.reviews VALUES (127, '2023-11-17 21:34:13.963453+00', '2023-11-17 21:34:13.963453+00', 18, 5, '', false, 9706988);
INSERT INTO public.reviews VALUES (128, '2023-11-20 19:51:59.143901+00', '2023-11-20 19:51:59.143901+00', 12, 5, '', false, 10276088);
INSERT INTO public.reviews VALUES (129, '2023-11-21 15:44:09.177067+00', '2023-11-21 15:44:09.177067+00', 39, 5, 'Îmi place acest Radio 
', false, 10490624);
INSERT INTO public.reviews VALUES (130, '2023-11-22 16:28:57.652115+00', '2023-11-22 16:28:57.652115+00', 12, 5, '', false, 10751929);
INSERT INTO public.reviews VALUES (131, '2023-11-22 21:52:10.714045+00', '2023-11-22 21:52:10.714045+00', 18, 5, '', false, 10790105);
INSERT INTO public.reviews VALUES (132, '2023-11-26 12:18:48.941511+00', '2023-11-26 12:18:48.941511+00', 2, 5, '', false, 11651398);
INSERT INTO public.reviews VALUES (133, '2023-11-29 20:17:22.572019+00', '2023-11-29 20:17:22.572019+00', 2, 5, '', false, 12606573);
INSERT INTO public.reviews VALUES (134, '2023-12-01 18:03:47.833655+00', '2023-12-01 18:03:47.833655+00', 18, 5, '', false, 13178962);
INSERT INTO public.reviews VALUES (135, '2023-12-09 15:51:55.048421+00', '2023-12-09 15:51:55.048421+00', 0, 5, '', false, 15665209);
INSERT INTO public.reviews VALUES (136, '2023-12-09 15:52:13.475769+00', '2023-12-09 15:52:13.475769+00', 2, 5, '', false, 15665297);
INSERT INTO public.reviews VALUES (137, '2023-12-13 11:18:04.021593+00', '2023-12-13 11:18:04.021593+00', 2, 5, '', false, 16928337);
INSERT INTO public.reviews VALUES (138, '2023-12-13 11:24:47.974912+00', '2023-12-13 11:24:47.974912+00', 2, 5, '', false, 16930308);
INSERT INTO public.reviews VALUES (139, '2023-12-13 11:25:26.916754+00', '2023-12-13 11:25:26.916754+00', 2, 5, '', false, 16930507);
INSERT INTO public.reviews VALUES (140, '2023-12-13 11:25:32.042877+00', '2023-12-13 11:25:32.042877+00', 2, 5, '', false, 16930533);
INSERT INTO public.reviews VALUES (141, '2023-12-13 11:25:38.005068+00', '2023-12-13 11:25:38.005068+00', 2, 5, '', false, 16930560);
INSERT INTO public.reviews VALUES (142, '2023-12-13 11:25:44.171327+00', '2023-12-13 11:25:44.171327+00', 2, 5, '', false, 16930589);
INSERT INTO public.reviews VALUES (143, '2023-12-13 11:25:50.046505+00', '2023-12-13 11:25:50.046505+00', 2, 5, '', false, 16930618);
INSERT INTO public.reviews VALUES (144, '2023-12-13 11:26:10.757368+00', '2023-12-13 11:26:10.757368+00', 2, 5, '', false, 16930723);
INSERT INTO public.reviews VALUES (145, '2023-12-13 11:26:17.372845+00', '2023-12-13 11:26:17.372845+00', 2, 5, '', false, 16930757);
INSERT INTO public.reviews VALUES (146, '2023-12-13 11:26:23.139309+00', '2023-12-13 11:26:23.139309+00', 2, 5, '', false, 16930789);
INSERT INTO public.reviews VALUES (147, '2023-12-13 11:26:27.353967+00', '2023-12-13 11:26:27.353967+00', 2, 5, '', false, 16930812);
INSERT INTO public.reviews VALUES (148, '2023-12-13 11:26:32.708719+00', '2023-12-13 11:26:32.708719+00', 2, 5, '', false, 16930840);
INSERT INTO public.reviews VALUES (149, '2023-12-13 11:26:44.667973+00', '2023-12-13 11:26:44.667973+00', 0, 5, '', false, 16930896);
INSERT INTO public.reviews VALUES (150, '2023-12-13 11:26:47.837378+00', '2023-12-13 11:26:47.837378+00', 0, 5, '', false, 16930912);
INSERT INTO public.reviews VALUES (151, '2023-12-13 11:26:50.85019+00', '2023-12-13 11:26:50.85019+00', 0, 5, '', false, 16930935);
INSERT INTO public.reviews VALUES (152, '2023-12-13 11:26:53.401974+00', '2023-12-13 11:26:53.401974+00', 0, 5, '', false, 16930945);
INSERT INTO public.reviews VALUES (153, '2023-12-13 11:26:55.876363+00', '2023-12-13 11:26:55.876363+00', 0, 5, '', false, 16930960);
INSERT INTO public.reviews VALUES (154, '2023-12-13 11:27:00.395139+00', '2023-12-13 11:27:00.395139+00', 0, 5, '', false, 16930985);
INSERT INTO public.reviews VALUES (155, '2023-12-13 11:27:03.223098+00', '2023-12-13 11:27:03.223098+00', 0, 5, '', false, 16930999);
INSERT INTO public.reviews VALUES (156, '2023-12-13 11:27:05.555146+00', '2023-12-13 11:27:05.555146+00', 0, 5, '', false, 16931011);
INSERT INTO public.reviews VALUES (157, '2023-12-13 11:27:07.840351+00', '2023-12-13 11:27:07.840351+00', 0, 5, '', false, 16931021);
INSERT INTO public.reviews VALUES (158, '2023-12-13 11:27:10.032507+00', '2023-12-13 11:27:10.032507+00', 0, 5, '', false, 16931029);
INSERT INTO public.reviews VALUES (159, '2023-12-13 11:27:12.260564+00', '2023-12-13 11:27:12.260564+00', 0, 5, '', false, 16931046);
INSERT INTO public.reviews VALUES (160, '2023-12-13 11:27:14.427824+00', '2023-12-13 11:27:14.427824+00', 0, 5, '', false, 16931053);
INSERT INTO public.reviews VALUES (161, '2023-12-13 11:27:18.188446+00', '2023-12-13 11:27:18.188446+00', 0, 5, '', false, 16931073);
INSERT INTO public.reviews VALUES (162, '2023-12-13 11:27:31.218575+00', '2023-12-13 11:27:31.218575+00', 0, 5, '', false, 16931145);
INSERT INTO public.reviews VALUES (163, '2023-12-13 11:27:34.038902+00', '2023-12-13 11:27:34.038902+00', 0, 5, '', false, 16931155);
INSERT INTO public.reviews VALUES (164, '2023-12-13 11:27:36.350407+00', '2023-12-13 11:27:36.350407+00', 0, 5, '', false, 16931169);
INSERT INTO public.reviews VALUES (165, '2023-12-13 11:27:38.527712+00', '2023-12-13 11:27:38.527712+00', 0, 5, '', false, 16931177);
INSERT INTO public.reviews VALUES (166, '2023-12-13 11:27:41.008727+00', '2023-12-13 11:27:41.008727+00', 0, 5, '', false, 16931191);
INSERT INTO public.reviews VALUES (167, '2023-12-13 11:27:43.86142+00', '2023-12-13 11:27:43.86142+00', 0, 5, '', false, 16931204);
INSERT INTO public.reviews VALUES (168, '2023-12-13 11:27:57.822667+00', '2023-12-13 11:27:57.822667+00', 1, 5, '', false, 16931273);
INSERT INTO public.reviews VALUES (169, '2023-12-13 11:28:00.080393+00', '2023-12-13 11:28:00.080393+00', 1, 5, '', false, 16931285);
INSERT INTO public.reviews VALUES (170, '2023-12-13 11:28:02.353328+00', '2023-12-13 11:28:02.353328+00', 1, 5, '', false, 16931298);
INSERT INTO public.reviews VALUES (171, '2023-12-13 11:28:04.862698+00', '2023-12-13 11:28:04.862698+00', 1, 5, '', false, 16931309);
INSERT INTO public.reviews VALUES (172, '2023-12-13 11:28:07.472755+00', '2023-12-13 11:28:07.472755+00', 1, 5, '', false, 16931322);
INSERT INTO public.reviews VALUES (173, '2023-12-13 11:28:09.819672+00', '2023-12-13 11:28:09.819672+00', 1, 5, '', false, 16931332);
INSERT INTO public.reviews VALUES (174, '2023-12-13 11:28:12.020897+00', '2023-12-13 11:28:12.020897+00', 1, 5, '', false, 16931348);
INSERT INTO public.reviews VALUES (175, '2023-12-13 11:28:15.432241+00', '2023-12-13 11:28:15.432241+00', 1, 5, '', false, 16931363);
INSERT INTO public.reviews VALUES (176, '2023-12-13 11:28:17.616324+00', '2023-12-13 11:28:17.616324+00', 1, 5, '', false, 16931373);
INSERT INTO public.reviews VALUES (177, '2023-12-13 11:28:19.886115+00', '2023-12-13 11:28:19.886115+00', 1, 5, '', false, 16931386);
INSERT INTO public.reviews VALUES (178, '2023-12-13 11:28:21.865182+00', '2023-12-13 11:28:21.865182+00', 1, 5, '', false, 16931401);
INSERT INTO public.reviews VALUES (179, '2023-12-13 11:28:24.070383+00', '2023-12-13 11:28:24.070383+00', 1, 5, '', false, 16931409);
INSERT INTO public.reviews VALUES (180, '2023-12-13 11:28:26.410452+00', '2023-12-13 11:28:26.410452+00', 1, 5, '', false, 16931424);
INSERT INTO public.reviews VALUES (181, '2023-12-13 11:28:28.847941+00', '2023-12-13 11:28:28.847941+00', 1, 5, '', false, 16931435);
INSERT INTO public.reviews VALUES (182, '2023-12-13 11:28:31.234664+00', '2023-12-13 11:28:31.234664+00', 1, 5, '', false, 16931451);
INSERT INTO public.reviews VALUES (183, '2023-12-13 11:28:33.508455+00', '2023-12-13 11:28:33.508455+00', 1, 5, '', false, 16931460);
INSERT INTO public.reviews VALUES (184, '2023-12-13 11:28:35.942574+00', '2023-12-13 11:28:35.942574+00', 1, 5, '', false, 16931473);
INSERT INTO public.reviews VALUES (185, '2023-12-13 11:28:38.313589+00', '2023-12-13 11:28:38.313589+00', 1, 5, '', false, 16931483);
INSERT INTO public.reviews VALUES (186, '2023-12-13 11:28:40.840648+00', '2023-12-13 11:28:40.840648+00', 1, 5, '', false, 16931496);
INSERT INTO public.reviews VALUES (187, '2023-12-13 20:01:41.151466+00', '2023-12-13 20:01:41.151466+00', 0, 5, '', false, 17082545);
INSERT INTO public.reviews VALUES (188, '2023-12-13 20:02:14.016389+00', '2023-12-13 20:02:14.016389+00', 0, 5, '', false, 17082690);
INSERT INTO public.reviews VALUES (189, '2023-12-13 20:02:18.556867+00', '2023-12-13 20:02:18.556867+00', 0, 5, '', false, 17082709);
INSERT INTO public.reviews VALUES (190, '2023-12-13 20:02:20.707951+00', '2023-12-13 20:02:20.707951+00', 0, 5, '', false, 17082719);
INSERT INTO public.reviews VALUES (191, '2023-12-13 20:02:24.956468+00', '2023-12-13 20:02:24.956468+00', 0, 5, '', false, 17082741);
INSERT INTO public.reviews VALUES (192, '2023-12-13 20:53:21.231739+00', '2023-12-13 20:53:21.231739+00', 0, 5, '', false, 17094039);
INSERT INTO public.reviews VALUES (193, '2023-12-13 22:33:49.07168+00', '2023-12-13 22:33:49.07168+00', 39, 4, '', false, 17109881);
INSERT INTO public.reviews VALUES (194, '2023-12-14 12:27:57.534424+00', '2023-12-14 12:27:57.534424+00', 0, 5, '', false, 17309771);
INSERT INTO public.reviews VALUES (195, '2023-12-14 12:28:19.994891+00', '2023-12-14 12:28:19.994891+00', 5, 5, '', false, 17309907);
INSERT INTO public.reviews VALUES (196, '2023-12-14 12:28:29.635018+00', '2023-12-14 12:28:29.635018+00', 2, 5, '', false, 17309963);
INSERT INTO public.reviews VALUES (197, '2023-12-14 12:28:34.883434+00', '2023-12-14 12:28:34.883434+00', 1, 5, '', false, 17309997);
INSERT INTO public.reviews VALUES (198, '2023-12-14 12:28:44.903945+00', '2023-12-14 12:28:44.903945+00', 46, 5, '', false, 17310058);
INSERT INTO public.reviews VALUES (199, '2023-12-15 06:50:41.005849+00', '2023-12-15 06:50:41.005849+00', 18, 5, '', false, 17533978);
INSERT INTO public.reviews VALUES (200, '2023-12-17 23:42:23.464192+00', '2023-12-17 23:42:23.464192+00', 75, 5, '', false, 18412390);
INSERT INTO public.reviews VALUES (201, '2023-12-21 12:32:47.541749+00', '2023-12-21 12:32:47.541749+00', 46, 5, 'felicitari , cat mai multe colinde roamnesti ( chiar si din cele mai vechi ) ', false, 19724606);
INSERT INTO public.reviews VALUES (202, '2024-01-01 19:49:24.880155+00', '2024-01-01 19:49:24.880155+00', 76, 5, 'Muzica super buna :)!', false, 22962373);
INSERT INTO public.reviews VALUES (203, '2024-02-05 19:17:36.259484+00', '2024-02-05 19:17:36.259484+00', 6, 5, 'Vă salut dragii mei!
Dumnezei cu noi.', false, 37647761);
INSERT INTO public.reviews VALUES (204, '2024-02-11 21:44:23.310737+00', '2024-02-11 21:44:23.310737+00', 18, 5, 'Domnul să vă binecuvânteze Muzica e foarte frumoasă și o muzică care se poate asculta cu placere...muzica care este în ziua de azi  la alte radiouriii asa zisa lauda si incinare e katastrofală vine din adincuriiii......', false, 40791766);
INSERT INTO public.reviews VALUES (205, '2024-03-07 09:23:53.994188+00', '2024-03-07 09:23:53.994188+00', 0, 5, 'FM NR ?', false, 48344560);
INSERT INTO public.reviews VALUES (206, '2024-03-27 18:54:33.938672+00', '2024-03-27 18:54:33.938672+00', 0, 5, 'Buna ziua ,imi place postul vostru de Radio .
Postati muzica crestina? As dori sa stiu daca va pot trimite niste cantari?
Multumesc Domnul sa va Binecuvinteze.', false, 50542116);
INSERT INTO public.reviews VALUES (207, '2024-04-13 20:50:13.09442+00', '2024-04-13 20:50:13.09442+00', 1, 5, 'Super', false, 52299977);
INSERT INTO public.reviews VALUES (208, '2024-09-18 00:38:33.654131+00', '2024-09-18 00:38:33.654131+00', 75, 5, 'Sunteti cei mai admirati si sunt fan de acest canal', false, 66663821);
INSERT INTO public.reviews VALUES (209, '2024-12-16 23:33:03.241799+00', '2024-12-16 23:33:03.241799+00', 62, 5, 'Minunat ', false, 76389237);
INSERT INTO public.reviews VALUES (210, '2024-12-27 05:20:19.010265+00', '2024-12-27 05:20:19.010265+00', 18, 5, 'Multa Pace, Domnul sa va binecuvinteze ', false, 77522709);
INSERT INTO public.reviews VALUES (211, '2024-12-27 13:55:44.350843+00', '2024-12-27 13:55:44.350843+00', 1, 5, 'Dunmnezeu sa va binecuvaneze pt mesajul Evangheliei Amin', false, 77568632);
INSERT INTO public.reviews VALUES (212, '2025-01-07 06:51:08.939421+00', '2025-01-07 06:51:08.939421+00', 18, 5, 'Un Radio Gosen este cel mai bun ce găsești alinarea sufletului și transmite mesajul său dat prin cântări și cuvântul Domnului.', false, 78558269);
INSERT INTO public.reviews VALUES (213, '2025-01-13 12:38:25.098932+00', '2025-01-13 12:38:25.098932+00', 21, 5, 'Un post de radio pentru suflet si toate vârstele.Dumnezeu sa va binecuvinteze în tot ce faceți. ', false, 79283348);
INSERT INTO public.reviews VALUES (214, '2025-02-28 05:42:15.603425+00', '2025-02-28 05:42:15.603425+00', 41, 5, 'MULTA BINECUVANTARE SA AVETI DIN PARTEA DOMNULUI ISUS', false, 84933592);
INSERT INTO public.reviews VALUES (215, '2025-04-04 07:18:29.433651+00', '2025-04-04 07:18:29.433651+00', 2, 5, 'Minunat program,fie Domnul lăudat!', false, 89962812);
INSERT INTO public.reviews VALUES (216, '2025-05-04 14:41:09.5735+00', '2025-05-04 14:41:09.5735+00', 18, 5, 'Domnul sa va binecuvinteze . foarte interesant.', false, 94030764);
INSERT INTO public.reviews VALUES (218, '2025-06-26 05:55:47.59748+00', '2025-06-26 05:55:47.59748+00', 40, 3, 'Pe FM se receptioneaza slab nici pe la marginea Zalaului(dincolo de gara)nu mai se rec.,am crezut ca schimbarea aduce si extensie,dar eu mai sper:fratele.Iuliu', false, 99910857);
INSERT INTO public.reviews VALUES (219, '2025-07-03 15:01:42.219105+00', '2025-07-03 15:01:42.219105+00', 0, 5, 'th', false, 100675233);
INSERT INTO public.reviews VALUES (220, '2025-07-18 15:34:01.395168+00', '2025-07-18 15:34:01.395168+00', 12, 5, 'Un radio foarte frumos !', false, 102287764);


ALTER TABLE public.reviews ENABLE TRIGGER ALL;

--
-- Data for Name: station_streams; Type: TABLE DATA; Schema: public; Owner: postgres
--

ALTER TABLE public.station_streams DISABLE TRIGGER ALL;



ALTER TABLE public.station_streams ENABLE TRIGGER ALL;

--
-- Data for Name: station_to_station_group; Type: TABLE DATA; Schema: public; Owner: postgres
--

ALTER TABLE public.station_to_station_group DISABLE TRIGGER ALL;



ALTER TABLE public.station_to_station_group ENABLE TRIGGER ALL;

--
-- Data for Name: stations_metadata_fetch; Type: TABLE DATA; Schema: public; Owner: postgres
--

ALTER TABLE public.stations_metadata_fetch DISABLE TRIGGER ALL;



ALTER TABLE public.stations_metadata_fetch ENABLE TRIGGER ALL;

--
-- Data for Name: stations_now_playing; Type: TABLE DATA; Schema: public; Owner: postgres
--

ALTER TABLE public.stations_now_playing DISABLE TRIGGER ALL;



ALTER TABLE public.stations_now_playing ENABLE TRIGGER ALL;

--
-- Data for Name: stations_uptime; Type: TABLE DATA; Schema: public; Owner: postgres
--

ALTER TABLE public.stations_uptime DISABLE TRIGGER ALL;



ALTER TABLE public.stations_uptime ENABLE TRIGGER ALL;

--
-- Name: django_admin_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.django_admin_log_id_seq', 621, true);


--
-- Name: posts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.posts_id_seq', 97179879, true);


--
-- Name: reviews_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.reviews_id_seq', 220, true);


--
-- Name: station_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.station_id_seq', 84, true);


--
-- Name: station_metadata_fetch_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.station_metadata_fetch_id_seq', 143, true);


--
-- Name: station_now_playing_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.station_now_playing_id_seq', 165174780, true);


--
-- Name: station_streams_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.station_streams_id_seq', 194, true);


--
-- Name: station_to_group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.station_to_group_id_seq', 524, true);


--
-- Name: station_to_station_group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.station_to_station_group_id_seq', 1, false);


--
-- Name: station_uptime_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.station_uptime_history_id_seq', 165202015, true);


--
-- Name: stations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.stations_id_seq', 1, false);


--
-- Name: stations_metadata_fetch_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.stations_metadata_fetch_id_seq', 1, false);


--
-- Name: stations_now_playing_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.stations_now_playing_id_seq', 1, false);


--
-- Name: stations_uptime_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.stations_uptime_id_seq', 1, false);


--
-- PostgreSQL database dump complete
--

