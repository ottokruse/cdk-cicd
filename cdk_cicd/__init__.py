from pathlib import Path
from typing import Any, List, TypedDict, Union, Literal, Mapping, cast
from typeguard import typechecked
from aws_cdk import (
    core,
    aws_codepipeline,
    aws_codepipeline_actions,
    aws_codecommit,
    aws_codebuild,
    aws_cloudformation,
    aws_iam,
    aws_lambda,
    aws_s3,
)

DIR = Path(__file__).parent

__all__ = [
    "setup_cicd",
    "Pipeline",
    "Stage",
    "CodeBuildAction",
    "CloudFormationCreateUpdateStackAction",
    "ApprovalAction",
    "CodeCommitAction",
    "LambdaInvokeAction",
    "Pipelines",
]


class ActionBase(TypedDict):
    name: str


class Action(ActionBase, total=False):
    run_order: int
    variables_namespace: str
    role_arn: str


class ApprovalActionBase(Action):
    type: Literal["APPROVAL"]


class ApprovalAction(ApprovalActionBase, total=False):
    pass


class CodeCommitActionBase(Action):
    type: Literal["CODECOMMIT"]
    output: str
    repository: str


class CodeCommitAction(CodeCommitActionBase, total=False):
    branch: str


class CodeBuildActionBase(Action):
    type: Literal["CODEBUILD"]
    build_spec: str
    input: str


class CodeBuildAction(CodeBuildActionBase, total=False):
    environment: dict
    environment_variables: dict
    outputs: List[str]
    extra_inputs: List[str]


class CloudFormationActionBase(Action):
    type: Literal["CLOUDFORMATION"]
    input: str
    action_mode: Literal["CREATE_UPDATE"]
    stack_name: str


class CloudFormationCreateUpdateStackAction(CloudFormationActionBase, total=False):
    template_path: str
    parameter_overrides: Mapping[str, Any]
    capabilities: List[
        Union[
            Literal["CAPABILITY_AUTO_EXPAND"],
            Literal["CAPABILITY_IAM"],
            Literal["CAPABILITY_NAMED_IAM"],
        ]
    ]


class LambdaInvokeBaseAction(Action):
    type: Literal["LAMBDA"]
    function_arn: str
    user_parameters: dict


class LambdaInvokeAction(LambdaInvokeBaseAction, total=False):
    pass


class Stage(TypedDict):
    name: str
    actions: List[
        Union[
            LambdaInvokeAction,
            CodeCommitAction,
            CodeBuildAction,
            CloudFormationCreateUpdateStackAction,
            ApprovalAction,
        ]
    ]


class PipelineBase(TypedDict):
    name: str
    stages: List[Stage]


class ArtifactAccess(TypedDict):
    role_arns: List[str]


class Pipeline(PipelineBase, total=False):
    artifact_access: ArtifactAccess


Pipelines = List[Pipeline]


@typechecked
def setup_cicd(scope: core.Construct, id: str, pipelines: Pipelines) -> None:
    for pipeline_def in pipelines:
        pipeline = aws_codepipeline.Pipeline(
            scope,
            generate_logical_id(pipeline_def["name"]),
            pipeline_name=pipeline_def["name"],
            restart_execution_on_update=True,
        )
        for stage_def in pipeline_def["stages"]:
            stage = pipeline.add_stage(stage_name=stage_def["name"])
            for action_def in stage_def["actions"]:
                action_id = generate_logical_id(
                    pipeline_def["name"], stage_def["name"], action_def["name"]
                )
                action = create_action(scope, action_id, action_def)
                stage.add_action(action)

        provide_access_to_artifacts(
            scope, pipeline_def=pipeline_def, artifact_bucket=pipeline.artifact_bucket
        )


def provide_access_to_artifacts(
    scope: core.Construct, *, pipeline_def: Pipeline, artifact_bucket: aws_s3.Bucket
) -> None:
    role_arns = set()
    for role_arn in pipeline_def.get("artifact_access", {}).get("role_arns", []):
        role_arns.add(role_arn)
    for stage_def in pipeline_def["stages"]:
        for action_def in stage_def["actions"]:
            if "role_arn" in action_def:
                account = core.Arn.parse(action_def["role_arn"]).account
                if account != core.Stack.of(scope).account:
                    role_arns.add(action_def["role_arn"])
    for role_arn in role_arns:
        artifact_bucket.add_to_resource_policy(
            aws_iam.PolicyStatement(
                actions=["s3:Get*"],
                resources=[artifact_bucket.arn_for_objects("*")],
                effect=aws_iam.Effect.ALLOW,
                principals=[aws_iam.ArnPrincipal(role_arn)],
            )
        )


def generate_logical_id(*components: str):
    """Generate a nice init-capped logical ID

    >>> generate_logical_id("test-abc-def")
    TestAbcDef

    >>> generate_logical_id("test-abc-def", "xyz-123")
    TestAbcDefXyz123
    """

    parts = dict.fromkeys(
        [part.title() for component in components for part in component.split("-")]
    )
    return "".join(parts)


def create_action(
    scope: core.Construct,
    id: str,
    action_def: Union[
        CodeCommitAction,
        CodeBuildAction,
        CloudFormationCreateUpdateStackAction,
        ApprovalAction,
        LambdaInvokeAction,
    ],
):
    action_name = action_def["name"]
    run_order = action_def.get("run_order", 1)
    role = (
        aws_iam.Role.from_role_arn(scope, f"{id}RoleRef", action_def["role_arn"])
        if "role_arn" in action_def
        else None
    )

    if action_def["type"] == "CODECOMMIT":
        action_def = cast(CodeCommitAction, action_def)
        repository = aws_codecommit.Repository.from_repository_name(
            scope, f"{id}Repo", action_def["repository"]
        )
        output = aws_codepipeline.Artifact(action_def["output"])
        return aws_codepipeline_actions.CodeCommitSourceAction(
            action_name=action_name,
            output=output,
            repository=repository,
            branch=action_def.get("branch", "master"),
            run_order=run_order,
            role=role,
        )
    elif action_def["type"] == "CODEBUILD":
        action_def = cast(CodeBuildAction, action_def)
        # Set up CodeBuild project
        project_params = {
            "build_spec": aws_codebuild.BuildSpec.from_source_filename(
                action_def.get("build_spec", "buildspec.yaml")
            )
        }
        project_params["environment"] = {
            "build_image": aws_codebuild.LinuxBuildImage.AMAZON_LINUX_2_3
        }
        if "environment" in action_def:
            if "build_image" in action_def["environment"]:
                project_params["environment"]["build_image"] = getattr(
                    aws_codebuild.LinuxBuildImage,
                    action_def["environment"].pop("build_image"),
                )
            project_params["environment"].update(**action_def["environment"])
        project_role = aws_iam.Role(
            scope,
            f"{id}CodeBuildRole",
            path="/codebuild/",
            assumed_by=aws_iam.ServicePrincipal(service="codebuild.amazonaws.com"),
        )
        project_role.add_to_policy(
            aws_iam.PolicyStatement(
                actions=["*"], resources=["*"], effect=aws_iam.Effect.ALLOW
            )
        )
        project = aws_codebuild.PipelineProject(
            scope, f"{id}Project", project_name=id, role=project_role, **project_params
        )
        environment_variables = (
            {
                var_key: aws_codebuild.BuildEnvironmentVariable(
                    value=var_value,
                    type=aws_codebuild.BuildEnvironmentVariableType.PLAINTEXT,
                )
                for var_key, var_value in action_def["environment_variables"].items()
            }
            if "environment_variables" in action_def
            else None
        )
        extra_inputs = (
            [aws_codepipeline.Artifact(input_) for input_ in action_def["extra_inputs"]]
            if "extra_inputs" in action_def
            else None
        )
        outputs = (
            [aws_codepipeline.Artifact(output) for output in action_def["outputs"]]
            if "outputs" in action_def
            else None
        )
        return aws_codepipeline_actions.CodeBuildAction(
            action_name=action_name,
            input=aws_codepipeline.Artifact(action_def["input"]),
            project=project,
            run_order=run_order,
            role=role,
            variables_namespace=action_def.get("variables_namespace"),
            environment_variables=environment_variables,
            extra_inputs=extra_inputs,
            outputs=outputs,
        )
    elif action_def["type"] == "CLOUDFORMATION":
        action_def = cast(CloudFormationCreateUpdateStackAction, action_def)
        return aws_codepipeline_actions.CloudFormationCreateUpdateStackAction(
            action_name=action_name,
            admin_permissions=False,
            stack_name=action_def["stack_name"],
            template_path=aws_codepipeline.ArtifactPath(
                aws_codepipeline.Artifact(action_def["input"]),
                action_def.get("template_path", "template.yaml"),
            ),
            capabilities=[
                # This lstrip does not support all possibilties, but is good enough for now
                aws_cloudformation.CloudFormationCapabilities[
                    capability.lstrip("CAPABILITY_")
                ]
                for capability in action_def["capabilities"]
            ]
            if "capabilities" in action_def
            else None,
            deployment_role=role,
            role=role,
            parameter_overrides=action_def.get("parameter_overrides"),
            run_order=run_order,
        )
    elif action_def["type"] == "APPROVAL":
        action_def = cast(ApprovalAction, action_def)
        return aws_codepipeline_actions.ManualApprovalAction(
            action_name=action_name, run_order=run_order, role=role
        )
    elif action_def["type"] == "LAMBDA":
        action_def = cast(LambdaInvokeAction, action_def)
        user_parameters = action_def.get("user_parameters")
        return aws_codepipeline_actions.LambdaInvokeAction(
            action_name=action_name,
            run_order=run_order,
            lambda_=aws_lambda.Function.from_function_arn(
                scope, f"{id}Lambda", action_def["function_arn"]
            ),
            user_parameters=user_parameters,
            role=role,
        )

