import asyncio
import unittest

from aiodnsresolver import (
    Resolver,
    IPv4AddressExpiresAt,
)
from aiohttp import (
    web,
)

from lowhaio import (
    Pool,
    buffered,
)
from lowhaio_redirect import (
    HttpTooManyRedirects,
    redirectable,
)


def async_test(func):
    def wrapper(*args, **kwargs):
        future = func(*args, **kwargs)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(future)
    return wrapper


class TestIntegration(unittest.TestCase):

    def add_async_cleanup(self, coroutine, *args):
        loop = asyncio.get_event_loop()
        self.addCleanup(loop.run_until_complete, coroutine(*args))

    @async_test
    async def test_get_301(self):

        async def handle_get_a(_):
            return web.Response(
                status=301,
                headers={
                    'location': '/b'
                },
            )

        async def handle_get_b(_):
            return web.Response(body=b'def')

        app = web.Application()
        app.add_routes([
            web.get('/a', handle_get_a),
            web.get('/b', handle_get_b),
        ])
        runner = web.AppRunner(app)
        await runner.setup()
        self.add_async_cleanup(runner.cleanup)
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()

        request, close = Pool()
        self.add_async_cleanup(close)

        redirectable_request = redirectable(request)
        response_status, _, response_body = await redirectable_request(
            b'GET', 'http://localhost:8080/a',
        )
        response_body_buffered = await buffered(response_body)

        self.assertEqual(response_body_buffered, b'def')
        self.assertEqual(response_status, b'200')

    @async_test
    async def test_post_301(self):
        async def handle_post_a(_):
            return web.Response(
                status=301,
                headers={
                    'location': '/b'
                },
            )

        async def handle_get_b(_):
            return web.Response(body=b'def')

        app = web.Application()
        app.add_routes([
            web.post('/a', handle_post_a),
            web.get('/b', handle_get_b),
        ])
        runner = web.AppRunner(app)
        await runner.setup()
        self.add_async_cleanup(runner.cleanup)
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()

        request, close = Pool()
        self.add_async_cleanup(close)

        async def data():
            yield b'a'
            yield b'b'
            yield b'c'

        redirectable_request = redirectable(request)
        response_status, _, response_body = await redirectable_request(
            b'POST', 'http://localhost:8080/a',
            body=data,
            headers=((b'content-length', b'3'),),
        )
        response_body_buffered = await buffered(response_body)

        self.assertEqual(response_body_buffered, b'def')
        self.assertEqual(response_status, b'200')

    @async_test
    async def test_post_307(self):
        body_b = None

        async def handle_post_a(request):
            await request.content.read()
            return web.Response(
                status=307,
                headers={
                    'location': '/b'
                },
            )

        async def handle_post_b(request):
            nonlocal body_b
            body_b = await request.content.read()
            return web.Response(body=b'def')

        app = web.Application()
        app.add_routes([
            web.post('/a', handle_post_a),
            web.post('/b', handle_post_b),
        ])
        runner = web.AppRunner(app)
        await runner.setup()
        self.add_async_cleanup(runner.cleanup)
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()

        request, close = Pool()
        self.add_async_cleanup(close)

        async def data():
            yield b'a'
            yield b'b'
            yield b'c'

        redirectable_request = redirectable(request)
        response_status, _, response_body = await redirectable_request(
            b'POST', 'http://localhost:8080/a',
            headers=((b'content-length', b'3'),),
            body=data,
        )
        response_body_buffered = await buffered(response_body)

        self.assertEqual(body_b, b'abc')
        self.assertEqual(response_body_buffered, b'def')
        self.assertEqual(response_status, b'200')

    @async_test
    async def test_post_307_chain(self):
        body_c = None

        async def handle_post_a(request):
            await request.content.read()
            return web.Response(
                status=307,
                headers={
                    'location': '/b'
                },
            )

        async def handle_post_b(request):
            await request.content.read()
            return web.Response(
                status=307,
                headers={
                    'location': '/c'
                },
            )

        async def handle_post_c(request):
            nonlocal body_c
            body_c = await request.content.read()
            return web.Response(body=b'def')

        app = web.Application()
        app.add_routes([
            web.post('/a', handle_post_a),
            web.post('/b', handle_post_b),
            web.post('/c', handle_post_c),
        ])
        runner = web.AppRunner(app)
        await runner.setup()
        self.add_async_cleanup(runner.cleanup)
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()

        request, close = Pool()
        self.add_async_cleanup(close)

        async def data():
            yield b'a'
            yield b'b'
            yield b'c'

        redirectable_request = redirectable(request)
        response_status, _, response_body = await redirectable_request(
            b'POST', 'http://localhost:8080/a',
            headers=((b'content-length', b'3'),),
            body=data,
        )
        response_body_buffered = await buffered(response_body)

        self.assertEqual(body_c, b'abc')
        self.assertEqual(response_body_buffered, b'def')
        self.assertEqual(response_status, b'200')

    @async_test
    async def test_get_301_too_many_redirects(self):

        async def handle_get_a(_):
            return web.Response(
                status=301,
                headers={
                    'location': '/b'
                },
            )

        async def handle_get_b(_):
            return web.Response(
                status=301,
                headers={
                    'location': '/a'
                },
            )

        app = web.Application()
        app.add_routes([
            web.get('/a', handle_get_a),
            web.get('/b', handle_get_b),
        ])
        runner = web.AppRunner(app)
        await runner.setup()
        self.add_async_cleanup(runner.cleanup)
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()

        request, close = Pool()
        self.add_async_cleanup(close)

        redirectable_request = redirectable(request)
        with self.assertRaises(HttpTooManyRedirects):
            await redirectable_request(
                b'GET', 'http://localhost:8080/a',
            )

    @async_test
    async def test_get_301_same_domain_auth_preserved(self):
        auth_b = None

        async def handle_get_a(_):
            return web.Response(
                status=301,
                headers={
                    'location': '/b'
                },
            )

        async def handle_get_b(request):
            nonlocal auth_b
            auth_b = request.headers['authorization']
            return web.Response()

        app = web.Application()
        app.add_routes([
            web.get('/a', handle_get_a),
            web.get('/b', handle_get_b),
        ])
        runner = web.AppRunner(app)
        await runner.setup()
        self.add_async_cleanup(runner.cleanup)
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()

        request, close = Pool()
        self.add_async_cleanup(close)

        redirectable_request = redirectable(request)
        _, _, body = await redirectable_request(
            b'GET', 'http://localhost:8080/a',
            headers=((b'Authorization', b'the-key'),)
        )
        await buffered(body)
        self.assertEqual(auth_b, 'the-key')

    @async_test
    async def test_get_301_different_domain_auth_lost(self):
        auth_b = None

        async def handle_get_a(_):
            return web.Response(
                status=301,
                headers={
                    'location': 'http://anotherhost.com:8080/b'
                },
            )

        async def handle_get_b(request):
            nonlocal auth_b
            auth_b = request.headers.get('authorization', None)
            return web.Response(body=b'def')

        app = web.Application()
        app.add_routes([
            web.get('/a', handle_get_a),
            web.get('/b', handle_get_b),
        ])
        runner = web.AppRunner(app)
        await runner.setup()
        self.add_async_cleanup(runner.cleanup)
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()

        def get_dns_resolver():
            async def get_host(_, __, ___):
                return IPv4AddressExpiresAt('127.0.0.1', expires_at=0)
            return Resolver(
                get_host=get_host,
            )

        request, close = Pool(get_dns_resolver=get_dns_resolver)
        self.add_async_cleanup(close)

        redirectable_request = redirectable(request)
        _, _, body = await redirectable_request(
            b'GET', 'http://localhost:8080/a',
            headers=((b'authorization', b'the-key'),)
        )
        response = await buffered(body)
        self.assertEqual(auth_b, None)
        self.assertEqual(response, b'def')
