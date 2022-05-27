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

import pandas as pd

# registered features
spec_registry = []


def spec_by_fqn(fqn: str):
    return next(filter(lambda m: m["kind"] == "feature" and m["fqn"] == fqn.split("[")[0], spec_registry), None)


def spec_by_src_name(src_name: str):
    return next(filter(lambda m: m["kind"] == "feature" and m["src_name"] == src_name, spec_registry), None)


# Calculated feature values
__feature_values = pd.DataFrame()


def store_feature_values(feature_values):
    global __feature_values
    __feature_values = pd.concat([__feature_values, feature_values])


def feature_values():
    return __feature_values.copy()
