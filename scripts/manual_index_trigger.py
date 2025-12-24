#!/usr/bin/env python3
"""Manual trigger script for Indexer Lambda

Usage:
    python3 scripts/manual_index_trigger.py --stack-name <stack-name>

Example:
    python3 scripts/manual_index_trigger.py --stack-name talktalk-auto-dev
"""
import argparse
import json
import sys

import boto3


def trigger_indexer(stack_name: str, region: str = "ap-northeast-2") -> None:
    """
    Manually trigger the Indexer Lambda function

    Args:
        stack_name: CloudFormation stack name
        region: AWS region (default: ap-northeast-2)
    """
    lambda_client = boto3.client("lambda", region_name=region)

    function_name = f"{stack_name}-IndexerFunction"

    print(f"Triggering Indexer Lambda: {function_name}")

    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps({"source": "manual_trigger"}),
        )

        status_code = response["StatusCode"]
        payload = json.loads(response["Payload"].read())

        print(f"\nResponse Status Code: {status_code}")
        print(f"Response Payload: {json.dumps(payload, indent=2)}")

        if status_code == 200:
            print("\n✅ Indexer Lambda triggered successfully")
            return
        else:
            print(f"\n❌ Indexer Lambda returned non-200 status code: {status_code}")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Failed to trigger Indexer Lambda: {str(e)}")
        sys.exit(1)


def main() -> None:
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Manually trigger Indexer Lambda for KB document sync"
    )
    parser.add_argument(
        "--stack-name",
        required=True,
        help="CloudFormation stack name (e.g., talktalk-auto-dev)",
    )
    parser.add_argument(
        "--region",
        default="ap-northeast-2",
        help="AWS region (default: ap-northeast-2)",
    )

    args = parser.parse_args()

    trigger_indexer(args.stack_name, args.region)


if __name__ == "__main__":
    main()
