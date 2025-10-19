import urllib.request
import urllib.error
import base64
import xml.etree.ElementTree as ET
from urllib.request import HTTPPasswordMgrWithDefaultRealm, HTTPDigestAuthHandler, build_opener
import socket
import time
from .libs.colors import success, error, warning
from .libs.logger import log_info, log_error, log_warning, log_success


class FritzBoxTR064:
    def __init__(self, host="192.168.1.1", port=49000, username="", password=""):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.base_url = f"http://{host}:{port}"
        self.session_id = None

    def _make_soap_request(self, service_url, action, soap_body, use_auth=True):
        """Make a SOAP request to the FritzBox with improved error handling"""

        soap_envelope = f'''<?xml version="1.0" encoding="utf-8"?>
                            <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
                                <s:Body>
                                    {soap_body}
                                </s:Body>
                            </s:Envelope>'''

        url = f"{self.base_url}{service_url}"

        # Log the attempt (without credentials)
        log_info(f"Making SOAP request to {service_url}")

        if use_auth and self.username and self.password:
            # Try with digest authentication first
            try:
                return self._make_authenticated_request(url, soap_envelope, action)
            except Exception as e:
                log_error(f"Authenticated request failed: {e}")
                return None
        else:
            # Try without authentication
            return self._make_simple_request(url, soap_envelope, action)

    def _make_simple_request(self, url, soap_envelope, action):
        """Make a simple SOAP request without authentication"""
        req = urllib.request.Request(url, data=soap_envelope.encode('utf-8'))
        req.add_header('Content-Type', 'text/xml; charset="utf-8"')
        req.add_header('SOAPAction', f'"{action}"')

        try:
            response = urllib.request.urlopen(req, timeout=10)
            return response.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            log_error(f"HTTP Error {e.code}: {e.reason}")
            return None
        except Exception as e:
            log_error(f"Request failed: {e}")
            return None

    def _make_authenticated_request(self, url, soap_envelope, action):
        """Make an authenticated SOAP request with digest auth"""
        # Create password manager and add credentials
        password_mgr = HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, url, self.username, self.password)

        # Create digest auth handler
        digest_handler = HTTPDigestAuthHandler(password_mgr)

        # Build opener with digest auth
        opener = build_opener(digest_handler)

        # Prepare request
        req = urllib.request.Request(url, data=soap_envelope.encode('utf-8'))
        req.add_header('Content-Type', 'text/xml; charset="utf-8"')
        req.add_header('SOAPAction', f'"{action}"')

        try:
            response = opener.open(req, timeout=10)
            return response.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            if e.code == 401:
                # Try basic auth as fallback
                return self._try_basic_auth(url, soap_envelope, action)
            else:
                print(f"HTTP Error {e.code}: {e.reason}")
                return None
        except Exception as e:
            print(f"Digest auth failed: {e}")
            # Try basic auth as fallback
            return self._try_basic_auth(url, soap_envelope, action)

    def _try_basic_auth(self, url, soap_envelope, action):
        """Try basic authentication as fallback"""
        print("Trying basic authentication as fallback...")

        req = urllib.request.Request(url, data=soap_envelope.encode('utf-8'))
        req.add_header('Content-Type', 'text/xml; charset="utf-8"')
        req.add_header('SOAPAction', f'"{action}"')

        # Add basic auth header
        auth_string = base64.b64encode(
            f"{self.username}:{self.password}".encode()).decode()
        req.add_header('Authorization', f'Basic {auth_string}')

        try:
            response = urllib.request.urlopen(req, timeout=10)
            return response.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            if e.code == 401:
                print("Authentication failed with both digest and basic auth.")
                print("Please verify:")
                print("1. Username and password are correct")
                print("2. User has admin privileges")
                print("3. TR-064 access is enabled for this user")
                return None
            else:
                print(f"HTTP Error {e.code}: {e.reason}")
                return None
        except Exception as e:
            print(f"Basic auth also failed: {e}")
            return None

    def get_device_info(self):
        """Get basic device information"""
        soap_body = '''
        <u:GetInfo xmlns:u="urn:dslforum-org:service:DeviceInfo:1">
        </u:GetInfo>'''

        response = self._make_soap_request(
            "/upnp/control/deviceinfo",
            "urn:dslforum-org:service:DeviceInfo:1#GetInfo",
            soap_body
        )

        if response:
            try:
                root = ET.fromstring(response)
                # Extract device info from SOAP response
                for elem in root.iter():
                    if 'ModelName' in elem.tag:
                        print(f"Model: {elem.text}")
                    elif 'SoftwareVersion' in elem.tag:
                        print(f"Software Version: {elem.text}")
                    elif 'SerialNumber' in elem.tag:
                        print(f"Serial Number: {elem.text}")
                return True
            except ET.ParseError:
                print(error("Failed to parse device info response"))
                return False
        return False

    def restart_router(self):
        """Send restart command to the FritzBox router"""
        log_info(f"Attempting to restart FritzBox at {self.host}...")

        # First, try to get device info to verify connection
        log_info("Verifying device connection...")
        if not self.get_device_info():
            log_warning(
                "Could not retrieve device info, proceeding with restart anyway...")

        # Try different restart methods
        restart_methods = [
            {
                'name': 'DeviceConfig Reboot',
                'service_url': '/upnp/control/deviceconfig',
                'action': 'urn:dslforum-org:service:DeviceConfig:1#Reboot',
                'soap_body': '''<u:Reboot xmlns:u="urn:dslforum-org:service:DeviceConfig:1"></u:Reboot>'''
            },
            {
                'name': 'DeviceConfig Restart',
                'service_url': '/upnp/control/deviceconfig',
                'action': 'urn:dslforum-org:service:DeviceConfig:1#Restart',
                'soap_body': '''<u:Restart xmlns:u="urn:dslforum-org:service:DeviceConfig:1"></u:Restart>'''
            },
            {
                'name': 'Alternative DeviceConfig',
                'service_url': '/tr064/upnp/control/deviceconfig',
                'action': 'urn:dslforum-org:service:DeviceConfig:1#Reboot',
                'soap_body': '''<u:Reboot xmlns:u="urn:dslforum-org:service:DeviceConfig:1"></u:Reboot>'''
            }
        ]

        for method in restart_methods:
            log_info(f"Trying {method['name']}...")

            response = self._make_soap_request(
                method['service_url'],
                method['action'],
                method['soap_body']
            )

            if response is not None:
                log_success(
                    f"Restart command sent successfully using {method['name']}!")
                log_info("The router should reboot within 30-60 seconds.")
                return True
            else:
                log_warning(f"{method['name']} failed, trying next method...")

        log_error("All restart methods failed.")
        return False

    def discover_services(self):
        """Discover available TR-064 services"""
        log_info("Discovering TR-064 services...")

        # Try to get the device description
        try:
            req = urllib.request.Request(f"{self.base_url}/tr64desc.xml")
            response = urllib.request.urlopen(req, timeout=10)
            xml_content = response.read().decode('utf-8')

            log_success("TR-064 device description found!")

            # Parse the XML to find services
            try:
                root = ET.fromstring(xml_content)
                services = []

                for service in root.iter():
                    if service.tag.endswith('service'):
                        service_type = None
                        control_url = None

                        for child in service:
                            if child.tag.endswith('serviceType'):
                                service_type = child.text
                            elif child.tag.endswith('controlURL'):
                                control_url = child.text

                        if service_type and control_url:
                            services.append((service_type, control_url))

                if services:
                    log_info("Available services:")
                    for service_type, control_url in services:
                        log_info(f"  - {service_type} -> {control_url}")
                else:
                    log_warning("No services found in device description")

                return services

            except ET.ParseError as e:
                log_error(f"Failed to parse device description: {e}")
                return []

        except Exception as e:
            log_error(f"Failed to get device description: {e}")

            # Try alternative discovery
            log_info("Trying alternative service discovery...")
            return self._try_common_services()

    def _try_common_services(self):
        """Try common TR-064 service endpoints"""
        common_endpoints = [
            "/upnp/control/deviceconfig",
            "/tr64/upnp/control/deviceconfig",
            "/upnp/control/deviceinfo",
            "/tr64/upnp/control/deviceinfo"
        ]

        working_endpoints = []

        for endpoint in common_endpoints:
            try:
                # Try a simple request to see if endpoint exists
                req = urllib.request.Request(f"{self.base_url}{endpoint}")
                req.add_header('Content-Type', 'text/xml')

                # This will likely fail with 405 (Method Not Allowed) but that's OK -
                # it means the endpoint exists
                try:
                    urllib.request.urlopen(req, timeout=5)
                except urllib.error.HTTPError as e:
                    if e.code in [405, 401, 500]:  # These indicate the endpoint exists
                        working_endpoints.append(endpoint)
                        log_success(f"Found endpoint: {endpoint}")
                except:
                    pass

            except:
                pass

        return working_endpoints

    def check_connection(self):
        """Check if the FritzBox is reachable with retry logic"""
        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)  # Increased timeout for production
                result = sock.connect_ex((self.host, self.port))
                sock.close()

                if result == 0:
                    if attempt > 0:
                        log_info(
                            f"Connection successful on attempt {attempt + 1}")
                    return True
                else:
                    if attempt < max_retries - 1:
                        log_warning(
                            f"Connection attempt {attempt + 1} failed, retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff

            except Exception as e:
                log_error(f"Connection attempt {attempt + 1} error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2

        log_error(
            f"Failed to connect to {self.host}:{self.port} after {max_retries} attempts")
        return False
