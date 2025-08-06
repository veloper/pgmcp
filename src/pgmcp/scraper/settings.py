from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, model_serializer


class Settings(BaseModel):
    # Core Scrapy settings with canonical names and types
    BOT_NAME                       : str            = Field(default="scrapybot",                               description="The name of the bot implemented by this Scrapy project.")
    CONCURRENT_ITEMS               : int            = Field(default=100,                                       description="Max number of concurrent items to process in pipelines.")
    CONCURRENT_REQUESTS            : int            = Field(default=16,                                        description="Max number of concurrent requests performed by the downloader.")
    CONCURRENT_REQUESTS_PER_DOMAIN : int            = Field(default=8,                                         description="Max concurrent requests per domain.")
    CONCURRENT_REQUESTS_PER_IP     : int            = Field(default=0,                                         description="Max concurrent requests per IP. If non-zero, overrides per-domain setting.")
    DEFAULT_ITEM_CLASS             : str            = Field(default="scrapy.Item",                             description="Default class used for items in the Scrapy shell.")
    DEPTH_LIMIT                    : int            = Field(default=0,                                         description="Max crawl depth. 0 means unlimited.")
    DEPTH_PRIORITY                 : int            = Field(default=0,                                         description="Adjusts request priority based on depth.")
    DNSCACHE_ENABLED               : bool           = Field(default=True,                                      description="Enable DNS in-memory cache.")
    DNSCACHE_SIZE                  : int            = Field(default=10000,                                     description="DNS in-memory cache size.")
    DNS_RESOLVER                   : str            = Field(default="scrapy.resolver.CachingThreadedResolver", description="The class to be used to resolve DNS names.")
    DOWNLOAD_DELAY                 : float          = Field(default=0,                                         description="Seconds to wait between consecutive requests to the same domain.")
    DOWNLOAD_TIMEOUT               : int            = Field(default=180,                                       description="Downloader timeout in seconds.")
    DUPEFILTER_CLASS               : str            = Field(default="scrapy.dupefilters.RFPDupeFilter",        description="Class used to detect and filter duplicate requests.")
    FEED_TEMPDIR                   : str | None     = Field(default=None,                                      description="Custom folder for temporary feed files.")
    FTP_PASSIVE_MODE               : bool           = Field(default=True,                                      description="Use passive mode for FTP transfers.")
    FTP_PASSWORD                   : str            = Field(default="guest",                                   description="FTP password if not set in Request meta.")
    FTP_USER                       : str            = Field(default="anonymous",                               description="FTP username if not set in Request meta.")
    ITEM_PIPELINES                 : Dict[str, int] = Field(default_factory=lambda: {
        "pgmcp.scraper.pipeline.Pipeline": 100,
    }, description="Item pipelines and their orders.")
    ITEM_PIPELINES_BASE            : Dict[str, int] = Field(default_factory=dict,                              description="Base item pipelines enabled by default in Scrapy.")
    JOBDIR                         : str | None     = Field(default=None,                                      description="Directory for storing crawl state for pausing/resuming.")

    # Logging settings
    LOG_ENABLED                    : bool       = Field(default=True,                                                description="Enable logging.")
    LOG_ENCODING                   : str        = Field(default="utf-8",                                             description="Encoding for logging output.")
    LOG_FILE                       : str | None = Field(default=None,                                                 description="File name for logging output. None means stderr.")
    LOG_FILE_APPEND                : bool       = Field(default=True,                                                description="Append to log file if True, overwrite if False.")
    LOG_DATEFORMAT                 : str        = Field(default="%Y-%m-%d %H:%M:%S",                                 description="Format string for log date/time.")
    LOG_LEVEL                      : str        = Field(default="DEBUG",                                             description="Minimum level to log. One of CRITICAL, ERROR, WARNING, INFO, DEBUG.")
    LOG_FORMAT                     : str        = Field(default="%(asctime)s [%(name)s] %(levelname)s: %(message)s", description="Format string for log messages.")

    # Request handling settings
    RANDOMIZE_DOWNLOAD_DELAY       : bool        = Field(default=True,                                                description="Randomize download delay between requests.")
    ROBOTSTXT_OBEY                 : bool        = Field(default=False,                                               description="Respect robots.txt policies.")
    SCHEDULER                      : str         = Field(default="scrapy.core.scheduler.Scheduler",                   description="Scheduler class to use for crawling.")

    # HTTP settings
    USER_AGENT                     : str            = Field(default="Scrapy/VERSION (+https://scrapy.org)", description="Default User-Agent for crawling.")
    DEFAULT_REQUEST_HEADERS        : Dict[str, str] = Field(default={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "en"}, description="Default headers for Scrapy HTTP requests.")
    
    # Extension and middleware settings
    ADDONS                         : Dict[str, int] = Field(default_factory=dict, description="Enabled add-ons and their priorities.")
    
    # AWS settings
    AWS_ACCESS_KEY_ID              : str | None  = Field(default=None, description="AWS access key for S3 and related services.")
    AWS_SECRET_ACCESS_KEY          : str | None  = Field(default=None, description="AWS secret key for S3 and related services.")
    AWS_SESSION_TOKEN              : str | None  = Field(default=None, description="AWS session token for temporary credentials.")
    AWS_ENDPOINT_URL               : str | None  = Field(default=None, description="Endpoint URL for S3-like storage.")
    AWS_USE_SSL                    : bool | None = Field(default=None, description="Use SSL for S3 connections.")
    AWS_VERIFY                     : bool | None = Field(default=None, description="Verify SSL for S3 connections.")
    AWS_REGION_NAME                : str | None  = Field(default=None, description="AWS region name for client.")
    
    # Advanced settings
    ASYNCIO_EVENT_LOOP             : str | None  = Field(default=None,      description="Import path for asyncio event loop class.")
    DEFAULT_DROPITEM_LOG_LEVEL     : str         = Field(default="WARNING", description="Default log level for dropped items.")
    DEPTH_STATS_VERBOSE            : bool        = Field(default=False,     description="Collect verbose depth stats.")
    DNS_TIMEOUT                    : float       = Field(default=60.0,      description="DNS query timeout in seconds.")
    DOWNLOADER_CLIENT_TLS_CIPHERS  : str         = Field(default="DEFAULT", description="TLS/SSL ciphers for HTTP/1.1 downloader.")
    DOWNLOADER_CLIENT_TLS_METHOD   : str         = Field(default="TLS",     description="TLS/SSL method for HTTP/1.1 downloader.")
    DOWNLOADER_CLIENT_TLS_VERBOSE_LOGGING: bool  = Field(default=False,     description="Enable verbose TLS logging.")
    DOWNLOADER_STATS               : bool        = Field(default=True,      description="Enable downloader stats collection.")
    DOWNLOADER                     : str         = Field(default="scrapy.core.downloader.Downloader", description="Downloader class to use.")
    DOWNLOADER_HTTPCLIENTFACTORY   : str         = Field(default="scrapy.core.downloader.webclient.ScrapyHTTPClientFactory", description="Twisted HTTP client factory for HTTP/1.0.")
    DOWNLOADER_CLIENTCONTEXTFACTORY: str         = Field(default="scrapy.core.downloader.contextfactory.ScrapyClientContextFactory", description="SSL/TLS context factory class.")
    DOWNLOADER_MIDDLEWARES         : Dict[str, int | None] = Field(default_factory=dict,          description="Enabled downloader middlewares and their orders.")
    DOWNLOADER_MIDDLEWARES_BASE    : Dict[str, int | None] = Field(default_factory=lambda: {
        "scrapy.downloadermiddlewares.offsite.OffsiteMiddleware"                 : 50,
        "scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware"             : 100,
        "scrapy.downloadermiddlewares.httpauth.HttpAuthMiddleware"               : 300,
        "scrapy.downloadermiddlewares.downloadtimeout.DownloadTimeoutMiddleware" : 350,
        "scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware"   : 400,
        "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware"             : 500,
        "scrapy.downloadermiddlewares.retry.RetryMiddleware"                     : 550,
        "scrapy.downloadermiddlewares.ajaxcrawl.AjaxCrawlMiddleware"             : 560,
        "scrapy.downloadermiddlewares.redirect.MetaRefreshMiddleware"            : 580,
        "scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware" : 590,
        "scrapy.downloadermiddlewares.redirect.RedirectMiddleware"               : 600,
        "scrapy.downloadermiddlewares.cookies.CookiesMiddleware"                 : 700,
        "scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware"             : 750,
        "scrapy.downloadermiddlewares.stats.DownloaderStats"                     : 850,
        "scrapy.downloadermiddlewares.httpcache.HttpCacheMiddleware"             : 900,
    }, description="Base downloader middlewares enabled by default in Scrapy.")
    
    DOWNLOAD_HANDLERS              : Dict[str, str] = Field(default_factory=dict, description="Enabled request download handlers.")
    DOWNLOAD_SLOTS                 : Dict[str, Any] = Field(default_factory=dict, description="Per-slot concurrency/delay parameters.")
    DOWNLOAD_MAXSIZE               : int            = Field(default=1073741824,   description="Max response body size in bytes.")
    DOWNLOAD_WARNSIZE              : int            = Field(default=33554432,     description="Warn if response size exceeds this value (bytes).")
    DOWNLOAD_FAIL_ON_DATALOSS      : bool           = Field(default=True,         description="Fail on broken responses (data loss).")
    DOWNLOAD_HANDLERS_BASE         : Dict[str, str] = Field(default_factory=lambda: {
        "data": "scrapy.core.downloader.handlers.datauri.DataURIDownloadHandler",
        "file": "scrapy.core.downloader.handlers.file.FileDownloadHandler",
        "http": "scrapy.core.downloader.handlers.http.HTTPDownloadHandler",
        "https": "scrapy.core.downloader.handlers.http.HTTPDownloadHandler",
        "s3": "scrapy.core.downloader.handlers.s3.S3DownloadHandler",
        "ftp": "scrapy.core.downloader.handlers.ftp.FTPDownloadHandler",
    }, description="Base download handlers enabled by default in Scrapy.")
    DUPEFILTER_DEBUG               : bool           = Field(default=False,        description="Log all duplicate requests.")
    
    EXTENSIONS                     : Dict[str, int | None] = Field(default_factory=lambda: {}, description="Enabled extensions and their priorities.")
    EXTENSIONS_BASE                : Dict[str, int | None] = Field(default_factory=lambda: {
        "scrapy.extensions.corestats.CoreStats"     : 0,
        "scrapy.extensions.telnet.TelnetConsole"    : 0,
        "scrapy.extensions.memusage.MemoryUsage"    : 0,
        "scrapy.extensions.memdebug.MemoryDebugger" : 0,
        "scrapy.extensions.closespider.CloseSpider" : 0,
        "scrapy.extensions.feedexport.FeedExporter" : 0,
        "scrapy.extensions.logstats.LogStats"       : 0,
        "scrapy.extensions.spiderstate.SpiderState" : 0,
        "scrapy.extensions.throttle.AutoThrottle"   : 0,
    }, description="Base extensions available by default in Scrapy.")
    
    # Feed export settings
    FEEDS                          : Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Feed export configuration.")
    FEED_STORAGE_GCS_ACL           : str | None             = Field(default=None,         description="ACL for Google Cloud Storage feeds.")
    FEED_STORAGE_S3_ACL            : str | None             = Field(default=None,         description="ACL for S3 feeds.")
    FEED_STORAGES                  : Dict[str, str]            = Field(default_factory=dict, description="Feed storage backends.")
    FEED_STORAGES_BASE             : Dict[str, str]            = Field(default_factory=dict, description="Base feed storage backends.")
    FEED_EXPORTERS                 : Dict[str, str]            = Field(default_factory=dict, description="Feed export formats.")
    FEED_EXPORTERS_BASE            : Dict[str, str]            = Field(default_factory=dict, description="Base feed export formats.")
    
    # Google Cloud settings
    GCS_PROJECT_ID                 : str | None = Field(default=None,                             description="Google Cloud Storage project ID.")
    
    # Additional logging settings
    LOG_FORMATTER                  : str         = Field(default="scrapy.logformatter.LogFormatter",  description="Class for formatting log messages.")
    LOG_STDOUT                     : bool        = Field(default=False,                               description="Redirect stdout/stderr to log.")
    LOG_SHORT_NAMES                : bool        = Field(default=False,                               description="Show only root path in logs.")
    LOGSTATS_INTERVAL              : float       = Field(default=60.0,                                description="Interval (seconds) between logging stats.")
    LOG_VERSIONS                   : List[str]   = Field(default_factory=lambda: ["lxml", "libxml2", "cssselect", "parsel", "w3lib", "Twisted", "Python", "pyOpenSSL", "cryptography", "Platform"], description="List of versions to log.")
    
    # Memory debugging and monitoring
    MEMDEBUG_ENABLED               : bool        = Field(default=False,        description="Enable memory debugging.")
    MEMDEBUG_NOTIFY                : List[str]   = Field(default_factory=list, description="Emails to notify for memory debug reports.")
    MEMUSAGE_ENABLED               : bool        = Field(default=True,         description="Enable memory usage extension.")
    MEMUSAGE_LIMIT_MB              : int         = Field(default=0,            description="Max memory usage (MB) before shutdown.")
    MEMUSAGE_CHECK_INTERVAL_SECONDS: float       = Field(default=60.0,         description="Interval (seconds) for memory usage checks.")
    MEMUSAGE_NOTIFY_MAIL           : List[str]   = Field(default_factory=list, description="Emails to notify if memory limit reached.")
    MEMUSAGE_WARNING_MB            : int         = Field(default=0,            description="Memory usage (MB) before warning email.")
    
    # Module and spider settings
    NEWSPIDER_MODULE               : str            = Field(default="",                              description="Module for new spiders.")
    SPIDER_CONTRACTS               : Dict[str, int] = Field(default_factory=dict,                    description="Enabled spider contracts and their orders.")
    SPIDER_CONTRACTS_BASE          : Dict[str, int] = Field(default_factory=lambda: {
        "scrapy.contracts.default.UrlContract": 1,
        "scrapy.contracts.default.ReturnsContract": 2,
        "scrapy.contracts.default.ScrapesContract": 3,
    }, description="Base spider contracts enabled by default in Scrapy.")

    SPIDER_LOADER_CLASS            : str            = Field(default="scrapy.spiderloader.SpiderLoader",  description="Class for loading spiders.")
    SPIDER_LOADER_WARN_ONLY        : bool           = Field(default=False,                               description="Warn only on spider import errors.")
    SPIDER_MIDDLEWARES             : Dict[str, int] = Field(default_factory=dict,                        description="Enabled spider middlewares and their orders.")
    SPIDER_MIDDLEWARES_BASE        : Dict[str, int] = Field(default_factory=lambda: {
        "scrapy.spidermiddlewares.httperror.HttpErrorMiddleware" : 50,
        "scrapy.spidermiddlewares.referer.RefererMiddleware"     : 700,
        "scrapy.spidermiddlewares.urllength.UrlLengthMiddleware" : 800,
        "scrapy.spidermiddlewares.depth.DepthMiddleware"         : 900,
    }, description="Base spider middlewares enabled by default in Scrapy.")

    SPIDER_MODULES                 : List[str]  = Field(default_factory=list, description="Modules to look for spiders.")
    
    # Reactor and threading settings
    REACTOR_THREADPOOL_MAXSIZE     : int        = Field(default=10, description="Max Twisted reactor thread pool size.")
    TWISTED_REACTOR                : str        = Field(default="twisted.internet.asyncioreactor.AsyncioSelectorReactor", description="Import path for Twisted reactor.")
    
    # Request routing and redirects
    REDIRECT_PRIORITY_ADJUST       : int        = Field(default=2, description="Adjust redirect request priority.")
    
    # Robots.txt settings
    ROBOTSTXT_PARSER               : str        = Field(default="scrapy.robotstxt.ProtegoRobotParser", description="Robots.txt parser backend.")
    ROBOTSTXT_USER_AGENT           : str | None = Field(default=None, description="User agent for robots.txt matching.")

    # Scheduler settings
    SCHEDULER_DEBUG                : bool = Field(default=False,                                description="Enable scheduler debug logging.")
    SCHEDULER_DISK_QUEUE           : str  = Field(default="scrapy.squeues.PickleLifoDiskQueue", description="Disk queue type for scheduler.")
    SCHEDULER_MEMORY_QUEUE         : str  = Field(default="scrapy.squeues.LifoMemoryQueue",     description="Memory queue type for scheduler.")
    SCHEDULER_START_DISK_QUEUE     : str  = Field(default="scrapy.squeues.PickleFifoDiskQueue", description="Disk queue type for start requests.")
    SCHEDULER_START_MEMORY_QUEUE   : str  = Field(default="scrapy.squeues.FifoMemoryQueue",     description="Memory queue type for start requests.")
    SCHEDULER_PRIORITY_QUEUE       : str  = Field(default="scrapy.pqueues.ScrapyPriorityQueue", description="Priority queue type for scheduler.")
    
    # Scraper settings
    SCRAPER_SLOT_MAX_ACTIVE_SIZE   : int         = Field(default=5000000, description="Soft limit (bytes) for active response data.")
    
    # Statistics settings
    STATS_CLASS                    : str       = Field(default="scrapy.statscollectors.MemoryStatsCollector", description="Class for collecting stats.")
    STATS_DUMP                     : bool      = Field(default=True,         description="Dump stats after spider finishes.")
    STATSMAILER_RCPTS              : List[str] = Field(default_factory=list, description="Emails to send stats after scraping.")
    
    # Template settings
    TEMPLATES_DIR                  : str       = Field(default="", description="Directory for Scrapy templates.")
    
    # URL handling
    URLLENGTH_LIMIT                : int       = Field(default=2083, description="Max allowed URL length.")
    
    # Additional core settings missing from original
    CLOSESPIDER_TIMEOUT            : int = Field(default=0, description="Timeout for closing spider.")
    CLOSESPIDER_ITEMCOUNT          : int = Field(default=0, description="Close spider after this many items.")
    CLOSESPIDER_PAGECOUNT          : int = Field(default=0, description="Close spider after this many pages.")
    CLOSESPIDER_ERRORCOUNT         : int = Field(default=0, description="Close spider after this many errors.")
    
    # Autothrottle extension
    AUTOTHROTTLE_ENABLED           : bool  = Field(default=False, description="Enable AutoThrottle extension.")
    AUTOTHROTTLE_START_DELAY       : float = Field(default=5.0,   description="Initial download delay.")
    AUTOTHROTTLE_MAX_DELAY         : float = Field(default=60.0,  description="Maximum download delay.")
    AUTOTHROTTLE_TARGET_CONCURRENCY: float = Field(default=1.0,   description="Target concurrency level.")
    AUTOTHROTTLE_DEBUG             : bool  = Field(default=False, description="Enable AutoThrottle debug logging.")
    
    # HTTP cache
    HTTPCACHE_ENABLED              : bool      = Field(default=False,        description="Enable HTTP caching.")
    HTTPCACHE_EXPIRATION_SECS      : int       = Field(default=0,            description="Cache expiration time in seconds.")
    HTTPCACHE_DIR                  : str       = Field(default="httpcache",  description="HTTP cache directory.")
    HTTPCACHE_IGNORE_HTTP_CODES    : List[int] = Field(default_factory=list, description="HTTP codes to ignore for caching.")
    HTTPCACHE_STORAGE              : str       = Field(default="scrapy.extensions.httpcache.FilesystemCacheStorage", description="HTTP cache storage backend.")
    HTTPCACHE_POLICY               : str       = Field(default="scrapy.extensions.httpcache.DummyPolicy", description="HTTP cache policy.")
    
    # Retry settings  
    RETRY_ENABLED                  : bool      = Field(default=True, description="Enable retry middleware.")
    RETRY_TIMES                    : int       = Field(default=2,    description="Maximum retry times.")
    RETRY_PRIORITY_ADJUST          : int       = Field(default=-1,   description="Adjust retry request priority.")
    RETRY_HTTP_CODES               : List[int] = Field(default=[500, 502, 503, 504, 522, 524, 408, 429], description="HTTP codes that trigger retries.")
    
    # Cookies
    COOKIES_ENABLED                : bool = Field(default=True,  description="Enable cookie middleware.")
    COOKIES_DEBUG                  : bool = Field(default=False, description="Enable cookie debug logging.")

    # Compression
    COMPRESSION_ENABLED            : bool = Field(default=True,  description="Enable response compression.")
    
    # Media pipeline settings
    MEDIA_ALLOW_REDIRECTS          : bool       = Field(default=False,        description="Allow redirects in media pipeline.")
    FILES_STORE                    : str | None = Field(default=None,         description="File storage path.")
    FILES_URLS_FIELD               : str        = Field(default="file_urls",  description="Item field containing file URLs.")
    FILES_RESULT_FIELD             : str        = Field(default="files",      description="Item field for file download results.")
    IMAGES_STORE                   : str | None = Field(default=None,         description="Image storage path.")
    IMAGES_URLS_FIELD              : str        = Field(default="image_urls", description="Item field containing image URLs.")
    IMAGES_RESULT_FIELD            : str        = Field(default="images",     description="Item field for image download results.")
    
    # Additional extension settings
    TELNETCONSOLE_ENABLED          : bool       = Field(default=True,         description="Enable telnet console.")
    TELNETCONSOLE_HOST             : str        = Field(default="127.0.0.1",  description="Telnet console host.")
    TELNETCONSOLE_PORT             : List[int]  = Field(default=[6023, 6073], description="Telnet console port range.")
    TELNETCONSOLE_PASSWORD         : str | None = Field(default=None,         description="Telnet console password.")
    TELNETCONSOLE_USERNAME         : str | None = Field(default=None,         description="Telnet console username.")
    
    # Item processor settings
    ITEM_PROCESSOR                 : str = Field(default="scrapy.pipelines.ItemPipelineManager", description="Item processor class.")
    
    # Commands module
    COMMANDS_MODULE                : str | None = Field(default=None, description="Module containing custom Scrapy commands.")
    
    # Email settings
    MAIL_FROM                      : str | None = Field(default=None,      description="Sender email address.")
    MAIL_HOST                      : str        = Field(default="localhost", description="SMTP server host.")
    MAIL_PORT                      : int        = Field(default=25,          description="SMTP server port.")
    MAIL_USER                      : str | None = Field(default=None,      description="SMTP username.")
    MAIL_PASS                      : str | None = Field(default=None,      description="SMTP password.")
    MAIL_TLS                       : bool       = Field(default=False,       description="Use TLS for SMTP connection.")
    MAIL_SSL                       : bool       = Field(default=False,       description="Use SSL for SMTP connection.")
    
    # Meta refresh settings
    METAREFRESH_ENABLED            : bool      = Field(default=True, description="Enable meta refresh middleware.")
    METAREFRESH_MAXDELAY           : int       = Field(default=100,  description="Maximum meta refresh delay in seconds.")
    METAREFRESH_IGNORE_TAGS        : List[str] = Field(default_factory=lambda: ["script", "noscript"], description="Tags to ignore for meta refresh.")
    
    # Redirect settings
    REDIRECT_ENABLED               : bool = Field(default=True, description="Enable redirect middleware.")
    REDIRECT_MAX_TIMES             : int  = Field(default=20,   description="Maximum number of redirects to follow.")
    
    # Referer settings
    REFERER_ENABLED                : bool = Field(default=True, description="Enable referer middleware.")
    REFERRER_POLICY                : str  = Field(default="scrapy.spidermiddlewares.referer.DefaultReferrerPolicy", description="Referrer policy class.")
    
    # HTTP Error settings
    HTTPERROR_ALLOWED_CODES        : List[int] = Field(default_factory=list, description="HTTP error codes to allow.")
    HTTPERROR_ALLOW_ALL            : bool      = Field(default=False,        description="Allow all HTTP error codes.")
    
    # HTTP Proxy settings
    HTTPPROXY_ENABLED              : bool = Field(default=True,      description="Enable HTTP proxy middleware.")
    HTTPPROXY_AUTH_ENCODING        : str  = Field(default="latin-1", description="Character encoding for proxy authentication.")
    
    # HTTP Cache advanced settings
    HTTPCACHE_ALWAYS_STORE         : bool      = Field(default=False,                    description="Always store responses in cache.")
    HTTPCACHE_DBM_MODULE           : str       = Field(default="dbm",                    description="DBM module for cache storage.")
    HTTPCACHE_GZIP                 : bool      = Field(default=False,                    description="Compress cached responses.")
    HTTPCACHE_IGNORE_MISSING       : bool      = Field(default=False,                    description="Ignore missing cache entries.")
    HTTPCACHE_IGNORE_SCHEMES       : List[str] = Field(default_factory=lambda: ["file"], description="URI schemes to ignore for caching.")
    HTTPCACHE_IGNORE_RESPONSE_CACHE_CONTROLS: List[str] = Field(default_factory=list,      description="Response cache control headers to ignore.")
    
    # Media pipeline advanced settings
    FILES_EXPIRES                  : int              = Field(default=90,           description="Files expiration time in days.")
    FILES_STORE_GCS_ACL            : str | None       = Field(default=None,         description="GCS ACL for files storage.")
    FILES_STORE_S3_ACL             : str | None       = Field(default=None,         description="S3 ACL for files storage.")
    IMAGES_EXPIRES                 : int              = Field(default=90,           description="Images expiration time in days.")
    IMAGES_MIN_HEIGHT              : int              = Field(default=0,            description="Minimum image height.")
    IMAGES_MIN_WIDTH               : int              = Field(default=0,            description="Minimum image width.")
    IMAGES_STORE_GCS_ACL           : str | None       = Field(default=None,         description="GCS ACL for images storage.")
    IMAGES_STORE_S3_ACL            : str | None       = Field(default=None,         description="S3 ACL for images storage.")
    IMAGES_THUMBS                  : Dict[str, tuple] = Field(default_factory=dict, description="Image thumbnail sizes.")
    
    # Feed export advanced settings
    FEED_EXPORT_ENCODING           : str              = Field(default="utf-8", description="Feed export encoding.")
    FEED_EXPORT_FIELDS             : List[str] | None = Field(default=None,    description="Fields to export in feeds.")
    FEED_EXPORT_INDENT             : int | None       = Field(default=None,    description="JSON indentation for feeds.")
    FEED_EXPORT_BATCH_ITEM_COUNT   : int              = Field(default=0,       description="Batch size for feed exports.")
    FEED_STORE_EMPTY               : bool             = Field(default=False,   description="Store empty feeds.")
    FEED_URI_PARAMS                : str | None       = Field(default=None,    description="URI parameters for feeds.")
    FEED_STORAGE_FTP_ACTIVE        : bool             = Field(default=False,   description="Use active FTP mode for feeds.")
    
    # CloseSpider extension settings
    CLOSESPIDER_TIMEOUT_NO_ITEM    : int = Field(default=0, description="Close spider after timeout with no items.")
    CLOSESPIDER_PAGECOUNT_NO_ITEM  : int = Field(default=0, description="Close spider after page count with no items.")
    
    # Periodic logging extension
    PERIODIC_LOG_STATS             : bool = Field(default=False, description="Enable periodic logging of stats.")
    PERIODIC_LOG_DELTA             : bool = Field(default=False, description="Log delta stats instead of totals.")
    PERIODIC_LOG_TIMING_ENABLED    : bool = Field(default=False, description="Enable timing information in periodic logs.")
    
    # Retry exceptions (documented elsewhere but missing)
    RETRY_EXCEPTIONS               : List[str]   = Field(default_factory=lambda: [
        "twisted.internet.defer.TimeoutError",
        "twisted.internet.error.TimeoutError",
        "twisted.internet.error.DNSLookupError",
        "twisted.internet.error.ConnectionRefusedError",
        "twisted.internet.error.ConnectionDone",
        "twisted.internet.error.ConnectError",
        "twisted.internet.error.ConnectionLost",
        "twisted.internet.error.TCPTimedOutError",
        "twisted.web.client.ResponseFailed",
        "builtins.IOError",
    ], description="Exception types that trigger retries.")
    
    # Warning settings
    DUPEFILTER_DEBUG : bool = Field(default=False, description="Log all duplicate requests.")
    
    # Final setting to fix the truncated one
    WARN_ON_GENERATOR_RETURN_VALUE : bool = Field(default=True,  description="Warn if generator callback returns a value.")

    @model_serializer
    def serialize(self) -> Dict[str, Any]:
        """Serialize the settings to a dictionary and handle merging _BASE versions
        with custom settings.
        
        This implements the Scrapy settings merging pattern where:
        1. Base settings provide defaults
        2. Custom settings override or extend base settings
        3. None values disable middlewares/extensions
        """
        # Access field values directly from the model instance to avoid recursion
        # Do NOT use self.model_dump() here as it would cause infinite recursion
        data = {}
        
        # Build data dict by accessing model fields directly
        for field_name, field_info in self.__class__.model_fields.items():
            # Get the raw value from the model instance
            value = getattr(self, field_name)
            
            # Convert Pydantic model values to serializable format
            if hasattr(value, 'model_dump'):
                # Handle nested Pydantic models
                value = value.model_dump()
            elif isinstance(value, list) and value and hasattr(value[0], 'model_dump'):
                # Handle lists of Pydantic models
                value = [item.model_dump() if hasattr(item, 'model_dump') else item for item in value]
            
            data[field_name] = value
        
        # Handle middleware merging patterns
        merged_data = {}
        
        for field_name, value in data.items():
            # Handle _BASE merging pattern for middleware/extension dicts
            if field_name.endswith('_BASE'):
                # This is a base setting, it will be merged with the non-_BASE version
                base_key = field_name
                custom_key = field_name.replace('_BASE', '')
                
                if custom_key in data:
                    # Merge base with custom settings
                    base_settings = value or {}
                    custom_settings = data[custom_key] or {}
                    
                    # Start with base settings
                    merged_settings = base_settings.copy()
                    
                    # Apply custom settings (None values disable middleware/extensions)
                    for k, v in custom_settings.items():
                        if v is None:
                            # None disables the middleware/extension
                            merged_settings.pop(k, None)
                        else:
                            # Override or add the setting
                            merged_settings[k] = v
                    
                    # Store the merged result under the custom key name
                    merged_data[custom_key] = merged_settings
                    
                # Don't include the _BASE key in final output
                continue
                
            elif field_name.replace('_BASE', '') + '_BASE' in data:
                # This field has a corresponding _BASE version, skip it here
                # as it will be handled by the _BASE processing above
                continue
            else:
                # Regular field, include as-is
                merged_data[field_name] = value
        
        return merged_data




class CustomSettings(Settings):
    """My custom scraper settings class that extends ScrapySettings with custom defaults."""

    HTTPCACHE_ENABLED              : bool  = Field(default=True)
    HTTPCACHE_DIR                  : str   = Field(default='/tmp/scrapy/httpcache')
    CONCURRENT_REQUESTS            : int   = Field(default=12)
    CONCURRENT_REQUESTS_PER_DOMAIN : int   = Field(default=3)
    RANDOMIZE_DOWNLOAD_DELAY       : bool  = Field(default=True)
    DOWNLOAD_DELAY                 : float = Field(default=0.25, description="Be respectful with delays")
    ROBOTSTXT_OBEY                 : bool  = Field(default=False)
    USER_AGENT                     : str   = Field(default='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36')
    LOG_LEVEL                      : str   = Field(default='INFO')
    DEPTH_LIMIT                    : int   = Field(default=3, description="Limit the depth of the crawl")

    EXTENSIONS : Dict[str, int | None] = Field(default_factory=lambda: {
        'pgmcp.scraper.job_state_ext.JobStateExt': 400,
        'pgmcp.scraper.job_periodic_status_ext.JobPeriodicStatusExt': 500,
    })

    ITEM_PIPELINES : Dict[str, int] = Field(default_factory=lambda: {
        'pgmcp.scraper.pipeline.Pipeline': 300
    })

