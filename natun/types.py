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

import re
import types
from enum import Enum


class AggrFn(Enum):
    Unknown = 0
    Sum = 1
    Avg = 2
    Max = 3
    Min = 4
    Count = 5


class PyExpTraceFrame:
    def __init__(self, frame):
        self.frame = frame
        self.f_lineno = frame.f_lineno


def WrapException(e: Exception, spec, *args, **kwargs):
    frame_str = re.match(r".*<pyexp>:([0-9]+):([0-9]+)?: (.*)", str(e).replace("\n", ""), flags=re.MULTILINE)
    if frame_str is None or "src_frame" not in spec or spec["src_frame"] is None:
        return e
    else:
        err_str = re.match(r"in (.*)Error in ([aA0-zZ09_]+): (.*)", frame_str.group(3))
        if err_str is None:
            err_str = frame_str.group(3).strip()
        else:
            err_str = f"Error in {err_str.group(2)}: {err_str.group(3).strip()}"
        frame = spec["src_frame"]
        loc = frame.f_lineno + int(frame_str.group(1)) - 1
        tb = types.TracebackType(tb_next=None,
                                 tb_frame=frame.frame,
                                 tb_lasti=e.__traceback__.tb_lasti,
                                 tb_lineno=loc)
        return PyExpException(
            f"on {spec['src_name']}:\n    {err_str}\n\n️Friendly tip: remember that PyExp is not python3 😬")\
            .with_traceback(tb)


class PyExpException(RuntimeError):
    def __int__(self, *args, **kwargs):
        Exception.__init__(*args, **kwargs)