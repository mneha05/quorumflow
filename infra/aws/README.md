# AWS deployment

QuorumFlow's AWS substrate is intentionally small: a versioned S3 artifact lake, a DynamoDB Raft snapshot table, and an ECR runtime repository.

## Preferred authentication: GitHub OIDC

No long-lived AWS access key is required.

From an authenticated AWS CloudShell or local AWS CLI session:

```bash
bash infra/aws/bootstrap-github-oidc.sh
```

The bootstrap:
1. creates/reuses the GitHub Actions OIDC provider,
2. creates a role restricted to `mneha05/quorumflow` on `main`,
3. attaches a resource-scoped policy for this Terraform root,
4. prints the `AWS_ROLE_ARN`.

Add that ARN as a GitHub Actions repository secret named `AWS_ROLE_ARN`, then rerun **Deploy AWS substrate**.

## Deployment evidence

A successful deploy workflow records:
- `aws sts get-caller-identity`,
- Terraform's S3 bucket output,
- DynamoDB table output,
- ECR repository output,

and uploads them as the `quorumflow-aws-deployment-receipt` artifact.

The workflow also supports `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY`, but OIDC is preferred because it avoids persistent cloud credentials in GitHub.
