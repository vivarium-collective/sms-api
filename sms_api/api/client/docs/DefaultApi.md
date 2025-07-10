# sms_api.api.client.DefaultApi

All URIs are relative to _http://localhost_

| Method                                                               | HTTP request     | Description  |
| -------------------------------------------------------------------- | ---------------- | ------------ |
| [**check_health_health_get**](DefaultApi.md#check_health_health_get) | **GET** /health  | Check Health |
| [**get_version_version_get**](DefaultApi.md#get_version_version_get) | **GET** /version | Get Version  |
| [**home_get**](DefaultApi.md#home_get)                               | **GET** /        | Home         |

# **check_health_health_get**

> Dict[str, str] check_health_health_get()

Check Health

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
        # Check Health
        api_response = api_instance.check_health_health_get()
        print("The response of DefaultApi->check_health_health_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->check_health_health_get: %s\n" % e)
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

| Status code | Description         | Response headers |
| ----------- | ------------------- | ---------------- |
| **200**     | Successful Response | -                |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

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

| Status code | Description         | Response headers |
| ----------- | ------------------- | ---------------- |
| **200**     | Successful Response | -                |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **home_get**

> object home_get()

Home

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
        # Home
        api_response = api_instance.home_get()
        print("The response of DefaultApi->home_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->home_get: %s\n" % e)
```

### Parameters

This endpoint does not need any parameter.

### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

### HTTP response details

| Status code | Description         | Response headers |
| ----------- | ------------------- | ---------------- |
| **200**     | Successful Response | -                |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)
