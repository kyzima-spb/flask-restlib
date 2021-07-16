.. _configuration:


Configuration
=============

Set the required options in your configuration file that uses your framework:

=========================================    ================================================================
Option                                       Description
=========================================    ================================================================
`RESTLIB_URL_PREFIX`                         URL prefix for all API endpoints.
                                             Defaults to ``''``.
`RESTLIB_PAGINATION_ENABLED`                 Allowe pagination for collections.
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
=========================================    ================================================================
