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
      - name: update-cicd
        actions:
          - name: update-cicd
            type: CODEBUILD
            input: source
            build_spec: buildspec-cicd.yaml
            environment:
              build_image: AMAZON_LINUX_2_3
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
```

2. Use pipelines.yaml to generate the CICD constructs needed:

```python
import yaml
from epr_cicd import setup_cicd
with open("pipelines.yaml")) as f:
    pipelines = yaml.load(f, Loader=yaml.FullLoader)["pipelines"]

# Then, somewhere in your CDK stack:
setup_cicd(scope, id, pipelines=pipelines)

# And :tata: now you have an AWS CodePipeline with all tha actions and stages in it, as per your spec
```
