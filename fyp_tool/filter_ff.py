import json
import os
from utils import fetch_data

TOTAL_SINGLE_FLUX = 0
TOTAL_NS_FLUX = 0
TOTAL_DOUBLE_FLUX = 0
TOTAL_NOT_FAST_FLUX = 0

def setup(id: int = 0, query_id: int = 2):
    """Fetch domain or status information from server."""
    queries = [
        f"domain?id={id}",               # Query 1: Basic domain info
        f"domain/details?id={id}",       # Query 2: Detailed domain info
        "db_status",                     # Query 3: Server status
    ]

    base_url = os.environ["SENTINELFLUX_API_URL"].rstrip("/")
    api_url = f"{base_url}/{queries[query_id - 1]}"

    try:
        return fetch_data(api_url)
    except Exception as e:
        print(f"Error fetching data (ID {id}): {e}")
        return None

def analyze_fast_flux(domain_data):
    """Classify domain as Single Flux, Name Server Flux, Double Flux, or Not Fast Flux."""
    a_records = domain_data.get("A_Records", [])
    a_ips = {record["ip"] for record in a_records}
    a_lowest_ttls = [record.get("lowest_ttl", record.get("ttl", 99999)) for record in a_records]

    unique_a_ip_count = len(a_ips)
    min_a_ttl = min(a_lowest_ttls, default=99999)

    ns_records = domain_data.get("NS_Records", [])
    ns_hostnames = [ns.get("nameserver") for ns in ns_records if ns.get("nameserver")]
    ns_ips = []
    ns_lowest_ttls = []

    for ns in ns_records:
        for ns_ip in ns.get("ns_ips", []):
            ns_ips.append(ns_ip.get("ip"))
            ns_lowest_ttls.append(ns_ip.get("lowest_ttl", ns_ip.get("ttl", 99999)))

    unique_ns_hostname_count = len(set(ns_hostnames))
    min_ns_ttl = min(ns_lowest_ttls, default=99999)

    is_single_flux = unique_a_ip_count >= 4 and min_a_ttl <= 1800
    is_ns_flux = unique_ns_hostname_count >= 4 and min_ns_ttl <= 1800

    if is_single_flux and is_ns_flux:
        global TOTAL_DOUBLE_FLUX
        TOTAL_DOUBLE_FLUX += 1
        return "Double Flux"
    elif is_single_flux:
        global TOTAL_SINGLE_FLUX
        TOTAL_SINGLE_FLUX += 1
        return "Single Flux"
    elif is_ns_flux:
        global TOTAL_NS_FLUX
        TOTAL_NS_FLUX += 1
        return "Name Server Flux"
    else:
        global TOTAL_NOT_FAST_FLUX
        TOTAL_NOT_FAST_FLUX += 1
        return "Not Fast Flux"

def filter_fast_flux(start_id: int, end_id: int, query_id: int = 2):
    """Fetch and analyze domains in a range, or return DB status if query 3 is selected."""
    
    if query_id == 3:
        # Only fetch and display DB status (no domain loop)
        response = setup(query_id=3)
        if response:
            print(json.dumps(response, indent=4))
        else:
            print("Failed to fetch DB status.")
        return

    results = []

    for domain_id in range(start_id, end_id + 1):
        print(f"Processing domain ID: {domain_id}")
        domain_data = setup(id=domain_id, query_id=query_id)

        if domain_data:
            domain_name = domain_data.get("domain_name", f"unknown_id_{domain_id}")
            flux_status = analyze_fast_flux(domain_data)

            result = {
                "domain_id": domain_id,
                "domain_name": domain_name,
                "fast_flux_status": flux_status
            }
            results.append(result)
        else:
            print(f"No data fetched for domain ID {domain_id}.")

    # Save result
    output_file = "fastflux_analysis_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)

    print(f"\nAnalysis complete. Results saved to: {output_file}")

def main():
    # Change this to switch between query modes
    # query_id = 1 (basic domain), 2 (detailed), 3 (DB status)
    query_id = 2

    if query_id == 3:
        filter_fast_flux(start_id=0, end_id=0, query_id=query_id)
    else:
        filter_fast_flux(start_id=7001, end_id=14876, query_id=query_id)
    #14876
    # Saved stats value in stats.txt
    global TOTAL_DOUBLE_FLUX
    global TOTAL_NOT_FAST_FLUX
    global TOTAL_SINGLE_FLUX
    global TOTAL_NS_FLUX
    with open("stats.txt", "w") as stats_file:
        stats_file.write(f"TOTAL_SINGLE_FLUX: {TOTAL_SINGLE_FLUX}\n")
        stats_file.write(f"TOTAL_NS_FLUX: {TOTAL_NS_FLUX}\n")
        stats_file.write(f"TOTAL_DOUBLE_FLUX: {TOTAL_DOUBLE_FLUX}\n")
        stats_file.write(f"TOTAL_NOT_FAST_FLUX: {TOTAL_NOT_FAST_FLUX}\n")

    print(f"TOTAL_SINGLE_FLUX: {TOTAL_SINGLE_FLUX}")
    print(f"TOTAL_NS_FLUX: {TOTAL_NS_FLUX}")
    print(f"TOTAL_DOUBLE_FLUX: {TOTAL_DOUBLE_FLUX}")
    print(f"TOTAL_NOT_FAST_FLUX: {TOTAL_NOT_FAST_FLUX}")

if __name__ == "__main__":
    main()