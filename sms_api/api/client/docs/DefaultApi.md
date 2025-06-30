# sms_api.api.client.DefaultApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_version_version_get**](DefaultApi.md#get_version_version_get) | **GET** /version | Get Version
[**root_get**](DefaultApi.md#root_get) | **GET** / | Root


# **get_version_version_get**
> str get_version_version_get()

Get Version

### Example


```python
import sms_api.api.client
from sms_api.api.client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = sms_api.api.client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with sms_api.api.client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = sms_api.api.client.DefaultApi(api_client)

    try:
        # Get Version
        api_response = api_instance.get_version_version_get()
        print("The response of DefaultApi->get_version_version_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->get_version_version_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**str**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **root_get**
> Dict[str, str] root_get()

Root

### Example


```python
import sms_api.api.client
from sms_api.api.client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = sms_api.api.client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with sms_api.api.client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = sms_api.api.client.DefaultApi(api_client)

    try:
        # Root
        api_response = api_instance.root_get()
        print("The response of DefaultApi->root_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->root_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**Dict[str, str]**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

