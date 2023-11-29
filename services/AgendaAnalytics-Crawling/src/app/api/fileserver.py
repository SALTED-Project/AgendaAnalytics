import requests
import json

from app.logs.logger import logging_text
import app.definitions as definitions

def upload(salted_fileserver_service,content, filename):
    try: 
        logging_text.info("uploading crawling results to SALTED fileserver")
        special_char_map = {ord('ä'):'ae', ord('ü'):'ue', ord('ö'):'oe', ord('ß'):'ss'}
        filename = filename.translate(special_char_map)
        r = requests.post(
                salted_fileserver_service+"/files/",
                files= [('file',(filename, content))]
            )
        response_json = r.json()
        file_uuid = response_json[0]
        status_code = definitions.MESSAGE_SUCCESS
    except:
        status_code = definitions.MESSAGE_ERROR
        logging_text.info(r.text)
        file_uuid = None
    return status_code, file_uuid