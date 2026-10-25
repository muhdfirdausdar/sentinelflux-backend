CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE EXTENSION IF NOT EXISTS timescaledb;

ALTER SEQUENCE _timescaledb_catalog.hypertable_id_seq RESTART WITH 1;

-- Drop tables to reset the schema. Error if tables not exist. Useful for testing db

DROP TABLE IF EXISTS domain_nameserver, fast_flux_analysis, nameserver_ip, ip_geolocation, domain_ip_malicious, domain_ip_connection, nameserver, ips, domain, sources, malicious_types, metrics_agg CASCADE;
DROP TABLE IF EXISTS history_domain;
DROP TABLE IF EXISTS history_ff_analysis;
DROP TABLE IF EXISTS history_dom_ip_conn;
DROP TABLE IF EXISTS history_dom_ns;
DROP TABLE IF EXISTS history_ns_ip;
DROP TABLE IF EXISTS history_geoip;
DROP TABLE IF EXISTS live_fast_flux_view;
DROP TABLE IF EXISTS user_request_data;
DROP TABLE IF EXISTS emailing_data;
DROP TABLE IF EXISTS domain_filter;
DROP TYPE IF EXISTS domain_status, fast_flux_type;

-- ENUM for domain status
CREATE TYPE domain_status AS ENUM ('active', 'inactive', 'unknown');

-- Malicious types lookup table
CREATE TABLE malicious_types (
	id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	name TEXT UNIQUE NOT NULL
);

-- Sources lookup table
CREATE TABLE sources (
	id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	name TEXT UNIQUE NOT NULL
);

-- Domain table
CREATE TABLE domain (
	id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	domain_name TEXT UNIQUE NOT NULL,
	first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	status domain_status NOT NULL,
	source_id BIGINT REFERENCES sources(id) ON DELETE SET NULL,
	last_ff_analysis TIMESTAMPTZ DEFAULT NULL,
	total_analysis_done INT DEFAULT 0,
	domain_analysis_type TEXT DEFAULT NULL,
	wait_to_ff_analysis BOOLEAN DEFAULT TRUE,
	is_unrated BOOLEAN DEFAULT FALSE,
	remarks VARCHAR(500)
);

CREATE TYPE fast_flux_type AS ENUM ('single', 'double', 'name', 'unknown');
CREATE TABLE fast_flux_analysis (
	id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	domain_id BIGINT REFERENCES domain(id) ON DELETE CASCADE,
	flux_type fast_flux_type NOT NULL,
	a_record_change_frequency INT NOT NULL,
	ns_record_change_frequency INT NOT NULL,
	detected_on TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	details JSONB DEFAULT '{}'::JSONB,
	UNIQUE (domain_id, flux_type)
);



-- IPs table
CREATE TABLE ips (
	id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	ip_address INET UNIQUE NOT NULL,
	first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Domain-IP Connection table
CREATE TABLE domain_ip_connection (
	id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	domain_id BIGINT REFERENCES domain(id) ON DELETE CASCADE NOT NULL,
	ip_id BIGINT REFERENCES ips(id) ON DELETE CASCADE NOT NULL,
	first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	ttl INT NOT NULL,
	lowest_ttl INT NOT NULL,
	lowest_ttl_time TIMESTAMPTZ NOT NULL,
	highest_ttl INT NOT NULL,
highest_ttl_time TIMESTAMPTZ NOT NULL,
	CONSTRAINT unique_domain_ip UNIQUE (domain_id, ip_id)
);



-- Malicious Domain-IP table
CREATE TABLE domain_ip_malicious (
domain_ip_id BIGINT NOT NULL REFERENCES domain_ip_connection(id) ON DELETE CASCADE,
    	malicious_type_id BIGINT NOT NULL REFERENCES malicious_types(id) ON DELETE CASCADE,
    	source_id BIGINT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    	first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    	last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    	PRIMARY KEY (domain_ip_id, malicious_type_id, source_id)
);

-- nameserver table
CREATE TABLE nameserver (
	id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	nameserver TEXT UNIQUE NOT NULL,
	remarks VARCHAR(500) -- Optional for additional notes
);



CREATE TABLE domain_nameserver (
	id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	domain_id BIGINT REFERENCES domain(id) ON DELETE SET NULL,
	nameserver_id BIGINT REFERENCES nameserver(id) ON DELETE SET NULL,
	first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	ttl INT NOT NULL,
	lowest_ttl INT NOT NULL,
	lowest_ttl_time TIMESTAMPTZ NOT NULL,
	highest_ttl INT NOT NULL,
    highest_ttl_time TIMESTAMPTZ NOT NULL,
	CONSTRAINT unique_domain_nameserver UNIQUE (domain_id, nameserver_id) 
);


-- Nameserver-IP mapping (A records)
CREATE TABLE nameserver_ip (
	id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	nameserver_id BIGINT REFERENCES nameserver(id) ON DELETE CASCADE NOT NULL,
	ip_id BIGINT REFERENCES ips(id) ON DELETE CASCADE NOT NULL,
	first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	ttl INT NOT NULL,
	lowest_ttl INT NOT NULL,
	lowest_ttl_time TIMESTAMPTZ NOT NULL,
	highest_ttl INT NOT NULL,
    highest_ttl_time TIMESTAMPTZ NOT NULL,
	CONSTRAINT unique_nameserver_ip UNIQUE (nameserver_id, ip_id)  -- Removed first_seen
);

-- IP Geolocation Table
CREATE TABLE ip_geolocation (
	id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	ip_id BIGINT REFERENCES ips(id) ON DELETE CASCADE NOT NULL,
	continent TEXT NOT NULL,
	country TEXT NOT NULL,
	latitude_longitude  TEXT NOT NULL,
	asn BIGINT NOT NULL,  
	aso TEXT NOT NULL,
	first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	CONSTRAINT unique_ip_geolocation UNIQUE (ip_id, asn, aso)  -- Removed first_seen
);


-- Metrics table for fast, frequent aggregation (updated every 30s)
CREATE TABLE IF NOT EXISTS metrics_agg (
    ts TIMESTAMPTZ NOT NULL DEFAULT NOW() PRIMARY KEY, -- aggregation timestamp (e.g., every 30s)
    dns_lookups INT DEFAULT 0,
    unique_domains INT DEFAULT 0,
    unique_ns INT DEFAULT 0,
    unique_ips INT DEFAULT 0,
    total_tasks INT DEFAULT 0,
    total_sources INT DEFAULT 0,
    unique_malicious_domains INT DEFAULT 0,
    unique_fastflux_domains INT DEFAULT 0,
    single_flux INT DEFAULT 0,
    name_flux INT DEFAULT 0,
    double_flux INT DEFAULT 0,
    domains_with_3_ips_change INT DEFAULT 0,
    domains_with_4_ips_change INT DEFAULT 0,
    domains_with_5_ips_change INT DEFAULT 0,
    -- Buffer metrics
    buffer_pending_tasks INT DEFAULT 0,
    buffer_active_tasks INT DEFAULT 0,
    buffer_registry_size INT DEFAULT 0,
    buffer_utilization_percent DECIMAL(5,2) DEFAULT 0.00
);

-- Indexing for performance
-- domain
CREATE INDEX domain_name_idx ON domain(domain_name);
CREATE INDEX domain_sourceid_idx ON domain(source_id);


-- ips
CREATE INDEX ips_idx ON ips(ip_address);
CREATE INDEX ips_firstseen_idx ON ips(first_seen);

-- domain_ip_malicious
CREATE INDEX mal_id_idx ON domain_ip_malicious(domain_ip_id);
CREATE INDEX mal_idsource_idx ON domain_ip_malicious(malicious_type_id, source_id);

-- nameserver
CREATE INDEX ns_idx ON nameserver(nameserver);

-- nameserver_ip
CREATE INDEX nsip_id_idx ON nameserver_ip(nameserver_id, ip_id);
CREATE INDEX nsip_ttl_idx ON nameserver_ip(ttl);
CREATE INDEX nsip_ttlow_idx ON nameserver_ip(lowest_ttl);
CREATE INDEX nsip_firstseen_idx ON nameserver_ip(first_seen);

-- domain_nameserver
CREATE INDEX domns_id_idx ON domain_nameserver(domain_id, nameserver_id);
CREATE INDEX domns_firstseen_idx ON domain_nameserver(first_seen);
CREATE INDEX domns_ttl_idx ON domain_nameserver(ttl);
CREATE INDEX domns_ttlow_idx ON domain_nameserver(lowest_ttl);

CREATE INDEX ipgeo_id_idx ON ip_geolocation(ip_id);
CREATE INDEX ipgeo_asn_idx ON ip_geolocation(asn);
CREATE INDEX ipgeo_multi_idx ON ip_geolocation(ip_id, asn, country, first_seen);

CREATE INDEX ff_analysis_domtypeff_idx ON fast_flux_analysis(domain_id, flux_type);


-- ================= Historical Time Series Tables =================

CREATE TABLE history_domain (
    domain_id BIGINT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status domain_status NOT NULL,
    remarks TEXT DEFAULT NULL,
    PRIMARY KEY (domain_id, updated_at)
);

CREATE TABLE history_ff_analysis (
	domain_id BIGINT NOT NULL,
	flux_type fast_flux_type NOT NULL,
	details JSONB DEFAULT '{}'::JSONB,
	a_record_change_frequency INT NOT NULL,
	ns_record_change_frequency INT NOT NULL,
	updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	PRIMARY KEY (domain_id, updated_at)
);

CREATE TABLE history_dom_ip_conn (
    domain_id BIGINT NOT NULL,
    ip_id BIGINT NOT NULL,
    ttl INT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (domain_id, ip_id, updated_at)
);

CREATE TABLE history_dom_ns (
    domain_id BIGINT NOT NULL,
    nameserver_id BIGINT NOT NULL,
    ttl INT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (domain_id, nameserver_id, updated_at)
);

CREATE TABLE history_ns_ip (
    ip_id BIGINT NOT NULL,
    nameserver_id BIGINT NOT NULL,
    ttl INT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (ip_id, nameserver_id, updated_at)
);

CREATE TABLE history_geoip (
    ip_id BIGINT NOT NULL,
    continent TEXT NOT NULL,
    country TEXT NOT NULL,
    latitude_longitude TEXT NOT NULL,
    asn BIGINT NOT NULL,
    aso TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (ip_id, updated_at)
);

-- Hypertable creation (for TimescaleDB)
SELECT create_hypertable('history_domain', 'updated_at', chunk_time_interval => interval '7 days');
SELECT create_hypertable('history_ff_analysis', 'updated_at', chunk_time_interval => interval '7 days');
SELECT create_hypertable('history_dom_ip_conn', 'updated_at', chunk_time_interval => interval '7 days');
SELECT create_hypertable('history_dom_ns', 'updated_at', chunk_time_interval => interval '7 days');
SELECT create_hypertable('history_ns_ip', 'updated_at', chunk_time_interval => interval '7 days');
SELECT create_hypertable('history_geoip', 'updated_at', chunk_time_interval => interval '7 days');

-- Indexes for historical tables
CREATE INDEX idx_hist_domain_id_time ON history_domain(domain_id, updated_at);
CREATE INDEX idx_hist_ff_domain_time ON history_ff_analysis(domain_id, updated_at);
CREATE INDEX idx_hist_ff_type_time ON history_ff_analysis(flux_type, updated_at);
CREATE INDEX idx_hist_domip_domip_time ON history_dom_ip_conn(domain_id, ip_id, updated_at);
CREATE INDEX idx_hist_domns_domns_time ON history_dom_ns(domain_id, nameserver_id, updated_at);
CREATE INDEX idx_hist_nsip_nsip_time ON history_ns_ip(ip_id, nameserver_id, updated_at);
CREATE INDEX idx_hist_geoip_ip_time ON history_geoip(ip_id, updated_at);


-- Other

CREATE TABLE live_fast_flux_view (
  domain_id BIGINT PRIMARY KEY REFERENCES domain(id) ON DELETE CASCADE,
  flux_type fast_flux_type NOT NULL,
  last_active TIMESTAMP NOT NULL DEFAULT NOW(),
  total_ips INT NOT NULL DEFAULT 0,
  geojson JSONB NOT NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- geojson structure example:
-- {
--   "192.168.1.10": {
--     "last_active": "2025-10-12T06:30:00Z",
--     "latitude": 3.139,
--     "longitude": 101.6869,
--     "country": "Malaysia"
--   },
--   "172.67.23.45": {
--     "last_active": "2025-10-11T21:00:00Z",
--     "latitude": 37.751,
--     "longitude": -97.822,
--     "country": "United States"
--   }
-- }



CREATE TABLE user_request_data (
    task_id UUID NOT NULL,
    end_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    run_number INT NOT NULL,
    raw_data JSONB NOT NULL,
    UNIQUE(task_id, end_time)
);

CREATE TABLE emailing_data (
	id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    email TEXT NOT NULL,
	send_type TEXT NOT NULL,
	is_done BOOLEAN NOT NULL DEFAULT FALSE,
	requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	body_data JSONB NOT NULL,
	status TEXT DEFAULT NULL
);

CREATE TABLE domain_filter (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    domain_name TEXT UNIQUE NOT NULL
);

CREATE INDEX idx_domain_lookup_name ON domain_filter(domain_name);