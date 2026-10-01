#!/usr/bin/env bash
set -euo pipefail

REGION="${AWS_REGION:-us-east-2}"
ROLE_NAME="quorumflow-github-deploy"
POLICY_NAME="quorumflow-github-deploy"
OIDC_URL="https://token.actions.githubusercontent.com"
OIDC_ARN_SUFFIX="oidc-provider/token.actions.githubusercontent.com"
THUMBPRINT="6938fd4d98bab03faadb97b34396831e3780aea1"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
echo "AWS account: $ACCOUNT_ID"
echo "Region: $REGION"

OIDC_ARN="arn:aws:iam::$ACCOUNT_ID:$OIDC_ARN_SUFFIX"
if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$OIDC_ARN" >/dev/null 2>&1; then
  echo "GitHub OIDC provider already exists."
else
  aws iam create-open-id-connect-provider     --url "$OIDC_URL"     --client-id-list sts.amazonaws.com     --thumbprint-list "$THUMBPRINT" >/dev/null
  echo "Created GitHub OIDC provider."
fi

TMP_TRUST="$(mktemp)"
sed "s/__ACCOUNT_ID__/$ACCOUNT_ID/g" infra/aws/github-oidc-trust.json > "$TMP_TRUST"

if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  aws iam update-assume-role-policy     --role-name "$ROLE_NAME"     --policy-document "file://$TMP_TRUST"
  echo "Updated role trust policy."
else
  aws iam create-role     --role-name "$ROLE_NAME"     --assume-role-policy-document "file://$TMP_TRUST" >/dev/null
  echo "Created role."
fi

POLICY_ARN="arn:aws:iam::$ACCOUNT_ID:policy/$POLICY_NAME"
if aws iam get-policy --policy-arn "$POLICY_ARN" >/dev/null 2>&1; then
  # IAM managed policies allow at most five versions. Keep the default plus
  # the newest non-default versions and prune the oldest before creating one.
  VERSION_COUNT="$(aws iam list-policy-versions     --policy-arn "$POLICY_ARN"     --query 'length(Versions)'     --output text)"
  if [[ "$VERSION_COUNT" -ge 5 ]]; then
    OLDEST_NON_DEFAULT="$(aws iam list-policy-versions       --policy-arn "$POLICY_ARN"       --query 'sort_by(Versions[?IsDefaultVersion==`false`], &CreateDate)[0].VersionId'       --output text)"
    if [[ -n "$OLDEST_NON_DEFAULT" && "$OLDEST_NON_DEFAULT" != "None" ]]; then
      aws iam delete-policy-version         --policy-arn "$POLICY_ARN"         --version-id "$OLDEST_NON_DEFAULT"
      echo "Deleted old policy version $OLDEST_NON_DEFAULT."
    fi
  fi

  VERSION_ID="$(aws iam create-policy-version     --policy-arn "$POLICY_ARN"     --policy-document file://infra/aws/github-deploy-policy.json     --set-as-default     --query 'PolicyVersion.VersionId'     --output text)"
  echo "Updated policy to $VERSION_ID."
else
  aws iam create-policy     --policy-name "$POLICY_NAME"     --policy-document file://infra/aws/github-deploy-policy.json >/dev/null
  echo "Created policy."
fi

aws iam attach-role-policy   --role-name "$ROLE_NAME"   --policy-arn "$POLICY_ARN"

ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME"
echo
echo "Bootstrap complete."
echo "Add this GitHub Actions repository secret:"
echo
echo "AWS_ROLE_ARN=$ROLE_ARN"
echo
echo "Then rerun the 'Deploy AWS substrate' workflow."
