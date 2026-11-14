"""collectstatic against S3 uploads only what changed."""

import hashlib
import tempfile
from pathlib import Path
from types import SimpleNamespace

from django.core.files.storage import FileSystemStorage
from django.test import SimpleTestCase
from storages.backends.s3 import S3Storage

from superapp.apps.storage.management.commands.collectstatic import Command


def md5(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()


class FakeBucket:
    """The bucket's object listing, counting the LIST requests."""

    def __init__(self, objects):
        self.listed, self._objects = 0, objects
        self.objects = SimpleNamespace(filter=self._filter)

    def _filter(self, Prefix):
        self.listed += 1
        return [SimpleNamespace(key=key, e_tag=f'"{etag}"') for key, etag in self._objects.items()
                if key.startswith(Prefix)]


class FakeS3Storage(S3Storage):
    """S3Storage whose bucket is a stub; no HEAD, DELETE or PUT reaches a server."""

    def __init__(self, objects):
        super().__init__(location='static/', bucket_name='static-test', access_key='x', secret_key='x')
        self.fake_bucket, self.deleted, self.saved = FakeBucket(objects), [], []

    @property
    def bucket(self):
        return self.fake_bucket

    def exists(self, name):
        raise AssertionError('exists() costs a HEAD per file')

    def get_modified_time(self, name):
        raise AssertionError('get_modified_time() costs a HEAD per file')

    def delete(self, name):
        self.deleted.append(name)

    def save(self, name, content, max_length=None):
        self.saved.append(name)
        return name


class CollectstaticTests(SimpleTestCase):
    def setUp(self):
        self.source_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.source_dir.cleanup)
        files = {'admin/css/base.css': b'body {}', 'admin/js/app.js': b'new code', 'img/logo.png': b'\x89PNG'}
        for name, content in files.items():
            path = Path(self.source_dir.name, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        self.source = FileSystemStorage(location=self.source_dir.name)
        self.target = FakeS3Storage({
            'static/admin/css/base.css': md5(b'body {}'),        # same content
            'static/admin/js/app.js': md5(b'old code'),          # changed
            'static/other/kept.txt': md5(b'not in the sources'),  # left alone
        })

    def collect(self, dry_run=False):
        command = Command()
        command.storage, command.symlink, command.dry_run, command.verbosity = self.target, False, dry_run, 0
        command.local = False
        for name in ('admin/css/base.css', 'admin/js/app.js', 'img/logo.png'):
            command.copy_file(name, name, self.source)
        return command

    def test_only_changed_and_new_files_are_uploaded(self):
        command = self.collect()
        self.assertEqual(self.target.saved, ['admin/js/app.js', 'img/logo.png'])
        self.assertEqual(command.unmodified_files, ['admin/css/base.css'])

    def test_a_changed_file_is_deleted_before_its_upload_as_before(self):
        self.collect()
        self.assertEqual(self.target.deleted, ['admin/js/app.js'])

    def test_the_bucket_is_listed_once(self):
        self.collect()
        self.assertEqual(self.target.fake_bucket.listed, 1)

    def test_a_multipart_etag_never_matches_so_the_file_is_uploaded(self):
        self.target.fake_bucket._objects['static/admin/css/base.css'] = md5(b'body {}') + '-2'
        self.collect()
        self.assertIn('admin/css/base.css', self.target.saved)

    def test_dry_run_deletes_nothing(self):
        self.collect(dry_run=True)
        self.assertEqual(self.target.deleted, [])

    def test_other_storages_keep_djangos_behaviour(self):
        command = Command()
        command.storage = FileSystemStorage(location=tempfile.mkdtemp())
        command.symlink = command.dry_run = False
        command.verbosity, command.local = 0, True
        self.assertTrue(command.delete_file('img/logo.png', 'img/logo.png', self.source))

    def test_this_command_replaces_djangos(self):
        from django.core.management import get_commands
        self.assertEqual(get_commands()['collectstatic'], 'superapp.apps.storage')
