"""collectstatic that skips static files already in S3 with the same content.

Django's collectstatic keeps a target only when it is newer than the source.
Every image build gives every source a new mtime, so each release deleted and
re-uploaded every file through the egress proxy (10-20 minutes, with 503s).
Against an S3 storage this lists the static prefix once and compares each
source's MD5 with the object's ETag (the MD5 of a single-part upload). An
equal file is left alone; a changed one is deleted and uploaded as before; a
new one is uploaded. Other storages keep Django's behaviour.

The storage app sits before django.contrib.staticfiles in INSTALLED_APPS, so
this command replaces Django's.
"""
import hashlib

from django.contrib.staticfiles.management.commands import collectstatic
from storages.backends.s3 import S3Storage
from storages.utils import clean_name


class Command(collectstatic.Command):
    _remote_etags = None

    def delete_file(self, path, prefixed_path, source_storage):
        if not isinstance(self.storage, S3Storage) or self.symlink:
            return super().delete_file(path, prefixed_path, source_storage)
        etag = self.remote_etags().get(self._key(prefixed_path))
        if etag is None:
            return True  # not in the bucket: upload it
        if etag == _md5(source_storage, path):
            if prefixed_path not in self.unmodified_files:
                self.unmodified_files.append(prefixed_path)
            self.log(f"Skipping '{path}' (content unchanged)")
            return False
        if self.dry_run:
            self.log(f"Pretending to delete '{path}'")
        else:
            self.log(f"Deleting '{path}'")
            self.storage.delete(prefixed_path)
        return True

    def remote_etags(self) -> dict:
        """{object key: ETag} under the static prefix, listed once."""
        if self._remote_etags is None:
            prefix = self._key('')
            self._remote_etags = {
                obj.key: obj.e_tag.strip('"')
                for obj in self.storage.bucket.objects.filter(Prefix=prefix)
            }
        return self._remote_etags

    def _key(self, name: str) -> str:
        return self.storage._normalize_name(clean_name(name))


def _md5(storage, path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with storage.open(path) as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()
