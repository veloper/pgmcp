import os

from collections import OrderedDict
from typing import Any, ClassVar, List, Self, Tuple, Union
from urllib.parse import urlparse

from pydantic import BaseModel, Field, SecretStr

from pgmcp.query_string_codec import QueryStringCodec


class DataSourceName(BaseModel):
    """Database connection string parser and validator."""

    query_string_codec: ClassVar[QueryStringCodec] = QueryStringCodec(
        encoding='utf-8',
        errors='replace',
        keep_blank_values=True
    )

    
    # Required fields
    driver:      str = Field(default="postgresql", description="Database driver, e.g., 'postgresql', 'sqlite3', etc.")
    username:    str = Field(...)
    hostname:    str = Field(...)
    port:        int = Field(...)
    
    # Optional fields
    password:    SecretStr | None = Field(default=None)
    database:    str | None = Field(default=None, description="Database name, if applicable")
    query:      OrderedDict[str, Any] | None = Field(default=None, description="Additional settings pulled from the DSN's query string")

    def model_dump_string(self, mask_secrets: bool = False) -> str:
        """Returns the FULL unmasked DSN string representation of this DataSourceName.
        
        ATTENTION: SecretStr values are NOT masked using this method as it will likely be used actually connect to the database.
                   Optionally, you can specify `mask_secrets=True` if that is desired.
        """

        query_str = self.query_string_codec.encode(self.query) if self.query else ''
        
        password : str = ""
        if self.password:
            if mask_secrets:
                password = "********"
            else:
                password = self.password.get_secret_value()
        
        # Construct the DSN string
        dsn_parts = filter(lambda x: x, [
            f"{self.driver}://",
            f"{self.username}",
            f":{password}" if password else "",
            f"@{self.hostname}",
            f":{self.port}" if self.port else "",
            f"/{self.database}" if self.database else "",
            f"?{query_str}" if query_str else ""
        ])

        return ''.join(dsn_parts)
    
    def __str__(self) -> str:
        """Return safe masked string representation of this DataSourceName."""
        return self.model_dump_string(mask_secrets=True)
    
    @classmethod
    def parse(cls, dsn_str: str) -> Self:
        """Create a DataSourceName instance from a DSN string with parsed components."""
        # expand any environment variables as interpolated values
        dsn_str = os.path.expandvars(dsn_str)
        parsed = urlparse(dsn_str)

        return cls.model_validate({
            "driver": parsed.scheme,
            "username": parsed.username,
            "password": SecretStr(parsed.password) if parsed.password else None,
            "hostname": parsed.hostname,
            "port": parsed.port,
            "database": parsed.path.lstrip('/') if parsed.path else None,
            "query": cls.query_string_codec.decode(parsed.query),
        })
