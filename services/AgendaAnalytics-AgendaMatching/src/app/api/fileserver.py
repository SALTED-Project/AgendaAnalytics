import requests
import json

from app.logs.logger import logging_text
import app.definitions as definitions

def upload(salted_fileserver_service, content, filename):
    try: 
        special_char_map = {ord('ä'):'ae', ord('ü'):'ue', ord('ö'):'oe', ord('ß'):'ss'}
        filename = filename.translate(special_char_map)
        logging_text.info("uploading results to SALTED fileserver")
        r = requests.post(
                salted_fileserver_service+"/files/",
                files= [('file',(filename, content))]
            )
        logging_text.info(r.text)
        response_json = r.json()
        file_uuid = response_json[0]
        status_code = definitions.MESSAGE_SUCCESS
    except Exception as e:
        status_code = definitions.MESSAGE_ERROR
        file_uuid = None
        logging_text.info(e)
    return status_code, file_uuid