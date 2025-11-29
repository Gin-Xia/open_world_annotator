import boto3
import botocore
import time

# ------------ 基本配置 ------------
REGION = "us-east-1"

ROLE_ARN = "arn:aws:iam::221482347185:role/SageMakerExecutionRole"
IMAGE_URI = "221482347185.dkr.ecr.us-east-1.amazonaws.com/open-world-annotator@sha256:503514df5c77122e8b9308b7f894c1ae0f57d527b53b55496ca6389c67d782eb"

MODEL_NAME = "open-world-annotator-model"
ENDPOINT_CONFIG = "open-world-annotator-config"
ENDPOINT_NAME = "open-world-annotator-endpoint"

INSTANCE_TYPE = "ml.g4dn.xlarge"

sm = boto3.client("sagemaker", region_name=REGION)


# ------------ 小工具函数：打印并抛错 ------------
def _handle_client_error(e, resource_desc: str, allow_exists: bool = False):
    err = e.response.get("Error", {})
    code = err.get("Code", "")
    msg = err.get("Message", "")
    print(f"[ERROR] {resource_desc} failed: {code} - {msg}")

    if allow_exists and ("already exists" in msg or code in ("ResourceInUse",)):
        print(f"[INFO] {resource_desc} already exists, skip")
        return
    raise e


# ------------ Step 1: 创建 Model ------------
print("=== Step 1: Creating SageMaker Model ===")

try:
    sm.create_model(
        ModelName=MODEL_NAME,
        PrimaryContainer={
            "Image": IMAGE_URI,
            "Mode": "SingleModel",
        },
        ExecutionRoleArn=ROLE_ARN,
    )
    print("[OK] Model created")

except botocore.exceptions.ClientError as e:
    _handle_client_error(e, "CreateModel", allow_exists=True)


# ------------ Step 2: 创建 Endpoint Config ------------
print("=== Step 2: Creating Endpoint Config ===")

try:
    sm.create_endpoint_config(
        EndpointConfigName=ENDPOINT_CONFIG,
        ProductionVariants=[
            {
                "VariantName": "AllTraffic",
                "ModelName": MODEL_NAME,
                "InitialInstanceCount": 1,
                "InstanceType": INSTANCE_TYPE,
                "InitialVariantWeight": 1.0,
            }
        ],
    )
    print("[OK] Endpoint Config created")

except botocore.exceptions.ClientError as e:
    _handle_client_error(e, "CreateEndpointConfig", allow_exists=True)


# ------------ Step 3: 创建或更新 Endpoint ------------
print("=== Step 3: Creating or Updating Endpoint ===")

need_create = True
try:
    resp = sm.describe_endpoint(EndpointName=ENDPOINT_NAME)
    status = resp["EndpointStatus"]
    print(f"[INFO] Endpoint {ENDPOINT_NAME} already exists, status = {status}")
    need_create = False
except botocore.exceptions.ClientError as e:
    err = e.response.get("Error", {}).get("Code", "")
    if err == "ResourceNotFound":
        print(f"[INFO] Endpoint {ENDPOINT_NAME} not found, will create new one")
        need_create = True
    else:
        raise e

if need_create:
    try:
        sm.create_endpoint(
            EndpointName=ENDPOINT_NAME,
            EndpointConfigName=ENDPOINT_CONFIG,
        )
        print("[OK] Endpoint creating...")
    except botocore.exceptions.ClientError as e:
        _handle_client_error(e, "CreateEndpoint", allow_exists=False)
else:
    try:
        sm.update_endpoint(
            EndpointName=ENDPOINT_NAME,
            EndpointConfigName=ENDPOINT_CONFIG,
        )
        print("[OK] Updating existing Endpoint...")
    except botocore.exceptions.ClientError as e:
        _handle_client_error(e, "UpdateEndpoint", allow_exists=False)


# ------------ Step 4: 等 Endpoint InService ------------
print("=== Step 4: Waiting for Endpoint to be InService ===")

while True:
    resp = sm.describe_endpoint(EndpointName=ENDPOINT_NAME)
    status = resp["EndpointStatus"]
    msg = resp.get("FailureReason", "")
    print(f"[STATUS] {ENDPOINT_NAME}: {status}")

    if status == "InService":
        print(f"✅ Endpoint ready: {ENDPOINT_NAME}")
        break

    if status == "Failed":
        print("❌ Endpoint failed")
        if msg:
            print("FailureReason:", msg)
        raise RuntimeError("Endpoint status = Failed")

    time.sleep(30)
