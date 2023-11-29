from jmespath import functions
import uuid
import datetime


class OrganizationFunctionsDiscoverAndStore(functions.Functions):    
    # create the id
    @functions.signature({'types': ['string']})
    def _func_get_id(self, type):
        return "urn:ngsi-ld:" + type + ":" + str(uuid.uuid4())  

    # create timestamp
    @functions.signature()
    def _func_get_timestamp(self):
        timest = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
        return str(timest)
    
    # create the streetaddress
    @functions.signature({'types': ['string']},{'types': ['string']})
    def _func_get_streetaddress(self, street, housenumber):
        streetaddress = street + " "+ housenumber  
        if streetaddress == " ":
            streetaddress = None
        return streetaddress

    # create the legalname
    @functions.signature({'types': ['string']},{'types': ['string']})
    def _func_get_legalname(self, name, legalform):
        legalname = name + " " + legalform
        if legalname == "":
            legalname = None
        return legalname
    
    @functions.signature({'types': ['string']})
    def _func_check_string(self, value):
        if value == "":
            value = None            
        return value
        
