"""client_ip believes forwarded headers only from trusted proxies."""

import os
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from ..utils import client_request
from ..utils.client_request import client_ip
from ..utils.rate_limits import over_limit

TRAEFIK = '10.42.3.17'
CLOUDFLARE_EDGE = '162.158.90.4'
CLIENT = '198.51.100.7'


def request(remote, **headers):
    return RequestFactory().get('/', REMOTE_ADDR=remote, **headers)


class ClientIpTests(SimpleTestCase):
    def test_a_direct_caller_is_its_own_address_whatever_it_sends(self):
        self.assertEqual(client_ip(request(
            '203.0.113.9', HTTP_CF_CONNECTING_IP='1.2.3.4', HTTP_X_REAL_IP='1.2.3.4', HTTP_X_FORWARDED_FOR='1.2.3.4',
        )), '203.0.113.9')

    def test_through_cloudflare_and_traefik_the_client_is_the_first_untrusted_hop(self):
        # The client sent its own X-Forwarded-For; Cloudflare appended the
        # real client and Traefik appended the Cloudflare edge.
        forwarded = f'1.2.3.4, {CLIENT}, {CLOUDFLARE_EDGE}'
        self.assertEqual(client_ip(request(TRAEFIK, HTTP_X_FORWARDED_FOR=forwarded,
                                           HTTP_CF_CONNECTING_IP='1.2.3.4')), CLIENT)

    def test_skipping_cloudflare_gets_the_address_traefik_saw(self):
        # Traefik replaces X-Forwarded-For from an untrusted peer with the peer.
        self.assertEqual(client_ip(request(TRAEFIK, HTTP_X_FORWARDED_FOR='203.0.113.9',
                                           HTTP_CF_CONNECTING_IP='1.2.3.4')), '203.0.113.9')

    def test_a_garbled_hop_stops_at_the_proxy(self):
        self.assertEqual(client_ip(request(TRAEFIK, HTTP_X_FORWARDED_FOR=f'{CLIENT}, not-an-ip')), TRAEFIK)

    def test_inside_the_cluster_without_forwarding_the_cf_header_is_read(self):
        self.assertEqual(client_ip(request('127.0.0.1', HTTP_CF_CONNECTING_IP=CLIENT)), CLIENT)
        self.assertEqual(client_ip(request(TRAEFIK)), TRAEFIK)

    def test_trusted_ranges_are_configurable(self):
        client_request._trusted_networks.cache_clear()
        try:
            with patch.dict(os.environ, {'TRUSTED_PROXY_CIDRS': '100.64.0.0/10'}):
                self.assertEqual(client_ip(request(TRAEFIK, HTTP_X_FORWARDED_FOR=CLIENT)), TRAEFIK)
                client_request._trusted_networks.cache_clear()
                self.assertEqual(client_ip(request('100.64.0.5', HTTP_X_FORWARDED_FOR=CLIENT)), CLIENT)
        finally:
            client_request._trusted_networks.cache_clear()


class OverLimitTests(SimpleTestCase):
    def test_a_caller_without_an_address_is_refused_not_pooled(self):
        self.assertTrue(over_limit(request(TRAEFIK), 'group', '', '1000/h'))
