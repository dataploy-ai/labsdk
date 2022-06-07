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
import json

import pandas as pd
from pandas.tseries.frequencies import to_offset

from . import durpy, local_state, replay_instructions
from .pyexp import pyexp, go


def __detect_ts_field(df) -> str:
    if 'timestamp' in df.columns:
        return 'timestamp'
    elif 'time' in df.columns:
        return 'time'
    elif 'date' in df.columns:
        return 'date'
    elif 'datetime' in df.columns:
        return 'datetime'
    elif 'ts' in df.columns:
        return 'ts'
    elif 'event_timestamp' in df.columns:
        return 'event_timestamp'
    elif 'event_at' in df.columns:
        return 'event_at'
    elif 'event_time' in df.columns:
        return 'event_time'
    elif 'event_date' in df.columns:
        return 'event_date'
    elif 'event_datetime' in df.columns:
        return 'event_datetime'
    elif 'event_ts' in df.columns:
        return 'event_ts'
    else:
        return None


def __detect_headers_field(df) -> str:
    if 'headers' in df.columns:
        return 'headers'
    else:
        return None


def __detect_entity_id(df) -> str:
    if 'entity_id' in df.columns:
        return 'entity_id'
    elif 'entityId' in df.columns:
        return 'entityId'
    elif 'entityID' in df.columns:
        return 'entityID'
    else:
        return None


def replay(spec):
    def _replay(df: pd.DataFrame, timestamp_field: str = None, headers_field: str = None, entity_id_field: str = None,
                store_locally=True):
        df = df.copy()
        if spec["kind"] != "feature":
            raise Exception("Not a Feature")

        if timestamp_field is None:
            timestamp_field = __detect_ts_field(df)
            if timestamp_field is None:
                raise Exception("No timestamp field found")
        df[timestamp_field] = pd.to_datetime(df[timestamp_field])  # normalize

        if entity_id_field is None:
            entity_id_field = __detect_entity_id(df)
            if entity_id_field is None:
                raise Exception("No entity_id field found")

        if headers_field is None:
            headers_field = __detect_headers_field(df)

        rt = pyexp.New(spec["src"], spec["fqn"])

        df["__natun.ret__"] = df.apply(__map(rt, timestamp_field, headers_field, entity_id_field), axis=1)

        # flip dataframe to feature_value df
        feature_values = df.filter([entity_id_field, "__natun.ret__", timestamp_field], axis=1)
        feature_values.rename(columns={
            entity_id_field: "entity_id",
            "__natun.ret__": "value",
            timestamp_field: "timestamp",
        }, inplace=True)

        if "aggr" not in spec["options"]:
            feature_values.insert(0, "fqn", spec["fqn"])
            if store_locally:
                local_state.store_feature_values(feature_values)
            return feature_values

        # aggregations
        feature_values.set_index('timestamp', inplace=True)
        win = to_offset(durpy.from_str(spec["options"]["staleness"]))
        fields = []
        for aggr in spec["options"]["aggr"]:
            aggr = aggr.name.lower()

            aggrf = aggr
            if aggrf == "avg":
                aggrf = "mean"
            f = f'{spec["fqn"]}[{aggr}]'
            feature_values[f] = feature_values \
                .groupby(["entity_id"]) \
                .rolling(win)["value"] \
                .agg(aggrf) \
                .reset_index(0, drop=True)
            fields.append(f)

        feature_values.reset_index(inplace=True)
        feature_values.drop(columns=["value"], inplace=True)
        feature_values = feature_values.melt(id_vars=["timestamp", "entity_id"], value_vars=fields,
                                             var_name="fqn", value_name="value")
        if store_locally:
            local_state.store_feature_values(feature_values)
        return feature_values

    return _replay


def __dependency_getter(fqn, eid, ts, val):
    try:
        spec = local_state.spec_by_fqn(fqn)
        if spec is None:
            raise Exception(f"feature `{fqn}` is not registered locally")

        ts = pd.to_datetime(ts)

        df = local_state.__feature_values
        odf = df
        df = df.loc[(df["fqn"] == fqn) & (df["entity_id"] == eid) & (df["timestamp"] <= ts)]

        staleness = durpy.from_str(spec["options"]["staleness"])
        if staleness.total_seconds() > 0:
            df = df.loc[(df["timestamp"] >= ts - staleness)]

        df = df.sort_values(by=["timestamp"], ascending=False).head(1)
        if df.empty:
            return str.encode("")
        res = df.iloc[0]

        v = pyexp.PyVal(handle=val)

        v.Value = json.dumps(res["value"])
        v.Timestamp = pyexp.PyTime(res["timestamp"].isoformat("T"), "")
        v.Fresh = True

        freshness = durpy.from_str(spec["options"]["freshness"])
        if freshness.total_seconds() > 0:
            v.Fresh = res["timestamp"] >= ts - freshness

    except Exception as e:
        """return error"""
        return str.encode(str(e))

    return str.encode("")


def __map(rt: pyexp.Runtime, timestamp_field: str, headers_field: str = None, entity_id_field: str = None):
    def map(row: pd.Series):
        ts = row[timestamp_field]
        # row.drop(timestamp_field, inplace=True)

        headers = go.nil
        if headers_field is not None:
            headers = row[headers_field]
            # row.drop(headers_field, inplace=True)

        entity_id = ""
        if entity_id_field is not None:
            entity_id = row[entity_id_field]
            # row.drop(entity_id_field, inplace=True)

        if isinstance(ts, datetime.datetime):
            ts = ts.isoformat("T")

        req = pyexp.PyExecReq(row.to_json(), __dependency_getter)
        req.Timestamp = pyexp.PyTime(ts, "")
        req.EntityID = entity_id
        req.Headers = headers

        try:
            res = rt.Exec(req)
            for i in res.Instructions:
                inst = pyexp.Instruction(handle=i)
                replay_instructions.__exec_instruction(inst)
            return json.loads(pyexp.JsonAny(res, "Value"))
        except RuntimeError as err:
            raise SystemExit(f"Error while executing PyExp: {str(err)}")
        except Exception as err:
            raise err

    return map


def historical_get(spec):
    def get(since: datetime.datetime, until: datetime.datetime):
        if spec["kind"] != "feature_set":
            raise Exception("Not a FeatureSet")
        if isinstance(since, str):
            since = pd.to_datetime(since)
        if isinstance(until, str):
            until = pd.to_datetime(until)

        if since > until:
            raise Exception("since > until")

        if since.tzinfo is None:
            since = since.replace(tzinfo=datetime.timezone.utc)
        if until.tzinfo is None:
            until = until.replace(tzinfo=datetime.timezone.utc)

        key_feature = spec["options"]["key_feature"]
        _key_feature_spec = local_state.spec_by_fqn(key_feature)
        features = spec["src"]

        if key_feature in features:
            features.remove(key_feature)

        df = local_state.__feature_values
        if df.empty:
            raise Exception("No data found. Have you Replayed on your data?")

        df = df.loc[(df["fqn"].isin(features + [key_feature]))
                    & (df["timestamp"] >= since)
                    & (df["timestamp"] <= until)
                    ]

        if df.empty:
            raise Exception("No data found")

        key_df = df.loc[df["fqn"] == key_feature]

        key_df.rename(columns={"value": key_feature}, inplace=True)
        key_df.drop(columns=["fqn"], inplace=True)

        for f in features:
            f_spec = local_state.spec_by_fqn(f)
            f_staleness = durpy.from_str(f_spec["options"]["staleness"])

            f_df = df.loc[df["fqn"] == f]
            f_df.rename(columns={"value": f}, inplace=True)
            f_df.drop(columns=["fqn"], inplace=True)
            # f_df["start_ts"] = f_df["end_ts"] - f_staleness

            if f_staleness.total_seconds() > 0:
                key_df = pd.merge_asof(key_df.sort_values("timestamp"), f_df.sort_values("timestamp"), on="timestamp",
                                       by="entity_id", direction="nearest", tolerance=f_staleness)
            else:
                key_df = pd.merge_asof(key_df.sort_values("timestamp"), f_df.sort_values("timestamp"), on="timestamp",
                                       by="entity_id", direction="nearest")

        return key_df.reset_index(drop=True)

    return get
