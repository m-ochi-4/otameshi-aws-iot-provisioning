
import json
from os import environ

import boto3
from cryptography.x509 import load_pem_x509_certificate
from cryptography.x509.oid import NameOID


_CA_CERTIFICATE_ID = environ["CA_CERTIFICATE_ID"]
_THING_GROUP_NAME = environ["THING_GROUP_NAME"]
_THING_TYPE_NAME = environ["THING_TYPE_NAME"]

_iot_client = boto3.client("iot")


def lambda_handler(event, _):

    print(json.dumps(event, separators=(",", ":")))

    assert event["caCertificateId"] == _CA_CERTIFICATE_ID
    assert event["certificateStatus"] == "PENDING_ACTIVATION"

    certificate_id = event["certificateId"]

    cert_description = _iot_client.describe_certificate(certificateId=certificate_id)["certificateDescription"]
    cert_arn = cert_description["certificateArn"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
    cert_pem = cert_description["certificatePem"]  # pyright: ignore[reportTypedDictNotRequiredAccess]

    cert = load_pem_x509_certificate(cert_pem.encode("ascii"))
    cert_common_name = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value

    thing_name = f"{cert_common_name}"

    try:
        _iot_client.create_thing(thingName=thing_name, thingTypeName=_THING_TYPE_NAME)

    except _iot_client.exceptions.ResourceAlreadyExistsException:
        print(f"Thing already exists. {thing_name=}")

    _iot_client.add_thing_to_thing_group(thingGroupName=_THING_GROUP_NAME, thingName=thing_name)
    _iot_client.attach_thing_principal(thingName=thing_name, principal=cert_arn)
    _iot_client.update_certificate(certificateId=certificate_id, newStatus="ACTIVE")
