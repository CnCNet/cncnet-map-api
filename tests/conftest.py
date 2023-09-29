import pytest
from django.test import Client


@pytest.fixture
def cnc_client(client) -> Client:
    return client
