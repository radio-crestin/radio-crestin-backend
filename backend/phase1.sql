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
-- Data for Name: analytics_events; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.analytics_events VALUES ('bcb5d19a-a17f-48ad-9f2d-7757eb124363', '2023-11-23 22:23:42.004233+00', '2023-11-23 22:23:42.004233+00', 'share-event', '{"ref": "nfc", "params": {}, "clientIP": "79.118.23.210", "deviceType": "android", "station_slug": "aripi-spre-cer-instrumental"}');
INSERT INTO public.analytics_events VALUES ('d563721a-1fd0-45ca-be89-1018e0f0d67c', '2023-11-23 22:45:29.887921+00', '2023-11-23 22:45:29.887921+00', 'share-event', '{"ref": "nfc", "params": {}, "clientIP": "79.118.23.210", "deviceType": "android", "station_slug": "aripi-spre-cer-instrumental"}');
INSERT INTO public.analytics_events VALUES ('9966a855-07d8-4229-b9b0-a8751ba921bb', '2023-11-23 22:55:08.450666+00', '2023-11-23 22:55:08.450666+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "52.204.27.85", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('d7d17b00-8e88-4e8d-a336-e70278aa9a00', '2023-11-23 23:06:36.436489+00', '2023-11-23 23:06:36.436489+00', 'share-event', '{"ref": "nfc", "params": {}, "clientIP": "79.118.23.210", "deviceType": "android", "station_slug": "aripi-spre-cer-instrumental"}');
INSERT INTO public.analytics_events VALUES ('40bfc69d-1dc6-4736-9f22-d00693ff03bd', '2023-11-23 23:07:05.784709+00', '2023-11-23 23:07:05.784709+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a06:98c0:3600::103", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('a56122b3-e7be-4674-862e-fa5d27568b9d', '2023-11-23 23:07:05.847889+00', '2023-11-23 23:07:05.847889+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a06:98c0:3600::103", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('42e418f4-965c-44f9-86d8-2e8e6092e613', '2023-11-23 23:07:14.739752+00', '2023-11-23 23:07:14.739752+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a06:98c0:3600::103", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('2985a9b2-ed14-4596-8cf2-60e81ac73271', '2023-11-23 23:07:15.74721+00', '2023-11-23 23:07:15.74721+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a06:98c0:3600::103", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('53dc3ab8-a9e4-4604-b8dc-9820fb779599', '2023-11-23 23:08:20.478974+00', '2023-11-23 23:08:20.478974+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a06:98c0:3600::103", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('7d260b9e-5167-496b-a8a7-29298fa15329', '2023-11-23 23:08:20.47987+00', '2023-11-23 23:08:20.47987+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a06:98c0:3600::103", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('f63243c7-b34a-451d-82c4-279ae74c102d', '2023-11-24 00:39:30.197262+00', '2023-11-24 00:39:30.197262+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "89.104.101.82", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('f99f24e8-8aac-4f3f-939c-daf6c5d1c3e1', '2023-11-24 00:39:34.668489+00', '2023-11-24 00:39:34.668489+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "89.104.111.29", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('dc10150b-7b17-42b1-95c1-5e33ff09c363', '2023-11-24 00:39:35.057006+00', '2023-11-24 00:39:35.057006+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "89.104.111.29", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('2c41cdf0-8af1-4796-90e9-a810bb50dc39', '2023-11-24 02:56:17.936816+00', '2023-11-24 02:56:17.936816+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "47.88.94.159", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('e63a9c3b-5710-4e27-ae2a-283f4fe8cbf4', '2023-11-24 02:56:19.180082+00', '2023-11-24 02:56:19.180082+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "47.254.76.138", "deviceType": "android", "station_slug": "Public/home/js/check.js"}');
INSERT INTO public.analytics_events VALUES ('2cf7412b-98d0-47bf-98f6-d11563fa5393', '2023-11-24 02:56:20.410385+00', '2023-11-24 02:56:20.410385+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "47.251.11.3", "deviceType": "android", "station_slug": "static/admin/javascript/hetong.js"}');
INSERT INTO public.analytics_events VALUES ('b0567815-a258-4715-9007-cc494640c6ab', '2023-11-24 02:56:50.195578+00', '2023-11-24 02:56:50.195578+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "47.88.87.97", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('78fb37f3-d0f0-4dab-93f8-ff502786ac31', '2023-11-24 02:56:51.421164+00', '2023-11-24 02:56:51.421164+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "47.254.76.138", "deviceType": "android", "station_slug": "Public/home/js/check.js"}');
INSERT INTO public.analytics_events VALUES ('6c644e3f-6c00-4d5a-aee0-a4d8f0a37262', '2023-11-24 02:56:52.464103+00', '2023-11-24 02:56:52.464103+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "47.251.13.32", "deviceType": "android", "station_slug": "static/admin/javascript/hetong.js"}');
INSERT INTO public.analytics_events VALUES ('10dd98ef-eaaf-4744-a752-594fd07b739c', '2023-11-24 02:59:19.159854+00', '2023-11-24 02:59:19.159854+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "47.254.74.59", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('aa87e3cc-49c8-473c-85e8-1c1cc7547bcb', '2023-11-24 02:59:20.49224+00', '2023-11-24 02:59:20.49224+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "47.88.5.56", "deviceType": "android", "station_slug": "Public/home/js/check.js"}');
INSERT INTO public.analytics_events VALUES ('968472d1-fc74-4b1b-9c33-e0139c6aaf1e', '2023-11-24 02:59:21.663822+00', '2023-11-24 02:59:21.663822+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "47.88.87.97", "deviceType": "android", "station_slug": "static/admin/javascript/hetong.js"}');
INSERT INTO public.analytics_events VALUES ('55397c75-11a4-409e-bd54-dd376719800e', '2023-11-24 02:59:33.050013+00', '2023-11-24 02:59:33.050013+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "47.88.101.3", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('07370a82-1345-4565-9bf8-a6e2359a7b94', '2023-11-24 02:59:34.21899+00', '2023-11-24 02:59:34.21899+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "47.254.25.10", "deviceType": "android", "station_slug": "Public/home/js/check.js"}');
INSERT INTO public.analytics_events VALUES ('1f31c5a3-22b6-4246-9fa2-8d361fd60681', '2023-11-24 02:59:35.453462+00', '2023-11-24 02:59:35.453462+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "47.89.195.210", "deviceType": "android", "station_slug": "static/admin/javascript/hetong.js"}');
INSERT INTO public.analytics_events VALUES ('ecefc00f-70fb-4e6a-9840-ed65af9092b1', '2023-11-24 03:40:01.029153+00', '2023-11-24 03:40:01.029153+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "195.211.77.140", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('e4023a0e-a1fc-47e6-af6c-a8aa0ba642b8', '2023-11-24 03:42:34.343046+00', '2023-11-24 03:42:34.343046+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "195.211.77.142", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('a865a6c8-7382-417c-a785-93d32d39d805', '2023-11-24 03:44:58.236248+00', '2023-11-24 03:44:58.236248+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "195.211.77.140", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('2b774eec-b8d6-4829-b5ef-f7a52535f393', '2023-11-24 03:47:14.499864+00', '2023-11-24 03:47:14.499864+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "195.211.77.142", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('fa12f484-2997-4dbc-ac08-288440a3d621', '2023-11-24 05:58:43.583724+00', '2023-11-24 05:58:43.583724+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.43", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('c35fbb89-4e34-472c-a7d5-b6b7d2993d7c', '2023-11-24 05:58:46.564791+00', '2023-11-24 05:58:46.564791+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.43", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('8e50fbdc-2f58-4791-93e9-413502867c28', '2023-11-24 06:34:01.566325+00', '2023-11-24 06:34:01.566325+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "199.45.155.17", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('64f959ff-20ac-4472-a016-41b77d408d48', '2023-11-24 07:00:54.021156+00', '2023-11-24 07:00:54.021156+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "199.45.154.49", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('d6923871-3490-4adf-b23a-ddf14029b891', '2023-11-24 07:56:31.600251+00', '2023-11-24 07:56:31.600251+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "199.45.155.35", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('9ad2c67b-5da6-42fc-8fcc-f363212fe400', '2023-11-24 07:59:50.961064+00', '2023-11-24 07:59:50.961064+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "199.45.155.17", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('641bddbb-7f92-4bb5-a279-53770ec7e5c5', '2023-11-24 08:18:50.369568+00', '2023-11-24 08:18:50.369568+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.54", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('47db8838-1bd1-40b2-89f9-24ad884b6552', '2023-11-24 08:19:25.430283+00', '2023-11-24 08:19:25.430283+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "54.92.107.92", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('d463f522-a55b-42c6-ba6f-edab622af55a', '2023-11-24 08:19:51.237277+00', '2023-11-24 08:19:51.237277+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "54.92.107.92", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('bca52a8e-678b-4dd3-b525-db287684bc07', '2023-11-24 08:19:53.16446+00', '2023-11-24 08:19:53.16446+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "54.92.107.92", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('6cd9163c-c907-47fc-9bf2-3bc15ef780a0', '2023-11-24 08:19:55.621891+00', '2023-11-24 08:19:55.621891+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "54.92.107.92", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('c79f1f72-4a61-4fb2-bbf6-61c2d64b4ad0', '2023-11-24 08:19:55.632898+00', '2023-11-24 08:19:55.632898+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "54.92.107.92", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('f1e50ee0-bf74-4577-a6b9-b79fb864302e', '2023-11-24 08:19:56.580231+00', '2023-11-24 08:19:56.580231+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "54.92.107.92", "deviceType": "ios", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('bc2ab97a-4d9b-468c-b06d-7fe792016288', '2023-11-24 08:19:55.691957+00', '2023-11-24 08:19:55.691957+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "54.92.107.92", "deviceType": "ios", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('387f00ad-7150-4b2e-be2d-ca47a7f544b7', '2023-11-24 08:54:28.733782+00', '2023-11-24 08:54:28.733782+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.168", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('dbcf16ac-d4ea-47b0-a6f4-f20336f1507d', '2023-11-24 10:54:38.677577+00', '2023-11-24 10:54:38.677577+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.74", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('5c19861e-4843-41c5-91ef-3b5353f1ed84', '2023-11-24 11:49:37.111498+00', '2023-11-24 11:49:37.111498+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.26", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('b44241e2-713b-44a8-94da-4a2145cd1f55', '2023-11-24 12:09:03.635067+00', '2023-11-24 12:09:03.635067+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.7", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('004987ba-4972-4075-93c7-a16756971e3d', '2023-11-24 12:38:36.538262+00', '2023-11-24 12:38:36.538262+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "199.45.154.48", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('210d1263-1bf6-4708-8942-d31b5874d401', '2023-11-24 12:55:02.051762+00', '2023-11-24 12:55:02.051762+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "199.45.155.32", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('3562b99b-cddb-4de1-bab0-8370e8441f6d', '2023-11-24 13:01:53.953699+00', '2023-11-24 13:01:53.953699+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "199.45.155.16", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('92e89086-42c4-4795-93d8-09460394e3c8', '2023-11-24 13:10:54.588532+00', '2023-11-24 13:10:54.588532+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.138", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('bd9571ee-ce1c-4aa7-85c7-3318bbd48527', '2023-11-24 13:53:32.478322+00', '2023-11-24 13:53:32.478322+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.20", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('e3342dec-480d-4ac6-bc06-f6bff161143f', '2023-11-24 13:58:57.642833+00', '2023-11-24 13:58:57.642833+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "138.197.163.38", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('dc6634e4-ea3b-49f1-a758-05e7d80acce7', '2023-11-24 13:58:57.910072+00', '2023-11-24 13:58:57.910072+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "138.197.163.38", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('c9671623-2c77-4aea-850e-33dff5af3d9e', '2023-11-24 14:06:37.510125+00', '2023-11-24 14:06:37.510125+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.115", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('0f38bdf8-232b-4288-87b8-2b156715d800', '2023-11-24 14:36:55.480344+00', '2023-11-24 14:36:55.480344+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.241", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('2007d51a-3934-4b71-a412-ad5f0f2f04d4', '2023-11-24 14:42:52.057154+00', '2023-11-24 14:42:52.057154+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "199.45.155.32", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('92355752-2ac8-4f36-9ab1-e98aa2b362d2', '2023-11-24 14:53:10.687185+00', '2023-11-24 14:53:10.687185+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.28", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('bb387ff7-a9a1-4e7e-bdb5-eae6ee7c2d34', '2023-11-24 15:13:18.919724+00', '2023-11-24 15:13:18.919724+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.185", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('db7c2e15-425e-4249-8817-5d5b9f4f2ddf', '2023-11-24 15:21:13.224718+00', '2023-11-24 15:21:13.224718+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "159.223.48.151", "deviceType": "unknown", "station_slug": "wordpress/wp-admin/setup-config.php"}');
INSERT INTO public.analytics_events VALUES ('00cee98d-c474-478d-9d62-0a37f87ccc72', '2023-11-24 16:11:22.835589+00', '2023-11-24 16:11:22.835589+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.206", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('ed6ecb7c-743e-45a8-b6ad-68736cad9dbd', '2023-11-24 16:37:59.650563+00', '2023-11-24 16:37:59.650563+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.210", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('2e5861ef-f128-4244-9046-d056a90bd983', '2023-11-24 17:14:07.424896+00', '2023-11-24 17:14:07.424896+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.135", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('0aa3d190-1724-4954-a239-1533760bafe6', '2023-11-24 17:15:15.87735+00', '2023-11-24 17:15:15.87735+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.42", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('67fca162-f87e-4bb0-9ad6-aeea2d100706', '2023-11-24 17:19:54.875914+00', '2023-11-24 17:19:54.875914+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "199.45.155.17", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('65cbc174-0c68-442e-942b-18a0e05208f9', '2023-11-24 17:20:47.516963+00', '2023-11-24 17:20:47.516963+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.159", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('1c9e7bde-b7df-49d0-a3d1-2e20d2045a5f', '2023-11-24 17:33:24.227695+00', '2023-11-24 17:33:24.227695+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "199.45.154.18", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('8e0c1256-e3d8-434b-8b8d-e215e6e17285', '2023-11-24 17:36:55.554164+00', '2023-11-24 17:36:55.554164+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2400:8902::f03c:93ff:fe55:c48", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('ca2c146b-8ecd-41da-98bc-3f0c773f16ac', '2023-11-24 17:36:59.694567+00', '2023-11-24 17:36:59.694567+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2400:8902::f03c:93ff:fe55:c48", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('94e7f300-ba4a-4052-9a67-e89dfb3645c5', '2023-11-24 17:40:48.977108+00', '2023-11-24 17:40:48.977108+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "199.45.154.49", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('dad1fa42-ad8a-4cd5-9a1b-6e6b43235877', '2023-11-24 17:58:38.682447+00', '2023-11-24 17:58:38.682447+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.24", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('a6b4ed5d-f3ae-4571-8052-e4c8ea849f9b', '2023-11-24 17:59:26.082657+00', '2023-11-24 17:59:26.082657+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "199.45.155.34", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('c1676989-785c-45c5-9e7c-2f487114e171', '2023-11-24 18:04:33.683922+00', '2023-11-24 18:04:33.683922+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.187", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('97d4d3e6-eef1-4ac3-8564-b959fe454904', '2023-11-24 18:34:10.38119+00', '2023-11-24 18:34:10.38119+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "159.223.48.151", "deviceType": "unknown", "station_slug": "wordpress/wp-admin/setup-config.php"}');
INSERT INTO public.analytics_events VALUES ('bd9d4f65-6f75-461f-ba8c-0c7ba9086633', '2023-11-24 18:44:02.344638+00', '2023-11-24 18:44:02.344638+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.78", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('0fd8e3a1-bca3-4479-bbc1-acb981c5f13f', '2023-11-24 19:24:16.673204+00', '2023-11-24 19:24:16.673204+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "37.251.221.83", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('7c2bd279-e5ff-4e49-8105-24b58b8fa655', '2023-11-24 19:56:13.160987+00', '2023-11-24 19:56:13.160987+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "45.192.152.25", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('59c20789-b250-4d95-885f-f010e259e5c0', '2023-11-24 19:57:00.896994+00', '2023-11-24 19:57:00.896994+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.48", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('2664b06a-6c40-4e12-9a0c-00ea9bb67a3c', '2023-11-24 21:27:58.243415+00', '2023-11-24 21:27:58.243415+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.44", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('140dbd2e-a504-480c-aaff-6eeb76884106', '2023-11-24 21:51:07.336483+00', '2023-11-24 21:51:07.336483+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "79.118.23.210", "deviceType": "desktop", "station_slug": "rve-timisoara"}');
INSERT INTO public.analytics_events VALUES ('b5a33961-67c4-4266-a265-556e50867fe9', '2023-11-24 21:53:54.153441+00', '2023-11-24 21:53:54.153441+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a06:98c0:3600::103", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('af29f638-481b-4a00-a58e-78163e8174f4', '2023-11-24 21:53:54.263722+00', '2023-11-24 21:53:54.263722+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a06:98c0:3600::103", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('e48f12ea-ff53-47c7-b0c7-f0ccd076ffac', '2023-11-24 21:54:24.227446+00', '2023-11-24 21:54:24.227446+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a06:98c0:3600::103", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('dc8ca7ac-af13-485b-bc48-b27c2d09140a', '2023-11-24 21:54:31.708498+00', '2023-11-24 21:54:31.708498+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a06:98c0:3600::103", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('0d425f95-fa7d-498e-94b5-729ce45f67e3', '2023-11-24 21:54:50.073161+00', '2023-11-24 21:54:50.073161+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a06:98c0:3600::103", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('81e58b16-8e20-4cdc-872d-2ade2a5a006a', '2023-11-24 21:56:30.098968+00', '2023-11-24 21:56:30.098968+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "79.118.23.210", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('bcef4b1d-e6cc-46f1-8e49-eb94af5b37d0', '2023-11-24 22:08:54.126575+00', '2023-11-24 22:08:54.126575+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "79.118.23.210", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('ba1d8180-1e7a-42e4-b461-a5206367e747', '2023-11-24 22:09:49.965707+00', '2023-11-24 22:09:49.965707+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:b0c0:3:d0::d1a:1", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('2f5e9d06-5613-4f9b-9e0f-175eca9a34ae', '2023-11-24 22:09:49.980354+00', '2023-11-24 22:09:49.980354+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:b0c0:2:d0::10fd:3001", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('e63d6e78-733a-4156-adb8-4f762c34c3be', '2023-11-24 22:09:50.139998+00', '2023-11-24 22:09:50.139998+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "159.65.58.104", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('06208f80-cbaa-4635-9772-7f42abb0fc7d', '2023-11-24 22:09:50.254423+00', '2023-11-24 22:09:50.254423+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "207.154.240.169", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('dccf470c-12d8-4969-908b-88f7737e7ad3', '2023-11-24 22:09:50.265757+00', '2023-11-24 22:09:50.265757+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "159.65.58.104", "deviceType": "unknown", "station_slug": ".vscode/sftp.json"}');
INSERT INTO public.analytics_events VALUES ('619fee47-97dc-4f2c-9927-35d0e207cdef', '2023-11-24 22:09:50.369798+00', '2023-11-24 22:09:50.369798+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:b0c0:3:d0::fe3:3001", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('b4498cd1-d759-447a-a288-2ee25e63051d', '2023-11-24 22:09:50.401588+00', '2023-11-24 22:09:50.401588+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "159.65.58.104", "deviceType": "unknown", "station_slug": "about"}');
INSERT INTO public.analytics_events VALUES ('9fefe5d5-62a3-43e4-a713-77f395856fa2', '2023-11-24 22:09:50.412833+00', '2023-11-24 22:09:50.412833+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "207.154.240.169", "deviceType": "unknown", "station_slug": ".vscode/sftp.json"}');
INSERT INTO public.analytics_events VALUES ('cf9dc51c-6e85-45f4-9c93-d8ff39efd8a0', '2023-11-24 22:09:50.436104+00', '2023-11-24 22:09:50.436104+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.110.156.182", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('279ddf4e-4ec1-4881-8409-9a223ebb5a29', '2023-11-24 22:09:50.474953+00', '2023-11-24 22:09:50.474953+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:b0c0:3:d0::11fa:8001", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('eb605944-2ba5-4d68-9622-20ceb3d1d323', '2023-11-24 22:09:50.475421+00', '2023-11-24 22:09:50.475421+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:b0c0:1:d0::e2e:7001", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('0d62bc37-4e4f-499f-b677-9d6b57407dcf', '2023-11-24 22:09:50.528098+00', '2023-11-24 22:09:50.528098+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "207.154.240.169", "deviceType": "unknown", "station_slug": "about"}');
INSERT INTO public.analytics_events VALUES ('3a06a8a0-10f0-41ec-a55c-b03b78b2d73e', '2023-11-24 22:09:50.545968+00', '2023-11-24 22:09:50.545968+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "159.65.58.104", "deviceType": "unknown", "station_slug": "debug/default/view"}');
INSERT INTO public.analytics_events VALUES ('9a9fe734-46b4-4e3c-a25c-3ee30b713c26', '2023-11-24 22:09:50.5793+00', '2023-11-24 22:09:50.5793+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:b0c0:1:d0::e8d:e001", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('c0efe9ea-f887-4c4d-967d-a86e3e1e4475', '2023-11-24 22:09:50.624281+00', '2023-11-24 22:09:50.624281+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.198.72.96", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('f2ef965a-7864-429d-a69a-741eb7738b91', '2023-11-24 22:09:50.631684+00', '2023-11-24 22:09:50.631684+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "207.154.240.169", "deviceType": "unknown", "station_slug": "debug/default/view"}');
INSERT INTO public.analytics_events VALUES ('70be146f-9d7e-4905-9ed5-d1a478dd05e1', '2023-11-24 22:09:50.660438+00', '2023-11-24 22:09:50.660438+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "159.65.58.104", "deviceType": "unknown", "station_slug": "v2/_catalog"}');
INSERT INTO public.analytics_events VALUES ('0b6e7488-efa3-4d4c-b119-76f73e1cb059', '2023-11-24 22:09:50.710821+00', '2023-11-24 22:09:50.710821+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "139.59.182.142", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('e2e9d662-21cb-4ab3-8007-8fa14995b423', '2023-11-24 22:09:50.718547+00', '2023-11-24 22:09:50.718547+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "207.154.240.169", "deviceType": "unknown", "station_slug": "v2/_catalog"}');
INSERT INTO public.analytics_events VALUES ('0668f2a9-5482-4f8f-8db4-a9ce27f0644a', '2023-11-24 22:09:50.749398+00', '2023-11-24 22:09:50.749398+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "128.199.195.68", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('4d31ee44-204b-4f53-8cc7-539af6cdd1aa', '2023-11-24 22:09:50.810578+00', '2023-11-24 22:09:50.810578+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "159.65.58.104", "deviceType": "unknown", "station_slug": "ecp/Current/exporttool/microsoft.exchange.ediscovery.exporttool.application"}');
INSERT INTO public.analytics_events VALUES ('e71436e9-de47-464f-81b5-da4c4f4d54f2', '2023-11-24 22:09:50.815405+00', '2023-11-24 22:09:50.815405+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "207.154.240.169", "deviceType": "unknown", "station_slug": "ecp/Current/exporttool/microsoft.exchange.ediscovery.exporttool.application"}');
INSERT INTO public.analytics_events VALUES ('9a46ea1b-27dd-42e7-a74b-39fbcb4978b4', '2023-11-24 22:09:50.835786+00', '2023-11-24 22:09:50.835786+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "139.59.182.142", "deviceType": "unknown", "station_slug": ".vscode/sftp.json"}');
INSERT INTO public.analytics_events VALUES ('e709dfcc-b5d6-4038-9f12-6aaae87ccb66', '2023-11-24 22:09:50.851092+00', '2023-11-24 22:09:50.851092+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.110.156.182", "deviceType": "unknown", "station_slug": ".vscode/sftp.json"}');
INSERT INTO public.analytics_events VALUES ('23bce2c9-ae8a-4035-a6a4-622a774aece6', '2023-11-24 22:09:50.907767+00', '2023-11-24 22:09:50.907767+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "207.154.240.169", "deviceType": "unknown", "station_slug": "server-status"}');
INSERT INTO public.analytics_events VALUES ('ab3abf7e-a557-4f36-8dd2-858f4dc077db', '2023-11-24 22:09:50.937963+00', '2023-11-24 22:09:50.937963+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "159.65.58.104", "deviceType": "unknown", "station_slug": "server-status"}');
INSERT INTO public.analytics_events VALUES ('4a74a52a-de64-4cc5-82f3-bb0d8d771284', '2023-11-24 22:09:50.965049+00', '2023-11-24 22:09:50.965049+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "139.59.182.142", "deviceType": "unknown", "station_slug": "about"}');
INSERT INTO public.analytics_events VALUES ('41c18768-13b5-4800-a4e9-bbbbe9548398', '2023-11-24 22:09:51.009231+00', '2023-11-24 22:09:51.009231+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "207.154.240.169", "deviceType": "unknown", "station_slug": "login.action"}');
INSERT INTO public.analytics_events VALUES ('ad958325-b844-4e8c-961b-3e1ed66c9cdf', '2023-11-24 22:09:51.028149+00', '2023-11-24 22:09:51.028149+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.198.72.96", "deviceType": "unknown", "station_slug": ".vscode/sftp.json"}');
INSERT INTO public.analytics_events VALUES ('66522e6f-ca3a-4d46-a833-3b732ceb9fbb', '2023-11-24 22:09:51.098979+00', '2023-11-24 22:09:51.098979+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "207.154.240.169", "deviceType": "unknown", "station_slug": "_all_dbs"}');
INSERT INTO public.analytics_events VALUES ('43a02f37-9f64-4396-aeed-6d2bef0b3913', '2023-11-24 22:09:51.103734+00', '2023-11-24 22:09:51.103734+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "159.65.58.104", "deviceType": "unknown", "station_slug": "login.action"}');
INSERT INTO public.analytics_events VALUES ('b0d2a660-f878-4519-93c1-fcf8a591b210', '2023-11-24 22:09:51.110603+00', '2023-11-24 22:09:51.110603+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "139.59.182.142", "deviceType": "unknown", "station_slug": "debug/default/view"}');
INSERT INTO public.analytics_events VALUES ('d8bb9674-f7d2-4454-b359-635a6da55c0a', '2023-11-24 22:09:51.132972+00', '2023-11-24 22:09:51.132972+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "128.199.195.68", "deviceType": "unknown", "station_slug": ".vscode/sftp.json"}');
INSERT INTO public.analytics_events VALUES ('0176662d-6a07-4f09-bee1-893a61ee9166', '2023-11-24 22:09:51.181698+00', '2023-11-24 22:09:51.181698+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "207.154.240.169", "deviceType": "unknown", "station_slug": ".DS_Store"}');
INSERT INTO public.analytics_events VALUES ('18409d23-e993-4f56-b36f-120e494aec9d', '2023-11-24 22:09:51.231111+00', '2023-11-24 22:09:51.231111+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "159.65.58.104", "deviceType": "unknown", "station_slug": "_all_dbs"}');
INSERT INTO public.analytics_events VALUES ('83ff6d44-c4d2-4bcb-a2c7-90f1b00cf3df', '2023-11-24 22:09:51.24716+00', '2023-11-24 22:09:51.24716+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "139.59.182.142", "deviceType": "unknown", "station_slug": "v2/_catalog"}');
INSERT INTO public.analytics_events VALUES ('0e7ce4b5-18f6-45c3-8b2c-2e63c324cd45', '2023-11-24 22:09:51.253964+00', '2023-11-24 22:09:51.253964+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.110.156.182", "deviceType": "unknown", "station_slug": "about"}');
INSERT INTO public.analytics_events VALUES ('94a213be-bc9f-4fee-97ba-3d66f3e2676e', '2023-11-24 22:09:51.276291+00', '2023-11-24 22:09:51.276291+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "207.154.240.169", "deviceType": "unknown", "station_slug": ".env"}');
INSERT INTO public.analytics_events VALUES ('3b24df87-bdb4-4a98-b15e-d4c88c9bdcf1', '2023-11-24 22:09:51.354352+00', '2023-11-24 22:09:51.354352+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "159.65.58.104", "deviceType": "unknown", "station_slug": ".DS_Store"}');
INSERT INTO public.analytics_events VALUES ('9643305c-6ae2-4c18-b84b-38aa1cbaf590', '2023-11-24 22:09:51.449655+00', '2023-11-24 22:09:51.449655+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.198.72.96", "deviceType": "unknown", "station_slug": "about"}');
INSERT INTO public.analytics_events VALUES ('f9db6c43-9630-445b-a34e-0c7355a3b1d3', '2023-11-24 22:09:53.091471+00', '2023-11-24 22:09:53.091471+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "128.199.195.68", "deviceType": "unknown", "station_slug": "server-status"}');
INSERT INTO public.analytics_events VALUES ('e316f880-edcb-40b5-a69e-8195db7286b8', '2023-11-24 22:09:51.357181+00', '2023-11-24 22:09:51.357181+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "207.154.240.169", "deviceType": "unknown", "station_slug": ".git/config"}');
INSERT INTO public.analytics_events VALUES ('94fe3a9f-81be-45ce-b416-267c0a965cd6', '2023-11-24 22:09:51.371751+00', '2023-11-24 22:09:51.371751+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "139.59.182.142", "deviceType": "unknown", "station_slug": "ecp/Current/exporttool/microsoft.exchange.ediscovery.exporttool.application"}');
INSERT INTO public.analytics_events VALUES ('0098a257-a34d-41dd-9fcd-218c7ae09a74', '2023-11-24 22:09:51.48973+00', '2023-11-24 22:09:51.48973+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "159.65.58.104", "deviceType": "unknown", "station_slug": ".env"}');
INSERT INTO public.analytics_events VALUES ('4d4c77f2-a261-437e-89f0-163703504e4b', '2023-11-24 22:09:51.763495+00', '2023-11-24 22:09:51.763495+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "207.154.240.169", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('47c8a7f9-6dbb-4df1-99ba-26c08b284316', '2023-11-24 22:09:51.884589+00', '2023-11-24 22:09:51.884589+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.198.72.96", "deviceType": "unknown", "station_slug": "debug/default/view"}');
INSERT INTO public.analytics_events VALUES ('c80e1ff7-958e-422e-a035-10f0bce93eac', '2023-11-24 22:09:51.936831+00', '2023-11-24 22:09:51.936831+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "128.199.195.68", "deviceType": "unknown", "station_slug": "debug/default/view"}');
INSERT INTO public.analytics_events VALUES ('270a10e8-da29-48a9-9c27-b01d34a5a6c4', '2023-11-24 22:09:52.04649+00', '2023-11-24 22:09:52.04649+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.110.156.182", "deviceType": "unknown", "station_slug": "v2/_catalog"}');
INSERT INTO public.analytics_events VALUES ('5965a1ae-6e09-44e0-8281-7f5cfd8cc566', '2023-11-24 22:09:52.060609+00', '2023-11-24 22:09:52.060609+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "159.65.58.104", "deviceType": "unknown", "station_slug": "telescope/requests"}');
INSERT INTO public.analytics_events VALUES ('91cc1696-8f77-4392-95b1-ad623aeaf675', '2023-11-24 22:09:52.099838+00', '2023-11-24 22:09:52.099838+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "139.59.182.142", "deviceType": "unknown", "station_slug": ".git/config"}');
INSERT INTO public.analytics_events VALUES ('750d8e58-8c35-47fc-93b7-9659593f8240', '2023-11-24 22:09:52.168612+00', '2023-11-24 22:09:52.168612+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "159.65.58.104", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('f64367b1-7bc5-4bf7-b7c1-40946dddac85', '2023-11-24 22:09:52.265621+00', '2023-11-24 22:09:52.265621+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "139.59.182.142", "deviceType": "unknown", "station_slug": "s/7373e26323e21323e2430313/_/;/META-INF/maven/com.atlassian.jira/jira-webapp-dist/pom.properties"}');
INSERT INTO public.analytics_events VALUES ('35983882-1fdf-410a-97d7-a1bb648e5050', '2023-11-24 22:09:52.328846+00', '2023-11-24 22:09:52.328846+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "128.199.195.68", "deviceType": "unknown", "station_slug": "v2/_catalog"}');
INSERT INTO public.analytics_events VALUES ('fab3058e-fd1d-461d-bba7-6a67211f4cbe', '2023-11-24 22:09:52.372249+00', '2023-11-24 22:09:52.372249+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "139.59.182.142", "deviceType": "unknown", "station_slug": "config.json"}');
INSERT INTO public.analytics_events VALUES ('ee35fe42-7cbd-4e1f-b4f0-1313b5a312ea', '2023-11-24 22:09:52.438246+00', '2023-11-24 22:09:52.438246+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.110.156.182", "deviceType": "unknown", "station_slug": "ecp/Current/exporttool/microsoft.exchange.ediscovery.exporttool.application"}');
INSERT INTO public.analytics_events VALUES ('77c8d964-0510-436b-bb22-bd6e7d0e314a', '2023-11-24 22:09:52.47299+00', '2023-11-24 22:09:52.47299+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "139.59.182.142", "deviceType": "unknown", "station_slug": "telescope/requests"}');
INSERT INTO public.analytics_events VALUES ('268ac2f3-bd9d-4f5b-93d4-696d4cff8e4a', '2023-11-24 22:09:52.580455+00', '2023-11-24 22:09:52.580455+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "139.59.182.142", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('59a3300d-f5b5-4037-8e6c-9d1bb9799a47', '2023-11-24 22:09:52.706685+00', '2023-11-24 22:09:52.706685+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "128.199.195.68", "deviceType": "unknown", "station_slug": "ecp/Current/exporttool/microsoft.exchange.ediscovery.exporttool.application"}');
INSERT INTO public.analytics_events VALUES ('573b924a-cf9f-4a57-9c3f-0a15d4565b7b', '2023-11-24 22:09:52.718671+00', '2023-11-24 22:09:52.718671+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.198.72.96", "deviceType": "unknown", "station_slug": "ecp/Current/exporttool/microsoft.exchange.ediscovery.exporttool.application"}');
INSERT INTO public.analytics_events VALUES ('c1bdda1c-6957-4e9a-b1c4-c1c31050171c', '2023-11-24 22:09:52.842681+00', '2023-11-24 22:09:52.842681+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.110.156.182", "deviceType": "unknown", "station_slug": "server-status"}');
INSERT INTO public.analytics_events VALUES ('b0816672-bcca-4ca5-9cec-68a02acd8e64', '2023-11-24 22:09:51.461551+00', '2023-11-24 22:09:51.461551+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "207.154.240.169", "deviceType": "unknown", "station_slug": "s/036313e2533313e27363e2237313/_/;/META-INF/maven/com.atlassian.jira/jira-webapp-dist/pom.properties"}');
INSERT INTO public.analytics_events VALUES ('e7d4b584-029f-454b-aaa9-c8b17424a7e0', '2023-11-24 22:09:51.490469+00', '2023-11-24 22:09:51.490469+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "139.59.182.142", "deviceType": "unknown", "station_slug": "server-status"}');
INSERT INTO public.analytics_events VALUES ('b7b6473d-365f-45c8-bf29-85a0d5cc7ffb', '2023-11-24 22:09:51.528969+00', '2023-11-24 22:09:51.528969+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "128.199.195.68", "deviceType": "unknown", "station_slug": "about"}');
INSERT INTO public.analytics_events VALUES ('8c7f44f1-6413-4c3d-b737-1f4f2fc2a661', '2023-11-24 22:09:51.563811+00', '2023-11-24 22:09:51.563811+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "207.154.240.169", "deviceType": "unknown", "station_slug": "config.json"}');
INSERT INTO public.analytics_events VALUES ('fc1909c3-903c-44e5-a068-7815e17b35f4', '2023-11-24 22:09:51.628369+00', '2023-11-24 22:09:51.628369+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "139.59.182.142", "deviceType": "unknown", "station_slug": "login.action"}');
INSERT INTO public.analytics_events VALUES ('49ed39d3-62c2-4267-8c86-0bfa9caf6b0d', '2023-11-24 22:09:51.644313+00', '2023-11-24 22:09:51.644313+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "159.65.58.104", "deviceType": "unknown", "station_slug": ".git/config"}');
INSERT INTO public.analytics_events VALUES ('fccf712b-7d4a-44c5-875f-706f0f613e08', '2023-11-24 22:09:51.654832+00', '2023-11-24 22:09:51.654832+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.110.156.182", "deviceType": "unknown", "station_slug": "debug/default/view"}');
INSERT INTO public.analytics_events VALUES ('9f95fa08-28a7-4acf-af09-a54356eb00eb', '2023-11-24 22:09:51.668394+00', '2023-11-24 22:09:51.668394+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "207.154.240.169", "deviceType": "unknown", "station_slug": "telescope/requests"}');
INSERT INTO public.analytics_events VALUES ('161cdd24-ebf2-44ed-8e5b-edfa3cfca33e', '2023-11-24 22:09:51.757374+00', '2023-11-24 22:09:51.757374+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "139.59.182.142", "deviceType": "unknown", "station_slug": "_all_dbs"}');
INSERT INTO public.analytics_events VALUES ('591a4251-2954-45d9-b5a7-05f76fd26289', '2023-11-24 22:09:51.766225+00', '2023-11-24 22:09:51.766225+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "159.65.58.104", "deviceType": "unknown", "station_slug": "s/7373e26323e21323e2430313/_/;/META-INF/maven/com.atlassian.jira/jira-webapp-dist/pom.properties"}');
INSERT INTO public.analytics_events VALUES ('39f5bb1f-21df-4d47-b5d5-5a0e80297073', '2023-11-24 22:09:51.892955+00', '2023-11-24 22:09:51.892955+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "139.59.182.142", "deviceType": "unknown", "station_slug": ".DS_Store"}');
INSERT INTO public.analytics_events VALUES ('82206d89-487b-42d0-b335-89dd39a3314e', '2023-11-24 22:09:51.931459+00', '2023-11-24 22:09:51.931459+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "159.65.58.104", "deviceType": "unknown", "station_slug": "config.json"}');
INSERT INTO public.analytics_events VALUES ('fea58b90-dc08-48c2-8450-2e723bea1f95', '2023-11-24 22:09:51.988596+00', '2023-11-24 22:09:51.988596+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "139.59.182.142", "deviceType": "unknown", "station_slug": ".env"}');
INSERT INTO public.analytics_events VALUES ('59242c46-af50-46de-beed-fb4a8a1b58c9', '2023-11-24 22:09:52.318911+00', '2023-11-24 22:09:52.318911+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.198.72.96", "deviceType": "unknown", "station_slug": "v2/_catalog"}');
INSERT INTO public.analytics_events VALUES ('7348a04a-ee02-448d-8c2b-8ec18bd046b8', '2023-11-24 22:09:53.116195+00', '2023-11-24 22:09:53.116195+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.198.72.96", "deviceType": "unknown", "station_slug": "server-status"}');
INSERT INTO public.analytics_events VALUES ('9b71e85a-5b1d-462a-bb31-beb1927d6aa9', '2023-11-24 22:09:53.213438+00', '2023-11-24 22:09:53.213438+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.110.156.182", "deviceType": "unknown", "station_slug": "login.action"}');
INSERT INTO public.analytics_events VALUES ('2c05ad71-39db-4c51-a96d-bad8b170d56f', '2023-11-24 22:09:53.337501+00', '2023-11-24 22:09:53.337501+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.198.72.96", "deviceType": "unknown", "station_slug": "login.action"}');
INSERT INTO public.analytics_events VALUES ('5530704d-2955-4e12-90b5-3a72f3e91716', '2023-11-24 22:09:53.45435+00', '2023-11-24 22:09:53.45435+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "128.199.195.68", "deviceType": "unknown", "station_slug": "login.action"}');
INSERT INTO public.analytics_events VALUES ('f12b9a5e-5542-4df7-a4ab-4b071e990d8e', '2023-11-24 22:09:53.605334+00', '2023-11-24 22:09:53.605334+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.110.156.182", "deviceType": "unknown", "station_slug": "_all_dbs"}');
INSERT INTO public.analytics_events VALUES ('be342689-afe7-468b-8667-8413d6d26b00', '2023-11-24 22:09:53.723903+00', '2023-11-24 22:09:53.723903+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.198.72.96", "deviceType": "unknown", "station_slug": "_all_dbs"}');
INSERT INTO public.analytics_events VALUES ('0b777e8f-4579-442d-ac94-6db5b4c307ec', '2023-11-24 22:09:53.837707+00', '2023-11-24 22:09:53.837707+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "128.199.195.68", "deviceType": "unknown", "station_slug": "_all_dbs"}');
INSERT INTO public.analytics_events VALUES ('10f6fadb-5d40-4bc8-9bb6-1d3789fd0fc4', '2023-11-24 22:09:53.996444+00', '2023-11-24 22:09:53.996444+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.110.156.182", "deviceType": "unknown", "station_slug": ".DS_Store"}');
INSERT INTO public.analytics_events VALUES ('7cbab94e-3bec-43f2-89a1-3d3f392ad6cd', '2023-11-24 22:09:54.127288+00', '2023-11-24 22:09:54.127288+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.198.72.96", "deviceType": "unknown", "station_slug": ".DS_Store"}');
INSERT INTO public.analytics_events VALUES ('5ebba321-7f84-4b0f-a839-7463ad98d1e3', '2023-11-24 22:09:54.183785+00', '2023-11-24 22:09:54.183785+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "104.164.173.203", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('c9c24f72-984c-474a-8431-b295356cd8bf', '2023-11-24 22:09:54.229895+00', '2023-11-24 22:09:54.229895+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "128.199.195.68", "deviceType": "unknown", "station_slug": ".DS_Store"}');
INSERT INTO public.analytics_events VALUES ('fb102258-b79d-4472-a1fe-4e8d835f7151', '2023-11-24 22:09:54.386871+00', '2023-11-24 22:09:54.386871+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.110.156.182", "deviceType": "unknown", "station_slug": ".env"}');
INSERT INTO public.analytics_events VALUES ('227fcc84-d02c-4208-937e-503f11031d83', '2023-11-24 22:09:54.550915+00', '2023-11-24 22:09:54.550915+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.198.72.96", "deviceType": "unknown", "station_slug": ".env"}');
INSERT INTO public.analytics_events VALUES ('9f25c664-f411-409f-a61a-858fc06b2a67', '2023-11-24 22:09:54.616568+00', '2023-11-24 22:09:54.616568+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "128.199.195.68", "deviceType": "unknown", "station_slug": ".env"}');
INSERT INTO public.analytics_events VALUES ('4eb7aec1-0300-4861-82db-d6837f0d3d62', '2023-11-24 22:09:54.778546+00', '2023-11-24 22:09:54.778546+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.110.156.182", "deviceType": "unknown", "station_slug": ".git/config"}');
INSERT INTO public.analytics_events VALUES ('445ffeb5-5e47-4531-9006-709caf92c5e3', '2023-11-24 22:09:54.79089+00', '2023-11-24 22:09:54.79089+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.198.72.96", "deviceType": "unknown", "station_slug": ".git/config"}');
INSERT INTO public.analytics_events VALUES ('05001745-fcc2-4cc1-a8a7-12c5f2fad9a2', '2023-11-24 22:09:55.006865+00', '2023-11-24 22:09:55.006865+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "128.199.195.68", "deviceType": "unknown", "station_slug": ".git/config"}');
INSERT INTO public.analytics_events VALUES ('f3ea4c09-bf4f-48c9-8703-39f9972e72bc', '2023-11-24 22:09:55.171109+00', '2023-11-24 22:09:55.171109+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.110.156.182", "deviceType": "unknown", "station_slug": "s/036313e2533313e27363e2237313/_/;/META-INF/maven/com.atlassian.jira/jira-webapp-dist/pom.properties"}');
INSERT INTO public.analytics_events VALUES ('68a48155-f897-411c-a380-9d7f252be5a4', '2023-11-24 22:09:55.196533+00', '2023-11-24 22:09:55.196533+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.198.72.96", "deviceType": "unknown", "station_slug": "s/036313e2533313e27363e2237313/_/;/META-INF/maven/com.atlassian.jira/jira-webapp-dist/pom.properties"}');
INSERT INTO public.analytics_events VALUES ('d6181bbb-0d76-4af2-8d48-c8940a96e75f', '2023-11-24 22:09:55.377314+00', '2023-11-24 22:09:55.377314+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "128.199.195.68", "deviceType": "unknown", "station_slug": "s/7373e26323e21323e2430313/_/;/META-INF/maven/com.atlassian.jira/jira-webapp-dist/pom.properties"}');
INSERT INTO public.analytics_events VALUES ('a368f1a6-5695-41d8-ba9d-5afb6e25f6db', '2023-11-24 22:09:55.568764+00', '2023-11-24 22:09:55.568764+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.110.156.182", "deviceType": "unknown", "station_slug": "config.json"}');
INSERT INTO public.analytics_events VALUES ('89398d4d-fdbb-40f7-9580-a031d34d4a68', '2023-11-24 22:09:55.609487+00', '2023-11-24 22:09:55.609487+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.198.72.96", "deviceType": "unknown", "station_slug": "config.json"}');
INSERT INTO public.analytics_events VALUES ('2be09975-65a6-43ef-86d2-d08322e9b4ac', '2023-11-24 22:09:55.757641+00', '2023-11-24 22:09:55.757641+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "128.199.195.68", "deviceType": "unknown", "station_slug": "config.json"}');
INSERT INTO public.analytics_events VALUES ('f8afddd8-6a28-42c1-92be-cd678522bf1f', '2023-11-24 22:09:55.984402+00', '2023-11-24 22:09:55.984402+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.110.156.182", "deviceType": "unknown", "station_slug": "telescope/requests"}');
INSERT INTO public.analytics_events VALUES ('b838a5c0-1f79-4baa-bddc-5a7c3de3d865', '2023-11-24 22:09:56.023782+00', '2023-11-24 22:09:56.023782+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.198.72.96", "deviceType": "unknown", "station_slug": "telescope/requests"}');
INSERT INTO public.analytics_events VALUES ('e1393da4-401a-424c-8042-878acb03b287', '2023-11-24 22:09:56.143285+00', '2023-11-24 22:09:56.143285+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "128.199.195.68", "deviceType": "unknown", "station_slug": "telescope/requests"}');
INSERT INTO public.analytics_events VALUES ('27dfb481-91e9-47f7-85f8-ed4f14f11a30', '2023-11-24 22:09:56.372606+00', '2023-11-24 22:09:56.372606+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.110.156.182", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('c4328207-e4ae-4547-963e-32aed464c2a6', '2023-11-24 22:09:56.401472+00', '2023-11-24 22:09:56.401472+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "143.198.72.96", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('fc55a7d2-eb2e-4f3f-95cc-426d25c46ded', '2023-11-24 22:09:56.519672+00', '2023-11-24 22:09:56.519672+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "128.199.195.68", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('d8fddf4d-88f6-4f78-85d8-5e45a0f6c178', '2023-11-24 22:10:05.655988+00', '2023-11-24 22:10:05.655988+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "195.211.77.140", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('0c00a5f1-64ca-4620-a24c-00f7268d77cb', '2023-11-24 22:10:27.510665+00', '2023-11-24 22:10:27.510665+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "195.211.77.142", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('dc775034-6521-4051-8167-7bbeee6db6ce', '2023-11-24 22:11:21.341185+00', '2023-11-24 22:11:21.341185+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "198.44.140.136", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('9f751ff6-9c54-470d-8664-188751be8ee7', '2023-11-24 22:11:55.542854+00', '2023-11-24 22:11:55.542854+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "34.173.214.193", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('39e1228b-e1d8-4214-8c46-2407c7d02618', '2023-11-24 22:12:20.853957+00', '2023-11-24 22:12:20.853957+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "109.134.179.189", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('52088bfa-32dd-4d4b-a86b-a73dcdd59037', '2023-11-24 22:12:21.134694+00', '2023-11-24 22:12:21.134694+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "109.134.179.189", "deviceType": "unknown", "station_slug": ".git/config"}');
INSERT INTO public.analytics_events VALUES ('0848aa54-7011-4efa-b162-12283f455400', '2023-11-24 22:14:03.809757+00', '2023-11-24 22:14:03.809757+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "146.70.188.139", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('09563fd9-bfa1-4261-85e9-ddb73d596628', '2023-11-24 22:32:18.238072+00', '2023-11-24 22:32:18.238072+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "5.164.29.116", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('04191d7d-cd64-4712-ac5f-79e899338557', '2023-11-24 22:50:51.397429+00', '2023-11-24 22:50:51.397429+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.77", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('107b9b31-d702-450f-b1e8-537e2ca2c978', '2023-11-24 22:55:29.682537+00', '2023-11-24 22:55:29.682537+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.224", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('cc800c51-dc26-4d2b-8efe-0fb66c1ca182', '2023-11-24 23:17:36.147868+00', '2023-11-24 23:17:36.147868+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a01:7e01::f03c:93ff:fee5:7576", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('d9a3b912-6fbb-46e0-81aa-311b0269c796', '2023-11-25 00:58:36.408911+00', '2023-11-25 00:58:36.408911+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.93", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('590fe9bc-d3f5-4160-bab6-872bc7db35f7', '2023-11-25 01:09:56.91041+00', '2023-11-25 01:09:56.91041+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "34.254.53.125", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('d552f62d-18cf-4d16-843b-34b16ae6b975', '2023-11-25 01:09:57.30297+00', '2023-11-25 01:09:57.30297+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "34.254.53.125", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('993dda5a-209b-443e-a154-b39400c217d7', '2023-11-25 01:20:48.437109+00', '2023-11-25 01:20:48.437109+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.156", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('e4be7ae4-799d-4380-8ed6-bad902dfc6d6', '2023-11-25 02:51:43.751926+00', '2023-11-25 02:51:43.751926+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.55", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('857f524b-4762-4424-a5f7-98c4b267e2a8', '2023-11-25 04:00:00.057181+00', '2023-11-25 04:00:00.057181+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "195.211.77.140", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('f87f903f-c328-4945-bf86-edd4e18dcc3c', '2023-11-25 04:03:25.541487+00', '2023-11-25 04:03:25.541487+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "195.211.77.142", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('af8b9561-86b0-4cd2-91cd-f2b8b658c96c', '2023-11-25 04:27:10.868662+00', '2023-11-25 04:27:10.868662+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.42", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('8a34f489-960a-49ed-9249-5ebbd8401232', '2023-11-25 04:28:01.043388+00', '2023-11-25 04:28:01.043388+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "199.45.155.35", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('27c4f79d-2a2d-4fea-a581-883886de53c3', '2023-11-25 04:46:53.796615+00', '2023-11-25 04:46:53.796615+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.93", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('26c1343c-2da8-49bb-90be-8418733b988b', '2023-11-25 05:36:49.241045+00', '2023-11-25 05:36:49.241045+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "199.45.155.16", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('66eeb6b3-c411-4712-acce-cd02196300fd', '2023-11-25 06:11:33.863508+00', '2023-11-25 06:11:33.863508+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "199.45.154.17", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('56a3dbc4-bfd1-4b3d-bf2f-774bf773e149', '2023-11-25 06:38:13.763508+00', '2023-11-25 06:38:13.763508+00', 'share-event', '{"ref": "nfc", "params": {}, "clientIP": "79.118.23.210", "deviceType": "android", "station_slug": "aripi-spre-cer-instrumental"}');
INSERT INTO public.analytics_events VALUES ('03041aab-24f5-4cfc-851c-296f165bd38a', '2023-11-25 06:38:46.353841+00', '2023-11-25 06:38:46.353841+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.102", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('414db64f-5ec0-43d1-9f5c-da786b5c55a8', '2023-11-25 06:45:36.288382+00', '2023-11-25 06:45:36.288382+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.229", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('9084aeab-a3f3-4c03-a8ae-db9ae93b22a5', '2023-11-25 08:22:42.890425+00', '2023-11-25 08:22:42.890425+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.167", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('63ebb22c-fe24-42e4-8cd6-fba402ebf049', '2023-11-25 09:05:24.013249+00', '2023-11-25 09:05:24.013249+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "199.45.155.18", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('a46eddd6-1c82-4c1b-a660-baa3fca28021', '2023-11-25 10:14:03.999492+00', '2023-11-25 10:14:03.999492+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "47.88.6.178", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('dc6f9dd8-3069-4005-96f0-1645fb2c17e9', '2023-11-25 10:14:05.284577+00', '2023-11-25 10:14:05.284577+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "47.88.94.159", "deviceType": "android", "station_slug": "Public/home/js/check.js"}');
INSERT INTO public.analytics_events VALUES ('e920c75e-c04f-405e-8033-3afe5712ccf2', '2023-11-25 10:14:06.526607+00', '2023-11-25 10:14:06.526607+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "47.254.85.182", "deviceType": "android", "station_slug": "static/admin/javascript/hetong.js"}');
INSERT INTO public.analytics_events VALUES ('69385d83-b328-4576-9799-ce892e994674', '2023-11-25 10:14:26.810636+00', '2023-11-25 10:14:26.810636+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "47.88.78.6", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('5ce1eb08-287f-4791-86bc-0ec4839c34fb', '2023-11-25 10:14:28.075541+00', '2023-11-25 10:14:28.075541+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "47.88.6.178", "deviceType": "android", "station_slug": "Public/home/js/check.js"}');
INSERT INTO public.analytics_events VALUES ('d916b350-8a08-46ab-b67a-a596f723aea1', '2023-11-25 10:14:29.24776+00', '2023-11-25 10:14:29.24776+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "47.88.6.178", "deviceType": "android", "station_slug": "static/admin/javascript/hetong.js"}');
INSERT INTO public.analytics_events VALUES ('f277a2b3-514f-4305-b9a5-f649402d5e36', '2023-11-25 11:25:02.476568+00', '2023-11-25 11:25:02.476568+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.62", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('16e77e0f-ebb8-40c0-bc54-123e70fee8c0', '2023-11-25 11:57:06.227442+00', '2023-11-25 11:57:06.227442+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.220", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('3a2f9d03-1128-4bd4-92ed-0013529220c4', '2023-11-25 13:04:47.900839+00', '2023-11-25 13:04:47.900839+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "188.166.70.179", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('13ee6258-3892-474b-b6b6-cf38977f1104', '2023-11-25 13:04:48.040734+00', '2023-11-25 13:04:48.040734+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "188.166.70.179", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('633bef08-7b65-4e0e-87b4-9122be6006d9', '2023-11-25 13:47:35.556457+00', '2023-11-25 13:47:35.556457+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.217", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('1ce2d07e-bf79-4069-8ad7-b34f86215536', '2023-11-25 16:36:06.711094+00', '2023-11-25 16:36:06.711094+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.55", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('eec02da5-7afb-4bc8-afda-2b9b09809d54', '2023-11-25 17:39:07.264245+00', '2023-11-25 17:39:07.264245+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2400:8902::f03c:93ff:fe55:c48", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('0fdab114-cc5f-4654-b3d4-ce04b87b4630', '2023-11-25 17:39:14.870894+00', '2023-11-25 17:39:14.870894+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2400:8902::f03c:93ff:fe55:c48", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('8318952e-b5c9-4b47-9b9c-0d25a5aec1d2', '2023-11-25 17:43:56.724679+00', '2023-11-25 17:43:56.724679+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.154", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('525ca325-5fd3-47ee-a7cd-601982984f38', '2023-11-25 17:47:37.452966+00', '2023-11-25 17:47:37.452966+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.42", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('0b25d77f-8461-4c33-9802-c5fa7547e73f', '2023-11-25 17:55:25.369131+00', '2023-11-25 17:55:25.369131+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.64.170", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('07c68ae3-7122-4487-8371-3a0660272272', '2023-11-25 19:09:18.987821+00', '2023-11-25 19:09:18.987821+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.7", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('7ac41f52-3081-40bb-a1a5-e9b1c712e635', '2023-11-25 19:21:33.694369+00', '2023-11-25 19:21:33.694369+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "45.86.15.58", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('c9be400a-bf15-4a4b-a34e-6bf4dc7bca52', '2023-11-25 19:37:52.537318+00', '2023-11-25 19:37:52.537318+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "34.207.114.204", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('9fc2cf15-341f-445c-8364-49cf0ca2ef63', '2023-11-25 19:37:52.80118+00', '2023-11-25 19:37:52.80118+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "34.207.114.204", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('03147e8c-5188-43ac-a2ee-5e9bf3bbffb9', '2023-11-25 19:37:53.710049+00', '2023-11-25 19:37:53.710049+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "34.207.114.204", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('3bf6843a-fa42-44b3-adce-69fb7aafcb89', '2023-11-25 19:37:53.973149+00', '2023-11-25 19:37:53.973149+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "34.207.114.204", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('00e6a57c-c243-49ae-9ac7-93c83faeabb9', '2023-11-25 19:39:04.58606+00', '2023-11-25 19:39:04.58606+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "34.207.114.204", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('bce03993-1c39-43e7-8bb8-9d136b5f8ae8', '2023-11-25 19:39:04.864099+00', '2023-11-25 19:39:04.864099+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "34.207.114.204", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('3bc38181-3a88-42b7-97fc-0329cca42fed', '2023-11-25 22:07:32.029575+00', '2023-11-25 22:07:32.029575+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.42", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('40d6adca-1c2a-49f7-a8e8-71568ac07651', '2023-11-25 23:07:42.540172+00', '2023-11-25 23:07:42.540172+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.239", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('9d45aedb-0870-47c8-a8e4-ff5fa476a187', '2023-11-25 23:17:22.369757+00', '2023-11-25 23:17:22.369757+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2400:8902::f03c:93ff:febc:f711", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('7f51b742-a7b4-4733-911b-897b5d20b174', '2023-11-25 23:18:58.476476+00', '2023-11-25 23:18:58.476476+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.85", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('3262fb99-45ef-4d21-8695-0516734e68cb', '2023-11-25 23:55:58.253298+00', '2023-11-25 23:55:58.253298+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.137", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('1c105b55-7bc3-4f27-8d0f-f47db72f1507', '2023-11-26 00:57:01.447127+00', '2023-11-26 00:57:01.447127+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "199.45.155.35", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('864c1f41-ded7-4f9a-a811-27f195ccb6c2', '2023-11-26 01:27:05.203483+00', '2023-11-26 01:27:05.203483+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "199.45.155.17", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('b96f98e8-38ab-4044-a7a5-233e40700fd1', '2023-11-26 01:41:39.937482+00', '2023-11-26 01:41:39.937482+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "185.216.70.5", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('1fce01b4-977d-4270-b301-d60737271fbf', '2023-11-26 02:01:56.653881+00', '2023-11-26 02:01:56.653881+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.168", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('a6f046d0-b059-4ca1-8755-b649cbc57569', '2023-11-26 02:46:01.087174+00', '2023-11-26 02:46:01.087174+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "199.45.154.17", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('583160e4-11ee-4cce-b8ca-50c3b97fe02a', '2023-11-26 03:05:41.768091+00', '2023-11-26 03:05:41.768091+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "87.236.176.194", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('b9b3827e-5482-4e46-a609-a212f5b2b228', '2023-11-26 03:40:47.291935+00', '2023-11-26 03:40:47.291935+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "34.220.16.150", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('302b9785-f070-4312-857c-993d92886c60', '2023-11-26 04:01:17.605121+00', '2023-11-26 04:01:17.605121+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "199.45.155.17", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('2ff5f2fa-caed-4546-8939-d3ec56d310e3', '2023-11-26 10:49:40.187329+00', '2023-11-26 10:49:40.187329+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "157.245.202.27", "deviceType": "unknown", "station_slug": "wordpress/wp-admin/setup-config.php"}');
INSERT INTO public.analytics_events VALUES ('d07c294a-a78f-4fd5-a2bb-33da3173fbfc', '2023-11-26 14:44:00.305416+00', '2023-11-26 14:44:00.305416+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "157.245.106.254", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('d7570547-baa7-4fb0-9772-94882225d070', '2023-11-26 14:44:00.968662+00', '2023-11-26 14:44:00.968662+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "157.245.106.254", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('82d837fd-bb3e-4348-8376-139d73ee3403', '2023-11-26 16:39:06.002825+00', '2023-11-26 16:39:06.002825+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "34.220.16.150", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('21123ad1-6012-4948-9673-7d1cbe750953', '2023-11-26 17:15:11.623484+00', '2023-11-26 17:15:11.623484+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.42", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('70c8c828-9123-412e-9a11-78ba0d3d3846', '2023-11-26 17:25:20.13089+00', '2023-11-26 17:25:20.13089+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.138", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('73a23dc4-dd7f-424d-92ef-2077ddc9f9e5', '2023-11-26 17:34:09.389802+00', '2023-11-26 17:34:09.389802+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a01:7e00::f03c:93ff:fe4f:aa16", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('87acfc3d-620e-481e-8e7a-7c87b4caa130', '2023-11-26 17:34:19.711147+00', '2023-11-26 17:34:19.711147+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a01:7e00::f03c:93ff:fe4f:aa16", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('3c3556fa-74a3-4f02-8a52-df0678fc8443', '2023-11-26 18:03:09.663958+00', '2023-11-26 18:03:09.663958+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "183.129.153.157", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('2a8cc423-a04b-4a8b-b02c-7c74098c2cc9', '2023-11-26 19:36:49.633306+00', '2023-11-26 19:36:49.633306+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.136", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('15b47c55-9b6f-4647-a0f5-4b6a54bd62e7', '2023-11-26 19:49:53.040368+00', '2023-11-26 19:49:53.040368+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.41", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('d9988d40-f4d9-45b2-a926-35e67a0d84d2', '2023-11-26 20:03:12.83645+00', '2023-11-26 20:03:12.83645+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "139.59.95.146", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('325f7c4b-2357-4dab-b76c-c61823dd3b9f', '2023-11-26 20:03:13.5077+00', '2023-11-26 20:03:13.5077+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "139.59.95.146", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('cc78d42a-4abf-468d-9d3a-84c2f9496570', '2023-11-26 22:19:47.609287+00', '2023-11-26 22:19:47.609287+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "159.223.48.151", "deviceType": "unknown", "station_slug": "wordpress/wp-admin/setup-config.php"}');
INSERT INTO public.analytics_events VALUES ('eaaa1b33-8faf-453c-b303-b9bcd2df5695', '2023-11-26 23:16:42.817511+00', '2023-11-26 23:16:42.817511+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a01:7e01::f03c:93ff:fee5:7576", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('7e931952-ff4d-4cd2-a08a-3fdb4fe97bc7', '2023-11-27 01:47:41.525596+00', '2023-11-27 01:47:41.525596+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "3.143.245.163", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('4376a0ab-8ab0-4b7c-8e6e-04943662092b', '2023-11-27 03:23:02.867714+00', '2023-11-27 03:23:02.867714+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "183.129.153.157", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('8a995533-2078-426b-bc23-6e9afa3792f2', '2023-11-27 03:44:04.560306+00', '2023-11-27 03:44:04.560306+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "172.234.49.237", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('8353c944-51cd-4256-bf0d-860aea29d609', '2023-11-27 03:44:12.436584+00', '2023-11-27 03:44:12.436584+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "172.234.49.237", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('db8adc25-0183-4a00-ae71-f0079ce0ee34', '2023-11-27 04:14:14.519221+00', '2023-11-27 04:14:14.519221+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "3.143.245.163", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('c3b97452-10b8-41a3-ab5a-2057094b88b0', '2023-11-27 13:10:05.482268+00', '2023-11-27 13:10:05.482268+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "159.223.48.151", "deviceType": "unknown", "station_slug": "wordpress/wp-admin/setup-config.php"}');
INSERT INTO public.analytics_events VALUES ('7c4d4108-ba7c-4bc0-a20d-6737311f969d', '2023-11-27 15:49:36.16153+00', '2023-11-27 15:49:36.16153+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "188.165.87.101", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('911f4d19-a3a2-4d1a-8583-55de259efdb6', '2023-11-27 15:59:18.381156+00', '2023-11-27 15:59:18.381156+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "188.165.87.97", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('35cf4682-ab2e-49c6-8559-3ecd84ad1bc5', '2023-11-27 17:17:04.325274+00', '2023-11-27 17:17:04.325274+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.44", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('64487581-d7f4-44c6-84da-a113571dcf6e', '2023-11-27 17:18:19.476455+00', '2023-11-27 17:18:19.476455+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "51.254.49.109", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('e0fde0a6-b7d5-4e1b-a17c-d0bcdb526e46', '2023-11-27 17:27:53.665711+00', '2023-11-27 17:27:53.665711+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.134", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('f6094f3f-69ce-41a7-bb4b-fadbe0d29409', '2023-11-27 17:37:04.446893+00', '2023-11-27 17:37:04.446893+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a01:7e01::f03c:93ff:febc:34f6", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('112fba4f-295d-4775-9184-34275e1510ce', '2023-11-27 17:37:13.306041+00', '2023-11-27 17:37:13.306041+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a01:7e01::f03c:93ff:febc:34f6", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('b01c7808-aa37-4d40-8ebb-38f25dc8b33b', '2023-11-27 18:36:20.219939+00', '2023-11-27 18:36:20.219939+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.136", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('d2188947-866b-4032-8b98-8e329d742880', '2023-11-27 19:52:44.426203+00', '2023-11-27 19:52:44.426203+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.44", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('bd3d5b6e-f394-421b-8de4-32f23efaa784', '2023-11-27 21:27:31.661664+00', '2023-11-27 21:27:31.661664+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "79.118.23.210", "deviceType": "unknown", "station_slug": "aripi-spre-cer-popular"}');
INSERT INTO public.analytics_events VALUES ('4c84883d-f78b-43be-a02d-a255d99c74a8', '2023-11-27 23:19:11.685183+00', '2023-11-27 23:19:11.685183+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2600:3c00::f03c:93ff:fe55:c26", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('a83fd40a-8437-4eb6-b202-23b4544ef26f', '2023-11-28 06:44:57.188131+00', '2023-11-28 06:44:57.188131+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "45.79.26.146", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('0769f7f1-2761-4fe9-a5a5-142cfc668231', '2023-11-28 06:51:51.420275+00', '2023-11-28 06:51:51.420275+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "45.79.26.146", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('3fa58dd7-098b-4e7f-a373-9e9d8f78344a', '2023-11-28 17:16:27.351162+00', '2023-11-28 17:16:27.351162+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.65.71", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('556993c4-54fc-44ff-98b8-227b5695ef12', '2023-11-28 17:24:49.117838+00', '2023-11-28 17:24:49.117838+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.135", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('1033301b-6252-49f7-97e3-dd9eded33e5e', '2023-11-28 17:39:18.700622+00', '2023-11-28 17:39:18.700622+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2400:8904::f03c:93ff:febc:d954", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('86de0672-ac89-49cb-a70b-8401c1919921', '2023-11-28 17:39:32.304984+00', '2023-11-28 17:39:32.304984+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2400:8904::f03c:93ff:febc:d954", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('72fd11c3-cc1f-47b7-8f7b-166466e89e1b', '2023-11-28 19:13:51.908029+00', '2023-11-28 19:13:51.908029+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.138", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('42ff1a8f-1ed9-42e1-b6c3-f4fe1dbfdbd4', '2023-11-28 19:54:55.680979+00', '2023-11-28 19:54:55.680979+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.65.71", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('320dfa75-f510-4fbd-94d6-7a9a795e12fe', '2023-11-28 23:23:11.715649+00', '2023-11-28 23:23:11.715649+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2400:8904::f03c:93ff:fe55:c47", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('d1c1ee82-3701-4f55-900a-c233cefaf716', '2023-11-29 16:41:23.946546+00', '2023-11-29 16:41:23.946546+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.44", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('6b7bd611-1580-4b47-ab60-1123590dbb88', '2023-11-29 16:41:24.494707+00', '2023-11-29 16:41:24.494707+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.42", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('f96b4241-b6c8-44a3-9333-f2c74013942e', '2023-11-29 16:41:36.078495+00', '2023-11-29 16:41:36.078495+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.42", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('126888ca-3373-4e40-be33-88dbe13b64b4', '2023-11-29 16:41:36.329084+00', '2023-11-29 16:41:36.329084+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.42", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('c0e4153d-f0d4-4d40-9d03-0d7e410896c6', '2023-11-29 17:34:26.884225+00', '2023-11-29 17:34:26.884225+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2400:8902::f03c:93ff:fe55:c48", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('f2e3e55e-23bf-4fc9-86a6-4d7cdf5d818c', '2023-11-29 17:34:31.446007+00', '2023-11-29 17:34:31.446007+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2400:8902::f03c:93ff:fe55:c48", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('ce4c649b-e407-4fa2-a512-35cad5f6761f', '2023-11-29 17:42:12.919872+00', '2023-11-29 17:42:12.919872+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.79.105", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('478a805f-f561-4030-8284-0454acfc66b4', '2023-11-29 19:13:17.106489+00', '2023-11-29 19:13:17.106489+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.44", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('a2dd6e04-19ab-42a6-a49b-b39b0d026e27', '2023-11-29 20:14:13.276816+00', '2023-11-29 20:14:13.276816+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.79.106", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('0644a639-c6b3-44ac-b058-6e9837f03cb3', '2023-11-29 23:20:33.395552+00', '2023-11-29 23:20:33.395552+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2600:3c04::f03c:93ff:fe55:ce8", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('6d29810c-82f8-4749-bece-84b6d6c49354', '2023-11-30 04:30:20.72846+00', '2023-11-30 04:30:20.72846+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "15.237.215.110", "deviceType": "android", "station_slug": ".env.production.local"}');
INSERT INTO public.analytics_events VALUES ('1286dd80-7497-470a-8e84-618d0d4458e5', '2023-11-30 04:37:17.895274+00', '2023-11-30 04:37:17.895274+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:32ff:74::face:b00c", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('096e86bb-9097-4fdc-9287-c14cde359dcf', '2023-11-30 04:50:36.315744+00', '2023-11-30 04:50:36.315744+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:ff:e::face:b00c", "deviceType": "unknown", "station_slug": "images/android-chrome-512x512.png"}');
INSERT INTO public.analytics_events VALUES ('ebae9b26-77bc-4df0-b268-b4075f1e0b45', '2023-11-30 04:51:54.829495+00', '2023-11-30 04:51:54.829495+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2607:fb90:3393:d8:8dbe:eca8:caf0:b3a", "deviceType": "ios", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('65acff76-c25c-45c1-8776-1bc54b96d449', '2023-11-30 05:46:09.272872+00', '2023-11-30 05:46:09.272872+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "15.237.215.110", "deviceType": "unknown", "station_slug": ".env.production"}');
INSERT INTO public.analytics_events VALUES ('dfd5251e-bd9d-40b0-8d18-d0ac2abb4fd8', '2023-11-30 06:06:22.914381+00', '2023-11-30 06:06:22.914381+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "15.237.215.110", "deviceType": "desktop", "station_slug": ".git/config"}');
INSERT INTO public.analytics_events VALUES ('7cc81206-6636-47d9-a706-6e553be00653', '2023-11-30 07:19:27.122415+00', '2023-11-30 07:19:27.122415+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:31ff:3::face:b00c", "deviceType": "unknown", "station_slug": "images/android-chrome-512x512.png"}');
INSERT INTO public.analytics_events VALUES ('411a047d-c9e7-4341-a8ac-7e55e0a4bf7f', '2023-11-30 07:27:24.762729+00', '2023-11-30 07:27:24.762729+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "15.237.215.110", "deviceType": "desktop", "station_slug": "api/.env"}');
INSERT INTO public.analytics_events VALUES ('f3af1c51-b633-44fa-a5f4-3bc18ca44951', '2023-11-30 07:27:40.044194+00', '2023-11-30 07:27:40.044194+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "15.237.215.110", "deviceType": "desktop", "station_slug": ".env"}');
INSERT INTO public.analytics_events VALUES ('ca126b9a-3b24-4e18-8cbe-9d08932469d7', '2023-11-30 07:41:21.316278+00', '2023-11-30 07:41:21.316278+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "86.124.207.72", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('a50d07d4-0c03-4744-a889-f2392c6643e1', '2023-11-30 11:37:32.512466+00', '2023-11-30 11:37:32.512466+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "15.237.215.110", "deviceType": "unknown", "station_slug": ".env.production"}');
INSERT INTO public.analytics_events VALUES ('04d4c3da-56e8-4720-b256-09f13d4affaa', '2023-11-30 14:47:12.76365+00', '2023-11-30 14:47:12.76365+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "15.237.215.110", "deviceType": "unknown", "station_slug": ".env.production"}');
INSERT INTO public.analytics_events VALUES ('4fadfb52-8a59-4721-b15d-bb5e4932c170', '2023-11-30 16:21:19.944119+00', '2023-11-30 16:21:19.944119+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:ff:11::face:b00c", "deviceType": "unknown", "station_slug": "images/android-chrome-512x512.png"}');
INSERT INTO public.analytics_events VALUES ('230fa581-6022-44a7-9351-76292feca8c9', '2023-11-30 17:23:24.135175+00', '2023-11-30 17:23:24.135175+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.42", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('316bd260-9f7f-4ef0-b6c8-8e361da8a697', '2023-11-30 17:34:28.598643+00', '2023-11-30 17:34:28.598643+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.79.104", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('b6514669-28a8-4c42-88a8-1f20899e5936', '2023-11-30 17:37:41.866559+00', '2023-11-30 17:37:41.866559+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2400:8901::f03c:93ff:fe55:c31", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('c40b7b4b-9bed-4088-af1b-ac68b9e51f63', '2023-11-30 17:37:43.617774+00', '2023-11-30 17:37:43.617774+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2400:8901::f03c:93ff:fe55:c31", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('1c447d62-de16-4574-b0de-45acfd5f1039', '2023-11-30 17:48:57.93884+00', '2023-11-30 17:48:57.93884+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "15.237.215.110", "deviceType": "unknown", "station_slug": ".env.production.local"}');
INSERT INTO public.analytics_events VALUES ('e93adaad-1895-4703-b41c-9f01a230a3f0', '2023-11-30 18:58:31.876293+00', '2023-11-30 18:58:31.876293+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.41", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('f3c21168-4184-498c-8c5b-871130daead3', '2023-11-30 19:18:29.185433+00', '2023-11-30 19:18:29.185433+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "15.237.215.110", "deviceType": "desktop", "station_slug": "api/.env"}');
INSERT INTO public.analytics_events VALUES ('cdfe07c7-4361-485a-a321-b94cdc370c1d', '2023-11-30 19:55:25.106011+00', '2023-11-30 19:55:25.106011+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "15.237.215.110", "deviceType": "desktop", "station_slug": ".env.production.local"}');
INSERT INTO public.analytics_events VALUES ('202efebb-e02b-41cc-a75f-ac2d3e91e04e', '2023-11-30 22:57:29.633973+00', '2023-11-30 22:57:29.633973+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "198.235.24.212", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('c2003a58-da5c-4ae4-8a69-0bb79db12ed0', '2023-11-30 23:10:57.99533+00', '2023-11-30 23:10:57.99533+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "15.237.215.110", "deviceType": "android", "station_slug": ".env"}');
INSERT INTO public.analytics_events VALUES ('6a6e0ba2-4be7-47ec-916e-63f758572f07', '2023-11-30 23:17:22.547502+00', '2023-11-30 23:17:22.547502+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a01:7e01::f03c:93ff:fe55:cb6", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('3780e397-f5c1-4202-bd8e-06fe978b3595', '2023-11-30 23:47:50.69753+00', '2023-11-30 23:47:50.69753+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "15.237.215.110", "deviceType": "desktop", "station_slug": ".git/config"}');
INSERT INTO public.analytics_events VALUES ('31057b0b-1ef4-4d0f-ada6-8094c13ad704', '2023-12-01 00:37:30.104633+00', '2023-12-01 00:37:30.104633+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "198.235.24.79", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('e0187f95-0b44-4eeb-8684-1ec65efa1c7d', '2023-12-01 01:05:58.449301+00', '2023-12-01 01:05:58.449301+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "15.237.215.110", "deviceType": "desktop", "station_slug": "api/.env"}');
INSERT INTO public.analytics_events VALUES ('572e7a3c-cfe7-4938-9730-58a2aba81a90', '2023-12-01 01:22:54.117596+00', '2023-12-01 01:22:54.117596+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "15.237.215.110", "deviceType": "desktop", "station_slug": ".git/config"}');
INSERT INTO public.analytics_events VALUES ('6e522b28-2593-4a47-85df-fd5662e49a93', '2023-12-01 01:52:20.500682+00', '2023-12-01 01:52:20.500682+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "205.210.31.177", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('60a04f07-5b86-407a-ab7f-2a1b4a87215c', '2023-12-01 03:14:58.599325+00', '2023-12-01 03:14:58.599325+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "205.210.31.212", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('0c871687-08ab-4d65-8901-69b042d22b8b', '2023-12-01 06:32:29.698017+00', '2023-12-01 06:32:29.698017+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "205.210.31.212", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('83b101fb-f04c-4c3c-94be-fe7edf64aa2a', '2023-12-01 09:46:21.162382+00', '2023-12-01 09:46:21.162382+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a02:2f0d:b220:af00:b93d:72c6:4c5d:eabb", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('ee2ebf45-f934-43d9-a3e3-08d6c0051791', '2023-12-01 09:46:32.617141+00', '2023-12-01 09:46:32.617141+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a02:2f0d:b220:af00:b93d:72c6:4c5d:eabb", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('eeaf1b09-aeed-4a10-893c-54392dfd0d94', '2023-12-01 11:00:31.254595+00', '2023-12-01 11:00:31.254595+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a02:2f0d:b220:af00:b93d:72c6:4c5d:eabb", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('3ae22706-98e4-4d72-9eea-82e7a37ff192', '2023-12-01 12:26:32.12948+00', '2023-12-01 12:26:32.12948+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "205.210.31.42", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('f24d456b-6d21-4d15-b0ee-e7197323c595', '2023-12-01 13:58:44.095855+00', '2023-12-01 13:58:44.095855+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "205.210.31.248", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('b8338704-47ae-4ea3-870d-b24ee153bb51', '2023-12-01 15:23:28.077914+00', '2023-12-01 15:23:28.077914+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "213.233.85.107", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('bdc0ee22-ca96-4687-8e5a-f43533079435', '2023-12-01 16:51:33.506406+00', '2023-12-01 16:51:33.506406+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "198.235.24.203", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('2eeb7362-020d-4188-81d3-b2ee4a2a2c84', '2023-12-01 17:30:22.228769+00', '2023-12-01 17:30:22.228769+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.43", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('59cf9eaa-4d79-4674-ad41-ea42228acf52', '2023-12-01 17:40:57.01427+00', '2023-12-01 17:40:57.01427+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.79.96", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('c49a35cd-777a-48a7-b92c-8dd198e495f1', '2023-12-01 19:11:25.502052+00', '2023-12-01 19:11:25.502052+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.79.97", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('021f752f-570f-44ae-b521-71fd4886afaa', '2023-12-01 19:26:14.322617+00', '2023-12-01 19:26:14.322617+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "89.39.81.105", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('6ba20151-8425-43da-a790-d11d4f92be02', '2023-12-01 19:31:56.590734+00', '2023-12-01 19:31:56.590734+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a02:2f07:440a:7b00:5539:58cf:2cbe:f4c8", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('a4d94b76-1deb-43fe-a7a9-bbdcb650adcb', '2023-12-01 19:32:02.256212+00', '2023-12-01 19:32:02.256212+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "37.251.220.216", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('bb8b9cd1-e2ee-490c-92e6-914ab3197e29', '2023-12-01 19:40:13.116931+00', '2023-12-01 19:40:13.116931+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "205.210.31.51", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('b7b2f10f-a14f-44ca-be61-bf8dc38bed74', '2023-12-01 20:46:58.236182+00', '2023-12-01 20:46:58.236182+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.40", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('456ecaa6-28ab-40aa-85e8-e45164d9cad5', '2023-12-01 21:41:59.552325+00', '2023-12-01 21:41:59.552325+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "198.235.24.164", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('7f6febd4-1612-4585-b7e4-289f1c769786', '2023-12-01 23:34:00.525116+00', '2023-12-01 23:34:00.525116+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2400:8901::f03c:93ff:fe55:c31", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('426e27ed-ee82-4e64-91b8-496b3d92d453', '2023-12-02 02:40:46.509403+00', '2023-12-02 02:40:46.509403+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "198.235.24.85", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('867a30ed-4a2c-4b79-9fb2-c3a28b189a16', '2023-12-02 06:12:21.935827+00', '2023-12-02 06:12:21.935827+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "198.235.24.88", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('1758d6d0-bd45-4bc5-897c-b1e458b41682', '2023-12-02 07:02:41.76396+00', '2023-12-02 07:02:41.76396+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "198.235.24.60", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('4d91e8d7-cb01-49fd-808c-e6bd2d035b24', '2023-12-02 08:30:14.951878+00', '2023-12-02 08:30:14.951878+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "205.210.31.16", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('257bdb27-ab71-4096-902a-37c0a3718cac', '2023-12-02 09:58:09.987094+00', '2023-12-02 09:58:09.987094+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "205.210.31.203", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('4e618866-7814-4b23-800e-8b869fe0b031', '2023-12-02 13:53:41.656335+00', '2023-12-02 13:53:41.656335+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "205.210.31.34", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('13d73bdf-49f0-42a7-ba87-51e7953b593c', '2023-12-02 17:08:34.112178+00', '2023-12-02 17:08:34.112178+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.40", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('8f3fe54d-51ae-43ca-86a8-55b984a659bd', '2023-12-02 17:19:11.927371+00', '2023-12-02 17:19:11.927371+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.79.105", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('39de03ec-944e-4133-b10a-d5d35436a6c8', '2023-12-02 20:44:20.89909+00', '2023-12-02 20:44:20.89909+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.41", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('2f4efa72-e656-44ab-8b16-f7a55d584273', '2023-12-03 17:23:46.844966+00', '2023-12-03 17:23:46.844966+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.40", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('dab5ee4a-d9cd-4684-84d1-ebd308587bd5', '2023-12-03 17:31:32.055481+00', '2023-12-03 17:31:32.055481+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.74.69", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('733d33bc-1a4f-4209-8036-5394c16f905b', '2023-12-03 20:21:45.870091+00', '2023-12-03 20:21:45.870091+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.41", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('36956bb5-b1e1-4f43-b02b-7b28010ad347', '2023-12-03 22:25:30.707707+00', '2023-12-03 22:25:30.707707+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a0c:5a80:1006:fd00:69bb:f797:2dd2:182e", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('fab5f7f2-8cd3-4a92-b77f-306efe8abda7', '2023-12-04 05:11:56.622228+00', '2023-12-04 05:11:56.622228+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a02:a020:3d1:9920:4443:d9e8:43e8:4e3f", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('edd552d8-3ab9-4fc1-a107-0c1cca67f805', '2023-12-04 05:44:43.596717+00', '2023-12-04 05:44:43.596717+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "79.117.99.178", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('309caaf9-b754-4ebe-aa0c-8e037652d4d1', '2023-12-04 08:55:32.802657+00', '2023-12-04 08:55:32.802657+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "188.27.251.248", "deviceType": "desktop", "station_slug": "radio/aripi-spre-cer-special"}');
INSERT INTO public.analytics_events VALUES ('351f80e8-6e82-4232-8728-4897bd9794ec', '2023-12-04 14:57:18.73971+00', '2023-12-04 14:57:18.73971+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "52.214.133.190", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('b01769db-410c-49b5-ab99-e2a5c270eb77', '2023-12-04 17:11:30.229463+00', '2023-12-04 17:11:30.229463+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.40", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('d1427a22-f82b-445e-b142-f38650efbc9c', '2023-12-04 17:20:24.68178+00', '2023-12-04 17:20:24.68178+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.134", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('08d3ab1c-f85d-488d-837a-8e08968e2084', '2023-12-04 17:59:28.827078+00', '2023-12-04 17:59:28.827078+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "86.124.118.187", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('155b2fe7-d8aa-4e36-a772-6400079e3d51', '2023-12-04 18:00:39.706779+00', '2023-12-04 18:00:39.706779+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "86.124.114.187", "deviceType": "ios", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('3004787c-9458-4b41-9900-e5582332893e', '2023-12-04 18:37:49.265746+00', '2023-12-04 18:37:49.265746+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a02:2f08:8517:7f00:5298:9bd1:969b:2665", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('f296cd5b-721d-4f17-9bee-5629ac504d46', '2023-12-04 19:42:42.293625+00', '2023-12-04 19:42:42.293625+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.44", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('ed120527-3d9f-4853-bd2e-c3a56db2ca1e', '2023-12-04 19:54:03.689301+00', '2023-12-04 19:54:03.689301+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "54.170.73.188", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('5ba0a72d-a6cd-4743-8f8d-9d52cf549b08', '2023-12-04 21:10:12.638667+00', '2023-12-04 21:10:12.638667+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "198.235.24.104", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('9b9a5852-c8a5-47b4-aa96-a15a6c4c7031', '2023-12-04 21:51:41.728887+00', '2023-12-04 21:51:41.728887+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "188.27.251.248", "deviceType": "android", "station_slug": "rve-timisoara"}');
INSERT INTO public.analytics_events VALUES ('8e33a4c1-cccc-44e5-b237-6002adee6708', '2023-12-04 22:02:05.131653+00', '2023-12-04 22:02:05.131653+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:24ff:78::face:b00c", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('2ad0280e-1c92-4dd9-b581-d0a81c0253d0', '2023-12-04 22:02:09.798062+00', '2023-12-04 22:02:09.798062+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:24ff:1::face:b00c", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('84bcd75d-d461-4602-859a-5a1833b5c519', '2023-12-04 22:02:10.444027+00', '2023-12-04 22:02:10.444027+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:24ff:76::face:b00c", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('ffb2e84a-3d18-458a-9334-7417dac318bf', '2023-12-04 22:02:25.97255+00', '2023-12-04 22:02:25.97255+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:23ff:4::face:b00c", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('47dd5bdf-d2a0-4f96-bbff-315b554b0514', '2023-12-04 22:02:26.029538+00', '2023-12-04 22:02:26.029538+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:23ff:5::face:b00c", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('d40278fd-f751-4993-935d-34341af896db', '2023-12-04 22:03:24.166669+00', '2023-12-04 22:03:24.166669+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:10ff:76::face:b00c", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('b8ed9d70-373a-4d50-9b05-b00a3a176a15', '2023-12-04 22:03:24.650043+00', '2023-12-04 22:03:24.650043+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:10ff:5::face:b00c", "deviceType": "unknown", "station_slug": "_next/static/chunks/pages/_app-2075b67cb21d3c94.js"}');
INSERT INTO public.analytics_events VALUES ('21d8eed7-626a-4728-8cea-91e6dd9fbb7a', '2023-12-04 22:03:24.700389+00', '2023-12-04 22:03:24.700389+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:10ff:6::face:b00c", "deviceType": "unknown", "station_slug": "_next/static/Rz4wsQjhALLKzyFN0QcC_/_buildManifest.js"}');
INSERT INTO public.analytics_events VALUES ('d2bb55af-7a50-4f45-aa86-fdfc43d69dee', '2023-12-04 22:03:24.702499+00', '2023-12-04 22:03:24.702499+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:10ff:77::face:b00c", "deviceType": "unknown", "station_slug": "_next/static/Rz4wsQjhALLKzyFN0QcC_/_ssgManifest.js"}');
INSERT INTO public.analytics_events VALUES ('6b93940f-00f8-4228-acf5-386f972ea8bf', '2023-12-04 22:03:24.707411+00', '2023-12-04 22:03:24.707411+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:10ff:8::face:b00c", "deviceType": "unknown", "station_slug": "_next/static/chunks/framework-66d32731bdd20e83.js"}');
INSERT INTO public.analytics_events VALUES ('aeb8edcf-15aa-401e-88f9-6811cc28c203', '2023-12-04 22:03:24.795521+00', '2023-12-04 22:03:24.795521+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:10ff:f::face:b00c", "deviceType": "unknown", "station_slug": "_next/static/chunks/pages/index-40a1dde43172b504.js"}');
INSERT INTO public.analytics_events VALUES ('8951a4fc-f8c7-48e2-93f2-6bf67465a560', '2023-12-04 22:03:24.806259+00', '2023-12-04 22:03:24.806259+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:10ff:19::face:b00c", "deviceType": "unknown", "station_slug": "_next/static/chunks/353-ddf84ec05249ec1e.js"}');
INSERT INTO public.analytics_events VALUES ('2d25f3b3-c700-4227-b340-19c1f15bc1c1', '2023-12-04 22:03:24.810514+00', '2023-12-04 22:03:24.810514+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:10ff:77::face:b00c", "deviceType": "unknown", "station_slug": "_next/static/chunks/main-9a499b2922c09507.js"}');
INSERT INTO public.analytics_events VALUES ('afa738f8-dd58-4c68-bf23-607da6f6711c', '2023-12-04 22:03:24.820496+00', '2023-12-04 22:03:24.820496+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:10ff:18::face:b00c", "deviceType": "unknown", "station_slug": "_next/static/chunks/polyfills-c67a75d1b6f99dc8.js"}');
INSERT INTO public.analytics_events VALUES ('35e169e5-f7a3-4b37-a380-2b0190e39660', '2023-12-04 22:03:24.851087+00', '2023-12-04 22:03:24.851087+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:10ff:75::face:b00c", "deviceType": "unknown", "station_slug": "_next/static/chunks/872-c0ee675d24e5f635.js"}');
INSERT INTO public.analytics_events VALUES ('7078eb76-8017-4f16-ad33-906763e72486', '2023-12-04 22:03:24.93494+00', '2023-12-04 22:03:24.93494+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:10ff:18::face:b00c", "deviceType": "unknown", "station_slug": "_next/static/chunks/webpack-be19c08a5712c31d.js"}');
INSERT INTO public.analytics_events VALUES ('fb889fed-96ab-49dc-81a3-960d64c24484', '2023-12-04 22:03:24.152636+00', '2023-12-04 22:03:24.152636+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:10ff:14::face:b00c", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('988aee20-b1a8-4054-9c4f-66795fa51f1d', '2023-12-04 22:23:03.028857+00', '2023-12-04 22:23:03.028857+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "205.210.31.253", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('14841397-8f05-4e1f-9a10-7db8ce51d79d', '2023-12-04 22:39:01.881392+00', '2023-12-04 22:39:01.881392+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:22ff:1::face:b00c", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('118bf86b-5c1f-4b5b-8b89-605e2a9fa82f', '2023-12-04 22:39:02.017337+00', '2023-12-04 22:39:02.017337+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:30ff:78::face:b00c", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('20a7bd0f-1f8f-4889-bd07-b212276c6126', '2023-12-04 22:39:02.768822+00', '2023-12-04 22:39:02.768822+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:20ff:d::face:b00c", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('671a39a7-875f-497d-b86d-54e511f42486', '2023-12-04 23:10:44.720843+00', '2023-12-04 23:10:44.720843+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "198.235.24.78", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('3ecb4565-f324-4bd8-99ec-c3308d9ad41f', '2023-12-05 04:58:17.547056+00', '2023-12-05 04:58:17.547056+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "205.210.31.49", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('366f7458-a485-4593-975d-c2d6266ee376', '2023-12-05 08:24:07.740744+00', '2023-12-05 08:24:07.740744+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "104.234.204.32", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('5df60814-c2c8-42fc-9744-920b225ff7e7', '2023-12-05 08:28:41.727523+00', '2023-12-05 08:28:41.727523+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "104.234.204.32", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('83cc1c07-5d7b-455e-b6e9-03b4fb74a33f', '2023-12-05 08:28:41.774211+00', '2023-12-05 08:28:41.774211+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "104.234.204.32", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('66f08b91-5e18-4e2f-81c8-a8b6c279cf30', '2023-12-05 09:16:11.26778+00', '2023-12-05 09:16:11.26778+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "198.235.24.22", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('6b5d2ada-ab8e-4be6-92b8-e94db369b7f0', '2023-12-05 10:38:21.796067+00', '2023-12-05 10:38:21.796067+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "205.210.31.229", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('2843890b-915d-4f27-9f8b-6c46f38ceccb', '2023-12-05 11:51:15.271571+00', '2023-12-05 11:51:15.271571+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "205.210.31.67", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('1af546e6-3650-43e4-a2e9-420aad680fc8', '2023-12-05 12:31:55.683261+00', '2023-12-05 12:31:55.683261+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a03:2880:20ff:78::face:b00c", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('26361561-a74f-4048-991d-a7ce4b11c1e6', '2023-12-05 13:01:58.470839+00', '2023-12-05 13:01:58.470839+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "3.249.228.154", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('bf74aaa8-e044-4f0f-ae25-50f3ea2450cf', '2023-12-05 13:02:02.640663+00', '2023-12-05 13:02:02.640663+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "3.252.222.162", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('9529a7d5-d700-44ef-b970-f1df4129aeda', '2023-12-05 14:34:21.357361+00', '2023-12-05 14:34:21.357361+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a02:a58:81ab:b700:2cbe:b5fd:e455:8603", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('9e779f9a-bbbe-4d82-8f5d-ca5232656622', '2023-12-05 17:49:42.572963+00', '2023-12-05 17:49:42.572963+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.79.200", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('e077cdd0-22f6-411b-9c45-9d1880f23788', '2023-12-05 17:58:13.824879+00', '2023-12-05 17:58:13.824879+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.135", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('d0bb8ef6-618b-45a3-8daf-324636d1777d', '2023-12-05 22:16:22.244227+00', '2023-12-05 22:16:22.244227+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.79.202", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('45e0b13b-c82c-4ecb-9cc9-24ecabbc7d26', '2023-12-05 22:53:20.897871+00', '2023-12-05 22:53:20.897871+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "205.210.31.100", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('2d30d23f-fc4b-48b2-bb21-f9d44385d54e', '2023-12-06 04:21:06.85215+00', '2023-12-06 04:21:06.85215+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "205.210.31.104", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('470653a3-5ee3-45bb-9ba4-90215ce37e10', '2023-12-06 06:09:52.297261+00', '2023-12-06 06:09:52.297261+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "188.27.251.248", "deviceType": "ios", "station_slug": "aripi-spre-cer-popular"}');
INSERT INTO public.analytics_events VALUES ('a16176d8-3be9-418d-a2ea-d55c473a9e90', '2023-12-06 07:47:48.475527+00', '2023-12-06 07:47:48.475527+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "34.247.38.120", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('f712eefd-08c2-4fd8-8fa8-eb2f65ba0631', '2023-12-06 07:50:28.750032+00', '2023-12-06 07:50:28.750032+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "198.235.24.202", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('58859f2b-cf9c-47a0-96e1-4b4c4811e050', '2023-12-06 10:05:38.916942+00', '2023-12-06 10:05:38.916942+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "198.235.24.220", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('1d277c26-6602-4acd-8a10-aaf4f64a0898', '2023-12-06 13:53:28.447539+00', '2023-12-06 13:53:28.447539+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "198.235.24.125", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('e811ea2a-3a30-4248-bc98-96630feb2f11', '2023-12-06 15:42:59.476683+00', '2023-12-06 15:42:59.476683+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "198.235.24.72", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('d5a4ad26-caf3-4cc0-b641-e2388414f0d1', '2023-12-06 16:00:05.835518+00', '2023-12-06 16:00:05.835518+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "63.33.48.63", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('3e3d9cdf-8fab-46c2-95dc-e285685b7e06', '2023-12-06 17:01:07.030207+00', '2023-12-06 17:01:07.030207+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "188.27.251.248", "deviceType": "ios", "station_slug": "aripi-spre-cer-popular"}');
INSERT INTO public.analytics_events VALUES ('b63044e1-601c-4461-9d82-0d8d15df8aa1', '2023-12-06 17:33:30.193298+00', '2023-12-06 17:33:30.193298+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "205.210.31.43", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('293241f7-4298-4b12-a064-7ac4a07f7ee5', '2023-12-06 18:01:39.705032+00', '2023-12-06 18:01:39.705032+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.79.194", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('48996048-b86d-4bff-ba2e-9e850ab19385', '2023-12-06 18:14:13.43521+00', '2023-12-06 18:14:13.43521+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.137", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('ac144fd3-8ab4-4950-bb43-166d4857ff62', '2023-12-06 18:50:14.814733+00', '2023-12-06 18:50:14.814733+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "198.235.24.111", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('577cf5c1-69cf-4d16-9d34-8d201d7e2d99', '2023-12-06 19:49:05.649946+00', '2023-12-06 19:49:05.649946+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "5.14.139.178", "deviceType": "ios", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('5c70d4b2-4273-423c-b831-01d787d4dc81', '2023-12-06 19:49:50.769413+00', '2023-12-06 19:49:50.769413+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a04:241a:a702:c80:201c:d7a8:78f0:b367", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('05594960-8018-4c2a-8529-be272d5c0bdc', '2023-12-06 19:51:18.351532+00', '2023-12-06 19:51:18.351532+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "2a04:241a:a702:c80:201c:d7a8:78f0:b367", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('6c81d849-2152-4a06-9baa-db76fe9bcfb1', '2023-12-06 19:53:16.825219+00', '2023-12-06 19:53:16.825219+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "34.254.252.39", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('1932569c-4229-4ddd-9304-9e7b42041c30', '2023-12-07 05:51:51.721541+00', '2023-12-07 05:51:51.721541+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.79.197", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('86164d5c-04c7-4573-a3d1-5068ac3d9a62', '2023-12-07 06:09:42.330678+00', '2023-12-07 06:09:42.330678+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "3.249.8.202", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('9cd58dc8-b1a2-4119-a2e7-edd5aed520e7', '2023-12-07 06:09:42.605169+00', '2023-12-07 06:09:42.605169+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "3.252.70.101", "deviceType": "ios", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('7e7e40db-721a-4104-8a2e-dcf3ceefe9b4', '2023-12-07 17:12:59.540654+00', '2023-12-07 17:12:59.540654+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.65.163", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('63d3b784-54bc-4790-bec3-67a60810b6a6', '2023-12-07 17:20:59.29462+00', '2023-12-07 17:20:59.29462+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.134", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('7e7f2bbe-b12d-469b-af25-cc3e081c5d69', '2023-12-07 19:57:42.933174+00', '2023-12-07 19:57:42.933174+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.138", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('92f3ff63-0c18-4c35-a649-19efab173253', '2023-12-08 00:41:57.035162+00', '2023-12-08 00:41:57.035162+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "52.31.16.165", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('e563cc53-386b-4917-8a8b-93a2ab4fcc30', '2023-12-08 02:09:17.987019+00', '2023-12-08 02:09:17.987019+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "205.210.31.238", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('2e81ba0b-1ec6-48c5-aad4-2b9859d65bd8', '2023-12-08 04:24:13.30094+00', '2023-12-08 04:24:13.30094+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "34.243.241.25", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('d366f89e-b466-4b40-95c6-134784334150', '2023-12-08 04:45:54.930726+00', '2023-12-08 04:45:54.930726+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "34.248.152.94", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('6e54f082-8782-4495-94f2-77ce4eae3c7e', '2023-12-08 05:37:24.637473+00', '2023-12-08 05:37:24.637473+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "54.154.174.124", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('86360079-bbd2-46a7-acc8-c5a18b27b28b', '2023-12-08 05:37:24.935197+00', '2023-12-08 05:37:24.935197+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "34.249.224.160", "deviceType": "ios", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('f16daced-4cfa-4207-93b8-a1e4b4b802ba', '2023-12-08 07:54:27.664306+00', '2023-12-08 07:54:27.664306+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "198.235.24.95", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('1f655723-ef3d-4fa4-8cba-ba8813efe910', '2023-12-08 14:16:00.309301+00', '2023-12-08 14:16:00.309301+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "34.254.227.55", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('d6b3a6ea-7ecc-42a9-b651-9b2b6945ff91', '2023-12-08 15:13:49.726269+00', '2023-12-08 15:13:49.726269+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "205.210.31.10", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('25e27e94-f816-4960-80fc-b55e393cb00a', '2023-12-08 16:11:26.076154+00', '2023-12-08 16:11:26.076154+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "198.235.24.14", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('0479132e-1b92-4fe3-abcf-cad3017b411b', '2023-12-08 17:10:16.258711+00', '2023-12-08 17:10:16.258711+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "205.210.31.178", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('57ca7887-9a0f-41c4-8c71-42bc29dc5f80', '2023-12-08 17:22:04.68577+00', '2023-12-08 17:22:04.68577+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "63.32.58.134", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('07b3c2f8-90f6-4768-9051-05e44fd4b1c8', '2023-12-08 17:24:07.995417+00', '2023-12-08 17:24:07.995417+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.65.165", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('99c06e7c-74d2-4539-a2b2-277236527d8a', '2023-12-08 17:32:06.832246+00', '2023-12-08 17:32:06.832246+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.66.134", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('3e0cdb5f-3b98-472c-bde1-cbcac3dd5646', '2023-12-08 20:08:25.374655+00', '2023-12-08 20:08:25.374655+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "198.235.24.197", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('97c4cc24-ec13-4292-871f-e7e6d1d5cf68', '2023-12-08 20:21:46.373774+00', '2023-12-08 20:21:46.373774+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.65.166", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('6f4e2882-0dc7-4c63-b905-4036890e4a06', '2023-12-08 20:32:58.608565+00', '2023-12-08 20:32:58.608565+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "54.217.136.96", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('0ef3b36f-b249-4ec9-91c2-6978befb89ff', '2023-12-08 21:48:29.617456+00', '2023-12-08 21:48:29.617456+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "198.235.24.203", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('26dd6068-6c50-4110-b297-dd50f9be1836', '2023-12-08 22:16:38.657773+00', '2023-12-08 22:16:38.657773+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "205.210.31.107", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('2eb8c894-b037-4607-9c6b-b748cf81e000', '2023-12-08 22:40:55.404562+00', '2023-12-08 22:40:55.404562+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "54.72.17.198", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('81e0c34f-a83f-4765-9ccd-0b2d08fef7d1', '2023-12-09 00:31:12.52006+00', '2023-12-09 00:31:12.52006+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "13.52.213.112", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('ed99007f-93af-4d15-896a-2525018e6f05', '2023-12-09 00:44:57.298766+00', '2023-12-09 00:44:57.298766+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "205.210.31.60", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('389b7c15-5ee6-4a71-a828-65ec1c2063a3', '2023-12-09 01:19:01.556834+00', '2023-12-09 01:19:01.556834+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "198.235.24.37", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('42423371-90b8-44d2-8a77-19a47386ad2d', '2023-12-09 01:57:48.709024+00', '2023-12-09 01:57:48.709024+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.65.164", "deviceType": "unknown", "station_slug": "robots.txt"}');
INSERT INTO public.analytics_events VALUES ('8c3f4304-6891-4240-bb76-d8cf8e9697b2', '2023-12-09 01:57:50.079463+00', '2023-12-09 01:57:50.079463+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "66.249.65.165", "deviceType": "android", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('f350c29f-aa7a-42eb-a8aa-d699773774fe', '2023-12-09 05:35:32.271335+00', '2023-12-09 05:35:32.271335+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "13.52.184.181", "deviceType": "ios", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('b7047514-88cc-49db-ac87-1b572324f34e', '2023-12-09 07:44:36.399411+00', '2023-12-09 07:44:36.399411+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "134.209.197.119", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('fefa5ba4-48a9-437c-b428-18a9f48a8948', '2023-12-09 07:44:36.533899+00', '2023-12-09 07:44:36.533899+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "134.209.197.119", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('b74f85e9-9001-4ae9-9a00-1a9932389645', '2023-12-09 08:41:43.996621+00', '2023-12-09 08:41:43.996621+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "205.210.31.102", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('106fa423-c408-40c2-a034-d810be7e675f', '2023-12-09 10:15:25.614243+00', '2023-12-09 10:15:25.614243+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "205.210.31.252", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('54aefb65-5190-4a94-a391-c5998d9bd3d8', '2023-12-09 10:21:53.972193+00', '2023-12-09 10:21:53.972193+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "34.216.112.78", "deviceType": "desktop", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('fb4bacab-b237-43d8-9c2b-6fe93a1fe84f', '2023-12-09 12:37:46.272678+00', '2023-12-09 12:37:46.272678+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "198.235.24.73", "deviceType": "unknown", "station_slug": ""}');
INSERT INTO public.analytics_events VALUES ('76b5fb05-e413-47f3-b8cb-16c077e95161', '2023-12-09 14:44:49.084922+00', '2023-12-09 14:44:49.084922+00', 'share-event', '{"ref": "unknown", "params": {}, "clientIP": "198.235.24.46", "deviceType": "unknown", "station_slug": ""}');


--
-- Data for Name: auth_group; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- Data for Name: django_content_type; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.django_content_type VALUES (1, 'authentication', 'user');
INSERT INTO public.django_content_type VALUES (2, 'admin', 'logentry');
INSERT INTO public.django_content_type VALUES (3, 'auth', 'permission');
INSERT INTO public.django_content_type VALUES (4, 'auth', 'group');
INSERT INTO public.django_content_type VALUES (5, 'contenttypes', 'contenttype');
INSERT INTO public.django_content_type VALUES (6, 'sessions', 'session');
INSERT INTO public.django_content_type VALUES (7, 'guardian', 'groupobjectpermission');
INSERT INTO public.django_content_type VALUES (8, 'guardian', 'userobjectpermission');
INSERT INTO public.django_content_type VALUES (9, 'account', 'emailaddress');
INSERT INTO public.django_content_type VALUES (10, 'account', 'emailconfirmation');
INSERT INTO public.django_content_type VALUES (11, 'usersessions', 'usersession');
INSERT INTO public.django_content_type VALUES (12, 'socialaccount', 'socialaccount');
INSERT INTO public.django_content_type VALUES (13, 'socialaccount', 'socialapp');
INSERT INTO public.django_content_type VALUES (14, 'socialaccount', 'socialtoken');
INSERT INTO public.django_content_type VALUES (15, 'sms', 'smsverification');
INSERT INTO public.django_content_type VALUES (16, 'radio_crestin', 'stationsmetadatafetch');
INSERT INTO public.django_content_type VALUES (17, 'radio_crestin', 'stationsuptime');
INSERT INTO public.django_content_type VALUES (18, 'radio_crestin', 'stationtostationgroup');
INSERT INTO public.django_content_type VALUES (19, 'radio_crestin', 'stationsnowplaying');
INSERT INTO public.django_content_type VALUES (20, 'radio_crestin', 'posts');
INSERT INTO public.django_content_type VALUES (21, 'radio_crestin', 'stationgroups');
INSERT INTO public.django_content_type VALUES (22, 'radio_crestin', 'stationstreams');
INSERT INTO public.django_content_type VALUES (23, 'radio_crestin', 'stations');
INSERT INTO public.django_content_type VALUES (24, 'radio_crestin', 'stationmetadatafetchcategories');
INSERT INTO public.django_content_type VALUES (25, 'radio_crestin', 'songs');
INSERT INTO public.django_content_type VALUES (26, 'radio_crestin', 'artists');


--
-- Data for Name: auth_permission; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.auth_permission VALUES (1, 'Can add user', 1, 'add_user');
INSERT INTO public.auth_permission VALUES (2, 'Can change user', 1, 'change_user');
INSERT INTO public.auth_permission VALUES (3, 'Can delete user', 1, 'delete_user');
INSERT INTO public.auth_permission VALUES (4, 'Can view user', 1, 'view_user');
INSERT INTO public.auth_permission VALUES (5, 'Can view dashboard', 1, 'can_view_dashboard');
INSERT INTO public.auth_permission VALUES (6, 'Can view custom page', 1, 'can_view_custom_page');
INSERT INTO public.auth_permission VALUES (7, 'Is a normal user?', 1, 'is_normal_user');
INSERT INTO public.auth_permission VALUES (8, 'Can add log entry', 2, 'add_logentry');
INSERT INTO public.auth_permission VALUES (9, 'Can change log entry', 2, 'change_logentry');
INSERT INTO public.auth_permission VALUES (10, 'Can delete log entry', 2, 'delete_logentry');
INSERT INTO public.auth_permission VALUES (11, 'Can view log entry', 2, 'view_logentry');
INSERT INTO public.auth_permission VALUES (12, 'Can add permission', 3, 'add_permission');
INSERT INTO public.auth_permission VALUES (13, 'Can change permission', 3, 'change_permission');
INSERT INTO public.auth_permission VALUES (14, 'Can delete permission', 3, 'delete_permission');
INSERT INTO public.auth_permission VALUES (15, 'Can view permission', 3, 'view_permission');
INSERT INTO public.auth_permission VALUES (16, 'Can add group', 4, 'add_group');
INSERT INTO public.auth_permission VALUES (17, 'Can change group', 4, 'change_group');
INSERT INTO public.auth_permission VALUES (18, 'Can delete group', 4, 'delete_group');
INSERT INTO public.auth_permission VALUES (19, 'Can view group', 4, 'view_group');
INSERT INTO public.auth_permission VALUES (20, 'Can add content type', 5, 'add_contenttype');
INSERT INTO public.auth_permission VALUES (21, 'Can change content type', 5, 'change_contenttype');
INSERT INTO public.auth_permission VALUES (22, 'Can delete content type', 5, 'delete_contenttype');
INSERT INTO public.auth_permission VALUES (23, 'Can view content type', 5, 'view_contenttype');
INSERT INTO public.auth_permission VALUES (24, 'Can add session', 6, 'add_session');
INSERT INTO public.auth_permission VALUES (25, 'Can change session', 6, 'change_session');
INSERT INTO public.auth_permission VALUES (26, 'Can delete session', 6, 'delete_session');
INSERT INTO public.auth_permission VALUES (27, 'Can view session', 6, 'view_session');
INSERT INTO public.auth_permission VALUES (28, 'Can add group object permission', 7, 'add_groupobjectpermission');
INSERT INTO public.auth_permission VALUES (29, 'Can change group object permission', 7, 'change_groupobjectpermission');
INSERT INTO public.auth_permission VALUES (30, 'Can delete group object permission', 7, 'delete_groupobjectpermission');
INSERT INTO public.auth_permission VALUES (31, 'Can view group object permission', 7, 'view_groupobjectpermission');
INSERT INTO public.auth_permission VALUES (32, 'Can add user object permission', 8, 'add_userobjectpermission');
INSERT INTO public.auth_permission VALUES (33, 'Can change user object permission', 8, 'change_userobjectpermission');
INSERT INTO public.auth_permission VALUES (34, 'Can delete user object permission', 8, 'delete_userobjectpermission');
INSERT INTO public.auth_permission VALUES (35, 'Can view user object permission', 8, 'view_userobjectpermission');
INSERT INTO public.auth_permission VALUES (36, 'Can add email address', 9, 'add_emailaddress');
INSERT INTO public.auth_permission VALUES (37, 'Can change email address', 9, 'change_emailaddress');
INSERT INTO public.auth_permission VALUES (38, 'Can delete email address', 9, 'delete_emailaddress');
INSERT INTO public.auth_permission VALUES (39, 'Can view email address', 9, 'view_emailaddress');
INSERT INTO public.auth_permission VALUES (40, 'Can add email confirmation', 10, 'add_emailconfirmation');
INSERT INTO public.auth_permission VALUES (41, 'Can change email confirmation', 10, 'change_emailconfirmation');
INSERT INTO public.auth_permission VALUES (42, 'Can delete email confirmation', 10, 'delete_emailconfirmation');
INSERT INTO public.auth_permission VALUES (43, 'Can view email confirmation', 10, 'view_emailconfirmation');
INSERT INTO public.auth_permission VALUES (44, 'Can add user session', 11, 'add_usersession');
INSERT INTO public.auth_permission VALUES (45, 'Can change user session', 11, 'change_usersession');
INSERT INTO public.auth_permission VALUES (46, 'Can delete user session', 11, 'delete_usersession');
INSERT INTO public.auth_permission VALUES (47, 'Can view user session', 11, 'view_usersession');
INSERT INTO public.auth_permission VALUES (48, 'Can add social account', 12, 'add_socialaccount');
INSERT INTO public.auth_permission VALUES (49, 'Can change social account', 12, 'change_socialaccount');
INSERT INTO public.auth_permission VALUES (50, 'Can delete social account', 12, 'delete_socialaccount');
INSERT INTO public.auth_permission VALUES (51, 'Can view social account', 12, 'view_socialaccount');
INSERT INTO public.auth_permission VALUES (52, 'Can add social application', 13, 'add_socialapp');
INSERT INTO public.auth_permission VALUES (53, 'Can change social application', 13, 'change_socialapp');
INSERT INTO public.auth_permission VALUES (54, 'Can delete social application', 13, 'delete_socialapp');
INSERT INTO public.auth_permission VALUES (55, 'Can view social application', 13, 'view_socialapp');
INSERT INTO public.auth_permission VALUES (56, 'Can add social application token', 14, 'add_socialtoken');
INSERT INTO public.auth_permission VALUES (57, 'Can change social application token', 14, 'change_socialtoken');
INSERT INTO public.auth_permission VALUES (58, 'Can delete social application token', 14, 'delete_socialtoken');
INSERT INTO public.auth_permission VALUES (59, 'Can view social application token', 14, 'view_socialtoken');
INSERT INTO public.auth_permission VALUES (60, 'Can add sms verification', 15, 'add_smsverification');
INSERT INTO public.auth_permission VALUES (61, 'Can change sms verification', 15, 'change_smsverification');
INSERT INTO public.auth_permission VALUES (62, 'Can delete sms verification', 15, 'delete_smsverification');
INSERT INTO public.auth_permission VALUES (63, 'Can view sms verification', 15, 'view_smsverification');
INSERT INTO public.auth_permission VALUES (64, 'Can add Station Metadata Fetch', 16, 'add_stationsmetadatafetch');
INSERT INTO public.auth_permission VALUES (65, 'Can change Station Metadata Fetch', 16, 'change_stationsmetadatafetch');
INSERT INTO public.auth_permission VALUES (66, 'Can delete Station Metadata Fetch', 16, 'delete_stationsmetadatafetch');
INSERT INTO public.auth_permission VALUES (67, 'Can view Station Metadata Fetch', 16, 'view_stationsmetadatafetch');
INSERT INTO public.auth_permission VALUES (68, 'Can add Station Uptime', 17, 'add_stationsuptime');
INSERT INTO public.auth_permission VALUES (69, 'Can change Station Uptime', 17, 'change_stationsuptime');
INSERT INTO public.auth_permission VALUES (70, 'Can delete Station Uptime', 17, 'delete_stationsuptime');
INSERT INTO public.auth_permission VALUES (71, 'Can view Station Uptime', 17, 'view_stationsuptime');
INSERT INTO public.auth_permission VALUES (72, 'Can add Station to Group Relationship', 18, 'add_stationtostationgroup');
INSERT INTO public.auth_permission VALUES (73, 'Can change Station to Group Relationship', 18, 'change_stationtostationgroup');
INSERT INTO public.auth_permission VALUES (74, 'Can delete Station to Group Relationship', 18, 'delete_stationtostationgroup');
INSERT INTO public.auth_permission VALUES (75, 'Can view Station to Group Relationship', 18, 'view_stationtostationgroup');
INSERT INTO public.auth_permission VALUES (76, 'Can add Station Now Playing', 19, 'add_stationsnowplaying');
INSERT INTO public.auth_permission VALUES (77, 'Can change Station Now Playing', 19, 'change_stationsnowplaying');
INSERT INTO public.auth_permission VALUES (78, 'Can delete Station Now Playing', 19, 'delete_stationsnowplaying');
INSERT INTO public.auth_permission VALUES (79, 'Can view Station Now Playing', 19, 'view_stationsnowplaying');
INSERT INTO public.auth_permission VALUES (80, 'Can add Post', 20, 'add_posts');
INSERT INTO public.auth_permission VALUES (81, 'Can change Post', 20, 'change_posts');
INSERT INTO public.auth_permission VALUES (82, 'Can delete Post', 20, 'delete_posts');
INSERT INTO public.auth_permission VALUES (83, 'Can view Post', 20, 'view_posts');
INSERT INTO public.auth_permission VALUES (84, 'Can add Station Group', 21, 'add_stationgroups');
INSERT INTO public.auth_permission VALUES (85, 'Can change Station Group', 21, 'change_stationgroups');
INSERT INTO public.auth_permission VALUES (86, 'Can delete Station Group', 21, 'delete_stationgroups');
INSERT INTO public.auth_permission VALUES (87, 'Can view Station Group', 21, 'view_stationgroups');
INSERT INTO public.auth_permission VALUES (88, 'Can add Station Stream', 22, 'add_stationstreams');
INSERT INTO public.auth_permission VALUES (89, 'Can change Station Stream', 22, 'change_stationstreams');
INSERT INTO public.auth_permission VALUES (90, 'Can delete Station Stream', 22, 'delete_stationstreams');
INSERT INTO public.auth_permission VALUES (91, 'Can view Station Stream', 22, 'view_stationstreams');
INSERT INTO public.auth_permission VALUES (92, 'Can add Station', 23, 'add_stations');
INSERT INTO public.auth_permission VALUES (93, 'Can change Station', 23, 'change_stations');
INSERT INTO public.auth_permission VALUES (94, 'Can delete Station', 23, 'delete_stations');
INSERT INTO public.auth_permission VALUES (95, 'Can view Station', 23, 'view_stations');
INSERT INTO public.auth_permission VALUES (96, 'Can add Station Metadata Fetch Category', 24, 'add_stationmetadatafetchcategories');
INSERT INTO public.auth_permission VALUES (97, 'Can change Station Metadata Fetch Category', 24, 'change_stationmetadatafetchcategories');
INSERT INTO public.auth_permission VALUES (98, 'Can delete Station Metadata Fetch Category', 24, 'delete_stationmetadatafetchcategories');
INSERT INTO public.auth_permission VALUES (99, 'Can view Station Metadata Fetch Category', 24, 'view_stationmetadatafetchcategories');
INSERT INTO public.auth_permission VALUES (100, 'Can add Song', 25, 'add_songs');
INSERT INTO public.auth_permission VALUES (101, 'Can change Song', 25, 'change_songs');
INSERT INTO public.auth_permission VALUES (102, 'Can delete Song', 25, 'delete_songs');
INSERT INTO public.auth_permission VALUES (103, 'Can view Song', 25, 'view_songs');
INSERT INTO public.auth_permission VALUES (104, 'Can add Artist', 26, 'add_artists');
INSERT INTO public.auth_permission VALUES (105, 'Can change Artist', 26, 'change_artists');
INSERT INTO public.auth_permission VALUES (106, 'Can delete Artist', 26, 'delete_artists');
INSERT INTO public.auth_permission VALUES (107, 'Can view Artist', 26, 'view_artists');


--
-- Data for Name: auth_user; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.auth_user VALUES (5, 'pbkdf2_sha256$320000$TswMiBhkUtdv9tkGsBmywV$sm2VpHecn03sKfPhSluBcNZkxb2ZDszXSxRbgUYgGkI=', '2022-03-27 12:08:45.30935+00', true, 'dev', '', '', 'dev@radio-crestin.com', true, true, '2022-03-27 12:08:39.384377+00');
INSERT INTO public.auth_user VALUES (6, 'pbkdf2_sha256$320000$twpATY41RuexOGsUYQ57pJ$BZjw3YNDXVJnlyRWgsIlGVmQrm/hPxpZ4hfln7NOA/w=', '2025-04-27 18:26:45.717509+00', true, 'elisei', '', '', '', true, true, '2023-01-08 20:22:53+00');
INSERT INTO public.auth_user VALUES (1, 'pbkdf2_sha256$320000$eTnMRFoD0BxJlVDS0cq148$ifTlIpgiQQI2jU1v8PRFVPUJisH21ZYAFBVG3d2CiGg=', '2025-07-20 18:08:31.281625+00', true, 'iosif', '', '', 'iosifnicolae2@gmail.com', true, true, '2022-04-09 10:59:41.102501+00');


--
-- Data for Name: django_migrations; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.django_migrations VALUES (1, 'authentication', '0001_initial', '2025-07-20 12:12:42.069085+00');
INSERT INTO public.django_migrations VALUES (2, 'account', '0001_initial', '2025-07-20 12:12:42.10613+00');
INSERT INTO public.django_migrations VALUES (3, 'account', '0002_email_max_length', '2025-07-20 12:12:42.113994+00');
INSERT INTO public.django_migrations VALUES (4, 'account', '0003_alter_emailaddress_create_unique_verified_email', '2025-07-20 12:12:42.122823+00');
INSERT INTO public.django_migrations VALUES (5, 'account', '0004_alter_emailaddress_drop_unique_email', '2025-07-20 12:12:42.144224+00');
INSERT INTO public.django_migrations VALUES (6, 'account', '0005_emailaddress_idx_upper_email', '2025-07-20 12:12:42.302972+00');
INSERT INTO public.django_migrations VALUES (7, 'account', '0006_emailaddress_lower', '2025-07-20 12:12:42.308682+00');
INSERT INTO public.django_migrations VALUES (8, 'account', '0007_emailaddress_idx_email', '2025-07-20 12:12:42.318133+00');
INSERT INTO public.django_migrations VALUES (9, 'account', '0008_emailaddress_unique_primary_email_fixup', '2025-07-20 12:12:42.326269+00');
INSERT INTO public.django_migrations VALUES (10, 'account', '0009_emailaddress_unique_primary_email', '2025-07-20 12:12:42.33105+00');
INSERT INTO public.django_migrations VALUES (11, 'contenttypes', '0001_initial', '2025-07-20 12:12:42.340202+00');
INSERT INTO public.django_migrations VALUES (12, 'admin', '0001_initial', '2025-07-20 12:12:42.356271+00');
INSERT INTO public.django_migrations VALUES (13, 'admin', '0002_logentry_remove_auto_add', '2025-07-20 12:12:42.358953+00');
INSERT INTO public.django_migrations VALUES (14, 'admin', '0003_logentry_add_action_flag_choices', '2025-07-20 12:12:42.361772+00');
INSERT INTO public.django_migrations VALUES (15, 'contenttypes', '0002_remove_content_type_name', '2025-07-20 12:12:42.369378+00');
INSERT INTO public.django_migrations VALUES (16, 'auth', '0001_initial', '2025-07-20 12:12:42.398762+00');
INSERT INTO public.django_migrations VALUES (17, 'auth', '0002_alter_permission_name_max_length', '2025-07-20 12:12:42.402448+00');
INSERT INTO public.django_migrations VALUES (18, 'auth', '0003_alter_user_email_max_length', '2025-07-20 12:12:42.404759+00');
INSERT INTO public.django_migrations VALUES (19, 'auth', '0004_alter_user_username_opts', '2025-07-20 12:12:42.407241+00');
INSERT INTO public.django_migrations VALUES (20, 'auth', '0005_alter_user_last_login_null', '2025-07-20 12:12:42.409904+00');
INSERT INTO public.django_migrations VALUES (21, 'auth', '0006_require_contenttypes_0002', '2025-07-20 12:12:42.411222+00');
INSERT INTO public.django_migrations VALUES (22, 'auth', '0007_alter_validators_add_error_messages', '2025-07-20 12:12:42.414363+00');
INSERT INTO public.django_migrations VALUES (23, 'auth', '0008_alter_user_username_max_length', '2025-07-20 12:12:42.417381+00');
INSERT INTO public.django_migrations VALUES (24, 'auth', '0009_alter_user_last_name_max_length', '2025-07-20 12:12:42.421444+00');
INSERT INTO public.django_migrations VALUES (25, 'auth', '0010_alter_group_name_max_length', '2025-07-20 12:12:42.427876+00');
INSERT INTO public.django_migrations VALUES (26, 'auth', '0011_update_proxy_permissions', '2025-07-20 12:12:42.434735+00');
INSERT INTO public.django_migrations VALUES (27, 'auth', '0012_alter_user_first_name_max_length', '2025-07-20 12:12:42.437251+00');
INSERT INTO public.django_migrations VALUES (28, 'authentication', '0002_initial', '2025-07-20 12:12:42.52946+00');
INSERT INTO public.django_migrations VALUES (29, 'authentication', '0003_alter_user_is_staff', '2025-07-20 12:12:42.535546+00');
INSERT INTO public.django_migrations VALUES (30, 'authentication', '0004_alter_account_unique_together_remove_account_user_and_more', '2025-07-20 12:12:42.614264+00');
INSERT INTO public.django_migrations VALUES (31, 'authentication', '0005_user_checkout_phone_number', '2025-07-20 12:12:42.623198+00');
INSERT INTO public.django_migrations VALUES (32, 'authentication', '0006_alter_user_options_user_organization_users', '2025-07-20 12:12:42.626916+00');
INSERT INTO public.django_migrations VALUES (33, 'guardian', '0001_initial', '2025-07-20 12:12:42.668996+00');
INSERT INTO public.django_migrations VALUES (34, 'guardian', '0002_generic_permissions_index', '2025-07-20 12:12:42.680506+00');
INSERT INTO public.django_migrations VALUES (35, 'sessions', '0001_initial', '2025-07-20 12:12:42.691378+00');
INSERT INTO public.django_migrations VALUES (36, 'sms', '0001_initial', '2025-07-20 12:12:42.697697+00');
INSERT INTO public.django_migrations VALUES (37, 'sms', '0002_alter_smsverification_code', '2025-07-20 12:12:42.700913+00');
INSERT INTO public.django_migrations VALUES (38, 'sms', '0003_alter_smsverification_phone_number', '2025-07-20 12:12:42.703174+00');
INSERT INTO public.django_migrations VALUES (39, 'sms', '0004_alter_smsverification_code', '2025-07-20 12:12:42.705492+00');
INSERT INTO public.django_migrations VALUES (40, 'socialaccount', '0001_initial', '2025-07-20 12:12:42.747484+00');
INSERT INTO public.django_migrations VALUES (41, 'socialaccount', '0002_token_max_lengths', '2025-07-20 12:12:42.758529+00');
INSERT INTO public.django_migrations VALUES (42, 'socialaccount', '0003_extra_data_default_dict', '2025-07-20 12:12:42.763317+00');
INSERT INTO public.django_migrations VALUES (43, 'socialaccount', '0004_app_provider_id_settings', '2025-07-20 12:12:42.773711+00');
INSERT INTO public.django_migrations VALUES (44, 'socialaccount', '0005_socialtoken_nullable_app', '2025-07-20 12:12:42.786304+00');
INSERT INTO public.django_migrations VALUES (45, 'socialaccount', '0006_alter_socialaccount_extra_data', '2025-07-20 12:12:42.798153+00');
INSERT INTO public.django_migrations VALUES (46, 'usersessions', '0001_initial', '2025-07-20 12:12:42.818103+00');
INSERT INTO public.django_migrations VALUES (47, 'usersessions', '0002_alter_usersession_session_key', '2025-07-20 12:12:42.82438+00');
INSERT INTO public.django_migrations VALUES (48, 'usersessions', '0003_alter_usersession_session_key', '2025-07-20 12:12:42.831698+00');
INSERT INTO public.django_migrations VALUES (49, 'radio_crestin', '0001_initial', '2025-07-20 12:15:14.58204+00');


--
-- Data for Name: station_groups; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.station_groups VALUES (1, '2022-04-02 07:55:16.07407+00', '2022-05-08 11:10:04.775478+00', 'general', 'General', 1);
INSERT INTO public.station_groups VALUES (2, '2022-04-02 07:55:20.365557+00', '2022-05-08 11:10:04.775478+00', 'muzica', 'Muzica', 2);
INSERT INTO public.station_groups VALUES (3, '2022-04-02 07:55:25.63402+00', '2022-05-08 11:10:04.775478+00', 'popular', 'Popular', 3);
INSERT INTO public.station_groups VALUES (4, '2022-04-02 07:55:31.011557+00', '2022-05-08 11:10:04.775478+00', 'predici', 'Predici', 4);
INSERT INTO public.station_groups VALUES (5, '2022-04-02 07:55:39.703678+00', '2022-05-08 11:10:04.775478+00', 'worship', 'Worship', 5);
INSERT INTO public.station_groups VALUES (6, '2022-04-02 07:55:48.711458+00', '2022-05-08 11:10:04.775478+00', 'international', 'International', 6);
INSERT INTO public.station_groups VALUES (7, '2022-04-02 07:56:00.734657+00', '2022-05-08 11:10:04.775478+00', 'gospel', 'Gospel', 7);
INSERT INTO public.station_groups VALUES (8, '2022-04-02 07:56:07.424406+00', '2022-05-08 11:10:04.775478+00', 'instrumental', 'Instrumental', 8);
INSERT INTO public.station_groups VALUES (9, '2022-04-02 07:56:17.259241+00', '2022-05-08 11:10:04.775478+00', 'emisiuni', 'Emisiuni', 3);
INSERT INTO public.station_groups VALUES (11, '2022-04-02 08:06:06.399178+00', '2022-05-08 11:10:04.775478+00', 'copii', 'Copii', 9);
INSERT INTO public.station_groups VALUES (10, '2022-04-02 08:02:36.106494+00', '2022-05-08 11:10:04.775478+00', 'biblia', 'Biblia', 10);
INSERT INTO public.station_groups VALUES (12, '2022-05-09 17:17:26.176937+00', '2022-05-09 17:20:11.034869+00', 'radio', 'Toate', -1);
INSERT INTO public.station_groups VALUES (13, '2023-12-09 11:09:40.277164+00', '2023-12-09 11:09:40.277194+00', 'colinde', 'Colinde', 20);


--
-- Data for Name: station_metadata_fetch_categories; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.station_metadata_fetch_categories VALUES (1, '2022-04-02 07:37:08.292572+00', '2022-04-16 17:25:44.372853+00', 'shoutcast');
INSERT INTO public.station_metadata_fetch_categories VALUES (2, '2022-04-02 07:37:11.255456+00', '2022-04-16 17:25:44.372853+00', 'radio_co');
INSERT INTO public.station_metadata_fetch_categories VALUES (3, '2022-04-02 07:37:14.275764+00', '2022-04-16 17:25:44.372853+00', 'icecast');
INSERT INTO public.station_metadata_fetch_categories VALUES (4, '2022-04-02 07:37:18.755908+00', '2022-04-16 17:25:44.372853+00', 'shoutcast_xml');
INSERT INTO public.station_metadata_fetch_categories VALUES (5, '2022-04-02 07:37:22.00779+00', '2022-04-16 17:25:44.372853+00', 'old_icecast_html');
INSERT INTO public.station_metadata_fetch_categories VALUES (6, '2022-04-02 07:37:25.030252+00', '2022-04-16 17:25:44.372853+00', 'old_shoutcast_html');
INSERT INTO public.station_metadata_fetch_categories VALUES (7, '2022-04-02 07:37:25.030252+00', '2022-04-16 17:25:44.372853+00', 'aripisprecer_api');
INSERT INTO public.station_metadata_fetch_categories VALUES (8, '2023-12-09 10:19:42.745666+00', '2023-12-09 10:19:42.74569+00', 'radio_filadelfia_api');
INSERT INTO public.station_metadata_fetch_categories VALUES (9, '2023-12-09 10:30:13.925187+00', '2023-12-09 10:30:13.92523+00', 'sonicpanel');
INSERT INTO public.station_metadata_fetch_categories VALUES (10, '2023-12-09 12:43:09.672131+00', '2023-12-09 12:43:09.672152+00', 'stream_id3');


--
-- Name: auth_group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_group_id_seq', 1, false);


--
-- Name: auth_permission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_permission_id_seq', 68, true);


--
-- Name: auth_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_user_id_seq', 6, true);


--
-- Name: django_content_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.django_content_type_id_seq', 17, true);


--
-- Name: django_migrations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.django_migrations_id_seq', 18, true);


--
-- Name: group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.group_id_seq', 13, true);


--
-- Name: station_groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.station_groups_id_seq', 1, false);


--
-- Name: station_metadata_fetch_categories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.station_metadata_fetch_categories_id_seq', 1, false);


--
-- Name: station_metadata_fetch_category_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.station_metadata_fetch_category_id_seq', 10, true);


--
-- PostgreSQL database dump complete
--

