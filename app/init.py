import requests
import logging
import os
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# PyACI requires to have the MetaData present locally. Since the metada changes depending on the APIC version I use an init container to pull it. 
# No you can't put it in the same container as the moment you try to import pyaci it crashed is the metadata is not there. Plus init containers are cool!
# Get the APIC Model. s.environ.get("APIC_IPS").split(',')[0] gets me the first APIC here I don't care about RR
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter(
        '%(asctime)s %(name)-1s %(levelname)-1s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

logger.info("Loading ACI Metadata")
try:
    url = "https://" + os.environ.get("APIC_IPS").split(',')[0]
    requests.get(url, verify=False, allow_redirects=True)
except Exception as e:
    logger.error("Unable to Connect to APIC %s", str(e))
    exit(1)

url = "https://" + os.environ.get("APIC_IPS").split(',')[0] + '/acimeta/aci-meta.json'
r = requests.get(url, verify=False, allow_redirects=True)
if os.environ.get("MODE") == "LOCAL":
    open('/tmp/aci-meta-vkaci.json','wb').write(r.content)
else:
    open('/app/aci-meta/aci-meta.json','wb').write(r.content)
logger.info("ACI Metadata Loaded")