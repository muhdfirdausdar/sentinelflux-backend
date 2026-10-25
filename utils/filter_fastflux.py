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
        return "Double Flux"
    elif is_single_flux:
        return "Single Flux"
    elif is_ns_flux:
        return "Name Server Flux"
    else:
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
async def reset_sequences(session: AsyncSession):
    tables_with_sequences = [
        ("domain", "domain_id_seq"),
        ("ips", "ips_id_seq"),
        ("domain_ip_connection", "domain_ip_connection_id_seq"),
        ("ip_geolocation", "ip_geolocation_id_seq"),
        ("domain_ip_malicious", "domain_ip_malicious_id_seq"),
        ("nameserver", "nameserver_id_seq"),
        ("domain_nameserver", "domain_nameserver_id_seq"),
        ("nameserver_ip", "nameserver_ip_id_seq"),
        ("malicious_types", "malicious_types_id_seq"),
        ("sources", "sources_id_seq"),
    ]

    for table, sequence in tables_with_sequences:
        query = text(f"""
        SELECT setval('{sequence}', COALESCE((SELECT MAX(id) FROM {table}), 1), true);
        """)
        await session.execute(query)

async def process_json_files(tar_gz_path: str):
    # Create a temporary directory to extract the tar.gz file
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract the tar.gz file
        with tarfile.open(tar_gz_path, "r:gz") as tar:
            tar.extractall(path=temp_dir)

        # Walk through the extracted directory to find all JSON files
        async with sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)() as session:
            try:
                for root, _, files in os.walk(temp_dir):
                    for file_name in files:
                        if file_name.endswith(".json"):
                            file_path = os.path.join(root, file_name)
                            print(f"Processing file: {file_path}")

                            # Check if the file is empty
                            if os.path.getsize(file_path) == 0:
                                print(f"Skipping empty file: {file_path}")
                                continue

                            # Read and parse the JSON file
                            with open(file_path, "r") as f:
                                try:
                                    data = json.load(f)
                                except json.JSONDecodeError as e:
                                    print(f"Invalid JSON in file {file_path}: {e}")
                                    continue

                                # Process each domain in the JSON data
                                for domain, info in data.items():
                                    await insert_domain_data(session, domain, info)

                await session.commit()
            except Exception as e:
                await session.rollback()
                print(f"Error occurred: {e}")
                #trace which line causing it

                traceback.print_exc()


            finally:
                # Reset sequences regardless of success or failure
                await reset_sequences(session)
                await session.commit()