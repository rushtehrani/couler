# Copyright 2021 The Couler Authors. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import pyaml
import yaml

from couler.core import proto_repr, states, step_update_utils, utils
from couler.core.templates import (
    Container,
    Job,
    Output,
    OutputArtifact,
    OutputJob,
    Script,
)
from couler.core.templates.output import (
    _container_output,
    _job_output,
    _script_output,
)
from couler.core.templates.volume import VolumeMount


def run_script(
    image,
    command=None,
    source=None,
    args=None,
    output=None,
    input=None,
    env=None,
    secret=None,
    resources=None,
    timeout=None,
    retry=None,
    step_name=None,
    image_pull_policy=None,
    pool=None,
    enable_ulogfs=True,
    daemon=False,
    volume_mounts=None,
    working_dir=None,
    node_selector=None,
):
    """
    Generate an Argo script template.  For example,
    https://github.com/argoproj/argo/tree/master/examples#scripts--results.
    :param image:
    :param command:
    :param source:
    :param args:
    :param output: output artifact for container output
    :param input: input artifact for container input
    :param env: environmental variable
    :param secret:
    :param resources: CPU or memory resource config dict
    :param timeout: in seconds
    :param retry: retry policy
    :param step_name: used for annotating step .
    :param image_pull_policy:
    :param pool:
    :param enable_ulogfs:
    :param daemon:
    :return:
    """
    if source is None:
        raise ValueError("Source must be provided")
    func_name, caller_line = utils.invocation_location()
    func_name = (
        utils.argo_safe_name(step_name) if step_name is not None else func_name
    )

    arguments = states._outputs_tmp
    if states.workflow.get_template(func_name) is None:
        # Generate the inputs parameter for the template
        if input is None:
            input = []

        if args is not None and not isinstance(args, list):
            args = [args]

        # Place output artifact into the input
        for arg in arguments or []:
            if isinstance(arg, (OutputArtifact, OutputJob)):
                input.append(arg)

        # Automatically append emptyDir volume and volume mount to work with
        # Argo k8sapi executor.
        # More info: https://argoproj.github.io/argo/empty-dir/
        if output is not None:
            if not isinstance(output, list):
                output = [output]
            if volume_mounts is None:
                volume_mounts = []
            mounted_path = []
            for i, out in enumerate(output):
                if "/tmp" in out.path:
                    raise ValueError("Mounting to /tmp is not supported")
                path_to_mount = os.path.dirname(out.path)
                # Avoid duplicate mount paths
                if path_to_mount not in mounted_path:
                    volume_mounts.append(
                        VolumeMount("couler-out-dir-%s" % i, path_to_mount)
                    )
                    mounted_path.append(path_to_mount)

        # Generate container and template
        template = Script(
            name=func_name,
            image=image,
            command=command,
            source=source,
            args=args,
            arguments=arguments,
            env=env,
            secret=states.get_secret(secret),
            resources=resources,
            image_pull_policy=image_pull_policy,
            retry=retry,
            timeout=timeout,
            output=output,
            input=input,
            pool=pool,
            enable_ulogfs=enable_ulogfs,
            daemon=daemon,
            volume_mounts=volume_mounts,
            working_dir=working_dir,
            node_selector=node_selector,
        )
        states.workflow.add_template(template)

    step_name = step_update_utils.update_step(
        func_name, arguments, step_name, caller_line
    )

    # TODO: need to switch to use field `output` directly
    step_templ = states.workflow.get_template(func_name)
    _output = step_templ.to_dict().get("outputs", None)
    _input = step_templ.to_dict().get("inputs", None)
    rets = _script_output(step_name, func_name, _output)
    states._steps_outputs[step_name] = rets

    proto_repr.step_repr(  # noqa: F841
        step_name=step_name,
        tmpl_name=func_name,
        image=image,
        command=command,
        source=source,
        script_output=rets,
        args=args,
        input=_input,
        output=_output,
        env=env,
        resources=resources,
    )

    return rets


def run_container(
    image,
    command=None,
    args=None,
    output=None,
    input=None,
    env=None,
    secret=None,
    resources=None,
    timeout=None,
    retry=None,
    step_name=None,
    image_pull_policy=None,
    pool=None,
    enable_ulogfs=True,
    daemon=False,
    volume_mounts=None,
    working_dir=None,
    node_selector=None,
):
    """
    Generate an Argo container template.  For example, the template whalesay
    in https://github.com/argoproj/argo/tree/master/examples#hello-world.
    :param image:
    :param command:
    :param args:
    :param output: output artifact for container output
    :param input: input artifact for container input
    :param env: environmental variable
    :param secret:
    :param resources: CPU or memory resource config dict
    :param timeout: in seconds
    :param retry: retry policy
    :param step_name: used for annotating step .
    :param image_pull_policy:
    :param pool:
    :param enable_ulogfs:
    :param daemon:
    :return:
    """
    func_name, caller_line = utils.invocation_location()
    func_name = (
        utils.argo_safe_name(step_name) if step_name is not None else func_name
    )

    arguments = states._outputs_tmp
    if states.workflow.get_template(func_name) is None:
        # Generate the inputs parameter for the template
        if input is None:
            input = []

        if args is not None and not isinstance(args, list):
            args = [args]

        # Place output artifact into the input
        for arg in arguments or []:
            if isinstance(arg, (OutputArtifact, OutputJob)):
                input.append(arg)

        # Automatically append emptyDir volume and volume mount to work with
        # Argo k8sapi executor.
        # More info: https://argoproj.github.io/argo/empty-dir/
        if output is not None:
            if not isinstance(output, list):
                output = [output]
            if volume_mounts is None:
                volume_mounts = []
            mounted_path = []
            for i, out in enumerate(output):
                if "/tmp" in out.path:
                    raise ValueError("Mounting to /tmp is not supported")
                path_to_mount = os.path.dirname(out.path)
                # Avoid duplicate mount paths
                if path_to_mount not in mounted_path:
                    volume_mounts.append(
                        VolumeMount("couler-out-dir-%s" % i, path_to_mount)
                    )
                    mounted_path.append(path_to_mount)

        # Generate container and template
        template = Container(
            name=func_name,
            image=image,
            command=command,
            args=args,
            arguments=arguments,
            env=env,
            secret=states.get_secret(secret),
            resources=resources,
            image_pull_policy=image_pull_policy,
            retry=retry,
            timeout=timeout,
            output=output,
            input=input,
            pool=pool,
            enable_ulogfs=enable_ulogfs,
            daemon=daemon,
            volume_mounts=volume_mounts,
            working_dir=working_dir,
            node_selector=node_selector,
        )
        states.workflow.add_template(template)

    step_name = step_update_utils.update_step(
        func_name, arguments, step_name, caller_line
    )

    # TODO: need to switch to use field `output` directly
    step_templ = states.workflow.get_template(func_name)
    _output = step_templ.to_dict().get("outputs", None)
    _input = step_templ.to_dict().get("inputs", None)

    rets = _container_output(step_name, func_name, _output)
    states._steps_outputs[step_name] = rets

    pb_step = proto_repr.step_repr(  # noqa: F841
        step_name=step_name,
        tmpl_name=func_name,
        image=image,
        command=command,
        source=None,
        script_output=None,
        args=args,
        input=_input,
        output=_output,
        env=env,
        resources=resources,
    )

    return rets


def run_job(
    manifest,
    success_condition,
    failure_condition,
    timeout=None,
    retry=None,
    step_name=None,
    pool=None,
    env=None,
    set_owner_reference=True,
):
    """
    Create a k8s job. For example, the pi-tmpl template in
    https://github.com/argoproj/argo/blob/master/examples/k8s-jobs.yaml
    :param manifest: YAML specification of the job to be created.
    :param success_condition: expression for verifying job success.
    :param failure_condition: expression for verifying job failure.
    :param timeout: To limit the elapsed time for a workflow in seconds.
    :param step_name: is only used while developing functions of step zoo.
    :param env: environmental parameter with a dict types, e.g., {"OS_ENV_1": "OS_ENV_value"}  # noqa: E501
    :param set_owner_reference: Whether to set the workflow as the job's owner reference.
        If `True`, the job will be deleted once the workflow is deleted.
    :return: output
    """
    if manifest is None:
        raise ValueError("Input manifest can not be null")

    func_name, caller_line = utils.invocation_location()
    func_name = (
        utils.argo_safe_name(step_name) if step_name is not None else func_name
    )

    args = []
    if states.workflow.get_template(func_name) is None:
        if states._outputs_tmp is not None and env is not None:
            env["inferred_outputs"] = states._outputs_tmp

        # Generate the inputs for the manifest template
        envs, parameters, args = utils.generate_parameters_run_job(env)

        # update the env
        if env is not None:
            manifest_dict = yaml.safe_load(manifest)
            manifest_dict["spec"]["env"] = envs

            # TODO this is used to pass the test cases,
            # should be fixed in a better way
            if (
                "labels" in manifest_dict["metadata"]
                and "argo.step.owner" in manifest_dict["metadata"]["labels"]
            ):
                manifest_dict["metadata"]["labels"][
                    "argo.step.owner"
                ] = "'{{pod.name}}'"

            manifest = pyaml.dump(manifest_dict)

        template = Job(
            name=func_name,
            args=args,
            action="create",
            manifest=manifest,
            set_owner_reference=set_owner_reference,
            success_condition=success_condition,
            failure_condition=failure_condition,
            timeout=timeout,
            retry=retry,
            pool=pool,
        )
        states.workflow.add_template(template)

    step_name = step_update_utils.update_step(
        func_name, args, step_name, caller_line
    )

    # return job name and job uid for reference
    rets = _job_output(step_name, func_name)
    states._steps_outputs[step_name] = rets

    pb_step = proto_repr.step_repr(  # noqa: F841
        step_name=step_name,
        tmpl_name=func_name,
        image=None,
        source=None,
        script_output=None,
        input=None,
        output=rets,
        manifest=manifest,
        success_cond=success_condition,
        failure_cond=failure_condition,
    )

    return rets


def run_canned_step(name, args, inputs=None, outputs=None, step_name=None):
    func_name, caller_line = utils.invocation_location()
    func_name = (
        utils.argo_safe_name(step_name) if step_name is not None else func_name
    )
    step_name = step_update_utils.update_step(
        func_name, args, step_name, caller_line
    )
    tmpl_args = []
    if states._outputs_tmp is not None:
        tmpl_args.extend(states._outputs_tmp)
    return proto_repr.step_repr(  # noqa: F841
        input=inputs,
        output=outputs,
        canned_step_name=name,
        canned_step_args=args,
        step_name=step_name,
        tmpl_name=step_name + "-tmpl",
        args=tmpl_args,
    )
