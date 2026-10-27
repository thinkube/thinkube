# Copyright Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

"""Content-MD5 on S3 batch deletes, for every S3 client the MLflow server makes.

MLflow deletes artifacts with S3's DeleteObjects. The JuiceFS S3 gateway in
front of MLflow's store requires a Content-MD5 header on that request, and
botocore sends a CRC32 checksum instead, with any of its checksum settings, so
the gateway answers MissingContentMD5 and no artifact can be deleted. Python
imports this module at start-up, as sitecustomize; it adds the header to
DeleteObjects on every S3 client botocore creates.
"""

import base64
import hashlib

import botocore.session

_create_client = botocore.session.Session.create_client


def _add_content_md5(params, **kwargs):
    body = params["body"]
    body = body if isinstance(body, bytes) else body.encode()
    params["headers"]["Content-MD5"] = base64.b64encode(hashlib.md5(body).digest()).decode()


def _create_client_with_md5(self, service_name, *args, **kwargs):
    client = _create_client(self, service_name, *args, **kwargs)
    if service_name == "s3":
        client.meta.events.register("before-call.s3.DeleteObjects", _add_content_md5)
    return client


botocore.session.Session.create_client = _create_client_with_md5
