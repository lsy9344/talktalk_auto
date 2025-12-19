from __future__ import annotations

import boto3

from .settings import get_settings


_CLIENTS: dict[str, object] = {}


def _client(service: str):
    settings = get_settings()
    key = f"{service}:{settings.aws_region}"
    if key not in _CLIENTS:
        _CLIENTS[key] = boto3.client(service, region_name=settings.aws_region)
    return _CLIENTS[key]


def dynamodb_resource():
    settings = get_settings()
    key = f"dynamodb-resource:{settings.aws_region}"
    if key not in _CLIENTS:
        _CLIENTS[key] = boto3.resource("dynamodb", region_name=settings.aws_region)
    return _CLIENTS[key]


def s3_client():
    return _client("s3")


def sqs_client():
    return _client("sqs")


def ssm_client():
    return _client("ssm")


def secrets_client():
    return _client("secretsmanager")
