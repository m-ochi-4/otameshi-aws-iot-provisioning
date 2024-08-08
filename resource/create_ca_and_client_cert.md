
# AWS IoT Core 向け プライベート CA とクライアント証明書作成

## プライベート CA

### ルート CA 作成

```sh
ROOT_CA_DIR=${WORK_DIR}/.tmp/ca/root/${ROOT_CA_NAME}
mkdir -p ${ROOT_CA_DIR}

cd ${ROOT_CA_DIR}

cp ${RESOURCE_DIR}/sample_root_ca.cnf ./${ROOT_CA_NAME}.cnf
sed -i s/'${ROOT_CA_NAME}'/${ROOT_CA_NAME}/g ./${ROOT_CA_NAME}.cnf

mkdir certs db private
chmod 700 private
touch db/index
openssl rand -hex 16 > db/serial
echo 1001 > db/crlnumber

openssl req -nodes -new -config ${ROOT_CA_NAME}.cnf -out ${ROOT_CA_NAME}.csr -keyout private/${ROOT_CA_NAME}.pem
openssl ca -selfsign -config ${ROOT_CA_NAME}.cnf -in ${ROOT_CA_NAME}.csr -out ${ROOT_CA_NAME}.crt -extensions ca_ext
```

### AWS IoT 検証証明書 (DEFAULT モード使用時のみ実行)

```sh
AWS_IOT_REGISTRATION_CODE=$(aws iot get-registration-code | jq -r .registrationCode)

cp ${RESOURCE_DIR}/sample_verification.cnf ./verification.cnf
sed -i s/'${AWS_IOT_REGISTRATION_CODE}'/${AWS_IOT_REGISTRATION_CODE}/g ./verification.cnf

openssl req -nodes -new -config verification.cnf -out verification.csr -newkey rsa:2048 -keyout private/verification.pem
openssl ca -config ${ROOT_CA_NAME}.cnf -in verification.csr -out verification.crt
```

### AWS IoT に CA 登録

#### DEFAULT モードで登録

```sh
aws iot register-ca-certificate --ca-certificate file://${ROOT_CA_DIR}/${ROOT_CA_NAME}.crt --verification-cert file://./verification.crt > register-ca-certificate_${AWS_REGION}_${AWS_PROFILE}.json
```

#### SNI_ONLY モードで登録

```sh
aws iot register-ca-certificate --ca-certificate file://${ROOT_CA_DIR}/${ROOT_CA_NAME}.crt --certificate-mode SNI_ONLY > register-ca-certificate_${AWS_REGION}_${AWS_PROFILE}.json
```

#### 登録確認と有効化

```sh
CA_CERT_ID=$(cat register-ca-certificate_${AWS_REGION}_${AWS_PROFILE}.json | jq -r .certificateId)
aws iot describe-ca-certificate --certificate-id ${CA_CERT_ID}
aws iot update-ca-certificate --certificate-id ${CA_CERT_ID} --new-status ACTIVE
```

## AWS IoT Core モノのクライアント証明書

```sh
THING_KEY_DIR=${WORK_DIR}/.tmp/ca/user/${THING_NAME}
mkdir -p ${THING_KEY_DIR}

cp ${RESOURCE_DIR}/sample_user.cnf ${THING_KEY_DIR}/${THING_NAME}.cnf
sed -i s/'${THING_NAME}'/${THING_NAME}/g ${THING_KEY_DIR}/${THING_NAME}.cnf

openssl req -nodes -new -config ${THING_KEY_DIR}/${THING_NAME}.cnf -out ${THING_KEY_DIR}/${THING_NAME}.csr -newkey rsa:2048 -keyout ${THING_KEY_DIR}/${THING_NAME}.pem
openssl ca -config ${ROOT_CA_NAME}.cnf -in ${THING_KEY_DIR}/${THING_NAME}.csr -out ${THING_KEY_DIR}/${THING_NAME}.crt
```

## CLI から証明書を削除する用の変数定義

```sh
THING_CERT_ID=$(openssl x509 -fingerprint -sha256 -in ${THING_KEY_DIR}/${THING_NAME}.crt -noout | cut -d '=' -f 2 | tr -d ':' | tr '[:upper:]' '[:lower:]')
THING_CERT_ARN=arn:aws:iot:${AWS_REGION}:${AWS_ACCOUNT}:cert/${THING_CERT_ID}
```

## 以降の作業のため CA ディレクトリから作業ディレクトリにもどす

```sh
cd ${WORK_DIR}
```
