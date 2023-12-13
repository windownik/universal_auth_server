
import clicksend_client
from clicksend_client import SmsMessage
from clicksend_client.rest import ApiException


configuration = clicksend_client.Configuration()
configuration.username = 'info@tyreapp.co.uk'
configuration.password = 'FDEA7587-E160-AC1B-3804-AF559C4DE5BD'

# create an instance of the API class
api_instance = clicksend_client.SMSApi(clicksend_client.ApiClient(configuration))


def send_sms_code(check_code: int, phone: int) -> bool:
    sms_message = SmsMessage(source="php",
                             body=f"TyreApp validation code #{check_code}",
                             to=f"+{phone}", )

    sms_messages = clicksend_client.SmsMessageCollection(messages=[sms_message])

    try:
        # Send sms message(s)
        api_response = api_instance.sms_send_post(sms_messages)
        print(api_response)
        return True
    except ApiException as e:
        print("Exception when calling SMSApi->sms_send_post: %s\n" % e)
        return False
