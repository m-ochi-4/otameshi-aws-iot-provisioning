
# クレーム証明書によるフリートプロビジョニング

## 初期設定

```sh
WORK_DIR=${WORK_ROOT}/claim
cd ${WORK_DIR}

THING_NAME_BARE=TestThingClaim
```

## クレーム証明書 作成

```sh
CLAIM_KEY_DIR=${WORK_DIR}/.tmp/key/claim
mkdir -p ${CLAIM_KEY_DIR}

aws iot create-keys-and-certificate \
  --set-as-active \
  --certificate-pem-outfile ${CLAIM_KEY_DIR}/certificate.pem.crt \
  --public-key-outfile ${CLAIM_KEY_DIR}/public.pem.key \
  --private-key-outfile ${CLAIM_KEY_DIR}/private.pem.key \
  > ${CLAIM_KEY_DIR}/out.json

CLAIM_CERT_ID=$(cat ${CLAIM_KEY_DIR}/out.json | jq -r .certificateId)
```

## フリートプロビジョニング 関連リソース作成用 CFn 展開

```sh
CLAIM_CFN_STACK_NAME=otameshi-claim

aws cloudformation package \
  --template-file otameshi-claim.cfn.yml \
  --s3-bucket ${AWS_CFN_PACKAGE_S3_BUCKET} \
  --output-template-file .tmp/otameshi-claim.packaged.cfn.yml

aws cloudformation deploy \
  --template-file .tmp/otameshi-claim.packaged.cfn.yml \
  --stack-name ${CLAIM_CFN_STACK_NAME} \
  --parameter-override ClaimCertId=${CLAIM_CERT_ID} \
  --capabilities CAPABILITY_IAM
```

## 模擬クライアント実行

```sh
THINGS_KEY_DIR=${WORK_DIR}/.tmp/key/thing
THING_KEY_DIR=${THINGS_KEY_DIR}/${THING_NAME_BARE}

CLAIM_CLIENT_ID_PREFIX=$(aws cloudformation describe-stacks --stack-name ${CLAIM_CFN_STACK_NAME} | jq -r '.Stacks[0].Outputs[] | select(.OutputKey == "ClaimClientIdPrefix") | .OutputValue')
CLAIM_TEMPLATE_NAME=$(aws cloudformation describe-stacks --stack-name ${CLAIM_CFN_STACK_NAME} | jq -r '.Stacks[0].Outputs[] | select(.OutputKey == "TemplateName") | .OutputValue')

python client_claim.py \
  --thing-key-dir ${THING_KEY_DIR} \
  --thing-name ${THING_NAME_BARE} \
  --claim-key-dir ${CLAIM_KEY_DIR} \
  --claim-client-id-prefix ${CLAIM_CLIENT_ID_PREFIX} \
  --template ${CLAIM_TEMPLATE_NAME} \
  --endpoint ${AWS_IOT_ENDPOINT_DATA_ATS} \
  --ca ${AMAZON_ROOT_CA_CERT} \
  --timeout 10
```

### 実行成功時の出力

#### 初回

```text
LifecycleAttemptingConnectData()
LifecycleConnectSuccessData(connack_packet=ConnackPacket(session_present=False, reason_code=<ConnectReasonCode.SUCCESS: 0>, session_expiry_interval_sec=None, receive_maximum=100, maximum_qos=<QoS.AT_LEAST_ONCE: 1>, retain_available=True, maximum_packet_size=149504, assigned_client_identifier=None, topic_alias_maximum=8, reason_string=None, user_properties=None, wildcard_subscriptions_available=True, subscription_identifiers_available=False, shared_subscription_available=True, server_keep_alive_sec=1200, response_information=None, server_reference=None), negotiated_settings=NegotiatedSettings(maximum_qos=<QoS.AT_LEAST_ONCE: 1>, session_expiry_interval_sec=0, receive_maximum_from_server=100, maximum_packet_size_to_server=149504, topic_alias_maximum_to_server=8, topic_alias_maximum_to_client=0, server_keep_alive_sec=1200, retain_available=True, wildcard_subscriptions_available=True, subscription_identifiers_available=False, shared_subscriptions_available=True, rejoined_session=False, client_id='Claim_TestThingClaim'))
PublishReceivedData(publish_packet=PublishPacket(payload=b'{"certificateId":"82e613adb5ecbbd8921073d9e9dee236f6cb41e44c330abbe7d718e978fcbc7c","certificatePem":"-----BEGIN CERTIFICATE-----\\n[証明書]\\n-----END CERTIFICATE-----\\n","privateKey":"-----BEGIN RSA PRIVATE KEY-----\\n[秘密鍵]\\n-----END RSA PRIVATE KEY-----\\n","certificateOwnershipToken":"[証明書有効化用のトークン]"}', qos=<QoS.AT_LEAST_ONCE: 1>, retain=False, topic='$aws/certificates/create/json/accepted', payload_format_indicator=None, message_expiry_interval_sec=None, topic_alias=None, response_topic=None, correlation_data=None, subscription_identifiers=None, content_type=None, user_properties=None))
PublishReceivedData(publish_packet=PublishPacket(payload=b'{"deviceConfiguration":{},"thingName":"Fleet_Provisioned_TestThingClaim"}', qos=<QoS.AT_LEAST_ONCE: 1>, retain=False, topic='$aws/provisioning-templates/OtameshiClaimTemplate/provision/json/accepted', payload_format_indicator=None, message_expiry_interval_sec=None, topic_alias=None, response_topic=None, correlation_data=None, subscription_identifiers=None, content_type=None, user_properties=None))
LifecycleDisconnectData(disconnect_packet=None, exception=AwsCrtError(name='AWS_ERROR_MQTT5_USER_REQUESTED_STOP', message='Mqtt5 client connection interrupted by user request.', code=5153))
LifecycleStoppedData()
LifecycleAttemptingConnectData()
LifecycleConnectSuccessData(connack_packet=ConnackPacket(session_present=False, reason_code=<ConnectReasonCode.SUCCESS: 0>, session_expiry_interval_sec=None, receive_maximum=100, maximum_qos=<QoS.AT_LEAST_ONCE: 1>, retain_available=True, maximum_packet_size=149504, assigned_client_identifier=None, topic_alias_maximum=8, reason_string=None, user_properties=None, wildcard_subscriptions_available=True, subscription_identifiers_available=False, shared_subscription_available=True, server_keep_alive_sec=1200, response_information=None, server_reference=None), negotiated_settings=NegotiatedSettings(maximum_qos=<QoS.AT_LEAST_ONCE: 1>, session_expiry_interval_sec=0, receive_maximum_from_server=100, maximum_packet_size_to_server=149504, topic_alias_maximum_to_server=8, topic_alias_maximum_to_client=0, server_keep_alive_sec=1200, retain_available=True, wildcard_subscriptions_available=True, subscription_identifiers_available=False, shared_subscriptions_available=True, rejoined_session=False, client_id='Fleet_Provisioned_TestThingClaim'))
```

#### モノの証明書プロビジョニング成功後 2回目以降

```text
LifecycleAttemptingConnectData()
LifecycleConnectSuccessData(connack_packet=ConnackPacket(session_present=False, reason_code=<ConnectReasonCode.SUCCESS: 0>, session_expiry_interval_sec=None, receive_maximum=100, maximum_qos=<QoS.AT_LEAST_ONCE: 1>, retain_available=True, maximum_packet_size=149504, assigned_client_identifier=None, topic_alias_maximum=8, reason_string=None, user_properties=None, wildcard_subscriptions_available=True, subscription_identifiers_available=False, shared_subscription_available=True, server_keep_alive_sec=1200, response_information=None, server_reference=None), negotiated_settings=NegotiatedSettings(maximum_qos=<QoS.AT_LEAST_ONCE: 1>, session_expiry_interval_sec=0, receive_maximum_from_server=100, maximum_packet_size_to_server=149504, topic_alias_maximum_to_server=8, topic_alias_maximum_to_client=0, server_keep_alive_sec=1200, retain_available=True, wildcard_subscriptions_available=True, subscription_identifiers_available=False, shared_subscriptions_available=True, rejoined_session=False, client_id='Fleet_Provisioned_TestThingClaim'))
```

## 削除

### リソース削除用の変数

```sh
THING_NAME=$(cat ${THING_KEY_DIR}/thing_name)
THING_CERT_ID=$(cat ${THING_KEY_DIR}/certificate_id)
THING_CERT_ARN=arn:aws:iot:${AWS_REGION}:${AWS_ACCOUNT}:cert/${THING_CERT_ID}
THING_CERT_POLICY_NAME=$(aws cloudformation describe-stacks --stack-name ${CLAIM_CFN_STACK_NAME} | jq -r '.Stacks[0].Outputs[] | select(.OutputKey == "IoTPolicyNameProvisioned") | .OutputValue')
```

### モノ

```sh
aws iot detach-thing-principal --thing-name ${THING_NAME} --principal ${THING_CERT_ARN}
aws iot delete-thing --thing-name ${THING_NAME}
```

### モノの証明書

```sh
aws iot detach-policy --policy-name ${THING_CERT_POLICY_NAME} --target ${THING_CERT_ARN}
aws iot update-certificate --certificate-id ${THING_CERT_ID} --new-status INACTIVE
aws iot delete-certificate --certificate-id ${THING_CERT_ID}
```

### CFn スタック

```sh
aws cloudformation delete-stack --stack-name ${CLAIM_CFN_STACK_NAME}
aws cloudformation wait stack-delete-complete --stack-name ${CLAIM_CFN_STACK_NAME}
```

### クレーム証明書

```sh
aws iot update-certificate --certificate-id ${CLAIM_CERT_ID} --new-status INACTIVE
aws iot delete-certificate --certificate-id ${CLAIM_CERT_ID}
```
