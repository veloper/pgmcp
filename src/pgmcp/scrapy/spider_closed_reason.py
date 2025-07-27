from enum import Enum
from typing import List


class SpiderClosedReason(Enum):
    FINISHED          = "finished"
    SHUTDOWN          = "shutdown"                      # Graceful shutdown (e.g., SIGTERM, pause with JOBDIR)
    CANCELLED         = "cancelled"                     # Manual/coded cancellation (e.g., CloseSpider exception/default)
    TIMEOUT           = "closespider_timeout"           # CLOSESPIDER_TIMEOUT: Closed due to exceeding CLOSESPIDER_TIMEOUT (seconds)
    TIMEOUT_NO_ITEM   = "closespider_timeout_no_item"   # CLOSESPIDER_TIMEOUT_NO_ITEM: Closed due to exceeding CLOSESPIDER_TIMEOUT_NO_ITEM (seconds without items)
    ITEMCOUNT         = "closespider_itemcount"         # CLOSESPIDER_ITEMCOUNT: Closed due to exceeding CLOSESPIDER_ITEMCOUNT (max items)
    PAGECOUNT         = "closespider_pagecount"         # CLOSESPIDER_PAGECOUNT: Closed due to exceeding CLOSESPIDER_PAGECOUNT (max responses/pages)
    PAGECOUNT_NO_ITEM = "closespider_pagecount_no_item" # CLOSESPIDER_PAGECOUNT_NO_ITEM: Closed due to exceeding CLOSESPIDER_PAGECOUNT_NO_ITEM (max consecutive responses with no items)
    ERRORCOUNT        = "closespider_errorcount"        # CLOSESPIDER_ERRORCOUNT: Closed due to exceeding CLOSESPIDER_ERRORCOUNT (max errors)

    UNKNOWN          = "unknown"                        # Unknown reason, not pre-defined by Scrapy

    def is_failure(self) -> bool: return self in self.get_failures()
    def is_success(self) -> bool: return self == self.FINISHED
    
    def get_loggable_reason(self) -> str:
        """Return an explanation for why the spider was closed."""
        if self == self.FINISHED:
            return "Finished successfully."
        if self == self.SHUTDOWN:
            return "Shutdown gracefully or paused (e.g., SIGTERM, JOBDIR)."
        elif self == self.CANCELLED:
            return "Cancelled manually or by code before completion (e.g., CloseSpider exception, usually due to an unhandled error)."
        elif self == self.TIMEOUT:
            return "Exceeded CLOSESPIDER_TIMEOUT setting (seconds)."
        elif self == self.TIMEOUT_NO_ITEM:
            return "Exceeded CLOSESPIDER_TIMEOUT_NO_ITEM setting (seconds without items)."
        elif self == self.ITEMCOUNT:
            return "Exceeded CLOSESPIDER_ITEMCOUNT setting (max items)."
        elif self == self.PAGECOUNT:
            return "Exceeded CLOSESPIDER_PAGECOUNT setting (max responses/pages)."
        elif self == self.PAGECOUNT_NO_ITEM:
            return "Exceeded CLOSESPIDER_PAGECOUNT_NO_ITEM setting (max consecutive responses with no items)."
        elif self == self.ERRORCOUNT:
            return "Exceeded CLOSESPIDER_ERRORCOUNT setting (max errors)."
        else:
            return "Unknown reason for closure, not pre-defined by Scrapy."

    @classmethod
    def from_reported_reason(cls, reported_reason: str) -> "SpiderClosedReason":
        """Create a CloseSpiderReason from a reported reason string."""
        if not isinstance(reported_reason, str):
            raise TypeError(f"Expected a string, got {type(reported_reason).__name__}.")

        for reason in cls:
            if reason.value == reported_reason:
                return reason

        return cls.UNKNOWN

    @classmethod
    def is_recognized(cls, reported_reason: str) -> bool:
        """Check if the reported reason is one of the defined shutdown reasons."""
        if not isinstance(reported_reason, str):
            raise TypeError(f"Expected a string, got {type(reported_reason).__name__}.")
        return reported_reason in [reason.value for reason in cls]


    @classmethod
    def get_failures(cls) -> List["SpiderClosedReason"]:
        """Return a list of all failure reasons -- yes, unknown is a failure."""
        return [
            cls.SHUTDOWN,
            cls.CANCELLED,
            cls.TIMEOUT,
            cls.TIMEOUT_NO_ITEM,
            cls.ITEMCOUNT,
            cls.PAGECOUNT,
            cls.PAGECOUNT_NO_ITEM,
            cls.ERRORCOUNT,
            cls.UNKNOWN
        ]
