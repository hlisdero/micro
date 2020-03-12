# micro
# Copyright (C) 2018 micro contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU
# Lesser General Public License as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License along with this program.
# If not, see <http://www.gnu.org/licenses/>.

# pylint: disable=missing-docstring; test module

from io import BytesIO
import os
from pathlib import Path
from tempfile import mkdtemp
from urllib.parse import urlsplit

from tornado.testing import AsyncTestCase, AsyncHTTPTestCase, gen_test
from tornado.web import Application, RequestHandler

from micro.error import CommunicationError
from micro.resource import (Analyzer, BrokenResourceError, Files, ForbiddenResourceError, Image,
                            NoResourceError, Resource)

from importlib import resources
import PIL
from . import RES_PATH

class AnalyzerTestCase(AsyncHTTPTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.analyzer = Analyzer(files=Files(mkdtemp()))

    def get_app(self) -> Application:
        return Application([(r'/codes/([^/]+)$', CodeEndpoint)], # type: ignore[misc]
                           static_path=os.path.join(os.path.dirname(__file__), 'res'))

    @gen_test # type: ignore[misc]
    async def test_analyze_blob(self) -> None:
        resource = await self.analyzer.analyze(self.get_url('/static/blob'))
        self.assertIsInstance(resource, Resource)
        self.assertRegex(resource.url, r'/static/blob$')
        self.assertEqual(resource.content_type, 'application/octet-stream')
        self.assertIsNone(resource.description)
        self.assertIsNone(resource.image)

    @gen_test # type: ignore[misc]
    async def test_analyze_image(self) -> None:
        # analyzer = Analyzer()
        # print('FILES', analyzer.files.path)
        # image = await analyzer.analyze(self.get_url('/static/image.svg'))
        image = await self.analyzer.analyze(self.get_url('/static/image.jpg'))
        self.assertIsInstance(image, Image)
        # self.assertEqual(image.content_type, 'image/svg+xml')
        self.assertEqual(image.content_type, 'image/jpeg')
        self.assertIsNone(image.description)
        # self.assertIsNone(image.image)
        assert image.image
        self.assertEqual(urlsplit(image.image.url).scheme, 'file')

    @gen_test # type: ignore[misc]
    async def test_analyze_webpage(self) -> None:
        # analyzer = Analyzer()
        webpage = await self.analyzer.analyze(self.get_url('/static/webpage.html'))
        self.assertIsInstance(webpage, Resource)
        self.assertEqual(webpage.content_type, 'text/html')
        self.assertEqual(webpage.description, 'Happy Blog')
        assert webpage.image
        # self.assertRegex(webpage.image.url, '/static/image.svg$')
        self.assertEqual(urlsplit(webpage.image.url).scheme, 'file')

    @gen_test # type: ignore[misc]
    async def test_analyze_file(self) -> None:
        assert self.analyzer.files
        url = await self.analyzer.files.write(b'Meow!', 'text/plain')
        resource = await self.analyzer.analyze(url)
        self.assertEqual(resource.url, url)
        self.assertEqual(resource.content_type, 'text/plain')

    @gen_test # type: ignore[misc]
    async def test_analyze_no_resource(self) -> None:
        with self.assertRaises(NoResourceError):
            await self.analyzer.analyze(self.get_url('/foo'))

    @gen_test # type: ignore[misc]
    async def test_analyze_forbidden_resource(self) -> None:
        with self.assertRaises(ForbiddenResourceError):
            await self.analyzer.analyze(self.get_url('/codes/403'))

    @gen_test # type: ignore[misc]
    async def test_analyze_resource_loop(self) -> None:
        # TODO
        # analyzer = Analyzer()
        with self.assertRaises(BrokenResourceError):
            await self.analyzer.analyze(self.get_url('/static/loop.html'))

    @gen_test # type: ignore[misc]
    async def test_analyze_error_response(self) -> None:
        with self.assertRaises(CommunicationError):
            await self.analyzer.analyze(self.get_url('/codes/500'))

    @gen_test # type: ignore[misc]
    async def test_analyze_no_host(self) -> None:
        with self.assertRaises(CommunicationError):
            await self.analyzer.analyze('https://example.invalid/')

    @gen_test # type: ignore[misc]
    async def test_process_image(self) -> None:
        # CC BY-SA Joaquim Alves Gaspar
        # (https://commons.wikimedia.org/wiki/File:Cat_August_2010-4.jpg)
        with open(Path(RES_PATH) / 'cat.jpg', 'rb') as f:
            data = f.read()
        image = await self.analyzer.process_image(data, 'image/jpeg')
        self.assertEqual(image.content_type, 'image/jpeg')
        self.assertIsNone(image.description)
        self.assertIsNone(image.image)
        assert self.analyzer.files
        data, _ = await self.analyzer.files.read(image.url)
        img = PIL.Image.open(BytesIO(data))
        self.assertEqual(img.size, (1177, 720))

    @gen_test # type: ignore[misc]
    async def test_process_image_broken(self) -> None:
        with self.assertRaisesRegex(BrokenResourceError, 'broken'):
            await self.analyzer.process_image(b'foo', 'image/jpeg')

class FilesTest(AsyncTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.files = Files(mkdtemp())

    @gen_test # type: ignore[misc]
    async def test_read(self) -> None:
        url = await self.files.write(b'Meow!', 'text/plain')
        data, content_type = await self.files.read(url)
        self.assertEqual(data, b'Meow!')
        self.assertEqual(content_type, 'text/plain')

    @gen_test # type: ignore[misc]
    async def test_read_no(self) -> None:
        with self.assertRaises(LookupError):
            await self.files.read('file:/foo.txt')

    @gen_test # type: ignore[misc]
    async def test_garbage_collect(self) -> None:
        urls = [await self.files.write(data, 'application/octet-stream')
                for data in (b'a', b'b', b'c', b'd')]
        n = await self.files.garbage_collect(urls[:2])
        self.assertEqual(n, 2)
        data, _ = await self.files.read(urls[0])
        self.assertEqual(data, b'a')
        data, _ = await self.files.read(urls[1])
        self.assertEqual(data, b'b')
        with self.assertRaises(LookupError):
            await self.files.read(urls[2])
        with self.assertRaises(LookupError):
            await self.files.read(urls[3])

class CodeEndpoint(RequestHandler):
    # pylint: disable=abstract-method; Tornado handlers define a semi-abstract data_received()

    def get(self, code: str) -> None:
        # pylint: disable=arguments-differ; Tornado handler arguments are defined by URLs
        self.set_status(int(code))
