
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from time import sleep

from awscrt.mqtt5 import PublishPacket, QoS
from awsiot import mqtt5_client_builder


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", type=str)
    parser.add_argument("--cert", type=Path)
    parser.add_argument("--pri-key", type=Path)
    parser.add_argument("--ca", type=Path)
    parser.add_argument("--client-id", type=str)
    args = parser.parse_args()

    endpoint: str = args.endpoint
    path_cert: Path = args.cert
    path_pri_key: Path = args.pri_key
    path_ca: Path = args.ca
    client_id: str = args.client_id

    assert "-ats.iot." in endpoint and endpoint.endswith(".amazonaws.com")
    assert path_cert.is_file() and path_pri_key.is_file() and path_ca.is_file()
    assert path_cert.stem == client_id and path_pri_key.stem == client_id

    mqtt_client = mqtt5_client_builder.mtls_from_path(
        cert_filepath=path_cert.as_posix(),
        pri_key_filepath=path_pri_key.as_posix(),
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
            topic=f"otameshi/aws-iot-provisioning/jit/{client_id}",
        ))

        count += 1

        sleep(1)


if __name__ == "__main__":
    main()
