
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from time import sleep
from typing import NamedTuple

from awscrt.mqtt5 import Client, PublishPacket, QoS
from awsiot import mqtt5, iotidentity, mqtt5_client_builder


class ClaimCertFleetProvisioningClient:

    def __init__(self,
            mqtt_client: Client,
            template_name: str,
            serial_number: str) -> None:

        id_client = iotidentity.IotIdentityClient(mqtt_client)

        req_subscribe_certificates_create = iotidentity.CreateKeysAndCertificateSubscriptionRequest()

        future_subscribe_to_create_keys_and_certificate_accepted, _ = id_client.subscribe_to_create_keys_and_certificate_accepted(
            request=req_subscribe_certificates_create,
            qos=mqtt5.QoS.AT_LEAST_ONCE,
            callback=self._on_certificates_create_accepted
        )
        future_subscribe_to_create_keys_and_certificate_rejected, _ = id_client.subscribe_to_create_keys_and_certificate_rejected(
            request=req_subscribe_certificates_create,
            qos=mqtt5.QoS.AT_LEAST_ONCE,
            callback=self._on_certificates_create_rejected
        )

        self._future_subscribe_to_create_keys_and_certificate_accepted = future_subscribe_to_create_keys_and_certificate_accepted
        self._future_subscribe_to_create_keys_and_certificate_rejected = future_subscribe_to_create_keys_and_certificate_rejected

        req_subscribe_register_thing = iotidentity.RegisterThingSubscriptionRequest(
            template_name=template_name
        )

        future_subscribe_to_register_thing_accepted, _ = id_client.subscribe_to_register_thing_accepted(
            request=req_subscribe_register_thing,
            qos=mqtt5.QoS.AT_LEAST_ONCE,
            callback=self._on_provisioning_templates_provision_accepted
        )
        future_subscribe_to_register_thing_rejected, _ = id_client.subscribe_to_register_thing_rejected(
            request=req_subscribe_register_thing,
            qos=mqtt5.QoS.AT_LEAST_ONCE,
            callback=self._on_provisioning_templates_provision_rejected
        )

        self._future_subscribe_to_register_thing_accepted = future_subscribe_to_register_thing_accepted
        self._future_subscribe_to_register_thing_rejected = future_subscribe_to_register_thing_rejected

        self._id_client = id_client
        self._template_name = template_name
        self._serial_number = serial_number

        self._finished = Event()
        self._error_response: iotidentity.ErrorResponse|None = None
        self._response_certificates_create: iotidentity.CreateKeysAndCertificateResponse|None = None
        self._response_provisioning_templates_provision: iotidentity.RegisterThingResponse|None = None

    @property
    def response_certificates_create(self) -> iotidentity.CreateKeysAndCertificateResponse:
        if self._response_certificates_create:
            return self._response_certificates_create
        raise RuntimeError()

    @property
    def response_provisioning_templates_provision(self) -> iotidentity.RegisterThingResponse:
        if self._response_provisioning_templates_provision:
            return self._response_provisioning_templates_provision
        raise RuntimeError()

    def _on_certificates_create_accepted(self, response: iotidentity.CreateKeysAndCertificateResponse) -> None:

        self._response_certificates_create = response

        req_register_thing = iotidentity.RegisterThingRequest(
            template_name=self._template_name,
            certificate_ownership_token=response.certificate_ownership_token,
            parameters={
                "SerialNumber": self._serial_number,
            }
        )

        future_publish_register_thing = self._id_client.publish_register_thing(
            request=req_register_thing,
            qos=mqtt5.QoS.AT_LEAST_ONCE,
        )

    def _on_certificates_create_rejected(self, response: iotidentity.ErrorResponse) -> None:
        self._error_response = response
        self._finished.set()

    def _on_provisioning_templates_provision_accepted(self, response: iotidentity.RegisterThingResponse) -> None:
        self._response_provisioning_templates_provision = response
        self._finished.set()

    def _on_provisioning_templates_provision_rejected(self, response: iotidentity.ErrorResponse) -> None:
        self._error_response = response
        self._finished.set()

    def wait_init(self, timeout: float) -> None:
        self._future_subscribe_to_create_keys_and_certificate_rejected.result(timeout)
        self._future_subscribe_to_create_keys_and_certificate_accepted.result(timeout)
        self._future_subscribe_to_register_thing_accepted.result(timeout)
        self._future_subscribe_to_register_thing_rejected.result(timeout)

    def start_provisioning(self):

        future_publish_create_keys_and_certificate = self._id_client.publish_create_keys_and_certificate(
            request=iotidentity.CreateKeysAndCertificateRequest(),
            qos=mqtt5.QoS.AT_LEAST_ONCE,
        )

    def wait_for_provisioned(self, timeout: float) -> iotidentity.ErrorResponse|None:

        self._finished.wait(timeout=timeout)

        if self._error_response:
            return self._error_response

        if not self._response_certificates_create or not self._response_provisioning_templates_provision:
            raise TimeoutError()

        return None


FILE_NAME_CERT_ID = 'certificate_id'
FILE_NAME_CERT = 'certificate.pem.crt'
FILE_NAME_PRI_KEY = 'private.pem.key'

FILE_NAME_THING_NAME = 'thing_name'
FILE_NAME_DEV_CONF = 'device_configuration.json'


class ThingConnInfo(NamedTuple):
    path_cert: Path
    path_pri_key: Path
    name: str
    config: dict


def fetch_thing_cert_and_pri_key(
        path_thing_key_dir: Path, thing_name_bare: str,
        path_claim_key_dir: Path, claim_client_id_prefix: str, template_name: str,
        endpoint: str, path_ca: Path, timeout: float) -> ThingConnInfo:

    path_thing_cert_id = Path(path_thing_key_dir, FILE_NAME_CERT_ID)
    path_thing_cert = Path(path_thing_key_dir, FILE_NAME_CERT)
    path_thing_pri_key = Path(path_thing_key_dir, FILE_NAME_PRI_KEY)
    path_thing_name = Path(path_thing_key_dir, FILE_NAME_THING_NAME)
    path_thing_conf = Path(path_thing_key_dir, FILE_NAME_DEV_CONF)

    if not path_thing_key_dir.is_dir():
        path_thing_key_dir.mkdir(parents=True)

    if any(not p.is_file() for p in (path_thing_cert, path_thing_pri_key, path_thing_cert_id, path_thing_name, path_thing_conf, )):

        path_claim_cert = Path(path_claim_key_dir, FILE_NAME_CERT)
        path_claim_pri_key = Path(path_claim_key_dir, FILE_NAME_PRI_KEY)
        claim_client_id = f"{claim_client_id_prefix}{thing_name_bare}"

        mqtt_client = mqtt5_client_builder.mtls_from_path(
            cert_filepath=path_claim_cert.as_posix(),
            pri_key_filepath=path_claim_pri_key.as_posix(),
            endpoint=endpoint,
            port=443,
            client_id=claim_client_id,
            on_publish_received=print,
            on_lifecycle_stopped=print,
            on_lifecycle_attempting_connect=print,
            on_lifecycle_connection_success=print,
            on_lifecycle_connection_failure=print,
            on_lifecycle_disconnection=print,
            ca_filepat=path_ca.as_posix()
        )
        mqtt_client.start()

        provisioning_client = ClaimCertFleetProvisioningClient(mqtt_client, template_name, thing_name_bare)
        provisioning_client.wait_init(timeout)
        provisioning_client.start_provisioning()
        if err := provisioning_client.wait_for_provisioned(timeout):
            print(err)
            raise Exception(err)

        mqtt_client.stop()

        response_certificates_create = provisioning_client.response_certificates_create
        response_provisioning_templates_provision = provisioning_client.response_provisioning_templates_provision

        path_thing_cert_id.write_text(response_certificates_create.certificate_id, encoding="ascii", newline="\n")  # pyright: ignore[reportArgumentType]
        path_thing_cert.write_text(response_certificates_create.certificate_pem, encoding="ascii", newline="\n")  # pyright: ignore[reportArgumentType]
        path_thing_pri_key.write_text(response_certificates_create.private_key, encoding="ascii", newline="\n")  # pyright: ignore[reportArgumentType]

        path_thing_name.write_text(response_provisioning_templates_provision.thing_name, encoding="utf-8", newline="\n")  # pyright: ignore[reportArgumentType]
        path_thing_conf.write_text(json.dumps(response_provisioning_templates_provision.device_configuration), encoding="utf-8", newline="\n")

    return ThingConnInfo(
        path_thing_cert,
        path_thing_pri_key,
        path_thing_name.read_text(),
        json.loads(path_thing_conf.read_bytes())
    )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--thing-key-dir", type=Path)
    parser.add_argument("--thing-name", type=str)
    parser.add_argument("--claim-key-dir", type=Path)
    parser.add_argument("--claim-client-id-prefix", type=str)
    parser.add_argument("--template", type=Path)
    parser.add_argument("--endpoint", type=str)
    parser.add_argument("--ca", type=Path)
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args()

    path_thing_key_dir: Path = args.thing_key_dir
    thing_name_bare = args.thing_name
    path_claim_key_dir: Path = args.claim_key_dir
    claim_client_id_prefix: str = args.claim_client_id_prefix
    template_name: str = args.template
    endpoint: str = args.endpoint
    path_ca: Path = args.ca
    timeout: float = args.timeout

    assert thing_name_bare
    assert path_claim_key_dir.is_dir()
    assert claim_client_id_prefix
    assert template_name
    assert "-ats.iot." in endpoint and endpoint.endswith(".amazonaws.com")
    assert path_ca.is_file()
    assert timeout > 0

    thing_conn_info = fetch_thing_cert_and_pri_key(
        path_thing_key_dir, thing_name_bare,
        path_claim_key_dir, claim_client_id_prefix, template_name,
        endpoint, path_ca, timeout
    )

    client_id = thing_conn_info.name
    mqtt_client = mqtt5_client_builder.mtls_from_path(
        cert_filepath=thing_conn_info.path_cert.as_posix(),
        pri_key_filepath=thing_conn_info.path_pri_key.as_posix(),
        endpoint=endpoint,
        port=443,
        client_id=client_id,
        on_publish_received=print,
        on_lifecycle_stopped=print,
        on_lifecycle_attempting_connect=print,
        on_lifecycle_connection_success=print,
        on_lifecycle_connection_failure=print,
        on_lifecycle_disconnection=print,
        ca_filepat=path_ca.as_posix(),
    )
    mqtt_client.start()

    count = 0

    while True:

        payload = json.dumps(
            {
                "published": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%:z"),
                "count": count,
            },
            separators=(",", ":"),
        )

        mqtt_client.publish(PublishPacket(
            payload=payload,
            qos=QoS.AT_LEAST_ONCE,  # pyright: ignore[reportArgumentType]
            topic=f"otameshi/aws-iot-provisioning/claim/{client_id}",
        ))

        count += 1

        sleep(1)


if __name__ == "__main__":
    main()
