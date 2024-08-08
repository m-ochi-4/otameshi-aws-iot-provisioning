
# JITP (Just-in-Time Provisioning)

## 初期設定

```sh
WORK_DIR=${WORK_ROOT}/jitp
cd ${WORK_DIR}

ROOT_CA_NAME=OtameshiJITPRootCA
THING_NAME=OtameshiJITPThing
```

[resource/create_ca_and_client_cert.md](../resource/create_ca_and_client_cert.md) を参考に、プライベート CA と、模擬クライアントのクライアント証明書を作成

## CFn スタック展開

```sh
JITP_CFN_STACK_NAME=otameshi-jitp
aws cloudformation deploy --template-file otameshi-jitp.cfn.yml --stack-name ${JITP_CFN_STACK_NAME} --capabilities CAPABILITY_IAM
```

## IoT ポリシー と IoT グループ関連付け

```sh
JITP_IOT_POLICY_NAME=$(aws cloudformation describe-stacks --stack-name ${JITP_CFN_STACK_NAME} | jq -r '.Stacks[0].Outputs[] | select(.OutputKey == "IoTPolicyNameProvisioned") | .OutputValue')
JITP_THING_GROUP_ID=$(aws cloudformation describe-stacks --stack-name ${JITP_CFN_STACK_NAME} | jq -r '.Stacks[0].Outputs[] | select(.OutputKey == "IoTThingGroupIdProvisioned") | .OutputValue')
JITP_THING_GROUP_ARN=arn:aws:iot:${AWS_REGION}:${AWS_ACCOUNT}:thinggroup/${JITP_THING_GROUP_ID}
aws iot attach-policy --policy-name ${JITP_IOT_POLICY_NAME} --target ${JITP_THING_GROUP_ARN}
```

## CA へプロビジョニングテンプレート関連付け

```sh
JITP_TEMPLATE_NAME=$(aws cloudformation describe-stacks --stack-name ${JITP_CFN_STACK_NAME} | jq -r '.Stacks[0].Outputs[] | select(.OutputKey == "TemplateName") | .OutputValue')
aws iot update-ca-certificate \
  --certificate-id ${CA_CERT_ID} \
  --new-auto-registration-status ENABLE \
  --registration-config templateName=${JITP_TEMPLATE_NAME} \
  --no-remove-auto-registration
```

## 模擬クライアント実行

```sh
python ${RESOURCE_DIR}/client_jit.py \
  --endpoint ${AWS_IOT_ENDPOINT_DATA_ATS} \
  --cert ${THING_KEY_DIR}/${THING_NAME}.crt \
  --pri-key ${THING_KEY_DIR}/${THING_NAME}.pem \
  --ca ${AMAZON_ROOT_CA_CERT} \
  --client-id ${THING_NAME}
```

### 実行成功時の出力

```text
LifecycleAttemptingConnectData()
LifecycleConnectFailureData(connack_packet=None, exception=AwsCrtError(name='AWS_ERROR_MQTT_UNEXPECTED_HANGUP', message='The connection was closed unexpectedly.', code=5134))
LifecycleAttemptingConnectData()
LifecycleConnectSuccessData(connack_packet=ConnackPacket(session_present=False, reason_code=<ConnectReasonCode.SUCCESS: 0>, session_expiry_interval_sec=None, receive_maximum=100, maximum_qos=<QoS.AT_LEAST_ONCE: 1>, retain_available=True, maximum_packet_size=149504, assigned_client_identifier=None, topic_alias_maximum=8, reason_string=None, user_properties=None, wildcard_subscriptions_available=True, subscription_identifiers_available=False, shared_subscription_available=True, server_keep_alive_sec=1200, response_information=None, server_reference=None), negotiated_settings=NegotiatedSettings(maximum_qos=<QoS.AT_LEAST_ONCE: 1>, session_expiry_interval_sec=0, receive_maximum_from_server=100, maximum_packet_size_to_server=149504, topic_alias_maximum_to_server=8, topic_alias_maximum_to_client=0, server_keep_alive_sec=1200, retain_available=True, wildcard_subscriptions_available=True, subscription_identifiers_available=False, shared_subscriptions_available=True, rejoined_session=False, client_id='OtameshiJITPThing'))
```

## 削除

### モノ

```sh
aws iot detach-thing-principal --thing-name ${THING_NAME} --principal ${THING_CERT_ARN}
aws iot delete-thing --thing-name ${THING_NAME}
```

### モノの証明書

```sh
aws iot update-certificate --certificate-id ${THING_CERT_ID} --new-status INACTIVE
aws iot delete-certificate --certificate-id ${THING_CERT_ID}
```

### CFn スタック

```sh
aws iot update-ca-certificate --certificate-id ${CA_CERT_ID} --new-auto-registration-status DISABLE --remove-auto-registration
aws iot detach-policy --policy-name ${JITP_IOT_POLICY_NAME} --target ${JITP_THING_GROUP_ARN}
aws cloudformation delete-stack --stack-name ${JITP_CFN_STACK_NAME}
aws cloudformation wait stack-delete-complete --stack-name ${JITP_CFN_STACK_NAME}
```

### CA

```sh
aws iot update-ca-certificate \
  --certificate-id ${CA_CERT_ID} \
  --new-status INACTIVE \
  --new-auto-registration-status DISABLE \
  --remove-auto-registration
aws iot delete-ca-certificate --certificate-id ${CA_CERT_ID}
```
