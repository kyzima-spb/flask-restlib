.. _configuration:


Configuration
=============

Set the required options in your configuration file that uses your framework:

=========================================    ================================================================
Option                                       Description
=========================================    ================================================================
`RESTLIB_URL_PREFIX`                         URL prefix for all API endpoints.
                                             Defaults to ``''``.
`RESTLIB_PAGINATION_ENABLED`                 Allow pagination for collections.
                                             Defaults to ``True``.
`RESTLIB_URL_PARAM_LIMIT`                    The name of the URL parameter
                                             that specifies the number of collection items per page.
                                             Defaults to ``limit``.
`RESTLIB_URL_PARAM_OFFSET`                   The name of the URL parameter
                                             that specifies the offset from the first item in the collection.
                                             Defaults to ``offset``.
`RESTLIB_PAGINATION_LIMIT`                   The default number of collection items per page.
                                             Defaults to ``25``.
`RESTLIB_SORTING_ENABLED`                    Allow sorting for collections.
                                             Defaults to ``True``.
`RESTLIB_URL_PARAM_SORT`                     The name of the URL parameter that is used for sorting.
                                             Defaults to ``sort``.
`RESTLIB_REMEMBER_ME`                        Allow users to remember them on the current device.
                                             The option only affects the display of the flag,
                                             the logic needs to be implemented.
                                             Defaults to ``False``.
`RESTLIB_HTTP_CACHE_DISABLE`                 Disable cache for safe operations.
                                             Defaults to ``False``.
`RESTLIB_CONCURRENCY_CONTROL_DISABLE`        Disable concurrency control for unsafe operations.
                                             Defaults to ``False``.
`RESTLIB_ID_FIELD`                           Name of the field used to uniquely identify resource items
                                             within the persistent storage.
                                             Defaults to ``'id'``.
`RESTLIB_CREATED_FIELD`                      Name for the field used to record a resource creation date.
                                             Defaults to ``'created'``.
`RESTLIB_UPDATED_FIELD`                      Name of the field used to record a resource last update date.
                                             Defaults to ``'updated'``.
`RESTLIB_DUMP_ONLY`                          Fields to skip during serialization (write-only fields).
                                             Defaults to ``()``.
`RESTLIB_LOAD_ONLY`                          Fields to skip during deserialization (read-only fields).
                                             Defaults to ``()``.
`RESTLIB_DEFAULT_SCOPE`                      Default scopes list.
                                             Used if no scope is specified for the client.
                                             Defaults to ``''``.
=========================================    ================================================================
