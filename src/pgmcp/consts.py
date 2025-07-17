from typing import Annotated, Dict, List, Tuple

from pydantic import Field


PG_TYPES_BY_CATEGORY = {
    "integer": [
        "SMALLINT", "INTEGER", "BIGINT", "INTARRAY", "INT4RANGE", "INT8RANGE", "INTAGG_STATE"
    ],
    "floating_point": [
        "REAL", "DOUBLE PRECISION"
    ],
    "serial_auto_increment": [
        "SMALLSERIAL", "SERIAL", "BIGSERIAL"
    ],
    "numeric_decimal": [
        "NUMERIC", "DECIMAL", "NUMRANGE"
    ],
    "character": [
        "CHAR", "CHARACTER", "CHARACTER VARYING", "VARCHAR", "CITEXT", "NAME"
    ],
    "text": [
        "TEXT", "LTXTQUERY"
    ],
    "boolean": [
        "BOOLEAN"
    ],
    "date": [
        "DATE", "DATERANGE"
    ],
    "time": [
        "TIME", "TIME WITH TIME ZONE", "TIME WITHOUT TIME ZONE", "TIMETZ"
    ],
    "timestamp": [
        "TIMESTAMP", "TIMESTAMP WITH TIME ZONE", "TIMESTAMP WITHOUT TIME ZONE", "TIMESTAMPTZ", "TSRANGE", "TSTZRANGE"
    ],
    "interval": [
        "INTERVAL"
    ],
    "network_address": [
        "CIDR", "INET", "MACADDR", "MACADDR8"
    ],
    "uuid": [
        "UUID"
    ],
    "json_jsonb": [
        "JSON", "JSONB", "JSONPATH"
    ],
    "range": [
        "INT4RANGE", "INT8RANGE", "NUMRANGE", "DATERANGE", "TSRANGE", "TSTZRANGE"
    ],
    "geometric": [
        "POINT", "LINE", "LSEG", "BOX", "PATH", "POLYGON", "CIRCLE", "SEG"
    ],
    "spatial_geospatial": [
        "GEOMETRY", "GEOGRAPHY", "BOX2D", "BOX3D", "RASTER", "H3INDEX", "SPHEROID", "TOPOGEOMETRY", "EARTH"
    ],
    "full_text_search": [
        "TSVECTOR", "TSQUERY", "LQUERY", "LTREE", "TRIGRAM", "GTRGM"
    ],
    "array": [
        "ANYARRAY", "REGCLASSARRAY", "REGCOLLATIONARRAY", "REGCONFIGARRAY", "REGDICTIONARYARRAY",
        "REGNAMESPACEARRAY", "REGOPERARRAY", "REGOPERATORARRAY", "REGPROCEDUREARRAY", "REGROLEARRAY",
        "REGTYPEARRAY"
    ],
    "money_currency": [
        "MONEY"
    ],
    "handler_support": [
        "FDW_HANDLER", "LANGUAGE_HANDLER", "TSM_HANDLER", "EVENT_TRIGGER", "TRIGGER"
    ],
    "extension_custom": [
        "AGTYPE", "BLOOM", "CUBE", "EAN13", "HASHID", "HSTORE", "HTTP_REQUEST", "HTTP_RESPONSE", "ISBN",
        "ISBN13", "ISMN", "ISSN", "PG_ENCRYPTED_PASSWORD", "PG_MCV_LIST", "PG_NDISTINCT", "PG_NODE_TREE",
        "PG_SNAPSHOT", "PGENCRYPTEDPASSWORD", "SIMHASH", "SIMILARITY", "UPC", "VECTOR", "XML"
    ],
    "binary_data": [
        "BYTEA", "CSTRING"
    ],
    "bit_string": [
        "BIT", "BIT VARYING"
    ],
}

PG_TYPES = []
PG_TYPES.extend(x for category in PG_TYPES_BY_CATEGORY.values() for x in category)
PG_TYPES = sorted(set(PG_TYPES))
PG_TYPES_PATTERN = "|".join([fr"^{x}(\[.*\])?$" for x in PG_TYPES])
PG_FUNCTION_NAME_PATTERN = r"^[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*$"
PG_FUNCTION_ARG_NAME_PATTERN = r"^[a-zA-Z_][a-zA-Z0-9_]*$"
