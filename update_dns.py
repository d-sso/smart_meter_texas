import requests
import os
import dns.resolver
import urllib3

urllib3.disable_warnings()

def get_api_key():
    api_key_path = os.path.join(os.path.dirname(__file__), "api_key")
    with open(api_key_path, "r") as f:
        return f.read().strip()

def resolve_ips(hostname, dns_server="8.8.8.8"):
    resolver = dns.resolver.Resolver()
    resolver.nameservers = [dns_server]
    answers = resolver.resolve(hostname, 'A')
    return [str(rdata) for rdata in answers]

def get_dns_entries(session, UNIFI_API_URL):
    resp = session.get(UNIFI_API_URL, verify=False)
    resp.raise_for_status()
    return resp.json()

def add_dns_entry(session, UNIFI_API_URL, hostname, ip):
    resp = session.post(
        UNIFI_API_URL,
        json={"key": hostname, "value": ip, "record_type": "A", "enabled": True},
        verify=False
    )
    resp.raise_for_status()

def sync_dns_record(api_key, base_unifi_url, logger, lookup_hostname="smartmetertexas.com", target_hostname="www.smartmetertexas.com"):
    UNIFI_API_URL = f"{base_unifi_url}/proxy/network/v2/api/site/default/static-dns/"
    try:
        ips = resolve_ips(lookup_hostname)

        session = requests.Session()
        session.headers.update({"X-API-KEY": f"{api_key}"})

        entries = get_dns_entries(session, UNIFI_API_URL)

        # Find existing entries for target_hostname
        existing = [e for e in entries if e.get("key") == target_hostname]

        # Remove existing entries
        for e in existing:
            logger.info(f"Removing existing DNS entry: {e['key']} -> {e['value']}")
            session.delete(f"{UNIFI_API_URL}/{e['_id']}", verify=False)

        # Add entries
        for ip in ips:
            logger.info(f"Adding DNS entry: {target_hostname} -> {ip}")
            add_dns_entry(session,UNIFI_API_URL, target_hostname, ip)

    except requests.RequestException as e:
        logger.error(f"Error updating DNS records: {e}")
    except dns.resolver.NoAnswer as e:
        logger.error(f"DNS resolution failed for {lookup_hostname}: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    print("Not supported")
