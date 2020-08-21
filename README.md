# CDK CICD library

Utility for generating AWS CICD pipelines using simple YAML syntax.

## Usage:

1. Create pipelines.yaml. For example:

```yaml
pipelines:
  - name: my-pipeline-name
    stages:
      - name: source
        actions:
          - name: source
            type: CODECOMMIT
            repository: my-repo-name
            output: source
      - name: deploy
        actions:
          - name: deploy
            type: CODEBUILD
            input: source
            environment:
              build_image: AMAZON_LINUX_2_3
              privileged: true
            build_spec: buildspec-multi-account-deploy.yaml # Use assume.sh in buildspec
            environment_variables:
              TARGET_ACCOUNT: "123456789012"
              TARGET_ROLE: deployment-role-in-target-account
      - name: run-smoke-test
        actions:
          - name: run-smoke-test
            type: LAMBDA
            input: source
            function_arn: arn:aws:lambda:us-east-1:123456789012:function:test-fn
            user_parameters:
              param1: true
              param2: "A string"
```

2. Use pipelines.yaml to generate the CICD constructs needed:

```python
import yaml
from epr_cicd import setup_cicd
with open("pipelines.yaml")) as f:
    pipelines = yaml.load(f, Loader=yaml.FullLoader)["pipelines"]

# Then, somewhere in your CDK stack:
setup_cicd(scope, id, pipelines=pipelines)

# :tada: now you have an AWS CodePipeline with all the actions and stages you defined in your YAML
```
