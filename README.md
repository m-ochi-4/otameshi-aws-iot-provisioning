
# AWS IoT デバイスプロビジョニング 実行サンプル

## 共通設定

```sh
AWS_CFN_PACKAGE_S3_BUCKET='[aws cloudformation packege コマンドの --s3-bucket に渡す S3 バケット名]'
export AWS_PROFILE='[AWS CLI のプロファイル名 (指定があれば)]'
export AWS_REGION='[AWS IoT Core を実行するリージョン名 (指定があれば)]'

AWS_ACCOUNT=$(aws sts get-caller-identity --query 'Account' --output text)
AWS_IOT_ENDPOINT_DATA_ATS=$(aws iot describe-endpoint --endpoint-type iot:Data-ATS --query 'endpointAddress' --output text)

WORK_ROOT=$(pwd)  # この README.md と同じディレクトリ
RESOURCE_DIR=${WORK_ROOT}/resource

AMAZON_ROOT_CA_CERT=${RESOURCE_DIR}/AmazonRootCA1.pem
curl https://www.amazontrust.com/repository/AmazonRootCA1.pem -o ${AMAZON_ROOT_CA_CERT}
```

## 実行サンプル

各サンプルは独立して実行可能です

- クレーム証明書によるフリートプロビジョニング -> [claim/claim.md](claim/claim.md)
- JITP (Just-in-Time Provisioning) -> [jitp/jitp.md](jitp/jitp.md)
- JITR (Just-in-Time Registration) -> [jitr/jitr.md](jitr/jitr.md)

## 参考リンク

["デバイスプロビジョニング - AWS IoT Core". https://docs.aws.amazon.com/ja_jp/iot/latest/developerguide/iot-provision.html](https://docs.aws.amazon.com/ja_jp/iot/latest/developerguide/iot-provision.html)

["3. デバイスのプロビジョニング". AWS IoT Device Management Workshop. https://catalog.us-east-1.prod.workshops.aws/workshops/7c2b04e7-8051-4c71-bc8b-6d2d7ce32727/ja-JP/provisioning-options](https://catalog.us-east-1.prod.workshops.aws/workshops/7c2b04e7-8051-4c71-bc8b-6d2d7ce32727/ja-JP/provisioning-options)
