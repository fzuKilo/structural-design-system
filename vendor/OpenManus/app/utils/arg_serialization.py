import json
import base64
from typing import Dict, Any


def encode_args(args: Dict[str, Any]) -> str:
    """Encode arguments dict into a JSON string, base64-encoding long or multiline text fields.

    Fields ending with `_b64` are preserved as-is.
    """
    out = {}
    for k, v in args.items():
        if k.endswith("_b64"):
            out[k] = v
            continue
        if isinstance(v, str) and ("\n" in v or '"' in v or len(v) > 200):
            out[f"{k}_b64"] = base64.b64encode(v.encode("utf-8")).decode("ascii")
        else:
            out[k] = v
    return json.dumps(out)


def decode_args(arg_str: str) -> Dict[str, Any]:
    """Decode arguments produced by `encode_args` (or a plain JSON string).

    Converts any key ending with `_b64` into the decoded original key.
    """
    try:
        data = json.loads(arg_str)
    except Exception:
        # If it's already a dict-like string produced elsewhere, re-raise
        raise

    out: Dict[str, Any] = {}
    for k, v in data.items():
        if k.endswith("_b64"):
            orig = k[: -4]
            try:
                out[orig] = base64.b64decode(v).decode("utf-8")
            except Exception:
                out[orig] = v
        else:
            out[k] = v
    return out
