"""
DNS Data Formatter
Transforms raw DNS task data into human-readable dig-style format
"""

from typing import Dict, Any, Optional
from datetime import datetime


def format_dns_data(raw_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Transform raw DNS task data into a human-readable dig-style format.
    
    Args:
        raw_data: Raw dictionary containing DNS task results from DNFlux
        
    Returns:
        Dictionary with single key "formatted_output" containing the formatted text
        
    Example Input:
        {
            "data": {
                "example.com": {
                    "status": "NOERROR",
                    "task_id": "e56a310a-8a92-476a-80a0-210c6f34fc59",
                    "timestamp": "2025-11-08 05:11:59.599004+0000",
                    "dig_info": {
                        "A_Records": [...],
                        "NS_Records": [...]
                    },
                    "minute_dig_every": 2,
                    ...
                }
            }
        }
    
    Example Output:
        {
            "formatted_output": "; <<>> Timestamp: 2025-11-08 05:11:59 UTC <<>> example.com\n..."
        }
    """
    try:
        # Extract the main data
        data = raw_data.get("data", {})
        
        if not data:
            return {"formatted_output": "Error: No data found in response"}
        
        # Get the first (and likely only) domain from the data
        domain_name = list(data.keys())[0] if data else "unknown"
        domain_data = data.get(domain_name, {})
        
        # Extract key information
        status = domain_data.get("status", "UNKNOWN")
        task_id = domain_data.get("task_id", "unknown")
        timestamp = domain_data.get("timestamp", "unknown")
        minute_dig_every = domain_data.get("minute_dig_every", "unknown")
        dig_info = domain_data.get("dig_info", {})
        
        # Format timestamp (remove microseconds and format timezone)
        formatted_timestamp = _format_timestamp(timestamp)
        
        # Build the formatted output
        output_lines = []
        
        # Header section
        output_lines.append(f"; <<>> Timestamp: {formatted_timestamp} <<>> {domain_name}")
        output_lines.append(f";; Status: {status}")
        output_lines.append(f";; Timestamp: {formatted_timestamp}")
        output_lines.append(f";; Task ID: {task_id}")
        output_lines.append(f";; Run Interval: {minute_dig_every} minute(s)")
        output_lines.append("")
        
        # A Records section
        a_records = dig_info.get("A_Records", [])
        if a_records:
            output_lines.append(";; ANSWER SECTION (A Records)")
            for record in a_records:
                ip = record.get("ip", "unknown")
                ttl = record.get("ttl", 0)
                asn = record.get("asn", "unknown")
                aso = record.get("aso", "unknown")
                country = record.get("country", "unknown")
                continent = record.get("continent", "unknown")
                lat_lon = record.get("latitude_longitude", "unknown")
                
                output_lines.append(f"{domain_name}.       {ttl}   IN   A   {ip}")
                output_lines.append(f"                   → ASN: {asn} ({aso})")
                output_lines.append(f"                   → Location: {country} ({continent})")
                output_lines.append(f"                   → Coordinates: {lat_lon}")
                output_lines.append("")
        
        # NS Records section
        ns_records = dig_info.get("NS_Records", [])
        if ns_records:
            output_lines.append(";; NAMESERVER SECTION")
            for ns in ns_records:
                nameserver = ns.get("nameserver", "unknown")
                ttl = ns.get("ttl", 0)
                ns_ips = ns.get("ns_ips", [])
                
                output_lines.append(f"{nameserver}.   {ttl}   IN   NS")
                
                for ns_ip in ns_ips:
                    ip = ns_ip.get("ip", "unknown")
                    asn = ns_ip.get("asn", "unknown")
                    aso = ns_ip.get("aso", "unknown")
                    country = ns_ip.get("country", "unknown")
                    continent = ns_ip.get("continent", "unknown")
                    lat_lon = ns_ip.get("latitude_longitude", "unknown")
                    
                    output_lines.append(f"                     ↳ IP: {ip}")
                    output_lines.append(f"                     → ASN: {asn} ({aso})")
                    output_lines.append(f"                     → Location: {country} ({continent})")
                    output_lines.append(f"                     → Coordinates: {lat_lon}")
                
                output_lines.append("")
        
        # Join all lines with explicit newline characters for client transmission
        formatted_output = "\\n".join(output_lines)
        
        return {"formatted_output": formatted_output}
    
    except Exception as e:
        return {"formatted_output": f"Error formatting DNS data: {str(e)}"}


def _format_timestamp(timestamp: str) -> str:
    """
    Format timestamp string to readable format.
    
    Args:
        timestamp: Timestamp string in format "YYYY-MM-DD HH:MM:SS.ffffff+0000"
        
    Returns:
        Formatted timestamp string "YYYY-MM-DD HH:MM:SS UTC"
    """
    if not timestamp or timestamp == "unknown":
        return "unknown"
    
    try:
        # Remove microseconds and timezone info
        if "." in timestamp:
            timestamp = timestamp.split(".")[0]
        
        # Remove timezone offset
        if "+" in timestamp:
            timestamp = timestamp.split("+")[0]
        
        # Add UTC suffix
        return f"{timestamp} UTC"
    
    except Exception:
        return timestamp


# ; <<>> Timestamp: 2025-11-08 05:11:59 UTC <<>> example.com
# ;; Status: NOERROR
# ;; Timestamp: 2025-11-08 05:11:59 UTC
# ;; Task ID: e56a310a-8a92-476a-80a0-210c6f34fc59
# ;; Run Interval: 2 minute(s)

# ;; ANSWER SECTION (A Records)
# example.com.       300   IN   A   23.192.228.80
#                    → ASN: AS20940 (Akamai International B.V.)
#                    → Location: United States of America (North America)
#                    → Coordinates: 37.339390, -121.894958

# example.com.       300   IN   A   23.215.0.138
#                    → ASN: AS20940 (Akamai International B.V.)
#                    → Location: United States of America (North America)
#                    → Coordinates: 39.039474, -77.491806

# example.com.       300   IN   A   23.220.75.245
#                    → ASN: AS20940 (Akamai International B.V.)
#                    → Location: United States of America (North America)
#                    → Coordinates: 34.052570, -118.243904

# ;; NAMESERVER SECTION
# a.iana-servers.net.   86400   IN   NS
#                      ↳ IP: 199.43.135.53
#                      → ASN: AS26710 (ICANN)
#                      → Location: United States of America (North America)
#                      → Coordinates: 38.895390, -77.039474

# b.iana-servers.net.   86400   IN   NS
#                      ↳ IP: 199.43.133.53
#                      → ASN: AS26710 (ICANN)
#                      → Location: United States of America (North America)
#                      → Coordinates: 38.881008, -77.104279

