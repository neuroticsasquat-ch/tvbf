"""The base class every Pydantic shape of *our* API inherits (NEU-2261).

One setting, and it exists for the committed `openapi.json` and the SPA types generated from it.
By default Pydantic leaves a field with a default out of `required` even in the serialization
schema, so `type: str | None = None` reaches the SPA as `type?: string | null`. That is not what
the API does: no route excludes unset or `None` fields, so every field of a response is always
present. `json_schema_serialization_defaults_required` says so, and only in the serialization
(response) schema; the validation (request) schema still marks a defaulted field optional, which
is what a request may genuinely omit.

Upstream parsers (`*/api_payloads.py`, `integrations/`) do not inherit it: they are never in the
document. A route that starts excluding fields from its response (`response_model_exclude_none`
and friends) makes this a lie for that model, and needs the field typed optional instead.
"""

from pydantic import BaseModel, ConfigDict


class ApiSchema(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)
