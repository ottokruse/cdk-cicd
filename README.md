# EPR CDK CICD library

Utility for generating CICD artifacts.

## Usage:

1. Create pipelines.yaml. For example:

```yaml
pipelines:
  - name: epr-shared
    stages:
      - name: source
        actions:
          - name: source
            type: CODECOMMIT
            repository: EPR-Shared-ProServe
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
```

2. Use pipelines.yaml to generate the CICD constructs needed:

```python
import yaml
from epr_cicd import setup_cicd
with open("pipelines.yaml")) as f:
    pipelines = yaml.load(f, Loader=yaml.FullLoader)["pipelines"]

# Then, somewhere in your CDK stack:
setup_cicd(scope, id, pipelines=pipelines)
```
