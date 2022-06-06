# Copyright 2022 Natun.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import inspect

from . import types, replay, local_state


def aggr(funcs: [types.AggrFn]):
    def decorator(func):
        for f in funcs:
            if f == types.AggrFn.Unknown:
                raise Exception("Unknown aggr function")
        func.aggr = funcs
        return func

    return decorator


def connector(name: str):
    def decorator(func):
        func.connector = name
        return func

    return decorator


def namespace(name: str):
    def decorator(func):
        func.namespace = name
        return func

    return decorator


def builder(kind: str, options=None):
    def decorator(func):
        func.builder = {"kind": kind, "options": options}
        return func

    return decorator


def register(primitive, freshness: str, staleness: str, options=None):
    if options is None:
        options = {}

    def decorator(func):
        if hasattr(func, "feature_spec"):
            raise Exception("Feature is already registered")

        options["freshness"] = freshness
        options["staleness"] = staleness

        if 'name' not in options and (func.__name__ == '<lambda>' or func.__name__ != 'handler'):
            options['name'] = func.__name__
        elif 'name' in options and options['name'] != 'handler':
            raise Exception("Function name is required")

        if 'desc' not in options and func.__doc__ is not None:
            options['desc'] = func.__doc__

        # verify signature
        fas = inspect.getfullargspec(func)
        if len(fas.annotations) != 0 or fas.varkw is None:
            raise Exception("Invalid signature")

        # verify primitive
        p = primitive
        if p == 'int' or p == int:
            p = 'int'
        elif p == 'float' or p == float:
            p = 'float'
        elif p == 'timestamp' or p == datetime:
            p = 'timestamp'
        elif p == 'str' or p == str:
            p = 'string'
        elif p == '[]str' or p == [str]:
            p = '[]str'
        elif p == '[]int' or p == [int]:
            p = '[]int'
        elif p == '[]float' or p == [float]:
            p = '[]float'
        elif p == '[]timestamp' or p == [datetime]:
            p = '[]timestamp'
        elif p == 'headless':
            p = 'headless'
        else:
            raise Exception("Primitive type not supported")
        options['primitive'] = p

        # add source coded (decorators stripped)
        src = []
        for line in inspect.getsourcelines(func)[0]:
            if line.startswith('@'):
                continue
            src.append(line)
        src = ''.join(src)

        # append annotations
        if hasattr(func, "builder"):
            options["builder"] = func.builder
        if "builder" not in options:
            options["builder"] = {"kind": "expression", "options": None}

        if hasattr(func, "namespace"):
            options["namespace"] = func.namespace
        if "namespace" not in options:
            options["namespace"] = "default"

        if hasattr(func, "connector"):
            options["connector"] = func.connector
        if hasattr(func, "aggr"):
            options["aggr"] = func.aggr

        # register the feature
        fqn = f"{options['name']}.{options['namespace']}"
        spec = {"kind": "feature", "options": options, "src": src, "src_name": func.__name__, "fqn": fqn}
        func.feature_spec = spec
        func.replay = replay.replay(spec)
        local_state.spec_registry.append(spec)

        return func

    return decorator


def feature_set(register=False, options=None):
    if options is None:
        options = {}

    def decorator(func):
        if hasattr(func, "feature_set_spec"):
            raise Exception("FeatureSet is already registered")
        if inspect.signature(func) != inspect.signature(lambda: []):
            raise Exception("Invalid signature")

        fts = []
        for f in func():
            if type(f) is str:
                fts.append(f)
            if callable(f):
                ft = local_state.spec_by_src_name(f.__name__)
                if ft is None:
                    raise Exception("Feature not found")
                if "aggr" in ft["options"]:
                    raise Exception("You must specify a FQN with AggrFn for aggregated features")
                fts.append(ft["fqn"])

        if "key_feature" not in options:
            options["key_feature"] = fts[0]

        if hasattr(func, "namespace"):
            options["namespace"] = func.namespace
        if "namespace" not in options:
            options["namespace"] = "default"

        if "timeout" not in options:
            options["timeout"] = "5s"

        if "name" not in options:
            options["name"] = func.__name__

        if "desc" not in options and func.__doc__ is not None:
            options["desc"] = func.__doc__

        fqn = f"{options['name']}.{options['namespace']}"
        spec = {"kind": "feature_set", "options": options, "src": fts, "src_name": func.__name__, "fqn": fqn}
        func.feature_set_spec = spec
        func.historical_get = replay.historical_get(spec)
        if register:
            local_state.spec_registry.append(spec)
        return func

    return decorator


def __feature_manifest(f):
    def _fmt(val, field=None):
        if val is None:
            return "~"
        elif field in val:
            return val[field]
        return "~"

    t = f"""apiVersion: k8s.natun.ai/v1alpha1
    kind: Feature
    metadata:
      name: {f['options']['name']}
      namespace: {f['options']['namespace']}
      annotations:
        a8r.io/description: "{_fmt(f['options'], 'desc')}"
    spec:
      primitive: {_fmt(f['options'], 'primitive')}
      freshness: {_fmt(f['options'], 'freshness')}
      staleness: {_fmt(f['options'], 'staleness')}"""
    if 'aggr' in f['options']:
        t += "\n  aggr:"
        for a in f['options']['aggr']:
            t += "\n    - " + a.name.lower()
    if 'timeout' in f['options']:
        t += f"\n  timeout: {_fmt(f['options'], 'timeout')}"
    t += f"""
      builder:
        kind: {_fmt(f['options']['builder'], 'kind')}"""
    if f['options']['builder']['options'] is not None:
        for k, v in f['options']['builder']['options']:
            t += f"    {k}: {_fmt(v)}\n"
    t += "\n    pyexp: |"
    for line in f['src'].split('\n'):
        t += "\n      " + line
    t += "\n"
    return t


def __feature_set_manifest(f):
    nl = "\n"
    return f"""apiVersion: k8s.natun.ai/v1alpha1
kind: FeatureSet
metadata:
  name: {f["options"]["name"]}
  namespace: {f["options"]["namespace"]}
spec:
  timeout: {f["options"]["timeout"]}
  keyFeature: {f["options"]["key_feature"]}
  features:
    {f'{nl}    - '.join(f["src"])}
"""


def manifests(save_to_tmp=False):
    """manifests will create a list of registered Natun manifests ready to install for your kubernetes cluster
    If save_to_tmp is True, it will save the manifests to a temporary file and return the path to the file.
    Otherwise, it will print the manifests.
    """
    mfts = []
    for m in local_state.spec_registry:
        if m["kind"] == "feature":
            mfts.append(__feature_manifest(m))
        elif m["kind"] == "feature_set":
            mfts.append(__feature_set_manifest(m))
        else:
            raise Exception("Invalid manifest")

    if len(mfts) == 0:
        return ""

    ret = '---\n'.join(mfts)
    if save_to_tmp:
        import tempfile
        f = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
        f.write(ret)
        file_name = f.name
        f.close()
        return file_name
    else:
        print(ret)
