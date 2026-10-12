"""Fail closed when existing cloud resources conflict with the setup contract."""
import json
import sys
from pathlib import Path


def require(condition: bool) -> None:
    if not condition:
        raise ValueError("resource configuration mismatch")


def validate(kind: str, resource: dict, expected: str) -> None:
    if kind == "firestore":
        require(resource["type"] == "FIRESTORE_NATIVE")
        require(resource["locationId"].lower() == expected)
    elif kind == "bucket":
        project, number = expected.split("/")
        require(resource["location"].lower() == "asia-southeast1")
        require(resource["iamConfiguration"]["uniformBucketLevelAccess"]["enabled"] is True)
        require(resource["iamConfiguration"]["publicAccessPrevention"] == "enforced")
        require(resource["name"] == f"highground-media-{project}")
        require(str(resource["projectNumber"]) == number)
    elif kind == "secret":
        replicas = resource["replication"]["userManaged"]["replicas"]
        require([r["location"] for r in replicas] == [expected])
    elif kind == "dataset":
        require(resource["location"].lower() == expected)
    elif kind == "table":
        require(resource["type"] == "TABLE")
        require(resource["schema"]["fields"] == json.loads(Path(expected).read_text()))
    elif kind == "service_account":
        require(resource["email"] == expected)
        require(not resource.get("disabled", False))
    elif kind == "role":
        require(set(resource["includedPermissions"]) == set(expected.split(",")))
        require(not resource.get("deleted", False))
        require(resource.get("stage", "GA") != "DISABLED")
    else:
        raise ValueError(f"Unknown resource type: {kind}")


if __name__ == "__main__":
    try:
        validate(sys.argv[1], json.loads(Path(sys.argv[2]).read_text()), sys.argv[3])
    except (AssertionError, KeyError, ValueError) as error:
        raise SystemExit(f"Existing {sys.argv[1]} conflicts with setup contract: {error}")
